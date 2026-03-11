from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.graph.state import ResearchState
from dotenv import load_dotenv
import os
from src.config import LLM_PRO

load_dotenv()


def _strip_to_float(v) -> float | None:
    """Convert formatted values like '$373.31B' or '18.03%' to a raw float."""
    try:
        s = str(v).replace("$", "").replace(",", "").replace("%", "").strip()
        mult = 1
        if s.endswith("T"):   mult = 1_000_000_000_000; s = s[:-1]
        elif s.endswith("B"): mult = 1_000_000_000;     s = s[:-1]
        elif s.endswith("M"): mult = 1_000_000;         s = s[:-1]
        return float(s) * mult
    except Exception:
        return None


def risk_scorer_agent(state: ResearchState) -> dict:
    """
    Uses Gemini to classify risk factors from all gathered data.
    Reads:  news_results, filing_excerpt, financial_data
    Writes: risk_assessment
    """
    print(f"⚠️  RiskScorer: analyzing risks for {state['ticker']}...")

    llm = ChatGoogleGenerativeAI(
        model=LLM_PRO,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2
    ).with_config({"run_name": "RiskScorer_LLM"})

    # ── News summary ──────────────────────────────────────────────────────────
    news_summary = ""
    for item in (state.get("news_results") or [])[:3]:
        news_summary += f"- {item['title']}\n"
    if not news_summary:
        news_summary = "No recent news available"

    # ── Financial flags ───────────────────────────────────────────────────────
    fin_data        = state.get("financial_data") or {}
    flags           = fin_data.get("analyst_flags", [])
    financial_flags = "\n".join(flags) if flags else "No major flags detected"

    # ── Pull metrics (corrected key names) ────────────────────────────────────
    pe_ratio         = fin_data.get("pe_ratio",          "N/A")
    forward_pe       = fin_data.get("forward_pe",         "N/A")
    gross_margin     = fin_data.get("gross_margin",       "N/A")
    operating_margin = fin_data.get("operating_margin",   "N/A")
    net_margin       = fin_data.get("net_margin",         "N/A")
    revenue_growth   = fin_data.get("revenue_growth",     "N/A")
    earnings_growth  = fin_data.get("earnings_growth",    "N/A")
    current_ratio    = fin_data.get("current_ratio",      "N/A")
    debt_to_equity   = fin_data.get("debt_to_equity",     "N/A")
    roe              = fin_data.get("roe",                "N/A")
    total_debt       = fin_data.get("total_debt",         "N/A")
    cash             = fin_data.get("cash",               "N/A")
    net_income       = fin_data.get("net_income",         "N/A")

    # ── Pre-compute ratios so Gemini can't ignore them ────────────────────────
    # This is the key fix for BRK-B type companies: give Gemini the ratios
    # as explicit numbers rather than letting it reason from raw absolutes.
    precomputed = []
    try:
        cash_f = _strip_to_float(cash)
        debt_f = _strip_to_float(total_debt)
        ni_f   = _strip_to_float(net_income)

        if cash_f is not None and debt_f is not None and debt_f > 0:
            ratio = cash_f / debt_f
            label = "cash EXCEEDS debt — net cash positive" if ratio > 1 else "debt exceeds cash"
            precomputed.append(f"Cash/Debt ratio = {ratio:.2f}x ({label})")

        if debt_f is not None and ni_f is not None and ni_f > 0:
            precomputed.append(f"Debt/NetIncome ratio = {debt_f / ni_f:.2f}x")

        if ni_f is not None and cash_f is not None and debt_f is not None:
            net_cash = cash_f - debt_f
            if net_cash > 0:
                precomputed.append(
                    f"Net cash position = ${net_cash/1e9:.2f}B (cash minus all debt)")

    except Exception:
        pass

    precomputed_block = ""
    if precomputed:
        precomputed_block = "\nPRE-COMPUTED RATIOS (treat these as facts, do not recalculate):\n"
        precomputed_block += "\n".join(f"- {p}" for p in precomputed)

    filing_snippet = (state.get("filing_excerpt") or "")[:1500]

    prompt = f"""You are a senior risk analyst at a top-tier investment bank.
Analyze {state['company_name']} ({state['ticker']}) using the data below.

KEY FINANCIAL METRICS:
- Gross Margin:      {gross_margin}
- Operating Margin:  {operating_margin}
- Net Margin:        {net_margin}
- Revenue Growth:    {revenue_growth}
- Earnings Growth:   {earnings_growth}
- Net Income:        {net_income}
- P/E Ratio:         {pe_ratio}
- Forward P/E:       {forward_pe}
- Current Ratio:     {current_ratio}
- Debt/Equity:       {debt_to_equity}
- Return on Equity:  {roe}
- Total Debt:        {total_debt}
- Cash:              {cash}
{precomputed_block}

ANALYST FLAGS FROM QUANTITATIVE SCREENING:
{financial_flags}

RECENT NEWS HEADLINES:
{news_summary}

SEC 10-K RISK FACTORS & MD&A (filing date: {state.get('filing_date', 'N/A')}):
{filing_snippet}

---
SCORING RULES — read all rules before scoring:

Score 1–2 (VERY LOW):
  - Gross margin >50%, net margin >20%, earnings growth >15%
  - Current ratio >2.0, minimal debt, zero analyst flags
  - Example: cash-rich software with dominant market position

Score 3–4 (LOW):
  - Good margins (gross >30%, net >10%), positive earnings growth
  - Current ratio >1.5, manageable debt, 0–1 minor flags
  - Example: established blue-chip, steady compounder

Score 5–6 (MEDIUM):
  - Mixed signals — some strong metrics offset by real concerns
  - Current ratio 1.0–1.5, moderate leverage, 1–2 flags
  - Example: profitable company with moderate debt or slowing growth

Score 7–8 (HIGH):
  - ANY ONE of these triggers a HIGH score:
    * Negative revenue growth AND thin margins (operating <10%)
    * Earnings growth below -20%
    * P/E ratio is N/A due to losses (company not profitable)
    * Very high leverage (D/E >200%) with weak earnings
    * Multiple analyst flags with deteriorating fundamentals
  - Example: turnaround story, declining business, margin collapse

Score 9–10 (VERY HIGH):
  - Earnings growth below -50%, near-insolvency signals
  - Current ratio <0.7, extreme leverage, existential risk
  - Example: company facing bankruptcy or regulatory shutdown

CRITICAL OVERRIDES — these rules are absolute and override everything above:
1. A healthy current ratio does NOT cancel out negative revenue growth or
   collapsed earnings. Score on the WORST metrics, not the average.
2. If P/E is N/A and revenue is declining, the company is likely losing money.
   This is HIGH risk (7–8), not MEDIUM.
3. If Cash/Debt ratio > 1.0 (see pre-computed above), debt is NOT a risk
   factor at all. The company has more cash than debt. Do not cite debt as a risk.
4. If Debt/NetIncome < 2.0x (see pre-computed above), debt is LOW risk.
   Do not cite it as a primary risk factor.
5. If operating margin is below 10% AND revenue growth is negative, minimum score is 7.
6. Revenue decline smaller than -5% with net margin >15% is NOT a risk trigger.
   Sub-5% fluctuations for large profitable conglomerates/insurers are normal.
   Only cite revenue decline as a risk if it exceeds -5% OR margins are below 10%.
7. HARD CEILING: A company with ALL THREE of the following gets a MAXIMUM score
   of 4/10 (LOW) — no exceptions:
     * Net income > $20B
     * Current ratio > 2.5
     * Cash/Debt ratio > 1.0 (cash exceeds total debt)
   These three together signal financial fortress status.
8. Do NOT default to 5/10 or 6/10. Apply the rules above mechanically.

CALIBRATION EXAMPLES (anchor your score here):
- Berkshire Hathaway ($67B net income, $373B cash > $135B debt, CR 7.07) → 3/10 LOW
- Visa (97% gross margin, strong earnings growth, stable) → 3/10 LOW
- Apple (47% gross, minor liquidity flag, solid growth) → 5/10 MEDIUM
- AMD (52% gross, +217% earnings, high P/E) → 5/10 MEDIUM
- Intel (negative revenue, 5% op margin, no P/E, turnaround) → 7/10 HIGH
- UnitedHealth (-99% earnings, current ratio <0.8) → 8/10 HIGH

Respond in EXACTLY this format with no extra text before or after:

OVERALL RISK LEVEL: [LOW / MEDIUM / HIGH / VERY HIGH]

TOP RISKS:
1. [Risk name]: [One precise sentence referencing actual numbers from the data]
2. [Risk name]: [One precise sentence referencing actual numbers from the data]
3. [Risk name]: [One precise sentence referencing actual numbers from the data]

KEY MITIGATING FACTOR:
[One sentence citing the single strongest reason this company can absorb these risks]

RISK SCORE: [X]/10"""

    try:
        response  = llm.invoke([HumanMessage(content=prompt)])
        risk_text = response.content

        # Log token usage
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            if isinstance(usage, dict):
                input_tokens  = usage.get('input_tokens') or usage.get('prompt_token_count', 0)
                output_tokens = usage.get('output_tokens') or usage.get('candidates_token_count', 0)
            else:
                input_tokens  = getattr(usage, 'input_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', 0)
            print(f"   Tokens — in: {input_tokens} out: {output_tokens}")

        print(f"   ✅ Risk assessment complete for {state['ticker']}")
        return {
            "risk_assessment": risk_text,
            "errors": state.get("errors") or []
        }

    except Exception as e:
        print(f"   ❌ RiskScorer failed: {e}")
        return {
            "risk_assessment": "Risk assessment unavailable",
            "errors": (state.get("errors") or []) + [f"RiskScorer: {str(e)}"]
        }
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.graph.state import ResearchState
from dotenv import load_dotenv
import os
from src.config import LLM_PRO

load_dotenv()


def writer_agent(state: ResearchState) -> dict:
    """
    Synthesizes all research into a structured investment memo.
    Reads:  financial_data, risk_assessment, valuation_result, news, filing
    Writes: investment_memo
    """
    print(f"✍️  Writer: composing investment memo for {state['ticker']}...")

    llm = ChatGoogleGenerativeAI(
        model=LLM_PRO,
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3
    ).with_config({"run_name": "Writer_LLM"})

    fin  = state.get("financial_data")   or {}
    news = state.get("news_results")     or []
    vr   = state.get("valuation_result") or {}

    news_titles = "\n".join([f"- {n['title']}" for n in news[:5]])

    # ── Round raw floats BEFORE feeding into prompt ───────────────────────────
    def fmt(key, decimals=2):
        v = fin.get(key, "N/A")
        if v is None or v == "N/A" or v == "":
            return "N/A"
        try:
            return f"{float(str(v).replace(',', '')):.{decimals}f}"
        except Exception:
            return str(v)

    # ── Format valuation block for prompt ─────────────────────────────────────
    if vr:
        model_lines = "\n".join(
            f"  - {m['name']} (weight {int(m['weight']*100)}%): "
            f"${m['fair_value']} | {m['upside_pct']:+.1f}% | {m['key_assumption']}"
            for m in vr.get("models", [])
        )
        vr_range = vr.get("valuation_range", ("N/A", "N/A"))
        valuation_block = f"""MULTI-MODEL VALUATION:
- Model type:          {vr.get('model_type', 'N/A')}
- Weighted fair value: ${vr.get('weighted_fair_value', 'N/A')}
- Current price:       ${vr.get('current_price', 'N/A')}
- Upside / downside:   {vr.get('upside_pct', 0):+.1f}%
- Valuation range:     ${vr_range[0]} – ${vr_range[1]}
- Verdict:             {vr.get('verdict', 'N/A')}
Individual models:
{model_lines}"""
    else:
        valuation_block = "MULTI-MODEL VALUATION: Insufficient data for quantitative valuation."

    prompt = f"""You are a senior equity research analyst at Goldman Sachs.
Write a professional, data-driven investment memo for {state['company_name']} ({state['ticker']}).

ALL DATA FOR THIS MEMO:

FINANCIALS (from Yahoo Finance):
- Revenue (TTM):        {fin.get('revenue_ttm',       'N/A')}
- Gross Profit:         {fin.get('gross_profit',       'N/A')}
- Net Income:           {fin.get('net_income',         'N/A')}
- EBITDA:               {fin.get('ebitda',             'N/A')}
- Gross Margin:         {fin.get('gross_margin',       'N/A')}
- Operating Margin:     {fin.get('operating_margin',   'N/A')}
- Net Margin:           {fin.get('net_margin',         'N/A')}
- P/E Ratio:            {fmt('pe_ratio')}
- Forward P/E:          {fmt('forward_pe')}
- EV/EBITDA:            {fin.get('ev_ebitda',          'N/A')}
- Revenue Growth YoY:   {fin.get('revenue_growth',     'N/A')}
- Earnings Growth YoY:  {fin.get('earnings_growth',    'N/A')}
- Total Debt:           {fin.get('total_debt',         'N/A')}
- Cash:                 {fin.get('cash',               'N/A')}
- Debt/Equity:          {fmt('debt_to_equity')}
- Return on Equity:     {fin.get('roe',                'N/A')}
- Current Ratio:        {fmt('current_ratio')}
- Analyst Consensus:    {str(fin.get('analyst_recommendation', 'N/A')).upper()}
- Analyst Price Target: ${fin.get('target_price',      'N/A')}
- Number of Analysts:   {fin.get('number_of_analysts', 'N/A')}
- Analyst Flags:        {', '.join(fin.get('analyst_flags', [])) or 'None'}

RECENT NEWS:
{news_titles}

RISK ASSESSMENT:
{state.get('risk_assessment', 'N/A')}

{valuation_block}

10-K FILING DATE: {state.get('filing_date', 'N/A')}
10-K KEY SECTIONS:
{(state.get('filing_excerpt') or '')[:1000]}

Write the memo with EXACTLY these sections. Be specific — cite actual numbers.
Never write vague sentences like "strong performance" without a number behind it.
When citing numbers, use the EXACT rounded values provided above — do not add extra decimal places.

## Executive Summary
[3-4 sentences: what the company does, headline financial performance, overall stance]

## Financial Highlights
[6-8 bullet points with specific numbers — revenue, margins, growth, valuation multiples]

## Recent Developments
[3-4 sentences on what the news tells us about current momentum]

## Risk Factors
[3 numbered risks, each with the specific data point that flags it]

## Valuation Analysis
[Use the multi-model valuation data above. Explain which model type was selected and why it fits this company.
State the weighted fair value, valuation range, and what each individual model implies.
Be specific about key assumptions — WACC, multiples, growth rates used.
End with the verdict: UNDERVALUED / FAIRLY VALUED / OVERVALUED with 1-sentence justification.]

## Investment Recommendation
[Final BUY / HOLD / SELL with price target, upside from current price of ${fmt('current_price')},
and a 2-sentence conviction statement tying together the risk score and valuation verdict.]

Tone: precise, institutional, zero fluff. Every claim must have a number."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        memo = response.content

        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            if isinstance(usage, dict):
                input_tokens  = usage.get('input_tokens') or usage.get('prompt_token_count', 0)
                output_tokens = usage.get('output_tokens') or usage.get('candidates_token_count', 0)
            else:
                input_tokens  = getattr(usage, 'input_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', 0)
            print(f"   Tokens — in: {input_tokens} out: {output_tokens}")

        print(f"   Memo written ({len(memo)} chars)")
        return {"investment_memo": memo}

    except Exception as e:
        print(f"   ❌ Writer failed: {e}")
        return {
            "investment_memo": "Memo generation failed",
            "errors": (state.get("errors") or []) + [f"Writer: {str(e)}"]
        }
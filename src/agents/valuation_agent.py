"""
valuation_agent.py
──────────────────
Multi-model valuation agent that selects and weights the right models
based on company type (sector, profitability, growth rate).

Model selection logic (mirrors real Wall Street practice):
  Banks / Insurance    → P/B (60%) + P/E Comps (40%)
  Energy / Cyclical    → EV/EBITDA (50%) + DCF (30%) + P/E (20%)
  High-growth / unprofitable → Revenue Multiple (60%) + DCF (40%)
  Stable profitable    → DCF (50%) + EV/EBITDA (30%) + P/E (20%)

Final output (valuation_result dict):
  model_type          — which regime was selected
  models              — list of {name, fair_value, weight, key_assumption}
  weighted_fair_value — weighted average fair value per share
  current_price       — live price for reference
  upside_pct          — upside to weighted fair value
  valuation_range     — (low, high) across all models
  verdict             — UNDERVALUED / FAIRLY VALUED / OVERVALUED
  summary             — one paragraph for the memo
"""

from src.graph.state import ResearchState


# ── Constants ─────────────────────────────────────────────────────────────────
RISK_FREE_RATE   = 0.043   # 10-yr US Treasury (Mar 2026)
EQUITY_RISK_PREM = 0.055   # Historical US ERP
DEFAULT_BETA     = 1.1


# ── WACC ──────────────────────────────────────────────────────────────────────
def compute_wacc(beta, debt, equity_mktcap, tax_rate=0.21, cost_of_debt=0.05):
    re    = RISK_FREE_RATE + beta * EQUITY_RISK_PREM
    total = debt + equity_mktcap
    if total == 0:
        return re
    wacc = (equity_mktcap / total) * re + (debt / total) * cost_of_debt * (1 - tax_rate)
    return max(wacc, 0.06)   # floor at 6%


# ── Money string parser (shared by all models) ────────────────────────────────
def parse_money(s) -> float:
    """'$90.51B' → 90510000000.0   |   raw float → float"""
    try:
        if s is None or s == "N/A":
            return 0.0
        if isinstance(s, (int, float)):
            return float(s)
        s = str(s).replace("$", "").replace(",", "").strip()
        if s.endswith("T"):
            return float(s[:-1]) * 1e12
        if s.endswith("B"):
            return float(s[:-1]) * 1e9
        if s.endswith("M"):
            return float(s[:-1]) * 1e6
        return float(s)
    except Exception:
        return 0.0


def parse_pct(s) -> float:
    """'15.70%' → 0.1570"""
    try:
        if isinstance(s, (int, float)):
            v = float(s)
            return v / 100 if v > 1 else v
        if isinstance(s, str) and "%" in s:
            return float(s.replace("%", "").strip()) / 100
        return 0.08
    except Exception:
        return 0.08


# ── Individual models ─────────────────────────────────────────────────────────

def model_dcf(fin: dict) -> dict | None:
    """5-year DCF on Free Cash Flow, CAPM WACC, 3% terminal growth."""
    try:
        fcf    = fin.get("free_cash_flow")
        shares = fin.get("shares_outstanding")
        price  = fin.get("current_price")
        beta   = float(fin.get("beta") or DEFAULT_BETA)

        if not fcf or not shares or not price:
            return None

        fcf    = float(fcf)
        shares = float(shares)
        price  = float(price)

        growth  = max(0.05, min(0.35, parse_pct(fin.get("revenue_growth", "8%"))))
        debt    = parse_money(fin.get("total_debt"))
        cash    = parse_money(fin.get("cash"))
        wacc    = compute_wacc(beta, debt, price * shares)
        tg      = 0.03   # terminal growth

        # Project & discount FCFs
        pv_fcfs = sum(fcf * (1 + growth) ** yr / (1 + wacc) ** yr
                      for yr in range(1, 6))

        # Terminal value
        fcf_yr5   = fcf * (1 + growth) ** 5
        term_val  = fcf_yr5 * (1 + tg) / (wacc - tg)
        pv_term   = term_val / (1 + wacc) ** 5

        eq_value  = pv_fcfs + pv_term - debt + cash
        fv        = eq_value / shares

        if fv <= 0 or fv > price * 10:
            return None

        return {
            "name":           "DCF (Free Cash Flow)",
            "fair_value":     round(fv, 2),
            "upside_pct":     round((fv - price) / price * 100, 1),
            "key_assumption": f"WACC {wacc*100:.1f}%, FCF growth {growth*100:.0f}%/yr, 3% terminal",
        }
    except Exception as e:
        print(f"   ⚠️  DCF failed: {e}")
        return None


def model_ev_ebitda(fin: dict, sector_mult: float = 15.0) -> dict | None:
    """Fair EV = EBITDA × sector multiple → equity value per share."""
    try:
        ebitda = fin.get("ebitda_raw")
        shares = fin.get("shares_outstanding")
        price  = fin.get("current_price")

        if not ebitda or ebitda <= 0 or not shares or not price:
            return None

        debt   = parse_money(fin.get("total_debt"))
        cash   = parse_money(fin.get("cash"))
        fv     = (float(ebitda) * sector_mult - debt + cash) / float(shares)
        price  = float(price)

        if fv <= 0 or fv > price * 10:
            return None

        return {
            "name":           "EV/EBITDA Comps",
            "fair_value":     round(fv, 2),
            "upside_pct":     round((fv - price) / price * 100, 1),
            "key_assumption": f"{sector_mult}x EBITDA sector multiple",
        }
    except Exception as e:
        print(f"   ⚠️  EV/EBITDA failed: {e}")
        return None


def model_pe_comps(fin: dict, sector_pe: float = 22.0) -> dict | None:
    """EPS × sector P/E. EPS estimated from operating margin × revenue × (1-tax)."""
    try:
        rev    = fin.get("total_revenue_raw")
        shares = fin.get("shares_outstanding")
        price  = fin.get("current_price")

        if not rev or not shares or not price:
            return None

        op_margin = parse_pct(fin.get("operating_margin", "15%"))
        eps       = float(rev) * op_margin * 0.72 / float(shares)   # 28% effective tax

        if eps <= 0:
            return None

        fv    = eps * sector_pe
        price = float(price)

        if fv <= 0 or fv > price * 10:
            return None

        return {
            "name":           "P/E Comps",
            "fair_value":     round(fv, 2),
            "upside_pct":     round((fv - price) / price * 100, 1),
            "key_assumption": f"{sector_pe}x forward P/E sector multiple",
        }
    except Exception as e:
        print(f"   ⚠️  P/E Comps failed: {e}")
        return None


def model_price_to_book(fin: dict, sector_pb: float = 1.3) -> dict | None:
    """Fair price = BVPS × sector P/B. Used for financials."""
    try:
        bvps  = fin.get("book_value_per_share")
        price = fin.get("current_price")

        if not bvps or float(bvps) <= 0 or not price:
            return None

        fv    = float(bvps) * sector_pb
        price = float(price)

        if fv <= 0 or fv > price * 10:
            return None

        return {
            "name":           "Price-to-Book",
            "fair_value":     round(fv, 2),
            "upside_pct":     round((fv - price) / price * 100, 1),
            "key_assumption": f"{sector_pb}x P/B — standard for financials",
        }
    except Exception as e:
        print(f"   ⚠️  P/B failed: {e}")
        return None


def model_revenue_multiple(fin: dict, sector_mult: float = 8.0) -> dict | None:
    """Fair EV = Revenue × multiple. Used for high-growth / pre-profit companies."""
    try:
        rev    = fin.get("total_revenue_raw")
        shares = fin.get("shares_outstanding")
        price  = fin.get("current_price")

        if not rev or not shares or not price:
            return None

        debt  = parse_money(fin.get("total_debt"))
        cash  = parse_money(fin.get("cash"))
        fv    = (float(rev) * sector_mult - debt + cash) / float(shares)
        price = float(price)

        if fv <= 0 or fv > price * 10:
            return None

        return {
            "name":           "Revenue Multiple",
            "fair_value":     round(fv, 2),
            "upside_pct":     round((fv - price) / price * 100, 1),
            "key_assumption": f"{sector_mult}x Revenue — growth-stage multiple",
        }
    except Exception as e:
        print(f"   ⚠️  Revenue multiple failed: {e}")
        return None


# ── Sector multiples (2025 market averages) ───────────────────────────────────
SECTOR_EV_EBITDA     = {"Technology": 22, "Consumer": 14, "Financials": 12,
                         "Healthcare": 16, "Energy": 8,   "Industrials": 13,
                         "Utilities": 12, "Media": 11,    "Telecom": 7, "Fintech": 20}

SECTOR_PE            = {"Technology": 28, "Consumer": 20, "Financials": 13,
                         "Healthcare": 18, "Energy": 12,  "Industrials": 18,
                         "Utilities": 16, "Media": 15,    "Telecom": 13, "Fintech": 30}

SECTOR_REV_MULTIPLE  = {"Technology": 10, "Fintech": 8,  "Healthcare": 6,
                         "Consumer": 3,   "Industrials": 2}


# ── Regime detection ──────────────────────────────────────────────────────────
def detect_regime(fin: dict) -> str:
    sector = fin.get("sector", "")
    rg     = parse_pct(fin.get("revenue_growth", "0%")) * 100
    fcf    = fin.get("free_cash_flow") or 0

    if sector == "Financials":
        return "financial"
    if sector == "Energy":
        return "energy"
    if rg > 25 or float(fcf) < 0:
        return "high_growth"
    return "stable"


# ── Weighted average ──────────────────────────────────────────────────────────
def weighted_avg(pairs: list) -> tuple | None:
    """pairs = [(model_result_or_None, weight), ...]"""
    total_w, total_wv, values = 0, 0, []
    for m, w in pairs:
        if m:
            total_wv += m["fair_value"] * w
            total_w  += w
            values.append(m["fair_value"])
    if not total_w:
        return None
    return round(total_wv / total_w, 2), (round(min(values), 2), round(max(values), 2))


# ── Main agent ────────────────────────────────────────────────────────────────
def valuation_agent(state: ResearchState) -> dict:
    """Runs multi-model valuation. Reads financial_data. Writes valuation_result."""
    ticker = state.get("ticker", "???")
    print(f"📐 Valuation: running multi-model analysis for {ticker}...")

    fin = state.get("financial_data") or {}
    if not fin:
        return {"valuation_result": None}

    price = fin.get("current_price")
    if not price or price == "N/A":
        return {"valuation_result": None}

    price  = float(price)
    sector = fin.get("sector", "N/A")
    regime = detect_regime(fin)

    ev_mult  = SECTOR_EV_EBITDA.get(sector,    15.0)
    pe_mult  = SECTOR_PE.get(sector,            18.0)
    rev_mult = SECTOR_REV_MULTIPLE.get(sector,  5.0)

    print(f"   Regime: {regime} | Sector: {sector}")

    # ── Select models by regime ───────────────────────────────────────────────
    if regime == "financial":
        pb  = model_price_to_book(fin, sector_pb=1.3)
        pe  = model_pe_comps(fin, sector_pe=pe_mult)
        pairs      = [(pb, 0.60), (pe, 0.40)]
        model_type = "Financial (P/B + P/E)"

    elif regime == "energy":
        ev  = model_ev_ebitda(fin, sector_mult=ev_mult)
        dcf = model_dcf(fin)
        pe  = model_pe_comps(fin, sector_pe=pe_mult)
        pairs      = [(ev, 0.50), (dcf, 0.30), (pe, 0.20)]
        model_type = "Cyclical (EV/EBITDA + DCF + P/E)"

    elif regime == "high_growth":
        rv  = model_revenue_multiple(fin, sector_mult=rev_mult)
        dcf = model_dcf(fin)
        pairs      = [(rv, 0.60), (dcf, 0.40)]
        model_type = "High-Growth (Revenue Multiple + DCF)"

    else:  # stable
        dcf = model_dcf(fin)
        ev  = model_ev_ebitda(fin, sector_mult=ev_mult)
        pe  = model_pe_comps(fin, sector_pe=pe_mult)
        pairs      = [(dcf, 0.50), (ev, 0.30), (pe, 0.20)]
        model_type = "Stable (DCF + EV/EBITDA + P/E)"

    # ── Aggregate ─────────────────────────────────────────────────────────────
    result = weighted_avg(pairs)
    if not result:
        print("   ⚠️  All models returned None — insufficient data")
        return {"valuation_result": None}

    weighted_fv, val_range = result
    upside_pct = round((weighted_fv - price) / price * 100, 1)

    verdict = ("UNDERVALUED"   if upside_pct > 15  else
               "OVERVALUED"    if upside_pct < -15 else
               "FAIRLY VALUED")

    # Build models list (only successful ones, with their intended weight)
    models_out = []
    for m, w in pairs:
        if m:
            models_out.append({**m, "weight": w})

    # Summary paragraph for the investment memo
    model_lines = "  |  ".join(
        f"{m['name']}: ${m['fair_value']} ({m['upside_pct']:+.1f}%)"
        for m in models_out
    )
    summary = (
        f"Our {model_type} valuation yields a weighted fair value of ${weighted_fv:.2f} "
        f"vs the current price of ${price:.2f}, implying "
        f"{'upside' if upside_pct > 0 else 'downside'} of {abs(upside_pct):.1f}%. "
        f"Valuation range across models: ${val_range[0]}–${val_range[1]}. "
        f"Model breakdown — {model_lines}. Verdict: {verdict}."
    )

    valuation_result = {
        "model_type":          model_type,
        "regime":              regime,
        "models":              models_out,
        "weighted_fair_value": weighted_fv,
        "current_price":       price,
        "upside_pct":          upside_pct,
        "valuation_range":     val_range,
        "verdict":             verdict,
        "summary":             summary,
    }

    print(f"   ✅ Fair value: ${weighted_fv:.2f} | Upside: {upside_pct:+.1f}% | {verdict}")
    for m in models_out:
        print(f"      {m['name']} (wt {m['weight']*100:.0f}%): ${m['fair_value']} — {m['key_assumption']}")

    return {"valuation_result": valuation_result}
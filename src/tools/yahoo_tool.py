import yfinance as yf
from dotenv import load_dotenv

from src.cache import cache_get, cache_set, cache_key

load_dotenv()


def get_financial_data(ticker: str) -> dict:
    """
    Fetch key financial metrics for a company using Yahoo Finance.

    Key naming convention matches what pdf_generator.py and all agents expect:
      net_margin       (not profit_margin)
      roe              (not return_on_equity)
      cash             (not total_cash)
      net_income       (fetched from financials)
      gross_profit     (fetched from financials)
      ebitda           (fetched from financials)
      ev_ebitda        (fetched from info)

    Valuation agent inputs (NEW — raw floats, not formatted strings):
      free_cash_flow        raw float in dollars
      shares_outstanding    raw float (count)
      beta                  float
      book_value_per_share  float (dollars per share)
      operating_cash_flow   raw float in dollars
      total_revenue_raw     raw float in dollars
      enterprise_value      raw float in dollars
      ebitda_raw            raw float in dollars
    """
    key    = cache_key("yahoo", ticker)
    cached = cache_get(key)
    if cached:
        print(f"   📦 Using cached Yahoo data for {ticker}")
        return cached

    stock = yf.Ticker(ticker)
    info  = stock.info

    # ── Helper formatters ────────────────────────────────────────────────────
    def fmt_number(val):
        if isinstance(val, (int, float)) and val != 0:
            if abs(val) >= 1_000_000_000_000:
                return f"${val / 1_000_000_000_000:.2f}T"
            elif abs(val) >= 1_000_000_000:
                return f"${val / 1_000_000_000:.2f}B"
            elif abs(val) >= 1_000_000:
                return f"${val / 1_000_000:.2f}M"
        return val

    def fmt_percent(val):
        if isinstance(val, float) and abs(val) < 10:
            return f"{val * 100:.2f}%"
        return val

    # ── Pull income statement ─────────────────────────────────────────────────
    net_income   = "N/A"
    gross_profit = "N/A"
    ebitda_val   = "N/A"

    try:
        financials = stock.financials
        if financials is not None and not financials.empty:
            col = financials.columns[0]

            if "Net Income" in financials.index:
                ni = financials.loc["Net Income", col]
                if ni is not None:
                    net_income = fmt_number(float(ni))

            if "Gross Profit" in financials.index:
                gp = financials.loc["Gross Profit", col]
                if gp is not None:
                    gross_profit = fmt_number(float(gp))

            ebitda_raw = info.get("ebitda")
            if ebitda_raw and isinstance(ebitda_raw, (int, float)) and ebitda_raw != 0:
                ebitda_val = fmt_number(ebitda_raw)
            elif "EBITDA" in financials.index:
                eb = financials.loc["EBITDA", col]
                if eb is not None:
                    ebitda_val = fmt_number(float(eb))
    except Exception as e:
        print(f"   ⚠️  Could not fetch income statement for {ticker}: {e}")

    # ── EV/EBITDA ─────────────────────────────────────────────────────────────
    ev_ebitda = "N/A"
    try:
        ev_raw     = info.get("enterpriseValue")
        ebitda_raw = info.get("ebitda")
        if ev_raw and ebitda_raw and ebitda_raw != 0:
            ev_ebitda = f"{ev_raw / ebitda_raw:.2f}x"
    except Exception:
        pass

    # ── Analyst flags ─────────────────────────────────────────────────────────
    analyst_flags = []
    pe = info.get("trailingPE")
    de = info.get("debtToEquity")
    cr = info.get("currentRatio")
    if pe and isinstance(pe, float) and pe > 40:
        analyst_flags.append(f"HIGH_VALUATION: P/E above 40 ({pe:.1f}x)")
    if de and isinstance(de, float) and de > 150:
        analyst_flags.append(f"HIGH_LEVERAGE: Debt/Equity above 150% ({de:.1f}%)")
    if cr and isinstance(cr, float) and cr < 1.0:
        analyst_flags.append(f"LIQUIDITY_RISK: Current ratio below 1.0 ({cr:.3f})")

    data = {
        "ticker":       ticker.upper(),
        "company_name": info.get("longName", ticker),
        "sector":       info.get("sector",   "N/A"),
        "industry":     info.get("industry", "N/A"),

        # Valuation (formatted strings for display)
        "current_price":  info.get("currentPrice",  "N/A"),
        "market_cap":     fmt_number(info.get("marketCap")),
        "pe_ratio":       info.get("trailingPE",    "N/A"),
        "forward_pe":     info.get("forwardPE",     "N/A"),
        "ev_ebitda":      ev_ebitda,
        "price_to_book":  info.get("priceToBook",   "N/A"),

        # Revenue & profit
        "revenue_ttm":   fmt_number(info.get("totalRevenue")),
        "gross_profit":  gross_profit,
        "net_income":    net_income,
        "ebitda":        ebitda_val,

        # Margins
        "gross_margin":     fmt_percent(info.get("grossMargins")),
        "operating_margin": fmt_percent(info.get("operatingMargins")),
        "net_margin":       fmt_percent(info.get("profitMargins")),
        "roe":              fmt_percent(info.get("returnOnEquity")),

        # Growth
        "revenue_growth":  fmt_percent(info.get("revenueGrowth")),
        "earnings_growth": fmt_percent(info.get("earningsGrowth")),

        # Financial health
        "total_debt":      fmt_number(info.get("totalDebt")),
        "cash":            fmt_number(info.get("totalCash")),
        "debt_to_equity":  info.get("debtToEquity",  "N/A"),
        "current_ratio":   info.get("currentRatio",  "N/A"),
        "return_on_assets":fmt_percent(info.get("returnOnAssets")),

        # Analyst sentiment
        "analyst_recommendation": info.get("recommendationKey", "N/A"),
        "target_price":           info.get("targetMeanPrice",   "N/A"),
        "number_of_analysts":     info.get("numberOfAnalystOpinions", "N/A"),
        "analyst_flags":          analyst_flags,

        # ── NEW: raw valuation inputs (kept as floats — valuation_agent does math) ──
        "free_cash_flow":       info.get("freeCashflow"),       # e.g. 106312753152
        "shares_outstanding":   info.get("sharesOutstanding"),  # e.g. 14681140000
        "beta":                 info.get("beta"),               # e.g. 1.116
        "book_value_per_share": info.get("bookValue"),          # e.g. 5.998
        "operating_cash_flow":  info.get("operatingCashflow"),  # e.g. 135471996928
        "total_revenue_raw":    info.get("totalRevenue"),       # e.g. 435617005568
        "enterprise_value":     info.get("enterpriseValue"),    # e.g. 3100000000000
        "ebitda_raw":           info.get("ebitda"),             # e.g. 129626997760
    }

    cache_set(key, data)
    return data


if __name__ == "__main__":
    print("Testing Yahoo Finance Tool...\n")
    result = get_financial_data("AAPL")

    print(f"Company:          {result['company_name']}")
    print(f"Sector:           {result['sector']}")
    print()
    print("--- Formatted Display Fields ---")
    print(f"Current Price:    {result['current_price']}")
    print(f"Market Cap:       {result['market_cap']}")
    print(f"P/E Ratio:        {result['pe_ratio']}")
    print(f"EV/EBITDA:        {result['ev_ebitda']}")
    print()
    print("--- NEW: Raw Valuation Inputs ---")
    fcf = result['free_cash_flow']
    shr = result['shares_outstanding']
    ocf = result['operating_cash_flow']
    print(f"Free Cash Flow:   ${fcf:,.0f}" if fcf else "FCF:    N/A")
    print(f"Shares Out:       {shr:,.0f}" if shr else "Shares: N/A")
    print(f"Beta:             {result['beta']}")
    print(f"Book Value/Share: ${result['book_value_per_share']}")
    print(f"Op. Cash Flow:    ${ocf:,.0f}" if ocf else "OCF:    N/A")
    print(f"Total Revenue:    ${result['total_revenue_raw']:,.0f}" if result['total_revenue_raw'] else "Rev:    N/A")
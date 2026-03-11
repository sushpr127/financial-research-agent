import yfinance as yf
from dotenv import load_dotenv

from src.cache import cache_get, cache_set, cache_key

load_dotenv()


def get_financial_data(ticker: str) -> dict:
    """
    Fetch key financial metrics for a company using Yahoo Finance.
    Returns revenue, profit margins, P/E ratio, debt, and growth metrics.

    Key naming convention matches what pdf_generator.py and all agents expect:
      net_margin       (not profit_margin)
      roe              (not return_on_equity)
      cash             (not total_cash)
      net_income       (fetched from financials)
      gross_profit     (fetched from financials)
      ebitda           (fetched from financials)
      ev_ebitda        (fetched from info)
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
        """Format large raw numbers into $XB / $XM strings."""
        if isinstance(val, (int, float)) and val != 0:
            if abs(val) >= 1_000_000_000_000:
                return f"${val / 1_000_000_000_000:.2f}T"
            elif abs(val) >= 1_000_000_000:
                return f"${val / 1_000_000_000:.2f}B"
            elif abs(val) >= 1_000_000:
                return f"${val / 1_000_000:.2f}M"
        return val

    def fmt_percent(val):
        """Convert decimal ratios (0.47) to percentage strings (47.00%)."""
        if isinstance(val, float) and abs(val) < 10:
            return f"{val * 100:.2f}%"
        return val

    def fmt_multiple(val, suffix="x"):
        """Round a float multiple to 2dp and add suffix."""
        if isinstance(val, float):
            return f"{val:.2f}{suffix}"
        return val

    # ── Pull income statement for fields not in info ─────────────────────────
    net_income   = "N/A"
    gross_profit = "N/A"
    ebitda_val   = "N/A"

    try:
        financials = stock.financials  # annual income statement
        if financials is not None and not financials.empty:
            col = financials.columns[0]  # most recent fiscal year

            if "Net Income" in financials.index:
                ni = financials.loc["Net Income", col]
                if ni is not None:
                    net_income = fmt_number(float(ni))

            if "Gross Profit" in financials.index:
                gp = financials.loc["Gross Profit", col]
                if gp is not None:
                    gross_profit = fmt_number(float(gp))

            # EBITDA = Operating Income + D&A  (or use info field)
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
    pe     = info.get("trailingPE")
    de     = info.get("debtToEquity")
    cr     = info.get("currentRatio")
    if pe  and isinstance(pe, float) and pe > 40:
        analyst_flags.append(f"HIGH_VALUATION: P/E above 40 ({pe:.1f}x)")
    if de  and isinstance(de, float) and de > 150:
        analyst_flags.append(f"HIGH_LEVERAGE: Debt/Equity above 150% ({de:.1f}%)")
    if cr  and isinstance(cr, float) and cr < 1.0:
        analyst_flags.append(f"LIQUIDITY_RISK: Current ratio below 1.0 ({cr:.3f})")

    # ── Build output dict — keys match pdf_generator + agents exactly ─────────
    data = {
        "ticker":       ticker.upper(),
        "company_name": info.get("longName", ticker),
        "sector":       info.get("sector",   "N/A"),
        "industry":     info.get("industry", "N/A"),

        # Valuation
        "current_price":  info.get("currentPrice",  "N/A"),
        "market_cap":     fmt_number(info.get("marketCap")),
        "pe_ratio":       info.get("trailingPE",    "N/A"),
        "forward_pe":     info.get("forwardPE",     "N/A"),
        "ev_ebitda":      ev_ebitda,
        "price_to_book":  info.get("priceToBook",   "N/A"),

        # Revenue & profit — fetched from income statement above
        "revenue_ttm":   fmt_number(info.get("totalRevenue")),
        "gross_profit":  gross_profit,       # ← was always N/A before
        "net_income":    net_income,         # ← was always N/A before
        "ebitda":        ebitda_val,         # ← was always N/A before

        # Margins — PDF expects net_margin and roe (not profit_margin / return_on_equity)
        "gross_margin":     fmt_percent(info.get("grossMargins")),
        "operating_margin": fmt_percent(info.get("operatingMargins")),
        "net_margin":       fmt_percent(info.get("profitMargins")),   # ← key renamed
        "roe":              fmt_percent(info.get("returnOnEquity")),  # ← key renamed

        # Growth
        "revenue_growth":  fmt_percent(info.get("revenueGrowth")),
        "earnings_growth": fmt_percent(info.get("earningsGrowth")),

        # Financial health
        "total_debt":      fmt_number(info.get("totalDebt")),
        "cash":            fmt_number(info.get("totalCash")),   # ← key renamed from total_cash
        "debt_to_equity":  info.get("debtToEquity",  "N/A"),
        "current_ratio":   info.get("currentRatio",  "N/A"),
        "return_on_assets":fmt_percent(info.get("returnOnAssets")),

        # Analyst sentiment
        "analyst_recommendation": info.get("recommendationKey", "N/A"),
        "target_price":           info.get("targetMeanPrice",   "N/A"),
        "number_of_analysts":     info.get("numberOfAnalystOpinions", "N/A"),

        # Flags for risk scorer + PDF
        "analyst_flags": analyst_flags,
    }

    cache_set(key, data)
    return data


if __name__ == "__main__":
    print("Testing Yahoo Finance Tool...\n")
    result = get_financial_data("AAPL")

    print(f"Company:          {result['company_name']}")
    print(f"Sector:           {result['sector']}")
    print(f"Industry:         {result['industry']}")
    print()
    print("--- Valuation ---")
    print(f"Current Price:    {result['current_price']}")
    print(f"Market Cap:       {result['market_cap']}")
    print(f"P/E Ratio:        {result['pe_ratio']}")
    print(f"Forward P/E:      {result['forward_pe']}")
    print(f"EV/EBITDA:        {result['ev_ebitda']}")
    print(f"Price/Book:       {result['price_to_book']}")
    print()
    print("--- Revenue & Profit ---")
    print(f"Revenue (TTM):    {result['revenue_ttm']}")
    print(f"Gross Profit:     {result['gross_profit']}")
    print(f"Net Income:       {result['net_income']}")
    print(f"EBITDA:           {result['ebitda']}")
    print()
    print("--- Margins ---")
    print(f"Gross Margin:     {result['gross_margin']}")
    print(f"Operating Margin: {result['operating_margin']}")
    print(f"Net Margin:       {result['net_margin']}")
    print(f"ROE:              {result['roe']}")
    print()
    print("--- Growth ---")
    print(f"Revenue Growth:   {result['revenue_growth']}")
    print(f"Earnings Growth:  {result['earnings_growth']}")
    print()
    print("--- Financial Health ---")
    print(f"Total Debt:       {result['total_debt']}")
    print(f"Cash:             {result['cash']}")
    print(f"Debt/Equity:      {result['debt_to_equity']}")
    print(f"Current Ratio:    {result['current_ratio']}")
    print()
    print("--- Analyst Sentiment ---")
    print(f"Recommendation:   {result['analyst_recommendation']}")
    print(f"Target Price:     {result['target_price']}")
    print(f"# of Analysts:    {result['number_of_analysts']}")
    print()
    print("--- Analyst Flags ---")
    for f in result['analyst_flags']:
        print(f"  ⚠️  {f}")
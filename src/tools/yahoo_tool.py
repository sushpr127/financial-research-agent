import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

def get_financial_data(ticker: str) -> dict:
    """
    Fetch key financial metrics for a company using Yahoo Finance.
    Returns revenue, profit margins, P/E ratio, debt, and growth metrics.
    """
    stock = yf.Ticker(ticker)
    info = stock.info
    
    # Pull the metrics our Financial Analyst agent will need
    data = {
        "ticker": ticker.upper(),
        "company_name": info.get("longName", ticker),
        "sector": info.get("sector", "N/A"),
        "industry": info.get("industry", "N/A"),
        
        # Valuation
        "current_price": info.get("currentPrice", "N/A"),
        "market_cap": info.get("marketCap", "N/A"),
        "pe_ratio": info.get("trailingPE", "N/A"),
        "forward_pe": info.get("forwardPE", "N/A"),
        "price_to_book": info.get("priceToBook", "N/A"),
        
        # Revenue & Profit
        "revenue_ttm": info.get("totalRevenue", "N/A"),
        "gross_margin": info.get("grossMargins", "N/A"),
        "operating_margin": info.get("operatingMargins", "N/A"),
        "profit_margin": info.get("profitMargins", "N/A"),
        
        # Growth
        "revenue_growth": info.get("revenueGrowth", "N/A"),
        "earnings_growth": info.get("earningsGrowth", "N/A"),
        
        # Financial Health
        "total_debt": info.get("totalDebt", "N/A"),
        "total_cash": info.get("totalCash", "N/A"),
        "debt_to_equity": info.get("debtToEquity", "N/A"),
        "current_ratio": info.get("currentRatio", "N/A"),
        "return_on_equity": info.get("returnOnEquity", "N/A"),
        "return_on_assets": info.get("returnOnAssets", "N/A"),
        
        # Analyst sentiment
        "analyst_recommendation": info.get("recommendationKey", "N/A"),
        "target_price": info.get("targetMeanPrice", "N/A"),
        "number_of_analysts": info.get("numberOfAnalystOpinions", "N/A"),
    }
    
    # Format large numbers for readability
    def format_number(val):
        if isinstance(val, (int, float)):
            if val >= 1_000_000_000:
                return f"${val/1_000_000_000:.2f}B"
            elif val >= 1_000_000:
                return f"${val/1_000_000:.2f}M"
        return val
    
    def format_percent(val):
        if isinstance(val, float) and val < 10:
            return f"{val*100:.2f}%"
        return val
    
    data["market_cap"] = format_number(data["market_cap"])
    data["revenue_ttm"] = format_number(data["revenue_ttm"])
    data["total_debt"] = format_number(data["total_debt"])
    data["total_cash"] = format_number(data["total_cash"])
    data["gross_margin"] = format_percent(data["gross_margin"])
    data["operating_margin"] = format_percent(data["operating_margin"])
    data["profit_margin"] = format_percent(data["profit_margin"])
    data["revenue_growth"] = format_percent(data["revenue_growth"])
    data["earnings_growth"] = format_percent(data["earnings_growth"])
    data["return_on_equity"] = format_percent(data["return_on_equity"])
    data["return_on_assets"] = format_percent(data["return_on_assets"])
    
    return data


if __name__ == "__main__":
    print("Testing Yahoo Finance Tool...\n")
    result = get_financial_data("AAPL")
    
    print(f"Company:         {result['company_name']}")
    print(f"Sector:          {result['sector']}")
    print(f"Industry:        {result['industry']}")
    print()
    print("--- Valuation ---")
    print(f"Current Price:   {result['current_price']}")
    print(f"Market Cap:      {result['market_cap']}")
    print(f"P/E Ratio:       {result['pe_ratio']}")
    print(f"Forward P/E:     {result['forward_pe']}")
    print(f"Price/Book:      {result['price_to_book']}")
    print()
    print("--- Revenue & Profit ---")
    print(f"Revenue (TTM):   {result['revenue_ttm']}")
    print(f"Gross Margin:    {result['gross_margin']}")
    print(f"Operating Margin:{result['operating_margin']}")
    print(f"Profit Margin:   {result['profit_margin']}")
    print()
    print("--- Growth ---")
    print(f"Revenue Growth:  {result['revenue_growth']}")
    print(f"Earnings Growth: {result['earnings_growth']}")
    print()
    print("--- Financial Health ---")
    print(f"Total Debt:      {result['total_debt']}")
    print(f"Total Cash:      {result['total_cash']}")
    print(f"Debt/Equity:     {result['debt_to_equity']}")
    print(f"Current Ratio:   {result['current_ratio']}")
    print(f"ROE:             {result['return_on_equity']}")
    print()
    print("--- Analyst Sentiment ---")
    print(f"Recommendation:  {result['analyst_recommendation']}")
    print(f"Target Price:    {result['target_price']}")
    print(f"# of Analysts:   {result['number_of_analysts']}")
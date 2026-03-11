import re
import yfinance as yf
from typing import Optional

def validate_ticker(ticker: str) -> tuple[bool, Optional[str]]:
    """
    Validate a ticker symbol before running the pipeline.
    Returns (is_valid, error_message).
    """
    # Basic format check
    if not ticker:
        return False, "Ticker cannot be empty"

    ticker = ticker.strip().upper()

    if not re.match(r'^[A-Z]{1,5}$', ticker):
        return False, f"'{ticker}' is not a valid ticker format. Use 1-5 letters (e.g. AAPL, MSFT)"

    # Live check against Yahoo Finance
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # If Yahoo returns no useful data, ticker doesn't exist
        if not info.get("regularMarketPrice") and not info.get("currentPrice") and not info.get("marketCap"):
            return False, f"Ticker '{ticker}' not found. Please check the symbol and try again."

        # Return the canonical company name too
        company_name = info.get("longName") or info.get("shortName") or ticker
        return True, company_name

    except Exception as e:
        return False, f"Could not validate ticker '{ticker}': {str(e)}"


def validate_pipeline_state(state: dict) -> tuple[bool, list[str]]:
    """
    Validate state between agents.
    Returns (is_valid, list of warnings).
    """
    warnings = []

    # Check each expected field
    if not state.get("news_results"):
        warnings.append("news_results is empty — Researcher may have failed")

    if not state.get("filing_excerpt") or state.get("filing_excerpt") == "Filing not available":
        warnings.append("filing_excerpt is missing — FilingParser may have failed")

    if not state.get("financial_data"):
        warnings.append("financial_data is empty — FinancialAnalyst may have failed")

    # If ALL three data sources failed, pipeline should stop
    critical_failure = (
        not state.get("news_results") and
        not state.get("financial_data") and
        (not state.get("filing_excerpt") or state.get("filing_excerpt") == "Filing not available")
    )

    return not critical_failure, warnings
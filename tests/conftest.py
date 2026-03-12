"""
conftest.py — shared pytest fixtures
Loaded automatically by pytest before any test file runs.
"""
import pytest
from dotenv import load_dotenv

load_dotenv()


# ── Minimal valid financial data (used across multiple test files) ────────────
@pytest.fixture
def sample_financial_data():
    """Realistic financial data matching what yahoo_tool.py returns for AAPL."""
    return {
        "ticker":         "AAPL",
        "company_name":   "Apple Inc.",
        "sector":         "Technology",
        "industry":       "Consumer Electronics",
        "current_price":  260.81,
        "market_cap":     "$3.83T",
        "pe_ratio":       33.01,
        "forward_pe":     28.07,
        "ev_ebitda":      "25.20x",
        "price_to_book":  43.48,
        "revenue_ttm":    "$435.62B",
        "gross_profit":   "$206.05B",
        "net_income":     "$112.01B",
        "ebitda":         "$152.90B",
        "gross_margin":   "47.33%",
        "operating_margin":"35.37%",
        "net_margin":     "27.04%",
        "roe":            "152.02%",
        "revenue_growth": "15.70%",
        "earnings_growth":"12.50%",
        "total_debt":     "$90.51B",
        "cash":           "$66.91B",
        "debt_to_equity": 102.63,
        "current_ratio":  0.97,
        "return_on_assets":"0.25%",
        "analyst_recommendation": "buy",
        "target_price":   290.00,
        "number_of_analysts": 38,
        "analyst_flags":  ["LIQUIDITY_RISK: Current ratio below 1.0 (0.970)"],
        # Raw valuation inputs
        "shares_outstanding":   14_681_140_000,
        "free_cash_flow":       106_312_753_152,
        "operating_cash_flow":  135_471_996_928,
        "beta":                 1.116,
        "book_value_per_share": 5.998,
        "enterprise_value":     3_200_000_000_000,
        "total_revenue_raw":    435_617_005_568,
        "ebitda_raw":           152_900_000_000,
        "total_debt_raw":       90_510_000_000,
        "total_cash_raw":       66_910_000_000,
        "price_to_book_raw":    43.48,
        "roe_raw":              1.5202,
        "revenue_growth_raw":   0.157,
        "operating_margin_raw": 0.3537,
        "net_income_raw":       112_010_000_000,
        "gross_profit_raw":     206_050_000_000,
    }


@pytest.fixture
def sample_bank_data():
    """JPMorgan data — used to test bank model selection."""
    return {
        "ticker":         "JPM",
        "company_name":   "JPMorgan Chase & Co.",
        "sector":         "Financial Services",
        "industry":       "Banks—Diversified",
        "current_price":  245.00,
        "shares_outstanding": 2_850_000_000,
        "book_value_per_share": 105.0,
        "roe_raw":        0.17,
        "net_income_raw": 50_000_000_000,
        "revenue_growth_raw": 0.05,
        "total_debt_raw": 0,
        "total_cash_raw": 0,
        "ebitda_raw":     None,
        "total_revenue_raw": 160_000_000_000,
        "operating_margin_raw": 0.35,
        "free_cash_flow": 40_000_000_000,
        "beta": 1.1,
        "analyst_flags": [],
    }


@pytest.fixture
def sample_growth_data():
    """NVDA-like data — used to test high-growth model selection."""
    return {
        "ticker":         "NVDA",
        "company_name":   "NVIDIA Corporation",
        "sector":         "Technology",
        "industry":       "Semiconductors",
        "current_price":  800.00,
        "shares_outstanding": 24_530_000_000,
        "book_value_per_share": 10.0,
        "roe_raw":        0.85,
        "net_income_raw": 30_000_000_000,
        "revenue_growth_raw": 0.122,  # 122% growth → high_growth
        "total_debt_raw": 10_000_000_000,
        "total_cash_raw": 26_000_000_000,
        "ebitda_raw":     35_000_000_000,
        "total_revenue_raw": 60_000_000_000,
        "operating_margin_raw": 0.55,
        "free_cash_flow": 27_000_000_000,
        "beta": 1.65,
        "analyst_flags": [],
    }


@pytest.fixture
def sample_noprofit_data():
    """RIVN-like data — used to test no-profit model selection."""
    return {
        "ticker":         "RIVN",
        "company_name":   "Rivian Automotive Inc.",
        "sector":         "Consumer Cyclical",
        "industry":       "Auto Manufacturers",
        "current_price":  15.00,
        "shares_outstanding": 950_000_000,
        "book_value_per_share": 8.0,
        "roe_raw":        -0.45,
        "net_income_raw": -5_400_000_000,   # negative — unprofitable
        "revenue_growth_raw": 0.32,          # 32% growth
        "total_debt_raw": 8_000_000_000,
        "total_cash_raw": 7_000_000_000,
        "ebitda_raw":     -3_000_000_000,
        "total_revenue_raw": 5_000_000_000,
        "operating_margin_raw": -0.60,
        "free_cash_flow": -4_000_000_000,
        "beta": 1.9,
        "analyst_flags": [],
    }


@pytest.fixture
def sample_state(sample_financial_data):
    """Minimal valid ResearchState for agent tests."""
    return {
        "ticker":           "AAPL",
        "company_name":     "Apple Inc.",
        "news_results":     [{"title": "Apple reports record Q4 earnings", "url": "https://example.com"}],
        "filing_excerpt":   "Apple designs, manufactures, and markets smartphones and personal computers.",
        "filing_date":      "2025-10-31",
        "financial_data":   sample_financial_data,
        "risk_assessment":  None,
        "valuation_result": None,
        "investment_memo":  None,
        "errors":           [],
    }

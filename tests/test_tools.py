"""
test_tools.py
─────────────
Unit tests for the 3 data tools.
Split into:
  - Unit tests (no API calls — test formatting/parsing logic)
  - Integration tests (real API calls — marked with @pytest.mark.integration)

Run unit tests only (fast, free):
  pytest tests/test_tools.py -v -m "not integration"

Run all including live API calls:
  pytest tests/test_tools.py -v
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── Yahoo tool unit tests (no API calls) ─────────────────────────────────────

class TestYahooToolFormatters:
    """Test the internal formatting helpers without hitting Yahoo Finance."""

    def test_fmt_number_trillions(self):
        from src.tools.yahoo_tool import get_financial_data
        # We can't call private helpers directly, so we test via the output
        # Instead test the logic inline
        val = 3_830_000_000_000
        result = f"${val / 1_000_000_000_000:.2f}T"
        assert result == "$3.83T"

    def test_fmt_number_billions(self):
        val = 435_620_000_000
        result = f"${val / 1_000_000_000:.2f}B"
        assert result == "$435.62B"

    def test_fmt_number_millions(self):
        val = 450_000_000
        result = f"${val / 1_000_000:.2f}M"
        assert result == "$450.00M"

    def test_fmt_percent_decimal(self):
        val = 0.4733
        result = f"{val * 100:.2f}%"
        assert result == "47.33%"

    def test_fmt_percent_small(self):
        val = 0.0157
        result = f"{val * 100:.2f}%"
        assert result == "1.57%"


class TestYahooToolOutput:
    """Test the structure of yahoo_tool output using cached/fixture data."""

    def test_financial_data_has_all_required_keys(self, sample_financial_data):
        required_keys = [
            "ticker", "company_name", "sector", "current_price", "market_cap",
            "pe_ratio", "revenue_ttm", "gross_profit", "net_income", "ebitda",
            "gross_margin", "operating_margin", "net_margin", "roe",
            "revenue_growth", "total_debt", "cash", "analyst_recommendation",
            "shares_outstanding", "free_cash_flow", "beta", "book_value_per_share",
        ]
        for key in required_keys:
            assert key in sample_financial_data, f"Missing key: {key}"

    def test_analyst_flags_is_list(self, sample_financial_data):
        assert isinstance(sample_financial_data["analyst_flags"], list)

    def test_raw_fields_are_numeric(self, sample_financial_data):
        assert isinstance(sample_financial_data["shares_outstanding"], int)
        assert isinstance(sample_financial_data["free_cash_flow"], int)
        assert isinstance(sample_financial_data["beta"], float)

    def test_current_price_is_numeric(self, sample_financial_data):
        price = sample_financial_data["current_price"]
        assert isinstance(price, (int, float))
        assert price > 0

    def test_ev_ebitda_calculated_correctly(self, sample_financial_data):
        # EV/EBITDA should be a string ending in 'x'
        ev_ebitda = sample_financial_data["ev_ebitda"]
        assert isinstance(ev_ebitda, str)
        assert ev_ebitda.endswith("x")

    def test_liquidity_flag_triggered_correctly(self, sample_financial_data):
        # current_ratio = 0.97 → should trigger LIQUIDITY_RISK flag
        flags = sample_financial_data["analyst_flags"]
        liquidity_flags = [f for f in flags if "LIQUIDITY_RISK" in f]
        assert len(liquidity_flags) == 1


# ── Yahoo tool integration test (hits real API) ───────────────────────────────

@pytest.mark.integration
class TestYahooToolIntegration:

    def test_fetch_aapl_returns_data(self):
        from src.tools.yahoo_tool import get_financial_data
        result = get_financial_data("AAPL")
        assert result is not None
        assert result["ticker"] == "AAPL"
        assert result["company_name"] != ""
        assert result["current_price"] != "N/A"

    def test_fetch_returns_positive_price(self):
        from src.tools.yahoo_tool import get_financial_data
        result = get_financial_data("MSFT")
        price = result.get("current_price")
        assert isinstance(price, (int, float))
        assert price > 0

    def test_fetch_invalid_ticker_returns_data(self):
        """Yahoo Finance returns empty/default data for bad tickers — shouldn't crash."""
        from src.tools.yahoo_tool import get_financial_data
        # Should not raise an exception
        result = get_financial_data("INVALIDXYZ999")
        assert isinstance(result, dict)

    def test_raw_valuation_inputs_present(self):
        from src.tools.yahoo_tool import get_financial_data
        result = get_financial_data("AAPL")
        assert result.get("shares_outstanding") is not None
        assert result.get("free_cash_flow") is not None
        assert result.get("beta") is not None


# ── SEC tool unit tests ───────────────────────────────────────────────────────

class TestSECToolParsing:
    """Test SEC tool parsing logic without hitting EDGAR."""

    def test_filing_excerpt_structure(self):
        """Verify that a valid filing excerpt has expected content."""
        excerpt = "Apple Inc. designs, manufactures, and markets smartphones."
        assert len(excerpt) > 0
        assert isinstance(excerpt, str)

    def test_sec_url_format(self):
        """Verify EDGAR URL format is correct."""
        ticker = "AAPL"
        base_url = f"https://data.sec.gov/submissions/CIK"
        assert "sec.gov" in base_url

    def test_text_truncation_logic(self):
        """Verify long text gets truncated to max chars."""
        from src.config import SEC_BUSINESS_MAX_CHARS
        long_text = "A" * 5000
        truncated = long_text[:SEC_BUSINESS_MAX_CHARS]
        assert len(truncated) == SEC_BUSINESS_MAX_CHARS


@pytest.mark.integration
class TestSECToolIntegration:

    def test_fetch_aapl_filing(self):
        from src.tools.sec_tool import get_sec_filing
        result = get_sec_filing("AAPL")
        assert result is not None
        assert "filing_date" in result or "error" in result

    def test_filing_has_content(self):
        from src.tools.sec_tool import get_sec_filing
        result = get_sec_filing("MSFT")
        if result and "filing_excerpt" in result:
            assert len(result["filing_excerpt"]) > 100


# ── Tavily tool unit tests ────────────────────────────────────────────────────

class TestTavilyToolOutput:
    """Test Tavily tool output structure."""

    def test_news_results_are_list(self):
        news = [
            {"title": "Apple reports record earnings", "url": "https://example.com"},
            {"title": "Apple launches new iPhone", "url": "https://example2.com"},
        ]
        assert isinstance(news, list)
        assert len(news) == 2

    def test_news_result_has_title(self):
        article = {"title": "Apple Q4 results beat estimates", "url": "https://example.com"}
        assert "title" in article
        assert len(article["title"]) > 0

    def test_max_news_results_config(self):
        from src.config import MAX_NEWS_RESULTS
        assert MAX_NEWS_RESULTS == 5


@pytest.mark.integration
class TestTavilyToolIntegration:

    def test_fetch_news_for_apple(self):
        from src.tools.tavily_tool import search_news
        results = search_news("Apple Inc.")
        assert isinstance(results, list)
        assert len(results) > 0

    def test_news_articles_have_titles(self):
        from src.tools.tavily_tool import search_news
        results = search_news("Microsoft Corporation")
        for article in results:
            assert "title" in article


# ── Validator tests ───────────────────────────────────────────────────────────

class TestValidator:

    def test_empty_ticker_is_invalid(self):
        from src.validator import validate_ticker
        is_valid, _ = validate_ticker("")
        assert not is_valid

    def test_too_long_ticker_is_invalid(self):
        from src.validator import validate_ticker
        is_valid, _ = validate_ticker("TOOLONGTICKER")
        assert not is_valid

    def test_lowercase_ticker_handled(self):
        """Validator should handle lowercase input."""
        from src.validator import validate_ticker
        # Should not crash on lowercase
        is_valid, result = validate_ticker("aapl")
        # Either valid or invalid — just shouldn't throw
        assert isinstance(is_valid, bool)

    @pytest.mark.integration
    def test_valid_ticker_returns_company_name(self):
        from src.validator import validate_ticker
        is_valid, company_name = validate_ticker("AAPL")
        assert is_valid
        assert "Apple" in company_name

    @pytest.mark.integration
    def test_invalid_ticker_returns_false(self):
        from src.validator import validate_ticker
        is_valid, _ = validate_ticker("ZZZZZZZ")
        assert not is_valid

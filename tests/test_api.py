"""
test_api.py
───────────
Integration tests for the FastAPI backend.
Uses httpx.AsyncClient to call endpoints without a running server.

Run: pytest tests/test_api.py -v
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from api.main import app
    return TestClient(app)


@pytest.fixture
def mock_pipeline_output():
    """Mock output from the research pipeline — avoids real API calls."""
    return {
        "ticker":           "AAPL",
        "company_name":     "Apple Inc.",
        "investment_memo":  "## Executive Summary\nApple Inc. reported strong results.",
        "risk_assessment":  "RISK SCORE: 3/10\nOVERALL RISK LEVEL: LOW\n1. Low debt risk",
        "filing_date":      "2025-10-31",
        "financial_data": {
            "ticker":               "AAPL",
            "company_name":         "Apple Inc.",
            "current_price":        260.81,
            "market_cap":           "$3.83T",
            "analyst_recommendation":"buy",
            "target_price":         290.00,
            "analyst_flags":        [],
        },
        "valuation_result": {
            "company_type":    "stable",
            "weighted_value":  195.74,
            "current_price":   260.81,
            "upside_pct":      -24.9,
            "price_range_low": 170.33,
            "price_range_high":227.52,
            "verdict":         "OVERVALUED",
            "margin_of_safety":-33.2,
            "models": [
                {"model": "DCF", "fair_value": 170.33, "weight": 0.5,
                 "weight_pct": "50%", "key_assumption": "WACC 10.3%"},
            ],
        },
        "errors": [],
    }


# ── Health endpoint ───────────────────────────────────────────────────────────

class TestHealthEndpoint:

    def test_health_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_ok_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "ok"

    def test_health_returns_service_name(self, client):
        response = client.get("/health")
        data = response.json()
        assert "service" in data
        assert data["service"] == "financial-research-agent"


# ── Root endpoint ─────────────────────────────────────────────────────────────

class TestRootEndpoint:

    def test_root_returns_200(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_version(self, client):
        response = client.get("/")
        data = response.json()
        assert "version" in data

    def test_root_lists_endpoints(self, client):
        response = client.get("/")
        data = response.json()
        assert "endpoints" in data


# ── Research endpoint — input validation ─────────────────────────────────────

class TestResearchEndpointValidation:

    def test_empty_ticker_returns_400(self, client):
        response = client.post("/research", json={"ticker": ""})
        assert response.status_code == 400

    def test_too_long_ticker_returns_400(self, client):
        response = client.post("/research", json={"ticker": "TOOLONGTICKER123"})
        assert response.status_code == 400

    def test_missing_ticker_field_returns_422(self, client):
        response = client.post("/research", json={})
        assert response.status_code == 422

    def test_wrong_content_type_returns_422(self, client):
        response = client.post("/research", data="not json")
        assert response.status_code in (422, 400)


# ── Research endpoint — mocked pipeline ──────────────────────────────────────

class TestResearchEndpointMocked:

    def test_research_returns_200_with_valid_ticker(self, client, mock_pipeline_output):
        with patch("api.main._run_pipeline", return_value=mock_pipeline_output):
            with patch("api.main.generate_pdf", return_value="outputs/AAPL_memo_2026-03-12.pdf"):
                response = client.post("/research", json={"ticker": "AAPL"})
        assert response.status_code == 200

    def test_research_response_has_required_fields(self, client, mock_pipeline_output):
        with patch("api.main._run_pipeline", return_value=mock_pipeline_output):
            with patch("api.main.generate_pdf", return_value="outputs/AAPL_memo_2026-03-12.pdf"):
                response = client.post("/research", json={"ticker": "AAPL"})
        data = response.json()
        required = ["ticker", "company_name", "investment_memo", "risk_assessment",
                    "financial_data", "valuation_result", "status", "recommendation"]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_research_returns_valuation_result(self, client, mock_pipeline_output):
        with patch("api.main._run_pipeline", return_value=mock_pipeline_output):
            with patch("api.main.generate_pdf", return_value="outputs/AAPL_memo_2026-03-12.pdf"):
                response = client.post("/research", json={"ticker": "AAPL"})
        data = response.json()
        assert data["valuation_result"] is not None
        assert "weighted_value" in data["valuation_result"]
        assert "verdict" in data["valuation_result"]

    def test_research_returns_financial_data(self, client, mock_pipeline_output):
        with patch("api.main._run_pipeline", return_value=mock_pipeline_output):
            with patch("api.main.generate_pdf", return_value="outputs/AAPL_memo_2026-03-12.pdf"):
                response = client.post("/research", json={"ticker": "AAPL"})
        data = response.json()
        assert data["financial_data"] is not None
        assert "current_price" in data["financial_data"]

    def test_research_ticker_uppercased(self, client, mock_pipeline_output):
        with patch("api.main._run_pipeline", return_value=mock_pipeline_output):
            with patch("api.main.generate_pdf", return_value="outputs/AAPL_memo_2026-03-12.pdf"):
                response = client.post("/research", json={"ticker": "aapl"})
        data = response.json()
        assert data["ticker"] == "AAPL"

    def test_research_recommendation_uppercased(self, client, mock_pipeline_output):
        with patch("api.main._run_pipeline", return_value=mock_pipeline_output):
            with patch("api.main.generate_pdf", return_value="outputs/AAPL_memo_2026-03-12.pdf"):
                response = client.post("/research", json={"ticker": "AAPL"})
        data = response.json()
        assert data["recommendation"] == data["recommendation"].upper()

    def test_pipeline_error_returns_500(self, client):
        with patch("api.main._run_pipeline", side_effect=Exception("Pipeline crashed")):
            response = client.post("/research", json={"ticker": "AAPL"})
        assert response.status_code == 500

    def test_invalid_ticker_returns_422(self, client):
        with patch("api.main._run_pipeline", side_effect=ValueError("Invalid ticker: FAKE")):
            response = client.post("/research", json={"ticker": "FAKE"})
        assert response.status_code == 422


# ── PDF endpoint ──────────────────────────────────────────────────────────────

class TestPDFEndpoint:

    def test_pdf_returns_404_when_not_found(self, client):
        response = client.get("/pdf/NOTEXIST")
        assert response.status_code == 404

    def test_pdf_404_message_is_helpful(self, client):
        response = client.get("/pdf/NOTEXIST")
        data = response.json()
        assert "detail" in data
        assert "NOTEXIST" in data["detail"] or "research" in data["detail"].lower()

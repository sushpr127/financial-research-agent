"""
test_valuation.py
─────────────────
Unit tests for valuation_agent.py — all 5 models + regime detection + full agent.
Zero API calls. Uses fixture data from conftest.py.

Run: pytest tests/test_valuation.py -v
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agents.valuation_agent import (
    valuation_agent,
    detect_regime,
    model_dcf,
    model_ev_ebitda,
    model_price_to_book,
    model_pe_comps,
    model_revenue_multiple,
    weighted_avg,
    parse_money,
    parse_pct,
    compute_wacc,
)


# ── parse_money tests ─────────────────────────────────────────────────────────

class TestParseMoney:

    def test_parses_billions(self):
        assert parse_money("$90.51B") == pytest.approx(90_510_000_000.0)

    def test_parses_trillions(self):
        assert parse_money("$3.83T") == pytest.approx(3_830_000_000_000.0)

    def test_parses_millions(self):
        assert parse_money("$450.00M") == pytest.approx(450_000_000.0)

    def test_parses_raw_float(self):
        assert parse_money(112_010_000_000) == pytest.approx(112_010_000_000.0)

    def test_returns_zero_for_none(self):
        assert parse_money(None) == 0.0

    def test_returns_zero_for_na(self):
        assert parse_money("N/A") == 0.0


# ── parse_pct tests ───────────────────────────────────────────────────────────

class TestParsePct:

    def test_parses_percent_string(self):
        assert parse_pct("15.70%") == pytest.approx(0.1570)

    def test_parses_small_percent(self):
        assert parse_pct("1.57%") == pytest.approx(0.0157)

    def test_parses_decimal_already(self):
        assert parse_pct(0.157) == pytest.approx(0.157)

    def test_parses_large_float_as_percent(self):
        assert parse_pct(15.7) == pytest.approx(0.157)


# ── compute_wacc tests ────────────────────────────────────────────────────────

class TestComputeWACC:

    def test_wacc_is_positive(self):
        wacc = compute_wacc(beta=1.1, debt=90e9, equity_mktcap=3_800e9)
        assert wacc > 0

    def test_wacc_floored_at_6_percent(self):
        wacc = compute_wacc(beta=0.1, debt=0, equity_mktcap=1e12)
        assert wacc >= 0.06

    def test_higher_beta_means_higher_wacc(self):
        wacc_low  = compute_wacc(beta=0.5, debt=0, equity_mktcap=1e12)
        wacc_high = compute_wacc(beta=2.0, debt=0, equity_mktcap=1e12)
        assert wacc_high > wacc_low

    def test_wacc_zero_total_falls_back_to_re(self):
        wacc = compute_wacc(beta=1.0, debt=0, equity_mktcap=0)
        expected_re = 0.043 + 1.0 * 0.055
        assert wacc == pytest.approx(max(expected_re, 0.06))


# ── weighted_avg tests ────────────────────────────────────────────────────────

class TestWeightedAvg:

    def test_basic_weighted_average(self):
        m1 = {"fair_value": 100}
        m2 = {"fair_value": 200}
        result, _ = weighted_avg([(m1, 0.5), (m2, 0.5)])
        assert result == pytest.approx(150.0)

    def test_skips_none_models(self):
        m1 = {"fair_value": 100}
        result, _ = weighted_avg([(m1, 0.5), (None, 0.5)])
        assert result == pytest.approx(100.0)

    def test_all_none_returns_none(self):
        result = weighted_avg([(None, 0.5), (None, 0.5)])
        assert result is None

    def test_returns_correct_range(self):
        m1 = {"fair_value": 100}
        m2 = {"fair_value": 200}
        _, val_range = weighted_avg([(m1, 0.5), (m2, 0.5)])
        assert val_range == (100.0, 200.0)

    def test_single_model_range_equals_value(self):
        m1 = {"fair_value": 150}
        _, val_range = weighted_avg([(m1, 1.0)])
        assert val_range == (150.0, 150.0)


# ── detect_regime tests ───────────────────────────────────────────────────────

class TestDetectRegime:

    def test_financials_sector_returns_financial(self):
        fin = {"sector": "Financials", "revenue_growth": "5%", "free_cash_flow": 1e9}
        assert detect_regime(fin) == "financial"

    def test_energy_sector_returns_energy(self):
        fin = {"sector": "Energy", "revenue_growth": "5%", "free_cash_flow": 1e9}
        assert detect_regime(fin) == "energy"

    def test_high_growth_returns_high_growth(self):
        fin = {"sector": "Technology", "revenue_growth": "30%", "free_cash_flow": 1e9}
        assert detect_regime(fin) == "high_growth"

    def test_negative_fcf_returns_high_growth(self):
        fin = {"sector": "Consumer", "revenue_growth": "10%", "free_cash_flow": -1e9}
        assert detect_regime(fin) == "high_growth"

    def test_stable_profitable_returns_stable(self):
        fin = {"sector": "Technology", "revenue_growth": "10%", "free_cash_flow": 5e9}
        assert detect_regime(fin) == "stable"


# ── DCF model tests ───────────────────────────────────────────────────────────

class TestModelDCF:

    def test_returns_dict_for_valid_data(self, sample_financial_data):
        result = model_dcf(sample_financial_data)
        assert result is not None
        assert isinstance(result, dict)

    def test_returns_required_keys(self, sample_financial_data):
        result = model_dcf(sample_financial_data)
        assert result is not None
        for key in ["name", "fair_value", "upside_pct", "key_assumption"]:
            assert key in result

    def test_fair_value_is_positive(self, sample_financial_data):
        result = model_dcf(sample_financial_data)
        assert result is not None
        assert result["fair_value"] > 0

    def test_returns_none_without_fcf(self, sample_financial_data):
        data = {**sample_financial_data, "free_cash_flow": None}
        assert model_dcf(data) is None

    def test_returns_none_without_shares(self, sample_financial_data):
        data = {**sample_financial_data, "shares_outstanding": None}
        assert model_dcf(data) is None

    def test_returns_none_without_price(self, sample_financial_data):
        data = {**sample_financial_data, "current_price": None}
        assert model_dcf(data) is None

    def test_key_assumption_mentions_wacc(self, sample_financial_data):
        result = model_dcf(sample_financial_data)
        assert result is not None
        assert "WACC" in result["key_assumption"]

    def test_upside_pct_matches_prices(self, sample_financial_data):
        result = model_dcf(sample_financial_data)
        assert result is not None
        price    = float(sample_financial_data["current_price"])
        expected = round((result["fair_value"] - price) / price * 100, 1)
        assert result["upside_pct"] == pytest.approx(expected, abs=0.2)


# ── EV/EBITDA model tests ─────────────────────────────────────────────────────

class TestModelEVEBITDA:

    def test_returns_dict_for_valid_data(self, sample_financial_data):
        assert model_ev_ebitda(sample_financial_data) is not None

    def test_returns_required_keys(self, sample_financial_data):
        result = model_ev_ebitda(sample_financial_data)
        assert result is not None
        for key in ["name", "fair_value", "upside_pct", "key_assumption"]:
            assert key in result

    def test_returns_none_without_ebitda(self, sample_financial_data):
        data = {**sample_financial_data, "ebitda_raw": None}
        assert model_ev_ebitda(data) is None

    def test_returns_none_for_negative_ebitda(self, sample_financial_data):
        data = {**sample_financial_data, "ebitda_raw": -1_000_000_000}
        assert model_ev_ebitda(data) is None

    def test_higher_multiple_gives_higher_value(self, sample_financial_data):
        r_low  = model_ev_ebitda(sample_financial_data, sector_mult=10.0)
        r_high = model_ev_ebitda(sample_financial_data, sector_mult=25.0)
        if r_low and r_high:
            assert r_high["fair_value"] > r_low["fair_value"]

    def test_key_assumption_mentions_multiple(self, sample_financial_data):
        result = model_ev_ebitda(sample_financial_data, sector_mult=22.0)
        assert result is not None
        assert "22" in result["key_assumption"]


# ── P/E comps model tests ─────────────────────────────────────────────────────

class TestModelPEComps:

    def test_returns_dict_for_valid_data(self, sample_financial_data):
        assert model_pe_comps(sample_financial_data) is not None

    def test_returns_required_keys(self, sample_financial_data):
        result = model_pe_comps(sample_financial_data)
        assert result is not None
        for key in ["name", "fair_value", "upside_pct", "key_assumption"]:
            assert key in result

    def test_returns_none_without_revenue(self, sample_financial_data):
        data = {**sample_financial_data, "total_revenue_raw": None}
        assert model_pe_comps(data) is None

    def test_returns_none_without_shares(self, sample_financial_data):
        data = {**sample_financial_data, "shares_outstanding": None}
        assert model_pe_comps(data) is None

    def test_higher_pe_gives_higher_value(self, sample_financial_data):
        r_low  = model_pe_comps(sample_financial_data, sector_pe=15.0)
        r_high = model_pe_comps(sample_financial_data, sector_pe=35.0)
        if r_low and r_high:
            assert r_high["fair_value"] > r_low["fair_value"]

    def test_negative_margin_returns_none(self, sample_financial_data):
        data = {**sample_financial_data, "operating_margin": "-30%"}
        assert model_pe_comps(data) is None


# ── Price-to-Book model tests ─────────────────────────────────────────────────

class TestModelPriceToBook:

    def test_returns_dict_for_valid_data(self, sample_bank_data):
        assert model_price_to_book(sample_bank_data) is not None

    def test_returns_required_keys(self, sample_bank_data):
        result = model_price_to_book(sample_bank_data)
        assert result is not None
        for key in ["name", "fair_value", "upside_pct", "key_assumption"]:
            assert key in result

    def test_returns_none_without_book_value(self, sample_bank_data):
        data = {**sample_bank_data, "book_value_per_share": None}
        assert model_price_to_book(data) is None

    def test_returns_none_for_zero_book_value(self, sample_bank_data):
        data = {**sample_bank_data, "book_value_per_share": 0}
        assert model_price_to_book(data) is None

    def test_higher_pb_gives_higher_value(self, sample_bank_data):
        r_low  = model_price_to_book(sample_bank_data, sector_pb=1.0)
        r_high = model_price_to_book(sample_bank_data, sector_pb=2.5)
        if r_low and r_high:
            assert r_high["fair_value"] > r_low["fair_value"]

    def test_fair_value_equals_bvps_times_pb(self, sample_bank_data):
        bvps   = float(sample_bank_data["book_value_per_share"])
        pb     = 1.5
        result = model_price_to_book(sample_bank_data, sector_pb=pb)
        if result:
            assert result["fair_value"] == pytest.approx(bvps * pb, abs=0.01)


# ── Revenue multiple model tests ──────────────────────────────────────────────

class TestModelRevenueMultiple:

    def test_returns_dict_for_valid_data(self, sample_noprofit_data):
        assert model_revenue_multiple(sample_noprofit_data) is not None

    def test_returns_required_keys(self, sample_noprofit_data):
        result = model_revenue_multiple(sample_noprofit_data)
        assert result is not None
        for key in ["name", "fair_value", "upside_pct", "key_assumption"]:
            assert key in result

    def test_returns_none_without_revenue(self, sample_noprofit_data):
        data = {**sample_noprofit_data, "total_revenue_raw": None}
        assert model_revenue_multiple(data) is None

    def test_returns_none_without_shares(self, sample_noprofit_data):
        data = {**sample_noprofit_data, "shares_outstanding": None}
        assert model_revenue_multiple(data) is None

    def test_higher_multiple_gives_higher_value(self, sample_noprofit_data):
        r_low  = model_revenue_multiple(sample_noprofit_data, sector_mult=3.0)
        r_high = model_revenue_multiple(sample_noprofit_data, sector_mult=12.0)
        if r_low and r_high:
            assert r_high["fair_value"] > r_low["fair_value"]


# ── Full valuation_agent tests ────────────────────────────────────────────────

class TestValuationAgent:

    def test_returns_valuation_result_key(self, sample_state):
        result = valuation_agent(sample_state)
        assert "valuation_result" in result

    def test_result_is_not_none(self, sample_state):
        result = valuation_agent(sample_state)
        assert result["valuation_result"] is not None

    def test_output_has_required_fields(self, sample_state):
        v = valuation_agent(sample_state)["valuation_result"]
        for field in ["model_type", "regime", "models", "weighted_fair_value",
                      "current_price", "upside_pct", "valuation_range",
                      "verdict", "summary"]:
            assert field in v, f"Missing field: {field}"

    def test_verdict_is_valid(self, sample_state):
        v = valuation_agent(sample_state)["valuation_result"]
        assert v["verdict"] in ("UNDERVALUED", "FAIRLY VALUED", "OVERVALUED")

    def test_valuation_range_low_lte_high(self, sample_state):
        v = valuation_agent(sample_state)["valuation_result"]
        assert v["valuation_range"][0] <= v["valuation_range"][1]

    def test_current_price_matches_input(self, sample_state):
        v = valuation_agent(sample_state)["valuation_result"]
        assert v["current_price"] == float(sample_state["financial_data"]["current_price"])

    def test_upside_pct_is_mathematically_correct(self, sample_state):
        v = valuation_agent(sample_state)["valuation_result"]
        expected = round((v["weighted_fair_value"] - v["current_price"]) / v["current_price"] * 100, 1)
        assert v["upside_pct"] == pytest.approx(expected, abs=0.2)

    def test_models_list_not_empty(self, sample_state):
        v = valuation_agent(sample_state)["valuation_result"]
        assert len(v["models"]) > 0

    def test_each_model_has_required_keys(self, sample_state):
        v = valuation_agent(sample_state)["valuation_result"]
        for m in v["models"]:
            for key in ["name", "fair_value", "upside_pct", "key_assumption", "weight"]:
                assert key in m, f"Model missing key: {key}"

    def test_returns_none_when_no_financial_data(self):
        state = {"ticker": "AAPL", "financial_data": None}
        result = valuation_agent(state)
        assert result["valuation_result"] is None

    def test_returns_none_when_no_price(self, sample_state):
        state = {**sample_state, "financial_data": {
            **sample_state["financial_data"], "current_price": None
        }}
        assert valuation_agent(state)["valuation_result"] is None

    def test_summary_contains_verdict(self, sample_state):
        v = valuation_agent(sample_state)["valuation_result"]
        assert v["verdict"] in v["summary"]

    def test_undervalued_when_price_very_low(self, sample_state):
        state = {**sample_state, "financial_data": {
            **sample_state["financial_data"], "current_price": 10.0
        }}
        v = valuation_agent(state)["valuation_result"]
        if v:
            assert v["verdict"] == "UNDERVALUED"

    def test_overvalued_when_price_very_high(self, sample_state):
        state = {**sample_state, "financial_data": {
            **sample_state["financial_data"], "current_price": 99999.0
        }}
        v = valuation_agent(state)["valuation_result"]
        if v:
            assert v["verdict"] == "OVERVALUED"
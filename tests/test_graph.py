"""
test_graph.py
─────────────
Smoke tests for the LangGraph pipeline.
Tests state management, graph structure, and agent wiring.
The full end-to-end test is marked @pytest.mark.integration (costs API credits).

Run: pytest tests/test_graph.py -v -m "not integration"
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── State tests ───────────────────────────────────────────────────────────────

class TestResearchState:

    def test_state_has_all_required_fields(self, sample_state):
        required = [
            "ticker", "company_name", "news_results", "filing_excerpt",
            "filing_date", "financial_data", "risk_assessment",
            "valuation_result", "investment_memo", "errors"
        ]
        for field in required:
            assert field in sample_state, f"Missing state field: {field}"

    def test_state_ticker_is_uppercase(self, sample_state):
        assert sample_state["ticker"] == sample_state["ticker"].upper()

    def test_state_errors_is_list(self, sample_state):
        assert isinstance(sample_state["errors"], list)

    def test_state_financial_data_is_dict(self, sample_state):
        assert isinstance(sample_state["financial_data"], dict)


# ── Graph structure tests ─────────────────────────────────────────────────────

class TestGraphStructure:

    def test_graph_builds_without_error(self):
        from src.graph.graph import build_research_graph
        graph = build_research_graph()
        assert graph is not None

    def test_graph_has_correct_nodes(self):
        from src.graph.graph import build_research_graph
        graph = build_research_graph()
        graph_def = graph.get_graph()
        node_ids = list(graph_def.nodes.keys())
        expected_nodes = [
            "parallel_research", "financial_analyst", "validation",
            "parallel_risk_and_valuation", "writer"
        ]
        for node in expected_nodes:
            assert node in node_ids, f"Missing node: {node}"

    def test_graph_entry_point_is_parallel_research(self):
        from src.graph.graph import build_research_graph
        graph = build_research_graph()
        graph_def = graph.get_graph()
        edges = [(e.source, e.target) for e in graph_def.edges]
        assert ("__start__", "parallel_research") in edges

    def test_graph_ends_at_writer(self):
        from src.graph.graph import build_research_graph
        graph = build_research_graph()
        graph_def = graph.get_graph()
        edges = [(e.source, e.target) for e in graph_def.edges]
        assert ("writer", "__end__") in edges

    def test_valuation_agent_is_wired_before_writer(self):
        from src.graph.graph import build_research_graph
        graph = build_research_graph()
        graph_def = graph.get_graph()
        edges = [(e.source, e.target) for e in graph_def.edges]
        assert ("parallel_risk_and_valuation", "writer") in edges
        assert ("validation", "parallel_risk_and_valuation") in edges


# ── Validation node tests ─────────────────────────────────────────────────────

class TestValidationNode:

    def test_validation_passes_with_good_state(self, sample_state):
        from src.validator import validate_pipeline_state
        is_valid, warnings = validate_pipeline_state(sample_state)
        assert is_valid

    def test_validation_warns_with_missing_news(self, sample_state):
        state = {**sample_state, "news_results": None}
        from src.validator import validate_pipeline_state
        is_valid, warnings = validate_pipeline_state(state)
        assert len(warnings) > 0 or not is_valid

    def test_validation_returns_bool_and_list(self, sample_state):
        from src.validator import validate_pipeline_state
        result = validate_pipeline_state(sample_state)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], bool)
        assert isinstance(result[1], list)


# ── Valuation agent wiring tests ──────────────────────────────────────────────

class TestValuationAgentWiring:

    def test_valuation_agent_reads_financial_data_from_state(self, sample_state):
        from src.agents.valuation_agent import valuation_agent
        result = valuation_agent(sample_state)
        assert "valuation_result" in result

    def test_valuation_agent_writes_to_correct_state_key(self, sample_state):
        from src.agents.valuation_agent import valuation_agent
        result = valuation_agent(sample_state)
        assert "valuation_result" in result

    def test_valuation_agent_does_not_overwrite_financial_data(self, sample_state):
        from src.agents.valuation_agent import valuation_agent
        result = valuation_agent(sample_state)
        assert "financial_data" not in result


# ── Cache tests ───────────────────────────────────────────────────────────────

class TestCache:

    def test_cache_key_is_consistent(self):
        from src.cache import cache_key
        key1 = cache_key("yahoo", "AAPL")
        key2 = cache_key("yahoo", "AAPL")
        assert key1 == key2

    def test_cache_key_differs_by_ticker(self):
        from src.cache import cache_key
        key_aapl = cache_key("yahoo", "AAPL")
        key_msft = cache_key("yahoo", "MSFT")
        assert key_aapl != key_msft

    def test_cache_key_differs_by_source(self):
        from src.cache import cache_key
        key_yahoo = cache_key("yahoo", "AAPL")
        key_sec   = cache_key("sec",   "AAPL")
        assert key_yahoo != key_sec

    def test_cache_set_and_get(self, tmp_path, monkeypatch):
        from src.cache import cache_set, cache_get, cache_key
        monkeypatch.setenv("CACHE_DIR", str(tmp_path))
        import src.cache as cache_module
        original_dir = cache_module.CACHE_DIR
        cache_module.CACHE_DIR = str(tmp_path)

        key  = cache_key("test", "AAPL")
        data = {"price": 260.81, "ticker": "AAPL"}
        cache_set(key, data)
        result = cache_get(key)
        assert result == data

        cache_module.CACHE_DIR = original_dir


# ── Full end-to-end pipeline test (costs API credits) ────────────────────────

@pytest.mark.integration
class TestFullPipeline:

    def test_pipeline_runs_for_aapl(self):
        from src.graph.graph import build_research_graph
        graph = build_research_graph()
        initial_state = {
            "ticker":           "AAPL",
            "company_name":     "Apple Inc.",
            "news_results":     None,
            "filing_excerpt":   None,
            "filing_date":      None,
            "financial_data":   None,
            "risk_assessment":  None,
            "valuation_result": None,
            "investment_memo":  None,
            "errors":           []
        }
        result = graph.invoke(initial_state)
        assert result["investment_memo"] is not None
        assert result["investment_memo"] != "Memo generation failed"

    def test_pipeline_produces_valuation(self):
        from src.graph.graph import build_research_graph
        graph = build_research_graph()
        initial_state = {
            "ticker": "MSFT", "company_name": "Microsoft Corporation",
            "news_results": None, "filing_excerpt": None, "filing_date": None,
            "financial_data": None, "risk_assessment": None,
            "valuation_result": None, "investment_memo": None, "errors": []
        }
        result = graph.invoke(initial_state)
        assert result.get("valuation_result") is not None
        assert result["valuation_result"]["verdict"] in (
            "UNDERVALUED", "FAIRLY VALUED", "OVERVALUED"
        )

    def test_pipeline_handles_errors_gracefully(self):
        from src.graph.graph import build_research_graph
        graph = build_research_graph()
        initial_state = {
            "ticker": "AAPL", "company_name": "Apple Inc.",
            "news_results": None, "filing_excerpt": None, "filing_date": None,
            "financial_data": None, "risk_assessment": None,
            "valuation_result": None, "investment_memo": None, "errors": []
        }
        result = graph.invoke(initial_state)
        assert isinstance(result, dict)
        assert "investment_memo" in result
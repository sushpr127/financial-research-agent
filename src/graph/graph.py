from langgraph.graph import StateGraph, END
from src.graph.state import ResearchState
from src.agents.researcher import researcher_agent
from src.agents.filing_parser import filing_parser_agent
from src.agents.financial_analyst import financial_analyst_agent
from src.agents.risk_scorer import risk_scorer_agent
from src.agents.writer import writer_agent
from src.validator import validate_pipeline_state


def validation_node(state: ResearchState) -> dict:
    """
    Runs between data-gathering agents and LLM agents.
    Checks that we have enough data to produce a meaningful memo.
    Logs warnings but never blocks the pipeline — graceful degradation.
    """
    is_valid, warnings = validate_pipeline_state(state)

    if warnings:
        print("\n⚠️  Pipeline validation warnings:")
        for w in warnings:
            print(f"   - {w}")

    if not is_valid:
        print("   ❌ Critical: all data sources failed. Memo quality will be very low.")

    return {}  # validation node doesn't modify state


def parallel_research(state: ResearchState) -> dict:
    """
    Runs Researcher and FilingParser in parallel using Python threads.
    Merges both results into state.
    This is genuine parallel execution — both hit external APIs simultaneously.
    """
    import concurrent.futures

    results = {}

    def run_researcher():
        return researcher_agent(state)

    def run_filing_parser():
        return filing_parser_agent(state)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_researcher    = executor.submit(run_researcher)
        future_filing_parser = executor.submit(run_filing_parser)

        researcher_result    = future_researcher.result()
        filing_parser_result = future_filing_parser.result()

    # Merge both results
    results.update(researcher_result)
    results.update(filing_parser_result)

    # Merge errors from both
    errors = []
    if researcher_result.get("errors"):
        errors.extend(researcher_result["errors"])
    if filing_parser_result.get("errors"):
        errors.extend(filing_parser_result["errors"])
    if errors:
        results["errors"] = (state.get("errors") or []) + errors

    return results


def build_research_graph():
    """
    Build the multi-agent research graph.

    Flow:
    [parallel_research] ──> [financial_analyst] ──> [validation] ──> [risk_scorer] ──> [writer] ──> END

    parallel_research runs Researcher + FilingParser simultaneously.
    validation checks data quality before expensive LLM calls.
    """
    graph = StateGraph(ResearchState)

    # Add nodes
    graph.add_node("parallel_research",  parallel_research)
    graph.add_node("financial_analyst",  financial_analyst_agent)
    graph.add_node("validation",         validation_node)
    graph.add_node("risk_scorer",        risk_scorer_agent)
    graph.add_node("writer",             writer_agent)

    # Wire the graph
    graph.set_entry_point("parallel_research")
    graph.add_edge("parallel_research", "financial_analyst")
    graph.add_edge("financial_analyst", "validation")
    graph.add_edge("validation",        "risk_scorer")
    graph.add_edge("risk_scorer",       "writer")
    graph.add_edge("writer",            END)

    return graph.compile()


if __name__ == "__main__":
    from dotenv import load_dotenv
    from src.validator import validate_ticker
    load_dotenv()

    ticker_input = "AAPL"

    # Validate before running
    print(f"Validating ticker: {ticker_input}...")
    is_valid, result = validate_ticker(ticker_input)

    if not is_valid:
        print(f"❌ {result}")
        exit(1)

    company_name = result
    print(f"✅ Valid ticker: {company_name}\n")

    app = build_research_graph()

    initial_state = {
        "ticker":           ticker_input.upper(),
        "company_name":     company_name,
        "news_results":     None,
        "filing_excerpt":   None,
        "filing_date":      None,
        "financial_data":   None,
        "risk_assessment":  None,
        "investment_memo":  None,
        "errors":           []
    }

    print("=" * 50)
    print(f"Running research pipeline for {ticker_input}")
    print("=" * 50 + "\n")

    result = app.invoke(initial_state)

    print("\n" + "=" * 50)
    print("FINAL INVESTMENT MEMO")
    print("=" * 50)
    print(result["investment_memo"])

    if result.get("errors"):
        print("\n⚠️  Errors encountered:")
        for err in result["errors"]:
            print(f"   - {err}")
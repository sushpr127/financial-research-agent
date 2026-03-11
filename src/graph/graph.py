from langgraph.graph import StateGraph, END
from src.graph.state import ResearchState
from src.agents.researcher import researcher_agent
from src.agents.filing_parser import filing_parser_agent
from src.agents.financial_analyst import financial_analyst_agent
from src.agents.risk_scorer import risk_scorer_agent
from src.agents.valuation_agent import valuation_agent
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

    return {}


def parallel_research(state: ResearchState) -> dict:
    """
    Runs Researcher and FilingParser in parallel using Python threads.
    Merges both results into state.
    """
    import concurrent.futures

    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_researcher    = executor.submit(researcher_agent,    state)
        future_filing_parser = executor.submit(filing_parser_agent, state)

        researcher_result    = future_researcher.result()
        filing_parser_result = future_filing_parser.result()

    results.update(researcher_result)
    results.update(filing_parser_result)

    errors = []
    if researcher_result.get("errors"):
        errors.extend(researcher_result["errors"])
    if filing_parser_result.get("errors"):
        errors.extend(filing_parser_result["errors"])
    if errors:
        results["errors"] = (state.get("errors") or []) + errors

    return results


def parallel_risk_and_valuation(state: ResearchState) -> dict:
    """
    Runs risk_scorer and valuation_agent in parallel — both only read financial_data.
    Saves ~10-15 seconds on every run.
    """
    import concurrent.futures

    results = {}

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_risk      = executor.submit(risk_scorer_agent, state)
        future_valuation = executor.submit(valuation_agent,   state)

        risk_result      = future_risk.result()
        valuation_result = future_valuation.result()

    results.update(risk_result)
    results.update(valuation_result)

    errors = []
    if risk_result.get("errors"):
        errors.extend(risk_result["errors"])
    if errors:
        results["errors"] = (state.get("errors") or []) + errors

    return results


def build_research_graph():
    """
    Build the multi-agent research graph.

    Flow:
    [parallel_research]
         ↓
    [financial_analyst]
         ↓
    [validation]
         ↓
    [parallel_risk_and_valuation]   ← risk + valuation run simultaneously
         ↓
    [writer]
         ↓
    END
    """
    graph = StateGraph(ResearchState)

    graph.add_node("parallel_research",          parallel_research)
    graph.add_node("financial_analyst",          financial_analyst_agent)
    graph.add_node("validation",                 validation_node)
    graph.add_node("parallel_risk_and_valuation", parallel_risk_and_valuation)
    graph.add_node("writer",                     writer_agent)

    graph.set_entry_point("parallel_research")
    graph.add_edge("parallel_research",           "financial_analyst")
    graph.add_edge("financial_analyst",           "validation")
    graph.add_edge("validation",                  "parallel_risk_and_valuation")
    graph.add_edge("parallel_risk_and_valuation", "writer")
    graph.add_edge("writer",                      END)

    return graph.compile()


if __name__ == "__main__":
    from dotenv import load_dotenv
    from src.validator import validate_ticker
    load_dotenv()

    ticker_input = "AAPL"

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
        "valuation_result": None,
        "investment_memo":  None,
        "errors":           []
    }

    print("=" * 50)
    print(f"Running research pipeline for {ticker_input}")
    print("=" * 50 + "\n")

    result = app.invoke(
        initial_state,
        config={
            "run_name": f"research_{ticker_input.upper()}",
            "tags": ["financial-research", ticker_input.upper()],
            "metadata": {
                "ticker":  ticker_input.upper(),
                "company": company_name,
                "version": "1.1"
            }
        }
    )

    print("\n" + "=" * 50)
    print("VALUATION RESULT")
    print("=" * 50)
    vr = result.get("valuation_result")
    if vr:
        print(f"Model type:   {vr['model_type']}")
        print(f"Fair value:   ${vr['weighted_fair_value']:.2f}")
        print(f"Upside:       {vr['upside_pct']:+.1f}%")
        print(f"Range:        ${vr['valuation_range'][0]} – ${vr['valuation_range'][1]}")
        print(f"Verdict:      {vr['verdict']}")
    else:
        print("No valuation result produced.")

    print("\n" + "=" * 50)
    print("FINAL INVESTMENT MEMO")
    print("=" * 50)
    print(result["investment_memo"])

    if result.get("errors"):
        print("\n⚠️  Errors encountered:")
        for err in result["errors"]:
            print(f"   - {err}")
from langgraph.graph import StateGraph, END
from src.graph.state import ResearchState
from src.agents.researcher import researcher_agent
from src.agents.filing_parser import filing_parser_agent
from src.agents.financial_analyst import financial_analyst_agent
from src.agents.risk_scorer import risk_scorer_agent
from src.agents.writer import writer_agent

def build_research_graph():
    """
    Build the multi-agent research graph.
    
    Flow:
    researcher ──┐
                 ├──> financial_analyst ──> risk_scorer ──> writer
    filing_parser┘
    
    Researcher and FilingParser run in PARALLEL.
    Then FinancialAnalyst runs (uses Yahoo, independent).
    Then RiskScorer synthesizes everything.
    Then Writer produces the final memo.
    """
    
    graph = StateGraph(ResearchState)
    
    # Add all nodes
    graph.add_node("researcher", researcher_agent)
    graph.add_node("filing_parser", filing_parser_agent)
    graph.add_node("financial_analyst", financial_analyst_agent)
    graph.add_node("risk_scorer", risk_scorer_agent)
    graph.add_node("writer", writer_agent)
    
    # Parallel start — both researcher and filing_parser run first simultaneously
    graph.set_entry_point("researcher")
    graph.add_edge("researcher", "financial_analyst")
    
    # filing_parser also starts at entry (parallel branch)
    graph.add_node("filing_parser_start", filing_parser_agent)
    graph.set_entry_point("filing_parser_start")
    graph.add_edge("filing_parser_start", "financial_analyst")
    
    # After both parallel branches feed into financial_analyst
    graph.add_edge("financial_analyst", "risk_scorer")
    graph.add_edge("risk_scorer", "writer")
    graph.add_edge("writer", END)
    
    return graph.compile()


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    print("Building research graph...\n")
    app = build_research_graph()
    
    # Initial state
    initial_state = {
        "ticker": "AAPL",
        "company_name": "Apple Inc",
        "news_results": None,
        "filing_excerpt": None,
        "filing_date": None,
        "financial_data": None,
        "risk_assessment": None,
        "investment_memo": None,
        "errors": []
    }
    
    print("=" * 50)
    print(f"Running research pipeline for AAPL")
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
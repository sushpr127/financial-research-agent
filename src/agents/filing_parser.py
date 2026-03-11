from src.tools.sec_tool import get_latest_10k_text
from src.graph.state import ResearchState

def filing_parser_agent(state: ResearchState) -> dict:
    """
    Fetches and parses the latest 10-K SEC filing.
    Reads:  ticker
    Writes: filing_excerpt, filing_date
    """
    print(f"📄 FilingParser: fetching 10-K for {state['ticker']}...")
    
    try:
        result = get_latest_10k_text(state["ticker"])
        print(f"   Filing date: {result['filing_date']}")
        return {
            "filing_excerpt": result["excerpt"],
            "filing_date": result["filing_date"]
        }
    except Exception as e:
        print(f"   ❌ FilingParser failed: {e}")
        return {
            "filing_excerpt": "Filing not available",
            "filing_date": "Unknown",
            "errors": (state.get("errors") or []) + [f"FilingParser: {str(e)}"]
        }
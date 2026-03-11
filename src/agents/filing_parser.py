from src.tools.sec_tool import get_latest_10k_text
from src.graph.state import ResearchState

def filing_parser_agent(state: ResearchState) -> dict:
    """
    Fetches and parses the latest 10-K SEC filing.
    Extracts: business overview, risk factors, and MD&A sections.
    """
    print(f"📄 FilingParser: fetching 10-K for {state['ticker']}...")

    try:
        result = get_latest_10k_text(state["ticker"])
        print(f"   Filing date: {result['filing_date']}")
        print(f"   Business overview: {len(result['business_overview'])} chars")
        print(f"   Risk factors: {len(result['risk_factors'])} chars")
        print(f"   MD&A: {len(result['management_discussion'])} chars")

        combined = f"""
=== BUSINESS OVERVIEW ===
{result['business_overview']}

=== RISK FACTORS (from 10-K) ===
{result['risk_factors']}

=== MANAGEMENT DISCUSSION & ANALYSIS ===
{result['management_discussion']}
""".strip()

        return {
            "filing_excerpt": combined,
            "filing_date": result["filing_date"]
        }
    except Exception as e:
        print(f"   ❌ FilingParser failed: {e}")
        return {
            "filing_excerpt": "Filing not available",
            "filing_date": "Unknown",
            "errors": (state.get("errors") or []) + [f"FilingParser: {str(e)}"]
        }
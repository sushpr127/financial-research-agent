from src.tools.tavily_tool import search_company_news
from src.graph.state import ResearchState

def researcher_agent(state: ResearchState) -> dict:
    """
    Searches for recent news and sentiment about the company.
    Reads:  ticker, company_name
    Writes: news_results
    """
    print(f"🔍 Researcher: searching news for {state['company_name']}...")
    
    try:
        results = search_company_news(state["company_name"])
        print(f"   Found {len(results)} articles")
        return {"news_results": results}
    except Exception as e:
        print(f"   ❌ Researcher failed: {e}")
        return {
            "news_results": [],
            "errors": (state.get("errors") or []) + [f"Researcher: {str(e)}"]
        }
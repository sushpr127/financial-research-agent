from src.tools.tavily_tool import search_company_news
from src.graph.state import ResearchState
from src.config import MAX_RETRIES
import time

def researcher_agent(state: ResearchState) -> dict:
    print(f"🔍 Researcher: searching news for {state['company_name']}...")

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            results = search_company_news(state["company_name"])
            if results:
                print(f"   Found {len(results)} articles")
                return {"news_results": results}
            else:
                print(f"   Attempt {attempt}: empty results, retrying...")
        except Exception as e:
            print(f"   Attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(1)

    print("   ❌ Researcher failed after all retries")
    return {
        "news_results": [],
        "errors": (state.get("errors") or []) + ["Researcher: failed after retries"]
    }
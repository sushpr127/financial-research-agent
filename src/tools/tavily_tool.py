from tavily import TavilyClient
from dotenv import load_dotenv
import os

load_dotenv()

def search_company_news(company_name: str, max_results: int = 5) -> list[dict]:
    """
    Search for recent news about a company.
    Returns a list of dicts with title, url, and content.
    """
    client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    
    query = f"{company_name} stock news earnings financial performance 2025"
    
    response = client.search(
        query=query,
        search_depth="advanced",
        max_results=max_results
    )
    
    results = []
    for item in response.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "content": item.get("content", "")
        })
    
    return results


if __name__ == "__main__":
    print("Testing Tavily Search Tool...\n")
    results = search_company_news("Apple Inc")
    
    for i, r in enumerate(results, 1):
        print(f"Result {i}:")
        print(f"  Title: {r['title']}")
        print(f"  URL:   {r['url']}")
        print(f"  Preview: {r['content'][:150]}...")
        print()
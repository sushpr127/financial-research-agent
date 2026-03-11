from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.graph.state import ResearchState
from dotenv import load_dotenv
import os

load_dotenv()

def risk_scorer_agent(state: ResearchState) -> dict:
    """
    Uses Gemini to classify risk factors from all gathered data.
    Reads:  news_results, filing_excerpt, financial_data
    Writes: risk_assessment
    """
    print(f"⚠️  RiskScorer: analyzing risks for {state['ticker']}...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.2
    )
    
    # Build context from previous agents
    news_summary = ""
    for item in (state.get("news_results") or [])[:3]:
        news_summary += f"- {item['title']}\n"
    
    financial_flags = ""
    fin_data = state.get("financial_data") or {}
    flags = fin_data.get("analyst_flags", [])
    if flags:
        financial_flags = "\n".join(flags)
    else:
        financial_flags = "No major flags detected"
    
    filing_snippet = (state.get("filing_excerpt") or "")[:500]
    
    prompt = f"""You are a risk analyst. Based on the following data about {state['company_name']} ({state['ticker']}), 
provide a concise risk assessment with:
1. Overall Risk Level: LOW / MEDIUM / HIGH
2. Top 3 risk factors (one sentence each)
3. One key mitigating factor

RECENT NEWS:
{news_summary}

FINANCIAL FLAGS:
{financial_flags}

10-K EXCERPT:
{filing_snippet}

Keep your response under 200 words. Be specific and factual."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        risk_text = response.content
        print(f"   Risk assessment complete")
        return {"risk_assessment": risk_text}
    except Exception as e:
        print(f"   ❌ RiskScorer failed: {e}")
        return {
            "risk_assessment": "Risk assessment unavailable",
            "errors": (state.get("errors") or []) + [f"RiskScorer: {str(e)}"]
        }
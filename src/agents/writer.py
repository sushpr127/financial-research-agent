from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from src.graph.state import ResearchState
from dotenv import load_dotenv
import os

load_dotenv()

def writer_agent(state: ResearchState) -> dict:
    """
    Synthesizes all research into a structured investment memo.
    Reads:  everything
    Writes: investment_memo
    """
    print(f"✍️  Writer: composing investment memo for {state['ticker']}...")
    
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=os.getenv("GEMINI_API_KEY"),
        temperature=0.3
    )
    
    # Gather all context
    fin = state.get("financial_data") or {}
    news = state.get("news_results") or []
    news_titles = "\n".join([f"- {n['title']}" for n in news[:5]])
    
    prompt = f"""You are a senior equity research analyst. Write a professional investment memo for {state['company_name']} ({state['ticker']}).

Use this data:

FINANCIALS:
- Revenue: {fin.get('revenue_ttm', 'N/A')}
- Gross Margin: {fin.get('gross_margin', 'N/A')}
- P/E Ratio: {fin.get('pe_ratio', 'N/A')}
- Revenue Growth: {fin.get('revenue_growth', 'N/A')}
- Debt/Equity: {fin.get('debt_to_equity', 'N/A')}
- Analyst Recommendation: {fin.get('analyst_recommendation', 'N/A')}
- Price Target: {fin.get('target_price', 'N/A')}

RECENT NEWS:
{news_titles}

RISK ASSESSMENT:
{state.get('risk_assessment', 'N/A')}

10-K FILING DATE: {state.get('filing_date', 'N/A')}

Write the memo with these exact sections:
## Executive Summary
## Financial Highlights
## Recent Developments
## Risk Factors
## Valuation & Recommendation

Keep it under 400 words. Write like a Goldman Sachs analyst — precise, data-driven, no fluff."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        memo = response.content
        print(f"   Memo written ({len(memo)} chars)")
        return {"investment_memo": memo}
    except Exception as e:
        print(f"   ❌ Writer failed: {e}")
        return {
            "investment_memo": "Memo generation failed",
            "errors": (state.get("errors") or []) + [f"Writer: {str(e)}"]
        }
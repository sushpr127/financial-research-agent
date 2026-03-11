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

    fin = state.get("financial_data") or {}
    news = state.get("news_results") or []
    news_titles = "\n".join([f"- {n['title']}" for n in news[:5]])

    prompt = f"""You are a senior equity research analyst at Goldman Sachs.
Write a professional, data-driven investment memo for {state['company_name']} ({state['ticker']}).

ALL DATA FOR THIS MEMO:

FINANCIALS (from Yahoo Finance):
- Revenue (TTM): {fin.get('revenue_ttm', 'N/A')}
- Gross Margin: {fin.get('gross_margin', 'N/A')}
- Operating Margin: {fin.get('operating_margin', 'N/A')}
- Net Margin: {fin.get('profit_margin', 'N/A')}
- P/E Ratio: {fin.get('pe_ratio', 'N/A')}
- Forward P/E: {fin.get('forward_pe', 'N/A')}
- Revenue Growth YoY: {fin.get('revenue_growth', 'N/A')}
- Earnings Growth YoY: {fin.get('earnings_growth', 'N/A')}
- Total Debt: {fin.get('total_debt', 'N/A')}
- Total Cash: {fin.get('total_cash', 'N/A')}
- Debt/Equity: {fin.get('debt_to_equity', 'N/A')}
- Return on Equity: {fin.get('return_on_equity', 'N/A')}
- Current Ratio: {fin.get('current_ratio', 'N/A')}
- Analyst Consensus: {str(fin.get('analyst_recommendation', 'N/A')).upper()}
- Analyst Price Target: ${fin.get('target_price', 'N/A')}
- Number of Analysts: {fin.get('number_of_analysts', 'N/A')}
- Analyst Flags: {', '.join(fin.get('analyst_flags', [])) or 'None'}

RECENT NEWS:
{news_titles}

RISK ASSESSMENT:
{state.get('risk_assessment', 'N/A')}

10-K FILING DATE: {state.get('filing_date', 'N/A')}
10-K KEY SECTIONS:
{(state.get('filing_excerpt') or '')[:1000]}

Write the memo with EXACTLY these sections. Be specific — cite actual numbers.
Never write vague sentences like "strong performance" without a number behind it.

## Executive Summary
[3-4 sentences: what the company does, headline financial performance, overall stance]

## Financial Highlights
[6-8 bullet points with specific numbers — revenue, margins, growth, valuation multiples]

## Recent Developments
[3-4 sentences on what the news tells us about current momentum]

## Risk Factors
[3 numbered risks, each with the specific data point that flags it]

## Valuation & Recommendation
[Price target justification, upside/downside from current price of {fin.get('current_price', 'N/A')}, final recommendation]

Tone: precise, institutional, zero fluff. Every claim must have a number."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        memo = response.content

        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            if isinstance(usage, dict):
                input_tokens  = usage.get('input_tokens') or usage.get('prompt_token_count', 0)
                output_tokens = usage.get('output_tokens') or usage.get('candidates_token_count', 0)
            else:
                input_tokens  = getattr(usage, 'input_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', 0)
            print(f"   Tokens — in: {input_tokens} out: {output_tokens}")

        print(f"   Memo written ({len(memo)} chars)")
        return {"investment_memo": memo}

    except Exception as e:
        print(f"   ❌ Writer failed: {e}")
        return {
            "investment_memo": "Memo generation failed",
            "errors": (state.get("errors") or []) + [f"Writer: {str(e)}"]
        }
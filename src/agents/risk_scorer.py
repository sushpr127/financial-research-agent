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

    filing_snippet = (state.get("filing_excerpt") or "")[:1500]

    prompt = f"""You are a senior risk analyst at a top-tier investment bank.
Analyze {state['company_name']} ({state['ticker']}) using the data below.

FINANCIAL FLAGS FROM QUANTITATIVE ANALYSIS:
{financial_flags}

RECENT NEWS HEADLINES:
{news_summary}

OFFICIAL 10-K RISK FACTORS & MD&A (from SEC filing dated {state.get('filing_date', 'N/A')}):
{filing_snippet}

Provide a structured risk assessment with EXACTLY this format:

OVERALL RISK LEVEL: [LOW / MEDIUM / HIGH]

TOP RISKS:
1. [Risk name]: [One precise sentence with specific data if available]
2. [Risk name]: [One precise sentence with specific data if available]
3. [Risk name]: [One precise sentence with specific data if available]

KEY MITIGATING FACTOR:
[One sentence on the strongest reason this company can handle these risks]

RISK SCORE: [X/10]

Be specific. Reference actual numbers from the data. Do not generalize."""

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        risk_text = response.content

        # Log token usage if available
        if hasattr(response, 'usage_metadata') and response.usage_metadata:
            usage = response.usage_metadata
            # usage_metadata can be a dict or object depending on LangChain version
            if isinstance(usage, dict):
                input_tokens  = usage.get('input_tokens') or usage.get('prompt_token_count', 0)
                output_tokens = usage.get('output_tokens') or usage.get('candidates_token_count', 0)
            else:
                input_tokens  = getattr(usage, 'input_tokens', 0)
                output_tokens = getattr(usage, 'output_tokens', 0)
            print(f"   Tokens — in: {input_tokens} out: {output_tokens}")

    except Exception as e:
        print(f"   ❌ RiskScorer failed: {e}")
        return {
            "risk_assessment": "Risk assessment unavailable",
            "errors": (state.get("errors") or []) + [f"RiskScorer: {str(e)}"]
        }
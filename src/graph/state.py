from typing import TypedDict, Optional

class ResearchState(TypedDict):
    # Input
    ticker: str
    company_name: str

    # Agent outputs — each agent fills in its section
    news_results:     Optional[list[dict]]
    filing_excerpt:   Optional[str]
    filing_date:      Optional[str]
    financial_data:   Optional[dict]
    risk_assessment:  Optional[str]
    valuation_result: Optional[dict]   # ← NEW: multi-model valuation output
    investment_memo:  Optional[str]

    # Tracking
    errors: Optional[list[str]]
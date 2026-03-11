from src.tools.yahoo_tool import get_financial_data
from src.graph.state import ResearchState

def financial_analyst_agent(state: ResearchState) -> dict:
    """
    Fetches financial metrics and computes key ratios.
    Reads:  ticker
    Writes: financial_data
    """
    print(f"📊 FinancialAnalyst: pulling metrics for {state['ticker']}...")
    
    try:
        data = get_financial_data(state["ticker"])
        
        # Add computed analysis flags
        pe = data.get("pe_ratio", "N/A")
        debt_equity = data.get("debt_to_equity", "N/A")
        current_ratio = data.get("current_ratio", "N/A")
        
        flags = []
        if isinstance(pe, float) and pe > 40:
            flags.append("HIGH_VALUATION: P/E above 40")
        if isinstance(debt_equity, float) and debt_equity > 150:
            flags.append("HIGH_LEVERAGE: Debt/Equity above 150")
        if isinstance(current_ratio, float) and current_ratio < 1.0:
            flags.append("LIQUIDITY_RISK: Current ratio below 1.0")
            
        data["analyst_flags"] = flags
        print(f"   Metrics fetched. Flags: {flags if flags else 'None'}")
        return {"financial_data": data}
    except Exception as e:
        print(f"   ❌ FinancialAnalyst failed: {e}")
        return {
            "financial_data": {},
            "errors": (state.get("errors") or []) + [f"FinancialAnalyst: {str(e)}"]
        }
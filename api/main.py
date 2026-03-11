import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import asyncio
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

from src.validator import validate_ticker
from src.graph.graph import build_research_graph
from src.output.pdf_generator import generate_pdf

app = FastAPI(
    title="Financial Research Agent API",
    description="AI-powered investment research pipeline",
    version="1.0.0"
)

# Allow React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

executor = ThreadPoolExecutor(max_workers=4)


class ResearchRequest(BaseModel):
    ticker: str


class ResearchResponse(BaseModel):
    ticker: str
    company_name: str
    investment_memo: str
    risk_assessment: str
    filing_date: str
    pdf_path: str | None
    errors: list[str]
    status: str


def _run_pipeline(ticker: str) -> dict:
    """Run the full research pipeline synchronously."""
    # Validate ticker
    is_valid, result = validate_ticker(ticker)
    if not is_valid:
        raise ValueError(f"Invalid ticker: {result}")

    company_name = result

    # Build and run graph
    graph = build_research_graph()
    initial_state = {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "news_results": None,
        "filing_excerpt": None,
        "filing_date": None,
        "financial_data": None,
        "risk_assessment": None,
        "investment_memo": None,
        "errors": []
    }

    output = graph.invoke(
        initial_state,
        config={
            "run_name": f"research_{ticker.upper()}",
            "tags": ["financial-research", ticker.upper()],
            "metadata": {"ticker": ticker.upper(), "version": "1.0"}
        }
    )

    return output


@app.get("/")
def root():
    return {
        "message": "Financial Research Agent API",
        "version": "1.0.0",
        "endpoints": {
            "POST /research": "Run full research pipeline for a ticker",
            "GET  /health":   "Health check",
            "GET  /pdf/{ticker}": "Download PDF report"
        }
    }


@app.get("/health")
def health():
    return {"status": "ok", "service": "financial-research-agent"}


@app.post("/research", response_model=ResearchResponse)
async def research(request: ResearchRequest):
    ticker = request.ticker.strip().upper()

    if not ticker:
        raise HTTPException(status_code=400, detail="Ticker is required")

    if len(ticker) > 10:
        raise HTTPException(status_code=400, detail="Invalid ticker format")

    print(f"\n🚀 API: Starting research for {ticker}")

    try:
        # Run blocking pipeline in thread pool so FastAPI stays responsive
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(executor, _run_pipeline, ticker)

    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline error: {str(e)}")

    memo         = output.get("investment_memo") or ""
    risk         = output.get("risk_assessment") or ""
    filing_date  = output.get("filing_date") or "Unknown"
    financial    = output.get("financial_data") or {}
    company_name = output.get("company_name", ticker)
    errors       = output.get("errors") or []

    # Generate PDF
    pdf_path = None
    if memo and memo != "Memo generation failed":
        try:
            pdf_path = generate_pdf(
                memo_text=memo,
                ticker=ticker,
                company_name=company_name,
                financial_data=financial,
                risk_assessment=risk,
                output_dir="outputs"
            )
            print(f"   ✅ PDF generated: {pdf_path}")
        except Exception as e:
            print(f"   ⚠️  PDF generation failed: {e}")
            errors.append(f"PDF: {str(e)}")

    status = "success" if memo and memo != "Memo generation failed" else "partial"
    if errors:
        status = "partial"

    print(f"   ✅ Research complete for {ticker} — status: {status}")

    return ResearchResponse(
        ticker=ticker,
        company_name=company_name,
        investment_memo=memo,
        risk_assessment=risk,
        filing_date=filing_date,
        pdf_path=pdf_path,
        errors=errors,
        status=status
    )


@app.get("/pdf/{ticker}")
def download_pdf(ticker: str):
    """Download the most recently generated PDF for a ticker."""
    from datetime import date
    today    = date.today().strftime("%Y-%m-%d")
    filepath = f"outputs/{ticker.upper()}_memo_{today}.pdf"

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404,
            detail=f"No PDF found for {ticker} today. Run /research first.")

    return FileResponse(
        filepath,
        media_type="application/pdf",
        filename=f"{ticker.upper()}_Investment_Memo_{today}.pdf"
    )
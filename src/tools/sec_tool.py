import requests
import re
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": "financial-research-agent contact@example.com"
}

def get_company_cik(ticker: str) -> str:
    tickers_url = "https://www.sec.gov/files/company_tickers.json"
    response = requests.get(tickers_url, headers=HEADERS)
    data = response.json()
    
    ticker_upper = ticker.upper()
    for entry in data.values():
        if entry["ticker"] == ticker_upper:
            return str(entry["cik_str"]).zfill(10)
    
    raise ValueError(f"Ticker {ticker} not found in SEC database")


def get_latest_10k_text(ticker: str) -> dict:
    cik = get_company_cik(ticker)
    
    # Get filing history
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = requests.get(url, headers=HEADERS)
    data = response.json()
    
    company_name = data.get("name", ticker)
    filings = data.get("filings", {}).get("recent", {})
    
    forms = filings.get("form", [])
    dates = filings.get("filingDate", [])
    accession_numbers = filings.get("accessionNumber", [])
    
    # Find most recent 10-K
    ten_k_index = None
    for i, form in enumerate(forms):
        if form == "10-K":
            ten_k_index = i
            break
    
    if ten_k_index is None:
        raise ValueError(f"No 10-K found for {ticker}")
    
    filing_date = dates[ten_k_index]
    accession = accession_numbers[ten_k_index].replace("-", "")
    accession_dashed = accession_numbers[ten_k_index]
    
    # Get the filing index to find the RIGHT document (not XBRL)
    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{accession_dashed}-index.htm"
    index_response = requests.get(index_url, headers=HEADERS)
    
    # Find the main 10-K HTM document from the index
    # Look for the largest .htm file that isn't the XBRL instance doc
    filing_index_url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    
    # Get document list for this specific filing
    doc_index_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=10-K&dateb=&owner=include&count=1&search_text="
    
    # Directly get filing index JSON
    index_json_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/index.json"
    index_json_response = requests.get(index_json_url, headers=HEADERS)
    index_data = index_json_response.json()
    
    # Find the main readable 10-K document (largest htm, not xbrl)
    best_doc = None
    best_size = 0
    
    for item in index_data.get("directory", {}).get("item", []):
        name = item.get("name", "")
        size = int(item.get("size", 0) or 0)
        # Pick the largest .htm file that looks like the main filing
        if (name.endswith(".htm") and 
            not name.startswith("R") and  # skip inline XBRL viewer files
            "xbrl" not in name.lower() and
            size > best_size):
            best_doc = name
            best_size = size
    
    if not best_doc:
        raise ValueError("Could not find readable 10-K document")
    
    doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{best_doc}"
    doc_response = requests.get(doc_url, headers=HEADERS)
    
    # Strip HTML tags and clean whitespace
    raw_text = doc_response.text
    clean_text = re.sub(r'<[^>]+>', ' ', raw_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    # Skip past any remaining metadata noise at the start
    # Look for where real content begins (usually after "UNITED STATES")
    start_markers = ["UNITED STATES", "Annual Report", "ANNUAL REPORT", "Item 1."]
    start_pos = 0
    for marker in start_markers:
        pos = clean_text.find(marker)
        if pos != -1:
            start_pos = pos
            break
    
    excerpt = clean_text[start_pos:start_pos + 3000]
    
    return {
        "ticker": ticker.upper(),
        "company_name": company_name,
        "filing_date": filing_date,
        "excerpt": excerpt,
        "source_url": doc_url
    }


if __name__ == "__main__":
    print("Testing SEC Filing Tool...\n")
    result = get_latest_10k_text("AAPL")
    
    print(f"Company:      {result['company_name']}")
    print(f"Ticker:       {result['ticker']}")
    print(f"Filing Date:  {result['filing_date']}")
    print(f"Source URL:   {result['source_url']}")
    print(f"\n--- 10-K Excerpt (first 500 chars) ---")
    print(result['excerpt'][:500])
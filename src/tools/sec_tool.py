import requests
import os
import re
import time
import json
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning
from dotenv import load_dotenv
from src.cache import cache_get, cache_set, cache_key

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
load_dotenv()

HEADERS = {
    "User-Agent": "financial-research-agent contact@example.com",
    "Accept-Encoding": "gzip, deflate",
}


def safe_request(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Request failed: {response.status_code} for {url}")
        return None
    time.sleep(0.2)
    return response


def get_company_cik(ticker: str) -> str:
    url = "https://www.sec.gov/files/company_tickers.json"
    response = safe_request(url)
    if not response:
        raise ValueError("Could not fetch SEC tickers")
    data = response.json()
    for entry in data.values():
        if entry["ticker"].lower() == ticker.lower():
            return str(entry["cik_str"]).zfill(10)
    raise ValueError(f"Ticker {ticker} not found")


def get_10k_filings(cik: str, limit: int = 1) -> list:
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    response = safe_request(url)
    if not response:
        return []
    data = response.json()
    filings = []
    recent = data["filings"]["recent"]
    for i in range(len(recent["form"])):
        if recent["form"][i] == "10-K":
            filings.append({
                "accession": recent["accessionNumber"][i],
                "filing_date": recent["filingDate"][i],
                "primary_doc": recent["primaryDocument"][i],
                "company_name": data.get("name", "Unknown")
            })
    return filings[:limit]


def get_best_htm_doc(cik: str, accession: str) -> str:
    acc_no_dash = accession.replace("-", "")
    index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/index.json"
    response = safe_request(index_url)
    if not response:
        return None

    index_data = response.json()
    best_doc = None
    best_size = 0

    for item in index_data.get("directory", {}).get("item", []):
        name = item.get("name", "")
        size = int(item.get("size", 0) or 0)
        if (name.endswith(".htm") and
                not name.startswith("R") and
                "xbrl" not in name.lower() and
                size > best_size):
            best_doc = name
            best_size = size

    return best_doc


def download_filing_html(cik: str, accession: str) -> str:
    acc_no_dash = accession.replace("-", "")

    best_doc = get_best_htm_doc(cik, accession)

    if best_doc:
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{best_doc}"
    else:
        filings = get_10k_filings(cik, limit=1)
        if not filings:
            return None
        primary_doc = filings[0]["primary_doc"]
        url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_no_dash}/{primary_doc}"

    response = requests.get(url, headers=HEADERS)
    if response.status_code != 200:
        return None
    time.sleep(0.2)
    return response.text


def _regex_extract_section(text: str, start_pattern: str, end_pattern: str, min_words: int = 200) -> str:
    pattern = re.compile(
        rf'{start_pattern}(.*?){end_pattern}',
        re.IGNORECASE | re.DOTALL
    )
    matches = pattern.findall(text)

    if not matches:
        return None

    best = max(matches, key=lambda x: len(x.split()))

    if len(best.split()) < min_words:
        return None

    return best.strip()


def extract_sections(html_content: str) -> dict:
    soup = BeautifulSoup(html_content, "lxml")

    text = soup.get_text(separator="\n")
    text = re.sub(r'\xa0', ' ', text)
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]+', ' ', text)

    risk_factors = _regex_extract_section(
        text,
        start_pattern=r'item\s+1a[\.\-–—:]?\s*risk\s*factors?',
        end_pattern=r'item\s+1b',
        min_words=200
    )

    business = _regex_extract_section(
        text,
        start_pattern=r'item\s+1[\.\-–—:]?\s*business',
        end_pattern=r'item\s+1a',
        min_words=100
    )

    mda = _regex_extract_section(
        text,
        start_pattern=r'item\s+7[\.\-–—:]?\s*management',
        end_pattern=r'item\s+7a',
        min_words=200
    )

    if not mda:
        mda = _regex_extract_section(
            text,
            start_pattern=r'item\s+7[\.\-–—:]?\s*management',
            end_pattern=r'item\s+8',
            min_words=200
        )

    def cap(t, max_chars):
        if t and len(t) > max_chars:
            return t[:max_chars]
        return t

    return {
        "business_overview":    cap(business,      1500) or "Business overview not extracted.",
        "risk_factors":         cap(risk_factors,   2500) or "Risk factors not extracted.",
        "management_discussion": cap(mda,           2500) or "MD&A not extracted."
    }


def get_latest_10k_text(ticker: str) -> dict:
    # Check cache first — avoids re-fetching SEC on repeat runs
    key = cache_key("sec", ticker)
    cached = cache_get(key)
    if cached:
        print(f"   📦 Using cached SEC data for {ticker}")
        return cached

    cik = get_company_cik(ticker)

    filings = get_10k_filings(cik, limit=1)
    if not filings:
        raise ValueError(f"No 10-K found for {ticker}")

    filing = filings[0]
    company_name = filing["company_name"]
    filing_date  = filing["filing_date"]
    accession    = filing["accession"]

    html = download_filing_html(cik, accession)
    if not html:
        raise ValueError(f"Could not download 10-K for {ticker}")

    sections = extract_sections(html)

    result = {
        "ticker":                ticker.upper(),
        "company_name":          company_name,
        "filing_date":           filing_date,
        "business_overview":     sections["business_overview"],
        "risk_factors":          sections["risk_factors"],
        "management_discussion": sections["management_discussion"],
    }

    # Save to cache for next time
    cache_set(key, result)
    return result


if __name__ == "__main__":
    print("Testing SEC Filing Tool...\n")
    result = get_latest_10k_text("AAPL")

    print(f"Company:      {result['company_name']}")
    print(f"Filing Date:  {result['filing_date']}")
    print(f"\n--- Business Overview (first 400 chars) ---")
    print(result['business_overview'][:400])
    print(f"\n--- Risk Factors (first 400 chars) ---")
    print(result['risk_factors'][:400])
    print(f"\n--- MD&A (first 400 chars) ---")
    print(result['management_discussion'][:400])
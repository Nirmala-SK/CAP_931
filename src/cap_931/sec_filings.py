import html
import os
import re

import requests
from dotenv import load_dotenv

from cap_931.web_research import get_company_name

load_dotenv()

# The SEC requires every automated program to identify its owner.
# Put SEC_CONTACT_EMAIL=your real email in the .env file (it stays off GitHub).
SEC_HEADERS = {
    "User-Agent": f"CAP931 Student Project {os.getenv('SEC_CONTACT_EMAIL', 'student@example.com')}"
}

STOP_WORDS = {"platform", "solution", "software", "service", "services", "system", "tool", "tools", "product", "cloud"}

_CACHE = {}


def find_company(company_name):
    """Look up a public company's SEC record. Returns None for private companies."""
    try:
        response = requests.get(
            "https://www.sec.gov/files/company_tickers.json", headers=SEC_HEADERS, timeout=15
        )
        response.raise_for_status()
        records = list(response.json().values())
    except (requests.RequestException, ValueError) as error:
        print(f"Could not load the SEC company list: {error}")
        return None

    matches = []
    for record in records:
        title = re.sub(r"[^a-z0-9]", "", record["title"].lower())
        if title.startswith(company_name):
            matches.append((len(title), record))
    if not matches:
        return None
    return min(matches, key=lambda match: match[0])[1]


def find_latest_annual_report(cik):
    """Find the newest 10-K filing for a company. Returns a dictionary or None."""
    url = f"https://data.sec.gov/submissions/CIK{str(cik).zfill(10)}.json"
    try:
        response = requests.get(url, headers=SEC_HEADERS, timeout=15)
        response.raise_for_status()
        recent = response.json()["filings"]["recent"]
    except (requests.RequestException, ValueError, KeyError) as error:
        print(f"Could not load SEC filings for CIK {cik}: {error}")
        return None

    filings = zip(
        recent["form"], recent["accessionNumber"], recent["primaryDocument"], recent["filingDate"]
    )
    for form, accession, document, filed in filings:
        if form == "10-K":
            folder = accession.replace("-", "")
            link = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{folder}/{document}"
            return {"form": form, "date": filed, "url": link}
    return None


def download_filing_text(url):
    """Download a filing and return its plain text."""
    try:
        response = requests.get(url, headers=SEC_HEADERS, timeout=60)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Could not download the filing: {error}")
        return ""

    raw = response.text
    raw = re.sub(r"(?is)<ix:header>.*?</ix:header>", " ", raw)
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    return " ".join(html.unescape(raw).split())


def make_keywords(product_category, competitor_names):
    """Words to look for inside the filing."""
    words = re.findall(r"[a-zA-Z]{5,}", product_category.lower())
    keywords = [word for word in words if word not in STOP_WORDS]
    return keywords + list(competitor_names) + ["competition"]


def pick_excerpts(text, keywords, max_excerpts=6, size=700):
    """Return short passages where the most keywords appear close together."""
    lower = text.lower()
    keywords = [k.lower() for k in keywords if k]
    candidates = []

    for word in keywords:
        position = lower.find(word)
        tries = 0
        while position != -1 and tries < 50:
            window = lower[max(0, position - size // 2): position + size // 2]
            score = sum(1 for k in keywords if k in window)
            candidates.append((score, position))
            position = lower.find(word, position + size)
            tries += 1

    candidates.sort(key=lambda c: (-c[0], c[1]))

    excerpts, used = [], []
    for score, position in candidates:
        if any(abs(position - other) < size for other in used):
            continue
        used.append(position)
        excerpts.append(text[max(0, position - size // 2): position + size // 2].strip())
        if len(excerpts) == max_excerpts:
            break
    return excerpts


def _build_report(company_name, keywords):
    record = find_company(company_name)
    if not record:
        return None
    report = find_latest_annual_report(record["cik_str"])
    if not report:
        return None
    text = download_filing_text(report["url"])
    if not text:
        return None
    excerpts = pick_excerpts(text, list(keywords))
    if not excerpts:
        return None
    return {
        "company": record["title"].title(),
        "form": report["form"],
        "date": report["date"],
        "url": report["url"],
        "excerpts": excerpts,
    }


def fetch_annual_report(company_url, product_category, competitor_names):
    """Return the latest 10-K excerpts for a public company, or None."""
    company_name = get_company_name(company_url)
    keywords = tuple(make_keywords(product_category, competitor_names))
    key = (company_name, keywords)

    if key not in _CACHE:
        result = _build_report(company_name, keywords)
        if result is None:
            return None
        _CACHE[key] = result
    return _CACHE[key]
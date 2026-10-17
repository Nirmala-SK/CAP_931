import re
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, urljoin, quote_plus

import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SalesAssistantBot/1.0; student project)"}
KEYWORDS = ["news", "press", "media", "career", "leadership", "investor", "strategy", "insights"]


def fetch_page_text(url, max_chars=5000):
    """Download a web page and return its readable text, or None if it fails."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Could not fetch {url}: {error}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    return text[:max_chars]


def get_company_name(url):
    """Turn https://www.crowdstrike.com into 'crowdstrike'."""
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host.split(".")[0]


def find_mentions(text, names):
    """Count how many times each name appears in the text."""
    squashed = re.sub(r"[^a-z0-9]", "", text.lower())
    return {name: squashed.count(name) for name in names}


def find_relevant_links(url, max_links=5):
    """Find links on a page that point to news, careers, leadership, etc."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
    except requests.RequestException as error:
        print(f"Could not fetch {url}: {error}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    site = urlparse(url).netloc
    found = []

    for a in soup.find_all("a", href=True):
        link = urljoin(url, a["href"]).split("#")[0]
        if urlparse(link).netloc != site or link == url or link in found:
            continue
        label = (a.get_text(" ", strip=True) + " " + link).lower()
        if any(word in label for word in KEYWORDS):
            found.append(link)
        if len(found) >= max_links:
            break

    return found


def fetch_site_pages(url, max_pages=5):
    """Return {page_url: text} for the homepage plus a few relevant pages."""
    pages = {url: fetch_page_text(url, max_chars=20000)}
    for link in find_relevant_links(url, max_pages):
        pages[link] = fetch_page_text(link, max_chars=20000)
    return {u: t for u, t in pages.items() if t}


def fetch_news(query, max_items=8):
    """Get recent news headlines from Google News. Returns a list of dictionaries."""
    url = f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
    except (requests.RequestException, ET.ParseError) as error:
        print(f"Could not fetch news for '{query}': {error}")
        return []

    articles = []
    for item in root.iter("item"):
        articles.append({
            "title": item.findtext("title", ""),
            "link": item.findtext("link", ""),
            "date": item.findtext("pubDate", ""),
            "source": item.findtext("source", ""),
        })
        if len(articles) >= max_items:
            break
    return articles


def fetch_company_news(company_url, competitor_names, topic, max_per_query=5):
    """Search news about the company + topic, and the company + each competitor."""
    company = get_company_name(company_url)
    queries = [f"{company} {topic} when:1y"]
    queries += [f"{company} {name} when:1y" for name in competitor_names]

    seen, articles = set(), []
    for query in queries:
        for article in fetch_news(query, max_per_query):
            if article["link"] not in seen:
                seen.add(article["link"])
                articles.append(article)
    return articles


if __name__ == "__main__":
    for a in fetch_news("JPMorgan Chase cybersecurity when:1y", 3):
        print(a["date"], "|", a["source"], "|", a["title"])
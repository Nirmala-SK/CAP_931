"""Keyword alerts: watch a company for new news items and email a digest.

Usage (from the project root):
    uv run python src/cap_931/alerts.py add --email you@example.com --company https://www.jpmorganchase.com --keywords "cybersecurity,AI"
    uv run python src/cap_931/alerts.py list
    uv run python src/cap_931/alerts.py run

Without SMTP settings in .env the digest is printed instead of emailed (dry run).
"""
import argparse
import hashlib
import os
import re
import smtplib
import sqlite3
from email.message import EmailMessage
from urllib.parse import urlparse

from dotenv import load_dotenv

from cap_931.web_research import fetch_news, get_company_name

load_dotenv()

DB_PATH = os.getenv("ALERTS_DB", "alerts.db")


def connect(db_path=DB_PATH):
    """Open the alerts database, creating the tables on first use."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS watchlist ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "email TEXT NOT NULL, company_url TEXT NOT NULL, keywords TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS seen_items ("
        "watch_id INTEGER NOT NULL, item_hash TEXT NOT NULL, "
        "PRIMARY KEY (watch_id, item_hash))"
    )
    conn.commit()
    return conn


def _valid_url(url):
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def add_watch(email, company_url, keywords, db_path=DB_PATH):
    """Save a company and its keywords to the watchlist."""
    keywords = [k.strip() for k in keywords if k.strip()]
    if not email or "@" not in email:
        raise ValueError("A valid email address is required.")
    if not _valid_url(company_url):
        raise ValueError("The company URL must start with http:// or https://")
    if not keywords:
        raise ValueError("Give at least one keyword.")

    conn = connect(db_path)
    conn.execute(
        "INSERT INTO watchlist (email, company_url, keywords) VALUES (?, ?, ?)",
        (email.strip(), company_url.strip(), ",".join(keywords)),
    )
    conn.commit()
    conn.close()

def _has_keyword(title, keyword):
    """True if the keyword appears in the title as a whole word (so 'AI' does not match 'said')."""
    pattern = r"(?<!\w)" + re.escape(keyword) + r"(?!\w)"
    return re.search(pattern, title, re.IGNORECASE) is not None

def _item_hash(link):
    return hashlib.sha256(link.encode("utf-8")).hexdigest()


def find_new_items(conn, watch_id, company_url, keywords, fetch=fetch_news):
    """Return news items from the last 7 days that match a keyword and were not sent before."""
    company = get_company_name(company_url)
    new_items, seen_this_run = [], set()

    for keyword in keywords:
        for item in fetch(f"{company} {keyword} when:7d", 10):
            digest = _item_hash(item["link"])
            if digest in seen_this_run:
                continue
            if not _has_keyword(item["title"], keyword):
                continue
            already_sent = conn.execute(
                "SELECT 1 FROM seen_items WHERE watch_id = ? AND item_hash = ?",
                (watch_id, digest),
            ).fetchone()
            if already_sent:
                continue
            seen_this_run.add(digest)
            new_items.append({**item, "keyword": keyword, "hash": digest})

    return new_items


def build_digest(company_url, items):
    """Write the email body for a list of new items."""
    lines = [f"New items about {get_company_name(company_url)}:", ""]
    for item in items:
        lines.append(f"- [{item['keyword']}] {item['title']} ({item['source']}, {item['date'][:16]})")
        lines.append(f"  {item['link']}")
    lines += ["", "You receive this because this company is on your watchlist."]
    return "\n".join(lines)


def send_email(to, subject, body):
    """Send an email through SMTP, or print it when SMTP_HOST is not set (dry run)."""
    host = os.getenv("SMTP_HOST")
    if not host:
        print(f"--- DRY RUN (no SMTP_HOST in .env): would send to {to} ---")
        print(f"Subject: {subject}\n\n{body}\n---")
        return "dry-run"

    message = EmailMessage()
    message["From"] = os.getenv("ALERT_FROM", os.getenv("SMTP_USER", ""))
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=30) as server:
        server.starttls()
        user = os.getenv("SMTP_USER")
        if user:
            server.login(user, os.getenv("SMTP_PASSWORD", ""))
        server.send_message(message)
    return "sent"


def run_alerts(db_path=DB_PATH, fetch=fetch_news, send=send_email):
    """Check every watchlist entry once. Returns [(email, company_url, number_sent)]."""
    conn = connect(db_path)
    results = []

    rows = conn.execute("SELECT id, email, company_url, keywords FROM watchlist").fetchall()
    for watch_id, email, company_url, keyword_text in rows:
        items = find_new_items(conn, watch_id, company_url, keyword_text.split(","), fetch)
        if not items:
            results.append((email, company_url, 0))
            continue

        subject = f"{len(items)} new item(s) about {get_company_name(company_url)}"
        try:
            send(email, subject, build_digest(company_url, items))
        except Exception as error:
            # Nothing is marked as seen, so these items are tried again on the next run.
            print(f"Could not send to {email}: {error}")
            results.append((email, company_url, 0))
            continue

        conn.executemany(
            "INSERT OR IGNORE INTO seen_items (watch_id, item_hash) VALUES (?, ?)",
            [(watch_id, item["hash"]) for item in items],
        )
        conn.commit()
        results.append((email, company_url, len(items)))

    conn.close()
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description="Keyword alerts for prospect companies.")
    commands = parser.add_subparsers(dest="command", required=True)

    add = commands.add_parser("add", help="add a company to the watchlist")
    add.add_argument("--email", required=True)
    add.add_argument("--company", required=True, help="company URL, e.g. https://www.jpmorganchase.com")
    add.add_argument("--keywords", required=True, help="comma-separated, e.g. cybersecurity,AI")

    commands.add_parser("list", help="show the watchlist")
    commands.add_parser("run", help="check for new items and send digests")

    args = parser.parse_args(argv)

    if args.command == "add":
        try:
            add_watch(args.email, args.company, args.keywords.split(","))
        except ValueError as error:
            print(f"Not added: {error}")
            return 1
        print("Added to the watchlist.")
    elif args.command == "list":
        conn = connect()
        for watch_id, email, company_url, keywords in conn.execute(
            "SELECT id, email, company_url, keywords FROM watchlist"
        ):
            print(f"{watch_id}: {email} | {company_url} | {keywords}")
        conn.close()
    else:
        for email, company_url, count in run_alerts():
            print(f"{email} | {company_url} | {count} new item(s) sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
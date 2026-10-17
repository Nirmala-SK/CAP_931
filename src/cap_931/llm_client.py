import os
from dotenv import load_dotenv
from openai import OpenAI
from cap_931.prompts import SYSTEM_PROMPT, build_user_prompt
from cap_931.web_research import get_company_name, find_mentions
from cap_931.report_generator import build_links_section

load_dotenv()

MODEL = "gemini-3.8-flash"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


def get_client():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY is missing. Add it to your .env file.")
    return OpenAI(api_key=key, base_url=BASE_URL)


def ask_llm(system_prompt, user_prompt):
    """Send a prompt to the model and return its text answer."""
    client = get_client()
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content


def generate_insights(inputs, pages, news=None):
    """Build the prompt from the inputs, pages and news, and return the brief."""
    news = news or []
    names = [get_company_name(c) for c in inputs["competitors"]]
    all_text = " ".join(pages.values()) + " " + " ".join(a["title"] for a in news)
    mentions = find_mentions(all_text, names)
    user_prompt = build_user_prompt(inputs, pages, mentions, news)
    brief = ask_llm(SYSTEM_PROMPT, user_prompt)
    return brief + "\n\n" + build_links_section(pages, news)


if __name__ == "__main__":
    from cap_931.web_research import fetch_site_pages

    inputs = {
        "product_name": "SentinelShield",
        "product_category": "Cybersecurity threat-detection platform",
        "value_prop": "Detects and stops cyber threats in real time, reducing breach risk and response time.",
        "target_customer": "Chief Information Security Officer (CISO)",
        "company_url": "https://www.jpmorganchase.com",
        "competitors": ["https://www.crowdstrike.com", "https://www.paloaltonetworks.com"],
    }
    pages = fetch_site_pages(inputs["company_url"])
    print(generate_insights(inputs, pages))
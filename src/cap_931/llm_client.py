import os

from dotenv import load_dotenv
from openai import OpenAI

from cap_931.prompts import EXTRACT_PROMPT, SYSTEM_PROMPT, build_user_prompt
from cap_931.report_generator import build_links_section
from cap_931.web_research import find_mentions, get_company_name

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


def generate_insights(inputs, pages, news=None, filing=None):
    """Two-step chain: extract facts first, then write the brief from them."""
    news = news or []
    names = [get_company_name(c) for c in inputs["competitors"]]

    all_text = " ".join(pages.values()) + " " + " ".join(a["title"] for a in news)
    if filing:
        all_text += " " + " ".join(filing["excerpts"])
    mentions = find_mentions(all_text, names)

    user_prompt = build_user_prompt(inputs, pages, mentions, news, filing)

    # Step 1: pull out only the facts the sources actually state
    facts = ask_llm(EXTRACT_PROMPT, user_prompt)

    # Step 2: write the brief, using those facts as the main material
    final_prompt = (
        user_prompt
        + "\n\nVERIFIED FACTS (use these as your main material; "
        + "every statement must come from them or from the competitor mention counts above):\n"
        + facts
    )
    brief = ask_llm(SYSTEM_PROMPT, final_prompt)
    return brief + "\n\n" + build_links_section(pages, news, filing)
import streamlit as st
from urllib.parse import urlparse
from cap_931.web_research import fetch_site_pages, fetch_company_news, get_company_name
from cap_931.llm_client import generate_insights
from cap_931.report_generator import build_docx
from cap_931.document_reader import read_uploaded_file
from cap_931.sec_filings import fetch_annual_report

st.set_page_config(page_title="Sales Assistant Agent", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 3.5rem; padding-bottom: 1rem;}
    h1 {padding-top: 0rem !important; padding-bottom: 0.5rem !important;}
    </style>
    """,
    unsafe_allow_html=True,
)


def is_valid_url(url):
    """Return True if the text looks like a real web address."""
    parsed = urlparse(url.strip())
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


st.title("Sales Assistant Agent")

row1 = st.columns(3)
product_name = row1[0].text_input("Product Name", placeholder="e.g., SentinelShield")
product_category = row1[1].text_input("Product Category", placeholder="e.g., Cybersecurity")
company_url = row1[2].text_input("Company URL", placeholder="https://www.example.com")

row2 = st.columns(3)
target_customer = row2[0].text_input("Target Customer", placeholder="e.g., CISO")
competitors = row2[1].text_area("Competitor URLs (one per line)", height=100)
value_prop = row2[2].text_area("Value Proposition", height=100)

uploaded_file = st.file_uploader(
    "Optional: product overview sheet or deck",
    type=["pdf", "docx", "pptx", "txt"],
)

generate = st.button("Generate Insights", type="primary")

st.subheader("Results")

if generate:
    errors = []

    if not product_name.strip():
        errors.append("Product Name is required.")
    if not is_valid_url(company_url):
        errors.append("Company URL must be a valid link starting with http:// or https://")
    if not product_category.strip():
        errors.append("Product Category is required.")
    if not value_prop.strip():
        errors.append("Value Proposition is required.")
    if not target_customer.strip():
        errors.append("Target Customer is required.")

    competitor_list = [c.strip() for c in competitors.splitlines() if c.strip()]
    if not competitor_list:
        errors.append("Enter at least one competitor URL.")
    for c in competitor_list:
        if not is_valid_url(c):
            errors.append(f"Competitor URL is not valid: {c}")

    if errors:
        st.session_state.pop("brief", None)
        st.error("Please fix: " + "  •  ".join(errors))
    else:
        with st.spinner("Reading company website pages..."):
            pages = fetch_site_pages(company_url)

        if not pages:
            st.warning("Could not read the company website. Check the URL and try again.")
        else:
            names = [get_company_name(c) for c in competitor_list]
            with st.spinner("Searching recent news..."):
                news = fetch_company_news(company_url, names, product_category)
            with st.spinner("Checking the SEC annual report (10-K)..."):
                filing = fetch_annual_report(company_url, product_category, names)
            if not filing:
                st.info("No SEC annual report found (private company, or no match). Continuing without it.")
            inputs = {
                "product_name": product_name,
                "product_category": product_category,
                "value_prop": value_prop,
                "target_customer": target_customer,
                "company_url": company_url,
                "competitors": competitor_list,
                "product_sheet": read_uploaded_file(uploaded_file) if uploaded_file else "",
            }
            try:
                with st.spinner("Generating account brief..."):
                    st.session_state["brief"] = generate_insights(inputs, pages, news, filing)
                    st.session_state["pages"] = pages
                    st.session_state["news"] = news
                    st.session_state["company"] = urlparse(company_url).netloc.replace("www.", "")
                    st.session_state["product"] = product_name
            except Exception as error:
                st.error(f"The AI model could not generate the brief: {error}")

if "brief" in st.session_state:
    st.markdown(st.session_state["brief"])

    st.download_button(
        "Download brief (.md)",
        st.session_state["brief"],
        file_name="account_brief.md",
        mime="text/markdown",
    )

    st.download_button(
        "Download one-page brief (.docx)",
        build_docx(
            st.session_state["brief"],
            st.session_state["company"],
            st.session_state["product"],
            "Nirmala Sendilkumar",
        ),
        file_name="account_brief.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    with st.expander("Pages read (sources)"):
        for page_url, text in st.session_state["pages"].items():
            st.write(f"- {page_url} ({len(text)} characters)")
        for a in st.session_state.get("news", []):
            st.write(f"- {a['date'][:16]} | {a['source']} | {a['title']}")
elif not generate:
    st.info("Fill in the form and click Generate Insights. Results will appear here.")
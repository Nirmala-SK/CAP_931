# CAP 931: AI Sales Assistant Agent

A prototype that helps a new sales representative research a prospective account. The rep enters a product, a target company URL, competitors and a value proposition. The app reads public web pages and recent news, asks an LLM to summarize them, and produces a one-page account brief as a Word document using the PerScholas template.

## What it produces
- Company strategy
- Competitor mentions
- Leadership information
- Product/strategy summary
- Talking points for the target customer
- Article links to every page and news item used

## Tech stack
Python, uv, Streamlit, python-docx, requests, BeautifulSoup, python-dotenv, and the OpenAI Python SDK pointed at Google's Gemini API (free tier).

## Setup
1. Install uv and clone this repository.
2. Install dependencies: `uv sync`
3. Create a `.env` file in the project root containing: `GEMINI_API_KEY=your-key`
4. Run the app: `uv run streamlit run src/cap_931/app.py`

## Project structure
- `app.py`: Streamlit interface and input validation
- `web_research.py`: page fetching, link discovery, Google News RSS
- `prompts.py`: system prompt and fact-extraction prompt
- `llm_client.py`: model calls and the two-step prompt chain
- `report_generator.py`: links section and Word document builder
- `perscholas_template.docx`: PerScholas Word template

## How it works
1. Validate the form inputs.
2. Fetch the company homepage and relevant pages (news, careers, leadership).
3. Search recent news about the company, the topic and each competitor.
4. Step 1 of the chain extracts only facts stated in the sources.
5. Step 2 writes the brief from those facts, with rules against inventing information.
6. Links are built in code, not by the model, so they are always accurate.

## Known limitations
- News results are headlines only, not full articles.
- The optional product-sheet upload is not processed yet.
- No 10-K or annual report parsing yet.
- Free-tier rate limits can slow or block requests.
- Competitor detection is a text match on names found in the sources.

## Documentation and sample outputs
- `docs/CAP931_Final_Report.pdf` and `docs/CAP931_Final_Report.docx`: the full project report in the PerScholas template
- `docs/sample_outputs/`: the one-page briefs from each experiment (v1 to v5; v5 is the final version)
- `docs/sample_inputs/sentinelshield_sheet.txt`: the fictional product overview uploaded to produce the v4 and v5 briefs. SentinelShield is an assumed product, not a real one.

## Author
Nirmala Sendilkumar

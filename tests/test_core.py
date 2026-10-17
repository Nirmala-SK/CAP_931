from cap_931.document_reader import read_uploaded_file
from cap_931.report_generator import build_docx, build_links_section
from cap_931.web_research import find_mentions, get_company_name


def test_get_company_name():
    assert get_company_name("https://www.crowdstrike.com") == "crowdstrike"
    assert get_company_name("https://paloaltonetworks.com/about") == "paloaltonetworks"


def test_find_mentions_ignores_spacing_and_case():
    text = "We compared Palo Alto Networks with CrowdStrike."
    result = find_mentions(text, ["crowdstrike", "paloaltonetworks", "other"])
    assert result == {"crowdstrike": 1, "paloaltonetworks": 1, "other": 0}


def test_links_section_uses_the_given_sources():
    pages = {"https://example.com": "text"}
    news = [
        {
            "title": "Big news - Pub",
            "link": "https://news.example/1",
            "source": "Pub",
            "date": "Tue, 07 Apr 2026 07:00:00 GMT",
        }
    ]
    section = build_links_section(pages, news)
    assert "[https://example.com](https://example.com)" in section
    assert "[Big news](https://news.example/1)" in section


def test_read_uploaded_text_file():
    class FakeFile:
        name = "sheet.txt"

        def getvalue(self):
            return b"Plain  text\n file"

    assert read_uploaded_file(FakeFile()) == "Plain text file"


def test_build_docx_returns_a_word_file():
    data = build_docx("## Company Strategy\nSome text.", "example.com", "Widget")
    assert data[:2] == b"PK"
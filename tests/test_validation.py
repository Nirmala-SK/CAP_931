from cap_931.validation import is_valid_url, parse_competitors, validate_inputs


def test_valid_urls():
    assert is_valid_url("https://www.jpmorganchase.com")
    assert is_valid_url("http://example.com/path?x=1")
    assert is_valid_url("  https://www.example.com  ")


def test_invalid_urls():
    assert not is_valid_url("")
    assert not is_valid_url("jpmorganchase.com")
    assert not is_valid_url("ftp://example.com")
    assert not is_valid_url("https://")
    assert not is_valid_url("https://localhost")


def test_two_urls_on_one_line_are_rejected():
    assert not is_valid_url("https://www.crowdstrike.com and https://www.paloaltonetworks.com")


def test_parse_competitors_ignores_blank_lines():
    text = "https://a.com\n\n  https://b.com  \n"
    assert parse_competitors(text) == ["https://a.com", "https://b.com"]


def test_empty_form_reports_every_problem():
    errors, competitors = validate_inputs("", "", "", "", "", "")
    assert len(errors) == 6
    assert competitors == []


def test_valid_form_has_no_errors():
    errors, competitors = validate_inputs(
        "SentinelShield", "https://www.jpmorganchase.com", "Cybersecurity", "Detects threats", "CISO",
        "https://www.crowdstrike.com\nhttps://www.paloaltonetworks.com",
    )
    assert errors == []
    assert len(competitors) == 2


def test_bad_competitor_line_is_reported():
    errors, _ = validate_inputs(
        "P", "https://www.example.com", "C", "V", "T", "https://a.com and https://b.com"
    )
    assert len(errors) == 1
    assert "one address per line" in errors[0]
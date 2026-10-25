"""Checks for the form inputs, kept separate from the interface so they can be tested."""
from urllib.parse import urlparse


def is_valid_url(url):
    """True for a single http(s) address with a real-looking host name."""
    url = url.strip()
    if not url or any(character.isspace() for character in url):
        return False
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and "." in parsed.netloc


def parse_competitors(text):
    """One competitor address per line; blank lines are ignored."""
    return [line.strip() for line in text.splitlines() if line.strip()]


def validate_inputs(product_name, company_url, product_category, value_prop, target_customer, competitors_text):
    """Return (errors, competitor_list). All problems are collected so they can be shown together."""
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

    competitor_list = parse_competitors(competitors_text)
    if not competitor_list:
        errors.append("Enter at least one competitor URL.")
    for url in competitor_list:
        if not is_valid_url(url):
            errors.append(f"Competitor URL is not valid (one address per line): {url}")

    return errors, competitor_list
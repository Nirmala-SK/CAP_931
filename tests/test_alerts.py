import pytest

from cap_931.alerts import add_watch, connect, run_alerts


def make_item(title, link):
    return {"title": title, "link": link, "source": "Pub", "date": "Tue, 07 Apr 2026 07:00:00 GMT"}


def test_add_watch_rejects_bad_input(tmp_path):
    db = str(tmp_path / "a.db")
    with pytest.raises(ValueError):
        add_watch("not-an-email", "https://www.example.com", ["ai"], db)
    with pytest.raises(ValueError):
        add_watch("a@b.com", "example.com", ["ai"], db)
    with pytest.raises(ValueError):
        add_watch("a@b.com", "https://www.example.com", ["  "], db)


def test_new_items_are_sent_once(tmp_path):
    db = str(tmp_path / "a.db")
    add_watch("a@b.com", "https://www.example.com", ["cyber"], db)
    sent = []

    def fetch(query, max_items):
        return [make_item("Example cyber breach", "https://n/1")]

    def send(to, subject, body):
        sent.append((to, subject, body))

    assert run_alerts(db, fetch, send)[0][2] == 1
    assert run_alerts(db, fetch, send)[0][2] == 0
    assert len(sent) == 1
    assert "https://n/1" in sent[0][2]


def test_items_without_the_keyword_in_the_title_are_ignored(tmp_path):
    db = str(tmp_path / "a.db")
    add_watch("a@b.com", "https://www.example.com", ["cyber"], db)
    sent = []
    fetch = lambda query, max_items: [make_item("Quarterly results announced", "https://n/2")]
    run_alerts(db, fetch, lambda *args: sent.append(args))
    assert sent == []


def test_failed_send_is_retried_next_run(tmp_path):
    db = str(tmp_path / "a.db")
    add_watch("a@b.com", "https://www.example.com", ["cyber"], db)
    fetch = lambda query, max_items: [make_item("Example cyber news", "https://n/3")]

    def broken_send(to, subject, body):
        raise RuntimeError("mail server down")

    assert run_alerts(db, fetch, broken_send)[0][2] == 0
    sent = []
    assert run_alerts(db, fetch, lambda *args: sent.append(args))[0][2] == 1
    conn = connect(db)
    assert conn.execute("SELECT COUNT(*) FROM seen_items").fetchone()[0] == 1
    conn.close()

    

def test_keywords_match_whole_words_only(tmp_path):
    db = str(tmp_path / "a.db")
    add_watch("a@b.com", "https://www.example.com", ["AI"], db)
    headlines = [
        make_item("The CEO said results were fair", "https://n/4"),
        make_item("Big AI push at the bank", "https://n/5"),
        make_item("Bank explores ai-driven tools", "https://n/6"),
    ]
    sent = []
    run_alerts(db, lambda query, max_items: headlines, lambda to, subject, body: sent.append(body))
    assert len(sent) == 1
    assert "Big AI push" in sent[0]
    assert "ai-driven" in sent[0]
    assert "said results" not in sent[0]
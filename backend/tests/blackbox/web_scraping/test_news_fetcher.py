"""
Black-box tests for scripts.web_scraping.news_fetcher.

Applies EP / BA / EG. All network calls are mocked via unittest.mock.
"""
from unittest.mock import MagicMock, patch

import pytest

from scripts.web_scraping.news_fetcher import NewsFetcher

pytestmark = pytest.mark.blackbox


def _html_response(body):
    m = MagicMock()
    m.status_code = 200
    m.content = body.encode("utf-8")
    m.raise_for_status = MagicMock()
    return m


def _xml_response(body):
    m = MagicMock()
    m.status_code = 200
    m.content = body.encode("utf-8")
    m.raise_for_status = MagicMock()
    return m


@pytest.fixture
def nf():
    return NewsFetcher()


SAMPLE_HN_HTML = """
<html><body>
<a class="storylink" href="https://x.com/story1">Headline one is long enough</a>
<a class="storylink" href="relative/story2">Headline two is also long enough here</a>
</body></html>
"""

SAMPLE_GENERIC_HTML = """
<html><body>
<h1>First generic headline that is long enough for the filter</h1>
<h2>Second generic headline that is long enough for the filter</h2>
</body></html>
"""

GOOGLE_NEWS_XML = """<?xml version="1.0"?>
<rss><channel>
<item>
  <title>Search title 1</title>
  <link>https://news.google.com/1</link>
  <description>desc 1</description>
</item>
<item>
  <title>Search title 2</title>
  <link>https://news.google.com/2</link>
  <description>desc 2</description>
</item>
</channel></rss>
"""


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestFetchFromSourceEP:
    def test_unknown_source_returns_empty_list(self, nf, capsys):
        # EP: unknown-source class -> [] + "Unknown source" message.
        result = nf.fetch_from_source("not_a_real_source")
        assert result == []
        assert "Unknown source" in capsys.readouterr().out

    def test_hackernews_parses_story_links(self, nf):
        # EP: hackernews branch class -> returns parsed list.
        with patch("requests.get", return_value=_html_response(SAMPLE_HN_HTML)):
            result = nf.fetch_from_source("hackernews", max_headlines=5)
        assert len(result) == 2
        assert result[0]["source"] == "hackernews"
        assert result[0]["title"].startswith("Headline one")

    def test_network_error_returns_empty_list(self, nf, capsys):
        # EP: network-error class -> [] (caught).
        with patch("requests.get", side_effect=Exception("down")):
            result = nf.fetch_from_source("hackernews")
        assert result == []


class TestFetchCustomSourceEP:
    def test_custom_source_success(self, nf):
        # EP: generic-scrape success class -> non-empty headlines.
        with patch("requests.get", return_value=_html_response(SAMPLE_GENERIC_HTML)):
            result = nf.fetch_custom_source("https://example.com")
        assert len(result) >= 1
        assert any("headline" in h["title"].lower() for h in result)

    def test_custom_source_network_failure(self, nf):
        # EP: request failure class -> empty list.
        with patch("requests.get", side_effect=Exception("boom")):
            result = nf.fetch_custom_source("https://example.com")
        assert result == []


class TestSearchNewsEP:
    def test_search_returns_items_from_rss(self, nf):
        # EP: 200 + valid RSS class -> parsed list.
        with patch("requests.get", return_value=_xml_response(GOOGLE_NEWS_XML)):
            results = nf.search_news("python")
        assert len(results) == 2
        assert results[0]["title"] == "Search title 1"
        assert results[0]["source"] == "Google News"

    def test_search_non_200_returns_empty(self, nf):
        # EP: non-200 status class -> empty.
        bad = MagicMock()
        bad.status_code = 500
        bad.content = b""
        with patch("requests.get", return_value=bad):
            assert nf.search_news("python") == []


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_max_headlines_zero_returns_empty(self, nf):
        # BA: max_headlines=0 -> empty list.
        with patch("requests.get", return_value=_html_response(SAMPLE_GENERIC_HTML)):
            result = nf.fetch_custom_source("https://example.com", max_headlines=0)
        assert result == []

    def test_max_headlines_one_returns_at_most_one(self, nf):
        # BA: max_headlines=1 -> list of length <=1.
        with patch("requests.get", return_value=_html_response(SAMPLE_GENERIC_HTML)):
            result = nf.fetch_custom_source("https://example.com", max_headlines=1)
        assert len(result) <= 1


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_filter_by_keyword_case_insensitive(self, nf):
        # EG: keyword filter lowercases both sides.
        headlines = [
            {"title": "Python is Great", "link": "x"},
            {"title": "News about cats", "link": "y"},
        ]
        result = nf.filter_headlines_by_keyword(headlines, ["python"])
        assert len(result) == 1
        assert result[0]["title"] == "Python is Great"

    def test_filter_by_multiple_keywords_matches_any(self, nf):
        # EG: OR semantics - any keyword match is sufficient.
        headlines = [
            {"title": "Rust programming", "link": "x"},
            {"title": "Go programming", "link": "y"},
            {"title": "Fishing tips", "link": "z"},
        ]
        result = nf.filter_headlines_by_keyword(headlines, ["rust", "go"])
        assert len(result) == 2

    def test_save_headlines_with_empty_list_is_noop(self, nf, tmp_path, monkeypatch):
        # EG: empty headlines -> no file written (early return).
        monkeypatch.chdir(tmp_path)
        nf.save_headlines([])
        assert list(tmp_path.iterdir()) == []

    def test_save_headlines_writes_json(self, nf, tmp_path):
        # EG: non-empty list -> JSON file with 'timestamp' and 'headlines'.
        import json

        f = tmp_path / "out.json"
        nf.save_headlines([{"title": "x", "link": "y", "source": "z"}], filename=str(f))
        data = json.loads(f.read_text())
        assert "timestamp" in data
        assert data["headlines"][0]["title"] == "x"

    def test_display_no_headlines_prints_message(self, nf, capsys):
        # EG: empty list -> "No headlines found".
        nf.display_headlines([])
        assert "No headlines found" in capsys.readouterr().out

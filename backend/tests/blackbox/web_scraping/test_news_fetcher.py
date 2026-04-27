from unittest.mock import MagicMock, patch

import pytest

from scripts.web_scraping.news_fetcher import NewsFetcher

pytestmark = pytest.mark.blackbox


# Defines the html_response helper.
def _html_response(body):
    m = MagicMock()
    m.status_code = 200
    m.content = body.encode("utf-8")
    m.raise_for_status = MagicMock()
    return m


# Defines the xml_response helper.
def _xml_response(body):
    m = MagicMock()
    m.status_code = 200
    m.content = body.encode("utf-8")
    m.raise_for_status = MagicMock()
    return m


# Provides the nf fixture.
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


class TestFetchFromSourceEP:
    # Tests unknown source returns empty list.
    def test_unknown_source_returns_empty_list(self, nf, capsys):
        result = nf.fetch_from_source("not_a_real_source")
        assert result == []
        assert "Unknown source" in capsys.readouterr().out

    # Tests hackernews parses story links.
    def test_hackernews_parses_story_links(self, nf):
        with patch("requests.get", return_value=_html_response(SAMPLE_HN_HTML)):
            result = nf.fetch_from_source("hackernews", max_headlines=5)
        assert len(result) == 2
        assert result[0]["source"] == "hackernews"
        assert result[0]["title"].startswith("Headline one")

    # Tests network error returns empty list.
    def test_network_error_returns_empty_list(self, nf, capsys):
        with patch("requests.get", side_effect=Exception("down")):
            result = nf.fetch_from_source("hackernews")
        assert result == []


class TestFetchCustomSourceEP:
    # Tests custom source success.
    def test_custom_source_success(self, nf):
        with patch("requests.get", return_value=_html_response(SAMPLE_GENERIC_HTML)):
            result = nf.fetch_custom_source("https://example.com")
        assert len(result) >= 1
        assert any("headline" in h["title"].lower() for h in result)

    # Tests custom source network failure.
    def test_custom_source_network_failure(self, nf):
        with patch("requests.get", side_effect=Exception("boom")):
            result = nf.fetch_custom_source("https://example.com")
        assert result == []


class TestSearchNewsEP:
    # Tests search returns items from rss.
    def test_search_returns_items_from_rss(self, nf):
        with patch("requests.get", return_value=_xml_response(GOOGLE_NEWS_XML)):
            results = nf.search_news("python")
        assert len(results) == 2
        assert results[0]["title"] == "Search title 1"
        assert results[0]["source"] == "Google News"

    # Tests search non 200 returns empty.
    def test_search_non_200_returns_empty(self, nf):
        bad = MagicMock()
        bad.status_code = 500
        bad.content = b""
        with patch("requests.get", return_value=bad):
            assert nf.search_news("python") == []


class TestBoundaries:
    # Tests max headlines zero returns empty.
    def test_max_headlines_zero_returns_empty(self, nf):
        with patch("requests.get", return_value=_html_response(SAMPLE_GENERIC_HTML)):
            result = nf.fetch_custom_source("https://example.com", max_headlines=0)
        assert result == []

    # Tests max headlines one returns at most one.
    def test_max_headlines_one_returns_at_most_one(self, nf):
        with patch("requests.get", return_value=_html_response(SAMPLE_GENERIC_HTML)):
            result = nf.fetch_custom_source("https://example.com", max_headlines=1)
        assert len(result) <= 1


class TestErrorGuessing:
    # Tests filter by keyword case insensitive.
    def test_filter_by_keyword_case_insensitive(self, nf):
        headlines = [
            {"title": "Python is Great", "link": "x"},
            {"title": "News about cats", "link": "y"},
        ]
        result = nf.filter_headlines_by_keyword(headlines, ["python"])
        assert len(result) == 1
        assert result[0]["title"] == "Python is Great"

    # Tests filter by multiple keywords matches any.
    def test_filter_by_multiple_keywords_matches_any(self, nf):
        headlines = [
            {"title": "Rust programming", "link": "x"},
            {"title": "Go programming", "link": "y"},
            {"title": "Fishing tips", "link": "z"},
        ]
        result = nf.filter_headlines_by_keyword(headlines, ["rust", "go"])
        assert len(result) == 2

    # Tests save headlines with empty list is noop.
    def test_save_headlines_with_empty_list_is_noop(self, nf, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        nf.save_headlines([])
        assert list(tmp_path.iterdir()) == []

    # Tests save headlines writes json.
    def test_save_headlines_writes_json(self, nf, tmp_path):

        import json

        f = tmp_path / "out.json"
        nf.save_headlines([{"title": "x", "link": "y", "source": "z"}], filename=str(f))
        data = json.loads(f.read_text())
        assert "timestamp" in data
        assert data["headlines"][0]["title"] == "x"

    # Tests display no headlines prints message.
    def test_display_no_headlines_prints_message(self, nf, capsys):
        nf.display_headlines([])
        assert "No headlines found" in capsys.readouterr().out

"""Whitebox coverage for ``scripts/web_scraping/news_fetcher.py``.

Trimmed to the core branches: generic scraping (success + error), HN source,
aggregator, RSS search, keyword filter, and JSON save.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.web_scraping.news_fetcher import NewsFetcher


def _resp(content=b"", status_code=200):
    r = MagicMock()
    r.content = content
    r.status_code = status_code
    r.raise_for_status.return_value = None
    return r


@pytest.fixture
def fetcher():
    return NewsFetcher()


class TestFetchHeadlinesGeneric:
    def test_extracts_headlines(self, fetcher):
        html = b"""
            <html><body>
                <a href='/relative'><h1>This is a long enough headline for matching</h1></a>
                <h2>Short</h2>
                <h1>Another headline that is long enough to keep</h1>
            </body></html>
        """
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(html)):
            out = fetcher.fetch_headlines_generic("https://example.com", max_headlines=5)
        titles = [h["title"] for h in out]
        assert any("long enough headline for matching" in t for t in titles)
        assert all("Short" != t for t in titles)
        rewritten = [h for h in out if h["link"]]
        assert rewritten and rewritten[0]["link"].startswith("https://example.com")

    def test_exception_returns_empty(self, fetcher, capsys):
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   side_effect=RuntimeError("net")):
            assert fetcher.fetch_headlines_generic("https://example.com") == []
        assert "Error fetching" in capsys.readouterr().out


class TestFetchFromSource:
    def test_hackernews_branch(self, fetcher):
        html = b"""<html><body>
            <a class='storylink' href='item?id=1'>HN headline one</a>
            <a class='storylink' href='https://abs/2'>HN headline two</a>
        </body></html>"""
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(html)):
            out = fetcher.fetch_from_source("hackernews", max_headlines=2)
        assert len(out) == 2
        assert out[0]["link"].startswith("https://news.ycombinator.com")
        assert out[1]["link"] == "https://abs/2"


class TestFetchAllSources:
    def test_aggregates(self, fetcher):
        with patch.object(NewsFetcher, "fetch_from_source",
                          side_effect=[[{"title": "a"}], [{"title": "b"}], []]), \
             patch("scripts.web_scraping.news_fetcher.time.sleep"):
            out = fetcher.fetch_all_sources(max_per_source=1)
        assert len(out) == 2


class TestSearchNews:
    def test_success(self, fetcher):
        item = MagicMock()
        item.title.get_text.return_value = "news 1"
        item.link.get_text.return_value = "http://a"
        item.description.get_text.return_value = "d1"
        soup = MagicMock()
        soup.find_all.return_value = [item]
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(b"<rss/>")), \
             patch("scripts.web_scraping.news_fetcher.BeautifulSoup",
                   return_value=soup):
            out = fetcher.search_news("python", max_results=2)
        assert len(out) == 1 and out[0]["title"] == "news 1"


class TestFilter:
    def test_matches(self, fetcher):
        items = [{"title": "Python is fun"}, {"title": "Java rules"}]
        out = fetcher.filter_headlines_by_keyword(items, ["python"])
        assert len(out) == 1 and out[0]["title"] == "Python is fun"


class TestSave:
    def test_explicit_filename(self, fetcher, tmp_path):
        out = tmp_path / "x.json"
        fetcher.save_headlines([{"title": "t"}], filename=str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["headlines"][0]["title"] == "t"

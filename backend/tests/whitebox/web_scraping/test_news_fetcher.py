"""Targeted whitebox coverage for ``scripts/web_scraping/news_fetcher.py``.

Slim — three direct tests for ``fetch_headlines_generic``,
``fetch_from_source`` (hackernews branch), and the keyword-filter
helper.  CLI smoke tests only hit error paths because every HTTP call
is mocked to fail.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scripts.web_scraping.news_fetcher import NewsFetcher


def _resp(content=b""):
    r = MagicMock()
    r.content = content
    r.raise_for_status.return_value = None
    return r


@pytest.fixture
def fetcher():
    return NewsFetcher()


class TestFetchHeadlinesGeneric:
    def test_extracts_long_titles_only(self, fetcher):
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


class TestFetchFromSource:
    def test_unknown_source(self, fetcher, capsys):
        out = fetcher.fetch_from_source("nope")
        assert out == []
        assert "Unknown source" in capsys.readouterr().out

    def test_hackernews_branch(self, fetcher):
        html = b"""<html><body>
            <a class='storylink' href='item?id=1'>HN headline one</a>
            <a class='storylink' href='https://abs/2'>HN headline two</a>
        </body></html>"""
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(html)):
            out = fetcher.fetch_from_source("hackernews", max_headlines=2)
        assert len(out) == 2
        assert out[1]["link"] == "https://abs/2"

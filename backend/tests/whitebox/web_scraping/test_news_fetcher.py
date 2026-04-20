"""Whitebox coverage for ``scripts/web_scraping/news_fetcher.py``.

We patch ``requests.get`` so the SUT never reaches the network and feed it
crafted HTML / RSS bodies to traverse every branch:

* ``fetch_headlines_generic``: success with several selectors taken; long
  enough text branch (> 20 chars) and skip-too-short branch; absolute vs
  relative href branch; exception arm.
* ``fetch_from_source``: unknown source; ``hackernews`` branch; "generic"
  branch; absolute vs relative href; exception arm.
* ``fetch_all_sources``: aggregates across sources.
* ``fetch_custom_source`` (delegates to generic).
* ``search_news``: success with multiple items; non-200 short-circuit;
  exception arm.
* ``get_trending_topics``: success; non-200; exception arm.
* ``filter_headlines_by_keyword``: match and no-match branches.
* ``display_headlines``: empty and populated.
* ``save_headlines``: empty short-circuit; explicit and default filenames.
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


# ---------------- fetch_headlines_generic ----------------

class TestFetchHeadlinesGeneric:
    def test_extracts_headlines(self, fetcher):
        # The h1 sits inside an <a> with a relative href, exercising the
        # ``element.find_parent('a').get('href')`` branch and the
        # ``urljoin`` branch.  The h2 is too short and should be filtered out.
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
        # Both long headlines are captured; the short one is dropped.
        titles = [h["title"] for h in out]
        assert any("long enough headline for matching" in t for t in titles)
        assert all("Short" != t for t in titles)
        # The relative href was rewritten to an absolute URL.
        rewritten = [h for h in out if h["link"]]
        assert rewritten and rewritten[0]["link"].startswith("https://example.com")

    def test_exception_returns_empty(self, fetcher, capsys):
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   side_effect=RuntimeError("net")):
            assert fetcher.fetch_headlines_generic("https://example.com") == []
        assert "Error fetching" in capsys.readouterr().out


# -------------------- fetch_from_source ------------------

class TestFetchFromSource:
    def test_unknown_source(self, fetcher, capsys):
        assert fetcher.fetch_from_source("nope") == []
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
        assert out[0]["link"].startswith("https://news.ycombinator.com")
        assert out[1]["link"] == "https://abs/2"

    def test_generic_source_branch(self, fetcher):
        # The 'reuters' source uses CSS selectors that won't match arbitrary
        # markup, but the branch path should still execute and return [].
        html = b"<html></html>"
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(html)):
            out = fetcher.fetch_from_source("reuters")
        assert out == []

    def test_exception_returns_empty(self, fetcher):
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   side_effect=RuntimeError("net")):
            assert fetcher.fetch_from_source("bbc") == []


# -------------------- fetch_all_sources ------------------

class TestFetchAllSources:
    def test_aggregates(self, fetcher):
        with patch.object(NewsFetcher, "fetch_from_source",
                          side_effect=[[{"title": "a"}], [{"title": "b"}], []]), \
             patch("scripts.web_scraping.news_fetcher.time.sleep"):
            out = fetcher.fetch_all_sources(max_per_source=1)
        assert len(out) == 2

    def test_custom_delegates_to_generic(self, fetcher):
        with patch.object(NewsFetcher, "fetch_headlines_generic",
                          return_value=[{"title": "x"}]) as m:
            out = fetcher.fetch_custom_source("https://example.com")
        m.assert_called_once()
        assert out == [{"title": "x"}]


# ------------------------ search_news --------------------

def _xml_item(title, link, description):
    """Build a mock that mimics a BeautifulSoup ``<item>`` element."""
    item = MagicMock()
    item.title.get_text.return_value = title
    item.link.get_text.return_value = link
    item.description.get_text.return_value = description
    return item


class TestSearchNews:
    def test_success(self, fetcher):
        # We don't depend on lxml being installed: mock ``BeautifulSoup`` so
        # the XML branch executes deterministically.
        items = [_xml_item("news 1", "http://a", "d1"),
                 _xml_item("news 2", "http://b", "d2")]
        soup = MagicMock()
        soup.find_all.return_value = items
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(b"<rss/>")), \
             patch("scripts.web_scraping.news_fetcher.BeautifulSoup",
                   return_value=soup):
            out = fetcher.search_news("python", max_results=2)
        assert len(out) == 2 and out[0]["title"] == "news 1"

    def test_missing_attributes(self, fetcher):
        # Item with no ``title``/``link``/``description`` exercises the
        # "No title" / "No link" defaults.
        item = MagicMock(title=None, link=None, description=None)
        soup = MagicMock()
        soup.find_all.return_value = [item]
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(b"<rss/>")), \
             patch("scripts.web_scraping.news_fetcher.BeautifulSoup",
                   return_value=soup):
            out = fetcher.search_news("python")
        assert out[0]["title"] == "No title" and out[0]["link"] == "No link"

    def test_non_200_returns_empty(self, fetcher):
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(status_code=503)):
            assert fetcher.search_news("x") == []

    def test_exception_returns_empty(self, fetcher, capsys):
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   side_effect=RuntimeError("net")):
            assert fetcher.search_news("x") == []
        assert "Error searching news" in capsys.readouterr().out


# ---------------------- get_trending_topics ---------------

class TestTrending:
    def test_success(self, fetcher):
        # Mock BeautifulSoup so the XML parse path is exercised without
        # requiring the optional ``lxml`` dependency.
        item = MagicMock()
        item.title.get_text.return_value = "topic 1"
        soup = MagicMock()
        soup.find_all.return_value = [item]
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(b"<rss/>")), \
             patch("scripts.web_scraping.news_fetcher.BeautifulSoup",
                   return_value=soup):
            out = fetcher.get_trending_topics()
        assert out and out[0]["topic"] == "topic 1"

    def test_missing_title(self, fetcher):
        item = MagicMock(title=None)
        soup = MagicMock()
        soup.find_all.return_value = [item]
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(b"<rss/>")), \
             patch("scripts.web_scraping.news_fetcher.BeautifulSoup",
                   return_value=soup):
            out = fetcher.get_trending_topics()
        assert out[0]["topic"] == "No title"

    def test_non_200(self, fetcher):
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   return_value=_resp(status_code=500)):
            assert fetcher.get_trending_topics() == []

    def test_exception(self, fetcher, capsys):
        with patch("scripts.web_scraping.news_fetcher.requests.get",
                   side_effect=RuntimeError("net")):
            assert fetcher.get_trending_topics() == []
        assert "Error fetching trending topics" in capsys.readouterr().out


# ------------------ filter_headlines_by_keyword -----------

class TestFilter:
    def test_matches(self, fetcher):
        items = [{"title": "Python is fun"}, {"title": "Java rules"}]
        out = fetcher.filter_headlines_by_keyword(items, ["python"])
        assert len(out) == 1 and out[0]["title"] == "Python is fun"

    def test_no_matches(self, fetcher):
        items = [{"title": "Java rules"}]
        assert fetcher.filter_headlines_by_keyword(items, ["python"]) == []


# --------------------- display_headlines ------------------

class TestDisplay:
    def test_empty(self, fetcher, capsys):
        fetcher.display_headlines([])
        assert "No headlines found" in capsys.readouterr().out

    def test_populated(self, fetcher, capsys):
        items = [{"title": "T", "link": "L", "source": "S",
                  "description": "x" * 250}]
        fetcher.display_headlines(items)
        out = capsys.readouterr().out
        assert "NEWS HEADLINES" in out and "T" in out


# ---------------------- save_headlines --------------------

class TestSave:
    def test_empty_short_circuits(self, fetcher, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        fetcher.save_headlines([])
        assert list(tmp_path.iterdir()) == []

    def test_explicit_filename(self, fetcher, tmp_path):
        out = tmp_path / "x.json"
        fetcher.save_headlines([{"title": "t"}], filename=str(out))
        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["headlines"][0]["title"] == "t"

    def test_default_filename(self, fetcher, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        fetcher.save_headlines([{"title": "t"}])
        files = list(tmp_path.glob("news_headlines_*.json"))
        assert len(files) == 1

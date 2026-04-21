"""Whitebox coverage for ``scripts/web_scraping/web_scraper.py``.

Trimmed to: get_page (success + error), text scraping with selectors, link
filtering, table parsing, JSON save, and page metadata extraction.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.web_scraping.web_scraper import WebScraper


def _resp(content=b""):
    r = MagicMock()
    r.content = content
    r.raise_for_status.return_value = None
    return r


@pytest.fixture
def s():
    return WebScraper(delay=0)


class TestGetPage:
    def test_success(self, s):
        with patch.object(s.session, "get", return_value=_resp(b"x")):
            assert s.get_page("https://x").content == b"x"

    def test_request_exception_returns_none(self, s, capsys):
        with patch.object(s.session, "get",
                          side_effect=requests.exceptions.RequestException("boom")):
            assert s.get_page("https://x") is None
        assert "Error fetching" in capsys.readouterr().out


class TestScrapeText:
    def test_with_selectors(self, s):
        html = b"<html><body><h1>A</h1><h1>B</h1></body></html>"
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_text("u", {"titles": "h1"})
        assert out["titles"] == ["A", "B"]


class TestScrapeLinks:
    def test_with_filter(self, s):
        html = b"<a href='/x.pdf'>x</a><a href='/y.html'>y</a>"
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_links("https://example.com", filter_pattern=r"\.pdf$")
        assert len(out) == 1 and out[0]["url"].endswith(".pdf")


class TestScrapeTable:
    def test_parses_table(self, s):
        html = b"""<table>
            <tr><th>a</th><th>b</th></tr>
            <tr><td>1</td><td>2</td></tr>
            <tr><td>3</td><td>4</td></tr>
        </table>"""
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_table("u")
        assert out[0]["headers"] == ["a", "b"]
        assert out[0]["rows"] == [["1", "2"], ["3", "4"]]


class TestSaveData:
    def test_json(self, s, tmp_path):
        p = tmp_path / "x.json"
        s.save_data([{"a": 1}], str(p), "json")
        assert json.loads(p.read_text(encoding="utf-8")) == [{"a": 1}]


class TestMetadata:
    def test_extracts_metadata(self, s):
        html = b"""<html lang='en'><head>
            <title>The Title</title>
            <meta name='description' content='desc'/>
            <meta name='keywords' content='k1,k2'/>
            <meta name='author' content='me'/>
            <meta charset='utf-8'/>
            <link rel='canonical' href='https://canon'/>
        </head></html>"""
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.get_page_metadata("u")
        assert out["title"] == "The Title"
        assert out["description"] == "desc"
        assert out["canonical_url"] == "https://canon"

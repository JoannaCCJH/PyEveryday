from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import requests

from scripts.web_scraping.web_scraper import WebScraper


# Defines the resp helper.
def _resp(content=b""):
    r = MagicMock()
    r.content = content
    r.raise_for_status.return_value = None
    return r


# Provides the s fixture.
@pytest.fixture
def s():
    return WebScraper(delay=0)


class TestGetPage:
    # Tests success.
    def test_success(self, s):
        with patch.object(s.session, "get", return_value=_resp(b"x")):
            assert s.get_page("https://x").content == b"x"

    # Tests request exception returns none.
    def test_request_exception_returns_none(self, s, capsys):
        with patch.object(s.session, "get",
                          side_effect=requests.exceptions.RequestException("boom")):
            assert s.get_page("https://x") is None
        assert "Error fetching" in capsys.readouterr().out


class TestScrapeText:
    # Tests with selectors.
    def test_with_selectors(self, s):
        html = b"<html><body><h1>A</h1><h1>B</h1></body></html>"
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_text("u", {"titles": "h1"})
        assert out["titles"] == ["A", "B"]


class TestScrapeForms:
    # Tests scrape forms.
    def test_scrape_forms(self, s):
        html = b"""<form action='/submit' method='post'>
            <input type='text' name='q'/>
            <input type='submit' value='Go'/>
        </form>"""
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_forms("https://example.com")
        assert len(out) == 1 and out[0]["method"].upper() == "POST"
        assert any(inp["name"] == "q" for inp in out[0]["fields"])

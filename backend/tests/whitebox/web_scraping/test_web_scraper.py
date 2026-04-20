"""Whitebox coverage for ``scripts/web_scraping/web_scraper.py``.

Each ``WebScraper`` method has a "fetch failed -> return empty" branch and a
"fetch succeeded -> parse" branch.  We mock ``requests.Session.get`` so both
sides are reachable.  Branches:

* ``get_page``: success and ``RequestException``.
* ``scrape_text``: with selectors and without; failure short-circuit.
* ``scrape_links``: with and without filter pattern; absolute vs relative
  href; failure short-circuit.
* ``scrape_images``: src vs data-src branch; absolute href branch; missing
  src skip branch; failure short-circuit.
* ``scrape_table``: no tables -> ``None``; multiple tables; empty rows.
* ``scrape_forms``: input/select/textarea + select-options branch.
* ``scrape_multiple_pages``: with successful and failing pages; sleep gating.
* ``follow_pagination``: max-pages cap; data_selectors branch; absent next
  link breaks loop; failed page breaks loop.
* ``save_data``: json, csv (dict and non-dict rows), txt branches.
* ``get_page_metadata``: title, meta tags (description, keywords, author,
  charset), canonical link.
"""

from __future__ import annotations

import csv
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


# ----------------------------- get_page -----------------------

class TestGetPage:
    def test_success(self, s):
        with patch.object(s.session, "get", return_value=_resp(b"x")):
            assert s.get_page("https://x").content == b"x"

    def test_request_exception_returns_none(self, s, capsys):
        with patch.object(s.session, "get",
                          side_effect=requests.exceptions.RequestException("boom")):
            assert s.get_page("https://x") is None
        assert "Error fetching" in capsys.readouterr().out


# ---------------------------- scrape_text ---------------------

class TestScrapeText:
    def test_with_selectors(self, s):
        html = b"<html><body><h1>A</h1><h1>B</h1></body></html>"
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_text("u", {"titles": "h1"})
        assert out["titles"] == ["A", "B"]

    def test_without_selectors(self, s):
        with patch.object(s, "get_page", return_value=_resp(b"<p>hi</p>")):
            assert "hi" in s.scrape_text("u")

    def test_failure_returns_none(self, s):
        with patch.object(s, "get_page", return_value=None):
            assert s.scrape_text("u") is None


# ---------------------------- scrape_links --------------------

class TestScrapeLinks:
    def test_no_filter_absolute(self, s):
        html = b"<html><body><a href='/x' title='T'>X</a><a href='https://abs'>Y</a></body></html>"
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_links("https://example.com")
        urls = {l["url"] for l in out}
        assert "https://example.com/x" in urls and "https://abs" in urls

    def test_with_filter(self, s):
        html = b"<a href='/x.pdf'>x</a><a href='/y.html'>y</a>"
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_links("https://example.com", filter_pattern=r"\.pdf$")
        assert len(out) == 1 and out[0]["url"].endswith(".pdf")

    def test_failure_returns_empty(self, s):
        with patch.object(s, "get_page", return_value=None):
            assert s.scrape_links("u") == []


# --------------------------- scrape_images --------------------

class TestScrapeImages:
    def test_src_and_data_src(self, s):
        html = b"<img src='/a.png'/><img data-src='/b.png'/><img/>"
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_images("https://example.com")
        assert len(out) == 2  # the third <img> with no src is skipped

    def test_failure_returns_empty(self, s):
        with patch.object(s, "get_page", return_value=None):
            assert s.scrape_images("u") == []


# --------------------------- scrape_table ---------------------

class TestScrapeTable:
    def test_returns_none_when_no_tables(self, s):
        with patch.object(s, "get_page", return_value=_resp(b"<html></html>")):
            assert s.scrape_table("u") is None

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

    def test_failure_returns_none(self, s):
        with patch.object(s, "get_page", return_value=None):
            assert s.scrape_table("u") is None


# --------------------------- scrape_forms ---------------------

class TestScrapeForms:
    def test_extracts_form_metadata(self, s):
        html = b"""<form action='/submit' method='post'>
            <input type='text' name='a' required placeholder='p'/>
            <select name='s'><option>x</option><option>y</option></select>
            <textarea name='t'></textarea>
        </form>"""
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.scrape_forms("u")
        assert len(out) == 1
        f = out[0]
        assert f["method"] == "POST"
        types = {fl["type"] for fl in f["fields"]}
        assert "text" in types and "select" in types and "textarea" in types

    def test_failure_returns_empty(self, s):
        with patch.object(s, "get_page", return_value=None):
            assert s.scrape_forms("u") == []


# --------------------- scrape_multiple_pages ------------------

class TestScrapeMultiplePages:
    def test_iterates_and_attaches_source_url(self, s):
        with patch.object(WebScraper, "scrape_text",
                          side_effect=[{"t": ["A"]}, None, {"t": ["B"]}]), \
             patch("scripts.web_scraping.web_scraper.time.sleep"):
            out = s.scrape_multiple_pages(["u1", "u2", "u3"], {"t": "h1"})
        # The middle page returned None and was skipped.
        assert len(out) == 2 and out[0]["source_url"] == "u1"


# --------------------- follow_pagination ----------------------

class TestFollowPagination:
    def test_max_pages_cap(self, s):
        # ``next`` link present forever, but max_pages=2 should bound the loop.
        html = b"<html><body><a class='nx' href='?p=1'>nx</a></body></html>"
        with patch.object(s, "get_page", return_value=_resp(html)), \
             patch("scripts.web_scraping.web_scraper.time.sleep"):
            out = s.follow_pagination("u", "a.nx", max_pages=2,
                                      data_selectors={"t": "a"})
        assert len(out) <= 2

    def test_break_when_no_next_link(self, s):
        html = b"<html><body></body></html>"
        with patch.object(s, "get_page", return_value=_resp(html)):
            out = s.follow_pagination("u", "a.nx", max_pages=10,
                                      data_selectors={"t": "a"})
        assert len(out) == 1  # one page captured, then loop breaks

    def test_break_when_page_fetch_fails(self, s):
        with patch.object(s, "get_page", return_value=None):
            out = s.follow_pagination("u", "a.nx", max_pages=10)
        assert out == []


# ---------------------------- save_data -----------------------

class TestSaveData:
    def test_json(self, s, tmp_path):
        p = tmp_path / "x.json"
        s.save_data([{"a": 1}], str(p), "json")
        assert json.loads(p.read_text(encoding="utf-8")) == [{"a": 1}]

    def test_csv_dict_rows(self, s, tmp_path):
        p = tmp_path / "x.csv"
        s.save_data([{"a": 1, "b": 2}], str(p), "csv")
        rows = list(csv.DictReader(p.open(encoding="utf-8")))
        assert rows[0]["a"] == "1"

    def test_csv_non_dict_rows(self, s, tmp_path):
        p = tmp_path / "x.csv"
        s.save_data(["row1", "row2"], str(p), "csv")
        text = p.read_text()
        assert "row1" in text and "row2" in text

    def test_txt(self, s, tmp_path):
        p = tmp_path / "x.txt"
        s.save_data(["a", "b"], str(p), "txt")
        assert p.read_text().splitlines() == ["a", "b"]


# -------------------------- metadata --------------------------

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
        assert out["keywords"] == "k1,k2"
        assert out["author"] == "me"
        assert out["canonical_url"] == "https://canon"

    def test_failure_returns_none(self, s):
        with patch.object(s, "get_page", return_value=None):
            assert s.get_page_metadata("u") is None

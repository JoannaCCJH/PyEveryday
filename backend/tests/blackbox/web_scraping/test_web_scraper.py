"""
Black-box tests for scripts.web_scraping.web_scraper.

Applies EP / BA / EG. All HTTP calls are mocked via unittest.mock.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.web_scraping.web_scraper import WebScraper

pytestmark = pytest.mark.blackbox


def _response(body, status=200):
    m = MagicMock()
    m.status_code = status
    m.content = body.encode("utf-8")
    if status >= 400:
        m.raise_for_status.side_effect = requests.HTTPError()
    return m


@pytest.fixture
def ws():
    return WebScraper(delay=0)


LINKS_HTML = """
<html><body>
<a href="https://ext.example.com/page1" title="external">External link</a>
<a href="/local/page">Local link</a>
<a href="#anchor">Anchor</a>
</body></html>
"""

IMAGES_HTML = """
<html><body>
<img src="https://x.example.com/a.png" alt="alt1" title="t1" width="10" height="20">
<img data-src="/b.png" alt="alt2">
<img alt="no-src">
</body></html>
"""

TABLE_HTML = """
<html><body>
<table>
<tr><th>Name</th><th>Age</th></tr>
<tr><td>Alice</td><td>30</td></tr>
<tr><td>Bob</td><td>25</td></tr>
</table>
</body></html>
"""

FORMS_HTML = """
<html><body>
<form action="/submit" method="POST">
  <input type="text" name="email" required>
  <select name="country"><option>US</option><option>UK</option></select>
  <textarea name="notes"></textarea>
</form>
</body></html>
"""

META_HTML = """
<html lang="en"><head>
<title>Page Title</title>
<meta name="description" content="A great page">
<meta name="keywords" content="a, b, c">
<meta name="author" content="Alice">
<link rel="canonical" href="https://canonical.example.com/">
</head><body></body></html>
"""


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestGetPageEP:
    def test_success_returns_response(self, ws):
        # EP: 200 class -> response returned.
        with patch.object(ws.session, "get", return_value=_response("ok")) as m:
            r = ws.get_page("https://example.com")
        assert r is not None
        m.assert_called_once()

    def test_request_exception_returns_none(self, ws, capsys):
        # EP: exception class -> None + printed error.
        with patch.object(ws.session, "get", side_effect=requests.ConnectionError("boom")):
            assert ws.get_page("https://example.com") is None
        assert "Error fetching" in capsys.readouterr().out


class TestScrapeLinksEP:
    def test_all_links_absolute_by_default(self, ws):
        # EP: absolute=True (default) class -> relative links are joined.
        with patch.object(ws.session, "get", return_value=_response(LINKS_HTML)):
            links = ws.scrape_links("https://base.example.com/")
        urls = [l["url"] for l in links]
        assert "https://ext.example.com/page1" in urls
        assert "https://base.example.com/local/page" in urls

    def test_filter_pattern_narrows_results(self, ws):
        # EP: filter pattern class -> only matching links returned.
        with patch.object(ws.session, "get", return_value=_response(LINKS_HTML)):
            links = ws.scrape_links("https://base.example.com/", filter_pattern=r"ext\.example\.com")
        assert len(links) == 1
        assert "ext.example.com" in links[0]["url"]

    def test_no_response_returns_empty_list(self, ws):
        # EP: fetch failure -> [].
        with patch.object(ws.session, "get", side_effect=requests.ConnectionError()):
            assert ws.scrape_links("https://x.example.com") == []


class TestScrapeImagesEP:
    def test_collects_images_with_src_or_data_src(self, ws):
        # EP: src + data-src class -> both captured.
        with patch.object(ws.session, "get", return_value=_response(IMAGES_HTML)):
            imgs = ws.scrape_images("https://base.example.com/")
        urls = [i["url"] for i in imgs]
        assert "https://x.example.com/a.png" in urls
        assert "https://base.example.com/b.png" in urls

    def test_image_without_src_is_skipped(self, ws):
        # EP: no-src class -> skipped.
        with patch.object(ws.session, "get", return_value=_response(IMAGES_HTML)):
            imgs = ws.scrape_images("https://base.example.com/")
        # Only 2 images should be collected.
        assert len(imgs) == 2


class TestScrapeTableEP:
    def test_table_parsed_with_headers_and_rows(self, ws):
        # EP: well-formed table class -> headers + data rows.
        with patch.object(ws.session, "get", return_value=_response(TABLE_HTML)):
            tables = ws.scrape_table("https://x.example.com")
        assert len(tables) == 1
        t = tables[0]
        assert t["headers"] == ["Name", "Age"]
        assert t["rows"] == [["Alice", "30"], ["Bob", "25"]]

    def test_no_table_returns_none(self, ws):
        # EP: no-match class -> None.
        with patch.object(ws.session, "get", return_value=_response("<html></html>")):
            assert ws.scrape_table("https://x.example.com") is None


class TestScrapeFormsEP:
    def test_form_fields_captured(self, ws):
        # EP: form with mixed field types -> list with type, name, required.
        with patch.object(ws.session, "get", return_value=_response(FORMS_HTML)):
            forms = ws.scrape_forms("https://x.example.com")
        assert len(forms) == 1
        f = forms[0]
        assert f["action"] == "/submit"
        assert f["method"] == "POST"
        names = {field["name"] for field in f["fields"]}
        assert names == {"email", "country", "notes"}
        email_field = next(x for x in f["fields"] if x["name"] == "email")
        assert email_field["required"] is True


class TestMetadataEP:
    def test_metadata_extracts_all_documented_fields(self, ws):
        # EP: complete-metadata class -> title, description, keywords, author,
        # canonical_url, lang.
        with patch.object(ws.session, "get", return_value=_response(META_HTML)):
            meta = ws.get_page_metadata("https://x.example.com")
        assert meta["title"] == "Page Title"
        assert meta["description"] == "A great page"
        assert meta["keywords"] == "a, b, c"
        assert meta["author"] == "Alice"
        assert meta["canonical_url"] == "https://canonical.example.com/"
        assert meta["lang"] == "en"


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_scrape_text_no_selectors_returns_stripped_text(self, ws):
        # BA: selectors=None class -> raw stripped text.
        with patch.object(ws.session, "get", return_value=_response("<html><body>  hi  </body></html>")):
            text = ws.scrape_text("https://x.example.com")
        assert text == "hi"

    def test_scrape_text_with_empty_selector_dict_falls_through(self, ws):
        # BA: empty dict is falsy -> SUT falls to the text-only branch.
        with patch.object(ws.session, "get", return_value=_response("<html><body>hi</body></html>")):
            result = ws.scrape_text("https://x.example.com", selectors={})
        assert result == "hi"

    def test_scrape_text_with_selectors(self, ws):
        # BA: non-empty selectors -> dict with one list per selector.
        with patch.object(ws.session, "get", return_value=_response(LINKS_HTML)):
            result = ws.scrape_text("https://x.example.com", selectors={"anchors": "a"})
        assert "anchors" in result
        assert len(result["anchors"]) == 3


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_save_data_json(self, ws, tmp_path):
        # EG: JSON save round-trip.
        import json

        f = tmp_path / "out.json"
        ws.save_data([{"a": 1}, {"a": 2}], str(f), format="json")
        assert json.loads(f.read_text()) == [{"a": 1}, {"a": 2}]

    def test_save_data_csv(self, ws, tmp_path):
        # EG: CSV save round-trip.
        f = tmp_path / "out.csv"
        ws.save_data([{"a": 1, "b": 2}], str(f), format="csv")
        content = f.read_text()
        assert "a,b" in content
        assert "1,2" in content

    def test_save_data_txt(self, ws, tmp_path):
        # EG: TXT save writes one item per line.
        f = tmp_path / "out.txt"
        ws.save_data(["line1", "line2"], str(f), format="txt")
        assert f.read_text() == "line1\nline2\n"

    def test_default_delay_is_one_second(self):
        # EG: documented default delay.
        assert WebScraper().delay == 1

    def test_session_user_agent_is_set(self, ws):
        # EG: default User-Agent header is configured on the session.
        assert "Mozilla" in ws.session.headers.get("User-Agent", "")

from unittest.mock import MagicMock, patch

import pytest

import requests

from scripts.web_scraping.web_scraper import WebScraper

pytestmark = pytest.mark.blackbox


# Defines the response helper.
def _response(body, status=200):
    m = MagicMock()
    m.status_code = status
    m.content = body.encode("utf-8")
    if status >= 400:
        m.raise_for_status.side_effect = requests.HTTPError()
    return m


# Provides the ws fixture.
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


class TestGetPageEP:
    # Tests success returns response.
    def test_success_returns_response(self, ws):
        with patch.object(ws.session, "get", return_value=_response("ok")) as m:
            r = ws.get_page("https://example.com")
        assert r is not None
        m.assert_called_once()

    # Tests request exception returns none.
    def test_request_exception_returns_none(self, ws, capsys):
        with patch.object(ws.session, "get", side_effect=requests.ConnectionError("boom")):
            assert ws.get_page("https://example.com") is None
        assert "Error fetching" in capsys.readouterr().out


class TestScrapeLinksEP:
    # Tests all links absolute by default.
    def test_all_links_absolute_by_default(self, ws):
        with patch.object(ws.session, "get", return_value=_response(LINKS_HTML)):
            links = ws.scrape_links("https://base.example.com/")
        urls = [l["url"] for l in links]
        assert "https://ext.example.com/page1" in urls
        assert "https://base.example.com/local/page" in urls

    # Tests filter pattern narrows results.
    def test_filter_pattern_narrows_results(self, ws):
        with patch.object(ws.session, "get", return_value=_response(LINKS_HTML)):
            links = ws.scrape_links("https://base.example.com/", filter_pattern=r"ext\.example\.com")
        assert len(links) == 1
        assert "ext.example.com" in links[0]["url"]

    # Tests no response returns empty list.
    def test_no_response_returns_empty_list(self, ws):
        with patch.object(ws.session, "get", side_effect=requests.ConnectionError()):
            assert ws.scrape_links("https://x.example.com") == []


class TestScrapeImagesEP:
    # Tests collects images with src or data src.
    def test_collects_images_with_src_or_data_src(self, ws):
        with patch.object(ws.session, "get", return_value=_response(IMAGES_HTML)):
            imgs = ws.scrape_images("https://base.example.com/")
        urls = [i["url"] for i in imgs]
        assert "https://x.example.com/a.png" in urls
        assert "https://base.example.com/b.png" in urls

    # Tests image without src is skipped.
    def test_image_without_src_is_skipped(self, ws):
        with patch.object(ws.session, "get", return_value=_response(IMAGES_HTML)):
            imgs = ws.scrape_images("https://base.example.com/")
        assert len(imgs) == 2


class TestScrapeTableEP:
    # Tests table parsed with headers and rows.
    def test_table_parsed_with_headers_and_rows(self, ws):
        with patch.object(ws.session, "get", return_value=_response(TABLE_HTML)):
            tables = ws.scrape_table("https://x.example.com")
        assert len(tables) == 1
        t = tables[0]
        assert t["headers"] == ["Name", "Age"]
        assert t["rows"] == [["Alice", "30"], ["Bob", "25"]]

    # Tests no table returns none.
    def test_no_table_returns_none(self, ws):
        with patch.object(ws.session, "get", return_value=_response("<html></html>")):
            assert ws.scrape_table("https://x.example.com") is None


class TestScrapeFormsEP:
    # Tests form fields captured.
    def test_form_fields_captured(self, ws):
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
    # Tests metadata extracts all documented fields.
    def test_metadata_extracts_all_documented_fields(self, ws):
        with patch.object(ws.session, "get", return_value=_response(META_HTML)):
            meta = ws.get_page_metadata("https://x.example.com")
        assert meta["title"] == "Page Title"
        assert meta["description"] == "A great page"
        assert meta["keywords"] == "a, b, c"
        assert meta["author"] == "Alice"
        assert meta["canonical_url"] == "https://canonical.example.com/"
        assert meta["lang"] == "en"


class TestBoundaries:
    # Tests scrape text no selectors returns stripped text.
    def test_scrape_text_no_selectors_returns_stripped_text(self, ws):
        with patch.object(ws.session, "get", return_value=_response("<html><body>  hi  </body></html>")):
            text = ws.scrape_text("https://x.example.com")
        assert text == "hi"

    # Tests scrape text with empty selector dict falls through.
    def test_scrape_text_with_empty_selector_dict_falls_through(self, ws):
        with patch.object(ws.session, "get", return_value=_response("<html><body>hi</body></html>")):
            result = ws.scrape_text("https://x.example.com", selectors={})
        assert result == "hi"

    # Tests scrape text with selectors.
    def test_scrape_text_with_selectors(self, ws):
        with patch.object(ws.session, "get", return_value=_response(LINKS_HTML)):
            result = ws.scrape_text("https://x.example.com", selectors={"anchors": "a"})
        assert "anchors" in result
        assert len(result["anchors"]) == 3


class TestErrorGuessing:
    # Tests save data json.
    def test_save_data_json(self, ws, tmp_path):

        import json

        f = tmp_path / "out.json"
        ws.save_data([{"a": 1}, {"a": 2}], str(f), format="json")
        assert json.loads(f.read_text()) == [{"a": 1}, {"a": 2}]

    # Tests save data csv.
    def test_save_data_csv(self, ws, tmp_path):
        f = tmp_path / "out.csv"
        ws.save_data([{"a": 1, "b": 2}], str(f), format="csv")
        content = f.read_text()
        assert "a,b" in content
        assert "1,2" in content

    # Tests save data txt.
    def test_save_data_txt(self, ws, tmp_path):
        f = tmp_path / "out.txt"
        ws.save_data(["line1", "line2"], str(f), format="txt")
        assert f.read_text() == "line1\nline2\n"

    # Tests default delay is one second.
    def test_default_delay_is_one_second(self):
        assert WebScraper().delay == 1

    # Tests session user agent is set.
    def test_session_user_agent_is_set(self, ws):
        assert "Mozilla" in ws.session.headers.get("User-Agent", "")

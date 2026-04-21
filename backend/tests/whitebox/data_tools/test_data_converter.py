"""Whitebox coverage for ``scripts/data_tools/data_converter.py``.

Trimmed to one representative happy-path / error-path per public surface:
JSON, CSV, Excel (if available), XML, flatten/unflatten, validate, compare,
convert_file, sanitize.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from scripts.data_tools.data_converter import DataConverter

try:
    import openpyxl  # noqa: F401
    HAS_EXCEL = True
except Exception:  # pragma: no cover
    HAS_EXCEL = False


@pytest.fixture
def dc():
    return DataConverter()


@pytest.fixture
def sample_records():
    return [
        {"id": 1, "name": "A", "score": 88.5},
        {"id": 2, "name": "B", "score": 92.0},
    ]


class TestJson:
    def test_read_json_list_of_dicts_returns_dataframe(self, tmp_path, dc, sample_records):
        p = tmp_path / "x.json"
        p.write_text(json.dumps(sample_records))
        result = dc.read_json(str(p))
        assert isinstance(result, pd.DataFrame)
        assert list(result["name"]) == ["A", "B"]

    def test_read_json_failure_returns_none(self, tmp_path, dc, capsys):
        assert dc.read_json(str(tmp_path / "missing.json")) is None
        assert "Error reading JSON" in capsys.readouterr().out

    def test_write_json_dataframe_branch(self, tmp_path, dc, sample_records):
        p = tmp_path / "out.json"
        assert dc.write_json(pd.DataFrame(sample_records), str(p)) is True
        assert json.loads(p.read_text())[0]["name"] == "A"


class TestCsv:
    def test_read_write_round_trip(self, tmp_path, dc, sample_records):
        p = tmp_path / "x.csv"
        assert dc.write_csv(sample_records, str(p)) is True
        df = dc.read_csv(str(p))
        assert list(df["name"]) == ["A", "B"]

    def test_write_csv_failure(self, tmp_path, dc):
        bad = tmp_path / "no" / "dir" / "x.csv"
        assert dc.write_csv([{"a": 1}], str(bad)) is False


@pytest.mark.skipif(not HAS_EXCEL, reason="openpyxl not installed")
class TestExcel:
    def test_round_trip(self, tmp_path, dc, sample_records):
        p = tmp_path / "x.xlsx"
        assert dc.write_excel(sample_records, str(p)) is True
        df = dc.read_excel(str(p))
        assert list(df["name"]) == ["A", "B"]


class TestXml:
    def test_round_trip_with_attribute_keys(self, tmp_path, dc):
        rows = [{"@id": "1", "name": "A"}, {"@id": "2", "name": "B"}]
        p = tmp_path / "x.xml"
        assert dc.write_xml(rows, str(p)) is True
        out = dc.read_xml(str(p))
        assert {r["name"] for r in out} == {"A", "B"}


class TestFlatten:
    def test_flatten_dict_with_nested(self, dc):
        out = dc.flatten_json({"a": {"b": {"c": 1}}, "d": 2})
        assert out == {"a.b.c": 1, "d": 2}

    def test_unflatten_dict(self, dc):
        out = dc.unflatten_json({"a.b.c": 1, "a.b.d": 2})
        assert out == {"a": {"b": {"c": 1, "d": 2}}}


class TestValidate:
    def test_validate_json_invalid(self, tmp_path, dc):
        p = tmp_path / "x.json"
        p.write_text("{not-json}")
        ok, msg = dc.validate_json(str(p))
        assert ok is False and "Invalid" in msg

    def test_validate_csv_missing_columns(self, tmp_path, dc):
        p = tmp_path / "x.csv"
        p.write_text("a,b\n1,2\n")
        ok, msg = dc.validate_csv(str(p), expected_columns=["a", "c"])
        assert ok is False and ("Missing" in msg or "Extra" in msg)


class TestCompareData:
    def test_different_content(self, tmp_path, dc, sample_records):
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(json.dumps(sample_records))
        modified = [dict(r) for r in sample_records]
        modified[0]["name"] = "Z"
        b.write_text(json.dumps(modified))
        result = dc.compare_data(str(a), str(b))
        assert result["equal"] is False and "differ at index 0" in result["reason"]


class TestConvertFile:
    def test_json_to_csv(self, tmp_path, dc, sample_records):
        src = tmp_path / "x.json"
        src.write_text(json.dumps(sample_records))
        dst = tmp_path / "x.csv"
        assert dc.convert_file(str(src), str(dst)) is True
        assert dst.exists()


class TestSanitize:
    def test_sanitize_strips_strings_and_fills_na(self, dc):
        df = pd.DataFrame({"name": [" A ", None, " B "], "score": [1, None, 2]})
        cleaned = dc.sanitize_data(df)
        assert list(cleaned["name"]) == ["A", "", "B"]

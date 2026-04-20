"""Whitebox coverage for ``scripts/data_tools/data_converter.py``.

The module is large and pure-functional (modulo file I/O and pandas).  Tests
hit every internal branch:

* ``read_json``: list-of-dicts -> DataFrame, plain dict, exception arm.
* ``write_json``: DataFrame branch and direct dict/list branch.
* ``read_csv`` / ``write_csv``: success + exception.
* ``read_excel`` / ``write_excel``: success + exception (skip cleanly if
  ``openpyxl`` is missing).
* ``read_xml`` / ``write_xml``: attribute branch (``@k``) and element branch.
* ``flatten_json`` / ``unflatten_json``: scalar/dict/list inputs.
* ``validate_json``: valid JSON, invalid JSON, IO error.
* ``validate_csv``: empty, missing/extra columns, valid.
* ``compare_data``: equal, different length, different content, missing input.
* ``auto_read``: every supported extension + unsupported + I/O failure.
* ``convert_file``: JSON->CSV, JSON->XML, JSON->JSON, ->TXT, unsupported,
  non-tabular -> CSV (raises -> handled), failure path.
* ``sanitize_data``, ``preview`` (DataFrame and non-DataFrame branches).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

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


# ---------------------------- JSON ----------------------------

class TestJson:
    def test_read_json_list_of_dicts_returns_dataframe(self, tmp_path, dc, sample_records):
        p = tmp_path / "x.json"
        p.write_text(json.dumps(sample_records))
        result = dc.read_json(str(p))
        assert isinstance(result, pd.DataFrame)
        assert list(result["name"]) == ["A", "B"]

    def test_read_json_returns_dict_for_plain_object(self, tmp_path, dc):
        p = tmp_path / "x.json"
        p.write_text(json.dumps({"k": 1}))
        result = dc.read_json(str(p))
        assert result == {"k": 1}

    def test_read_json_returns_empty_dataframe_for_empty_list(self, tmp_path, dc):
        p = tmp_path / "x.json"
        p.write_text("[]")
        result = dc.read_json(str(p))
        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_read_json_failure_returns_none(self, tmp_path, dc, capsys):
        result = dc.read_json(str(tmp_path / "missing.json"))
        assert result is None
        assert "Error reading JSON" in capsys.readouterr().out

    def test_write_json_dataframe_branch(self, tmp_path, dc, sample_records):
        p = tmp_path / "out.json"
        ok = dc.write_json(pd.DataFrame(sample_records), str(p))
        assert ok is True
        assert json.loads(p.read_text())[0]["name"] == "A"

    def test_write_json_dict_branch(self, tmp_path, dc):
        p = tmp_path / "out.json"
        assert dc.write_json({"k": 1}, str(p)) is True
        assert json.loads(p.read_text()) == {"k": 1}

    def test_write_json_failure_branch(self, tmp_path, dc):
        # Writing into a non-existent directory raises.
        bad = tmp_path / "no" / "dir" / "out.json"
        assert dc.write_json({"k": 1}, str(bad)) is False


# ---------------------------- CSV ----------------------------

class TestCsv:
    def test_read_write_round_trip(self, tmp_path, dc, sample_records):
        p = tmp_path / "x.csv"
        assert dc.write_csv(sample_records, str(p)) is True
        df = dc.read_csv(str(p))
        assert list(df["name"]) == ["A", "B"]

    def test_read_csv_failure(self, tmp_path, dc, capsys):
        assert dc.read_csv(str(tmp_path / "missing.csv")) is None
        assert "Error reading CSV" in capsys.readouterr().out

    def test_write_csv_dataframe_branch(self, tmp_path, dc, sample_records):
        p = tmp_path / "x.csv"
        assert dc.write_csv(pd.DataFrame(sample_records), str(p)) is True

    def test_write_csv_failure(self, tmp_path, dc):
        bad = tmp_path / "no" / "dir" / "x.csv"
        assert dc.write_csv([{"a": 1}], str(bad)) is False


# ---------------------------- Excel ---------------------------

@pytest.mark.skipif(not HAS_EXCEL, reason="openpyxl not installed")
class TestExcel:
    def test_round_trip(self, tmp_path, dc, sample_records):
        p = tmp_path / "x.xlsx"
        assert dc.write_excel(sample_records, str(p)) is True
        df = dc.read_excel(str(p))
        assert list(df["name"]) == ["A", "B"]

    def test_read_excel_failure(self, tmp_path, dc):
        assert dc.read_excel(str(tmp_path / "missing.xlsx")) is None

    def test_write_excel_failure(self, tmp_path, dc):
        bad = tmp_path / "no" / "dir" / "x.xlsx"
        assert dc.write_excel([{"a": 1}], str(bad)) is False


# ---------------------------- XML -----------------------------

class TestXml:
    def test_round_trip_with_attribute_keys(self, tmp_path, dc):
        rows = [{"@id": "1", "name": "A"}, {"@id": "2", "name": "B"}]
        p = tmp_path / "x.xml"
        assert dc.write_xml(rows, str(p)) is True
        out = dc.read_xml(str(p))
        assert {r["name"] for r in out} == {"A", "B"}
        assert all("@id" in r for r in out)

    def test_write_xml_handles_none_value(self, tmp_path, dc):
        p = tmp_path / "x.xml"
        assert dc.write_xml([{"a": None}], str(p)) is True
        text = p.read_text()
        assert "<a></a>" in text or "<a/>" in text  # both are valid serializations

    def test_read_xml_failure(self, tmp_path, dc, capsys):
        assert dc.read_xml(str(tmp_path / "missing.xml")) is None
        assert "Error reading XML" in capsys.readouterr().out

    def test_write_xml_failure(self, tmp_path, dc):
        bad = tmp_path / "no" / "dir" / "x.xml"
        assert dc.write_xml([{"a": 1}], str(bad)) is False


# ------------------- Flatten / Unflatten ----------------------

class TestFlatten:
    def test_flatten_dict_with_nested(self, dc):
        out = dc.flatten_json({"a": {"b": {"c": 1}}, "d": 2})
        assert out == {"a.b.c": 1, "d": 2}

    def test_flatten_list_serializes_to_string(self, dc):
        out = dc.flatten_json({"a": [1, 2, 3]})
        assert out["a"] == "[1, 2, 3]"

    def test_flatten_top_level_list(self, dc):
        out = dc.flatten_json([{"a": {"b": 1}}, 7])
        assert out[0] == {"a.b": 1}
        assert out[1] == 7  # scalar in list short-circuits

    def test_unflatten_dict(self, dc):
        out = dc.unflatten_json({"a.b.c": 1, "a.b.d": 2})
        assert out == {"a": {"b": {"c": 1, "d": 2}}}

    def test_unflatten_list_branch(self, dc):
        out = dc.unflatten_json([{"a.b": 1}, "skip"])
        assert out[0] == {"a": {"b": 1}}
        assert out[1] == "skip"


# -------------------------- Validate --------------------------

class TestValidate:
    def test_validate_json_ok(self, tmp_path, dc):
        p = tmp_path / "x.json"
        p.write_text("[]")
        ok, msg = dc.validate_json(str(p))
        assert ok is True and "Valid" in msg

    def test_validate_json_invalid(self, tmp_path, dc):
        p = tmp_path / "x.json"
        p.write_text("{not-json}")
        ok, msg = dc.validate_json(str(p))
        assert ok is False and "Invalid" in msg

    def test_validate_json_missing_file(self, tmp_path, dc):
        ok, msg = dc.validate_json(str(tmp_path / "nope"))
        assert ok is False and "Error reading file" in msg

    def test_validate_csv_empty(self, tmp_path, dc):
        p = tmp_path / "x.csv"
        p.write_text("")
        ok, _ = dc.validate_csv(str(p))
        assert ok is False

    def test_validate_csv_missing_columns(self, tmp_path, dc):
        p = tmp_path / "x.csv"
        p.write_text("a,b\n1,2\n")
        ok, msg = dc.validate_csv(str(p), expected_columns=["a", "c"])
        assert ok is False and ("Missing" in msg or "Extra" in msg)

    def test_validate_csv_valid(self, tmp_path, dc):
        p = tmp_path / "x.csv"
        p.write_text("a,b\n1,2\n")
        ok, msg = dc.validate_csv(str(p), expected_columns=["a", "b"])
        assert ok is True and "1 rows" in msg

    def test_validate_csv_internal_failure(self, tmp_path, dc):
        # Force the inner read_csv to raise so we hit the outer except.
        with patch.object(DataConverter, "read_csv", side_effect=RuntimeError("boom")):
            ok, msg = dc.validate_csv("doesnt-matter.csv")
        assert ok is False and "Error validating CSV" in msg


# --------------------------- Compare --------------------------

class TestCompareData:
    def test_equal(self, tmp_path, dc, sample_records):
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(json.dumps(sample_records))
        b.write_text(json.dumps(sample_records))
        result = dc.compare_data(str(a), str(b))
        assert result["equal"] is True

    def test_different_length(self, tmp_path, dc, sample_records):
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(json.dumps(sample_records))
        b.write_text(json.dumps(sample_records[:1]))
        result = dc.compare_data(str(a), str(b))
        assert result["equal"] is False
        assert "Different number of records" in result["reason"]

    def test_different_content(self, tmp_path, dc, sample_records):
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(json.dumps(sample_records))
        modified = [dict(r) for r in sample_records]
        modified[0]["name"] = "Z"
        b.write_text(json.dumps(modified))
        result = dc.compare_data(str(a), str(b))
        assert result["equal"] is False and "differ at index 0" in result["reason"]

    def test_returns_none_when_input_unreadable(self, tmp_path, dc):
        result = dc.compare_data(str(tmp_path / "nope1.json"),
                                 str(tmp_path / "nope2.json"))
        assert result is None


# -------------------------- Auto-read -------------------------

class TestAutoRead:
    def test_csv(self, tmp_path, dc):
        p = tmp_path / "x.csv"
        p.write_text("a\n1\n")
        assert isinstance(dc.auto_read(str(p)), pd.DataFrame)

    def test_json(self, tmp_path, dc):
        p = tmp_path / "x.json"
        p.write_text("[]")
        out = dc.auto_read(str(p))
        assert isinstance(out, pd.DataFrame)

    @pytest.mark.skipif(not HAS_EXCEL, reason="openpyxl not installed")
    def test_xlsx(self, tmp_path, dc, sample_records):
        p = tmp_path / "x.xlsx"
        dc.write_excel(sample_records, str(p))
        assert isinstance(dc.auto_read(str(p)), pd.DataFrame)

    def test_xml(self, tmp_path, dc):
        p = tmp_path / "x.xml"
        dc.write_xml([{"a": 1}], str(p))
        assert dc.auto_read(str(p)) is not None

    def test_txt(self, tmp_path, dc):
        p = tmp_path / "x.txt"
        p.write_text("hello")
        assert dc.auto_read(str(p)) == "hello"

    def test_unsupported_extension(self, tmp_path, dc, capsys):
        p = tmp_path / "x.weird"
        p.write_text("noop")
        assert dc.auto_read(str(p)) is None
        assert "Unsupported file extension" in capsys.readouterr().out

    def test_failure_branch(self, tmp_path, dc):
        # Force an unexpected exception path inside auto_read.
        with patch.object(DataConverter, "read_csv", side_effect=RuntimeError("boom")):
            assert dc.auto_read(str(tmp_path / "x.csv")) is None


# --------------------------- Convert --------------------------

class TestConvertFile:
    def test_json_to_csv(self, tmp_path, dc, sample_records):
        src = tmp_path / "x.json"
        src.write_text(json.dumps(sample_records))
        dst = tmp_path / "x.csv"
        assert dc.convert_file(str(src), str(dst)) is True
        assert dst.exists()

    def test_json_to_json(self, tmp_path, dc, sample_records):
        src = tmp_path / "x.json"
        src.write_text(json.dumps(sample_records))
        dst = tmp_path / "y.json"
        assert dc.convert_file(str(src), str(dst)) is True

    def test_json_to_xml(self, tmp_path, dc, sample_records):
        src = tmp_path / "x.json"
        src.write_text(json.dumps(sample_records))
        dst = tmp_path / "x.xml"
        assert dc.convert_file(str(src), str(dst)) is True

    def test_dict_to_txt_uses_json_dump(self, tmp_path, dc):
        src = tmp_path / "x.json"
        src.write_text(json.dumps({"a": 1}))
        dst = tmp_path / "x.txt"
        assert dc.convert_file(str(src), str(dst)) is True
        assert "\"a\": 1" in dst.read_text()

    def test_str_to_txt_uses_str_branch(self, tmp_path, dc):
        src = tmp_path / "x.txt"
        src.write_text("hello")
        dst = tmp_path / "y.txt"
        assert dc.convert_file(str(src), str(dst)) is True
        assert dst.read_text() == "hello"

    def test_unsupported_output(self, tmp_path, dc, sample_records, capsys):
        src = tmp_path / "x.json"
        src.write_text(json.dumps(sample_records))
        dst = tmp_path / "x.weird"
        assert dc.convert_file(str(src), str(dst)) is False
        assert "Unsupported output extension" in capsys.readouterr().out

    def test_input_unreadable(self, tmp_path, dc):
        assert dc.convert_file(str(tmp_path / "nope.json"),
                               str(tmp_path / "x.csv")) is False

    def test_non_tabular_to_csv_raises_branch(self, tmp_path, dc):
        # auto_read returns plain string for .txt -> ValueError in convert_file
        src = tmp_path / "x.txt"
        src.write_text("plain string, not tabular")
        dst = tmp_path / "x.csv"
        assert dc.convert_file(str(src), str(dst)) is False


# ---------------------- Samples / Sanitize --------------------

class TestSamples:
    @pytest.mark.skipif(not HAS_EXCEL, reason="openpyxl not installed")
    def test_create_sample_files(self, tmp_path, dc):
        out = tmp_path / "samples"
        paths = dc.create_sample_files(str(out))
        for key in ["sample.csv", "sample.json", "sample.xlsx", "sample.xml", "sample.txt"]:
            assert Path(paths[key]).exists()


class TestSanitizeAndPreview:
    def test_sanitize_strips_strings_and_fills_na(self, dc):
        df = pd.DataFrame({"name": [" A ", None, " B "], "score": [1, None, 2]})
        cleaned = dc.sanitize_data(df)
        assert list(cleaned["name"]) == ["A", "", "B"]

    def test_preview_dataframe_path(self, tmp_path, dc, sample_records, capsys):
        p = tmp_path / "x.json"
        p.write_text(json.dumps(sample_records))
        dc.preview(str(p))
        out = capsys.readouterr().out
        assert "Preview" in out and "Columns" in out

    def test_preview_non_dataframe_path(self, tmp_path, dc, capsys):
        p = tmp_path / "x.txt"
        p.write_text("hello")
        dc.preview(str(p))
        assert "Content" in capsys.readouterr().out

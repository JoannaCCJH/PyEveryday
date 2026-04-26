"""
Black-box tests for scripts.data_tools.data_converter.

Applies EP / BA / EG. Each test is labeled with its technique and goal.

Uses tmp_path for real file IO (no mocks - pandas-on-disk is part of
the contract under test).
"""
import json
import os

import pytest

from scripts.data_tools.data_converter import DataConverter

pytestmark = pytest.mark.blackbox


@pytest.fixture
def dc():
    return DataConverter()


SAMPLE_RECORDS = [
    {"id": 1, "name": "A", "score": 88.5},
    {"id": 2, "name": "B", "score": 92.0},
    {"id": 3, "name": "C", "score": 77.0},
]


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestAutoReadEP:
    """EP per file extension class."""

    def test_auto_read_json(self, dc, tmp_path):
        # EP: .json extension -> read_json path.
        f = tmp_path / "x.json"
        f.write_text(json.dumps(SAMPLE_RECORDS))
        data = dc.auto_read(str(f))
        assert len(data) == 3

    def test_auto_read_csv(self, dc, tmp_path):
        # EP: .csv extension.
        f = tmp_path / "x.csv"
        f.write_text("a,b\n1,2\n3,4\n")
        data = dc.auto_read(str(f))
        assert list(data.columns) == ["a", "b"]

    def test_auto_read_txt(self, dc, tmp_path):
        # EP: .txt extension -> raw file content.
        f = tmp_path / "x.txt"
        f.write_text("hello world")
        assert dc.auto_read(str(f)) == "hello world"

    def test_auto_read_unknown_extension_returns_none(self, dc, tmp_path):
        # EP: unsupported extension class.
        f = tmp_path / "x.foo"
        f.write_text("content")
        assert dc.auto_read(str(f)) is None

    def test_auto_read_case_insensitive_extension(self, dc, tmp_path):
        # EP: extension dispatch is case-insensitive.
        f = tmp_path / "x.JSON"
        f.write_text(json.dumps({"k": "v"}))
        assert dc.auto_read(str(f)) == {"k": "v"}


class TestValidateJsonEP:
    def test_valid_json_returns_true(self, dc, tmp_path):
        # EP: valid json class.
        f = tmp_path / "v.json"
        f.write_text('{"k": 1}')
        ok, msg = dc.validate_json(str(f))
        assert ok is True

    def test_invalid_json_returns_false(self, dc, tmp_path):
        # EP: invalid json class.
        f = tmp_path / "bad.json"
        f.write_text("{not: valid}")
        ok, msg = dc.validate_json(str(f))
        assert ok is False
        assert "Invalid" in msg

    def test_missing_file_returns_false(self, dc, tmp_path):
        # EP: missing file class.
        ok, msg = dc.validate_json(str(tmp_path / "nope.json"))
        assert ok is False


class TestValidateCsvEP:
    def test_empty_csv_is_invalid(self, dc, tmp_path):
        # EP: empty-file class.
        f = tmp_path / "empty.csv"
        f.write_text("")
        ok, msg = dc.validate_csv(str(f))
        assert ok is False

    def test_csv_with_expected_columns_present(self, dc, tmp_path):
        # EP: expected-columns match class.
        f = tmp_path / "ok.csv"
        f.write_text("a,b\n1,2\n")
        ok, msg = dc.validate_csv(str(f), expected_columns=["a", "b"])
        assert ok is True

    def test_csv_with_missing_column(self, dc, tmp_path):
        # EP: missing-expected-column class.
        f = tmp_path / "miss.csv"
        f.write_text("a\n1\n")
        ok, msg = dc.validate_csv(str(f), expected_columns=["a", "b"])
        assert ok is False
        assert "Missing" in msg


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_empty_list_json_write_and_read(self, dc, tmp_path):
        # BA: empty collection boundary.
        import pandas as pd
        f = tmp_path / "empty.json"
        assert dc.write_json([], str(f)) is True
        data = dc.read_json(str(f))
        # List-of-dicts normally returns a DataFrame; empty list may land
        # as either an empty list or an empty DataFrame.
        if isinstance(data, pd.DataFrame):
            assert data.empty
        else:
            assert data == []

    def test_single_record_round_trip(self, dc, tmp_path):
        # BA: minimum non-empty dataset (1 record).
        f = tmp_path / "one.json"
        assert dc.write_json([{"k": 1}], str(f)) is True
        data = dc.read_json(str(f))
        assert len(data) == 1

    def test_flatten_empty_dict(self, dc):
        # BA: empty dict -> empty dict (identity-ish).
        assert dc.flatten_json({}) == {}

    def test_unflatten_empty_dict(self, dc):
        # BA: empty input -> empty output.
        assert dc.unflatten_json({}) == {}


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_flatten_nested_dict(self, dc):
        # EG: nested dict flattens with dot-joined keys.
        nested = {"a": {"b": {"c": 1}}}
        assert dc.flatten_json(nested) == {"a.b.c": 1}

    def test_unflatten_round_trip_for_nested_dict(self, dc):
        # EG: flatten then unflatten must restore the original structure.
        nested = {"a": {"b": 1, "c": {"d": 2}}}
        assert dc.unflatten_json(dc.flatten_json(nested)) == nested

    def test_flatten_list_becomes_json_string(self, dc):
        # EG / contract: flatten encodes lists as json strings (lossy).
        result = dc.flatten_json({"k": [1, 2, 3]})
        assert result == {"k": "[1, 2, 3]"}

    def test_convert_file_json_to_csv(self, dc, tmp_path):
        # EG: JSON list-of-dicts -> CSV should succeed.
        src = tmp_path / "src.json"
        dst = tmp_path / "dst.csv"
        src.write_text(json.dumps(SAMPLE_RECORDS))
        assert dc.convert_file(str(src), str(dst)) is True
        assert dst.exists()

    def test_convert_file_scalar_json_to_csv_fails_gracefully(self, dc, tmp_path):
        # EG: JSON scalar -> CSV is non-tabular and must return False, not crash.
        src = tmp_path / "scalar.json"
        dst = tmp_path / "out.csv"
        src.write_text('"just a string"')
        assert dc.convert_file(str(src), str(dst)) is False

    def test_convert_file_unknown_output_extension_returns_false(self, dc, tmp_path):
        # EG: unknown output extension -> False.
        src = tmp_path / "s.json"
        src.write_text(json.dumps(SAMPLE_RECORDS))
        dst = tmp_path / "out.foo"
        assert dc.convert_file(str(src), str(dst)) is False

    def test_compare_identical_files_equal(self, dc, tmp_path):
        # EG: two files with identical contents -> equal.
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(json.dumps(SAMPLE_RECORDS))
        b.write_text(json.dumps(SAMPLE_RECORDS))
        result = dc.compare_data(str(a), str(b))
        assert result["equal"] is True

    def test_compare_different_row_order_not_equal(self, dc, tmp_path):
        # EG / FAULT-HUNTING: compare_data is ORDER SENSITIVE. Two files
        # containing the same records in different order currently report
        # "not equal". This documents the contract.
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(json.dumps(SAMPLE_RECORDS))
        b.write_text(json.dumps(list(reversed(SAMPLE_RECORDS))))
        result = dc.compare_data(str(a), str(b))
        assert result["equal"] is False

    def test_compare_different_lengths(self, dc, tmp_path):
        # EG: unequal record counts -> not equal with descriptive reason.
        a = tmp_path / "a.json"
        b = tmp_path / "b.json"
        a.write_text(json.dumps(SAMPLE_RECORDS))
        b.write_text(json.dumps(SAMPLE_RECORDS[:2]))
        result = dc.compare_data(str(a), str(b))
        assert result["equal"] is False
        assert "Different number" in result["reason"]

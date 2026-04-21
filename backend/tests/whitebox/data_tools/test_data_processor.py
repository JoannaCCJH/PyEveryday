"""Whitebox coverage for ``scripts/data_tools/data_processor.py``.

Tightened to one test per public surface: IO, info, clean, filter (equals +
contains), aggregate, sort, datetime conversion.
"""

from __future__ import annotations

import json

import pandas as pd
import pytest

from scripts.data_tools.data_processor import DataProcessor


@pytest.fixture
def dp():
    return DataProcessor(verbose=False)


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "name": ["A", "B", "B", "C"],
        "age": [25, 30, 30, 40],
        "city": ["NY", "LA", "LA", "TX"],
    })


class TestReadData:
    def test_csv(self, tmp_path, dp):
        p = tmp_path / "x.csv"
        p.write_text("a,b\n1,2\n")
        df = dp.read_data(str(p))
        assert list(df.columns) == ["a", "b"]

    def test_unsupported_extension_raises(self, tmp_path, dp):
        p = tmp_path / "x.weird"
        p.write_text("noop")
        with pytest.raises(ValueError):
            dp.read_data(str(p))


class TestWriteData:
    def test_csv(self, tmp_path, dp, sample_df):
        out = tmp_path / "x.csv"
        dp.write_data(sample_df, str(out))
        assert out.exists()


class TestInfo:
    def test_get_data_info_shape_and_dtypes(self, dp, sample_df):
        info = dp.get_data_info(sample_df)
        assert info["rows"] == 4
        assert info["columns"] == 3
        assert info["duplicates"] == 1


class TestClean:
    def test_fill_nulls_object_and_numeric(self, dp):
        df = pd.DataFrame({"a": [1.0, None, 3.0], "b": ["x", None, "y"]})
        out = dp.clean_data(df, {"fill_nulls": True})
        assert out["b"].isna().sum() == 0
        assert out["a"].isna().sum() == 0


class TestFilter:
    @pytest.fixture
    def df(self):
        return pd.DataFrame({"a": [1, 2, 3, 4, 5], "s": ["foo", "bar", "baz", "qux", "foo"]})

    def test_equals(self, dp, df):
        out = dp.filter_data(df, [{"column": "a", "operator": "equals", "value": 3}])
        assert len(out) == 1

    def test_contains(self, dp, df):
        out = dp.filter_data(df, [{"column": "s", "operator": "contains", "value": "fo"}])
        assert len(out) == 2


class TestAggregate:
    def test_aggregate(self, dp, sample_df):
        out = dp.aggregate_data(sample_df, group_by="city", aggregations={"age": "mean"})
        assert "city" in out.columns and "age" in out.columns


class TestSort:
    def test_sort_desc(self, dp, sample_df):
        sorted_df = dp.sort_data(sample_df, "age", ascending=False)
        assert list(sorted_df["age"]) == [40, 30, 30, 25]


class TestConvertDataTypes:
    def test_datetime_conversion(self, dp):
        df = pd.DataFrame({"d": ["2020-01-01", "2020-01-02"]})
        out = dp.convert_data_types(df, {"d": "datetime"})
        assert pd.api.types.is_datetime64_any_dtype(out["d"])

"""
Black-box tests for scripts.MachineLearning.prediction.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
Tests target pure-logic pieces: date parsing, sales parsing, model
contract (train + forecast). File-extraction paths (PDF/DOCX/image) are
out of scope - they depend on optional system tools.
"""
from datetime import datetime

import pandas as pd
import pytest

from scripts.MachineLearning.prediction import SalesPredictor

pytestmark = pytest.mark.blackbox


@pytest.fixture
def predictor():
    return SalesPredictor()


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestTryParseDateEP:
    @pytest.mark.parametrize("s, expected", [
        ("2024-06-15", datetime(2024, 6, 15)),
        ("2024/06/15", datetime(2024, 6, 15)),
        ("15-06-2024", datetime(2024, 6, 15)),
        ("2024-06", datetime(2024, 6, 1)),
    ])
    def test_accepted_date_formats(self, predictor, s, expected):
        # EP: one representative per accepted format class.
        assert predictor.try_parse_date(s) == expected

    def test_unparseable_returns_none(self, predictor):
        # EP: invalid input class -> None.
        assert predictor.try_parse_date("not-a-date") is None

    def test_empty_string_returns_none(self, predictor):
        # EP: empty string class -> None.
        assert predictor.try_parse_date("") is None


class TestParseSalesEP:
    def test_valid_line_produces_row(self, predictor):
        # EP: valid-line class -> at least one row is produced.
        df = predictor.parse_sales("2024-01-15 100")
        assert len(df) >= 1
        assert "date" in df.columns and "sales" in df.columns

    def test_line_without_date_is_ignored(self, predictor):
        # EP: no-date class -> row skipped.
        df = predictor.parse_sales("hello 123.45")
        assert df.empty

    def test_line_without_number_returns_dataframe(self, predictor):
        # EP: no-number class -> returns DataFrame (no crash).
        df = predictor.parse_sales("2024-01-15 nothing numeric")
        assert isinstance(df, pd.DataFrame)

    def test_empty_text_returns_empty_dataframe(self, predictor):
        # EP: empty input class -> empty DataFrame with the right columns.
        df = predictor.parse_sales("")
        assert df.empty
        assert list(df.columns) == ["date", "sales"]

    def test_duplicates_removed(self, predictor):
        # EP: duplicate lines class -> deduplicated.
        text = "2024-01-15 100\n2024-01-15 100"
        df = predictor.parse_sales(text)
        assert len(df) == 1

    def test_result_sorted_by_date(self, predictor):
        # EP: multi-line class -> output sorted ascending by date.
        text = "2024-03-01 30\n2024-01-01 10\n2024-02-01 20"
        df = predictor.parse_sales(text)
        # Three distinct dates parsed; order must be ascending.
        dates = df["date"].tolist()
        assert dates == sorted(dates)


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestTrainForecastBA:
    def _tiny_frame(self):
        return pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03",
                                    "2024-01-04", "2024-01-05"]),
            "sales": [10.0, 12.0, 14.0, 16.0, 18.0],
        })

    def test_forecast_before_training_raises(self, predictor):
        # BA: pre-condition - forecast without train -> RuntimeError.
        with pytest.raises(RuntimeError):
            predictor.forecast(10)

    def test_forecast_returns_exactly_n_days(self, predictor):
        # BA: forecast(n) -> exactly n rows.
        predictor.train(self._tiny_frame())
        out = predictor.forecast(days=7)
        assert len(out) == 7
        assert list(out.columns) == ["date", "sales"]

    def test_forecast_two_days_returns_two_rows(self, predictor):
        # BA: days=2 near lower bound.
        predictor.train(self._tiny_frame())
        out = predictor.forecast(days=2)
        assert len(out) == 2

    def test_forecast_one_day_is_minimum(self, predictor):
        # BA: days=1 minimum positive.
        predictor.train(self._tiny_frame())
        out = predictor.forecast(days=1)
        assert len(out) == 1
        # First forecast date must be AFTER the last training date.
        assert out.iloc[0]["date"] > predictor.df["date"].max()


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_parse_sales_does_not_crash_on_separators(self, predictor):
        # EG: thousands-separator input class -> no crash.
        df = predictor.parse_sales("2024-01-15 12,345")
        assert isinstance(df, pd.DataFrame)

    def test_parse_sales_with_only_numbers_but_no_dates_returns_empty(self, predictor):
        # EG: numbers-only input class -> empty DataFrame.
        df = predictor.parse_sales("100\n200\n300")
        assert df.empty

    def test_train_drops_rows_with_nat_dates(self, predictor):
        # EG: rows with unparseable dates are silently dropped before fit.
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "bogus", "2024-01-03"],
            "sales": [1, 2, 3, 4],
        })
        predictor.train(df)
        # train() stores the cleaned frame in self.df
        assert len(predictor.df) == 3

    def test_train_returns_the_fitted_model(self, predictor):
        # EG: train returns the model instance for chaining.
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "sales": [1.0, 2.0, 3.0],
        })
        model = predictor.train(df)
        assert model is predictor.model

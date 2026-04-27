from datetime import datetime

import pandas as pd

import pytest

from scripts.MachineLearning.prediction import SalesPredictor

pytestmark = pytest.mark.blackbox


# Provides the predictor fixture.
@pytest.fixture
def predictor():
    return SalesPredictor()


class TestTryParseDateEP:
    # Tests accepted date formats.
    @pytest.mark.parametrize("s, expected", [
        ("2024-06-15", datetime(2024, 6, 15)),
        ("2024/06/15", datetime(2024, 6, 15)),
        ("15-06-2024", datetime(2024, 6, 15)),
        ("2024-06", datetime(2024, 6, 1)),
    ])
    def test_accepted_date_formats(self, predictor, s, expected):
        assert predictor.try_parse_date(s) == expected

    # Tests unparseable returns none.
    def test_unparseable_returns_none(self, predictor):
        assert predictor.try_parse_date("not-a-date") is None

    # Tests empty string returns none.
    def test_empty_string_returns_none(self, predictor):
        assert predictor.try_parse_date("") is None


class TestParseSalesEP:
    # Tests valid line produces row.
    def test_valid_line_produces_row(self, predictor):
        df = predictor.parse_sales("2024-01-15 100")
        assert len(df) >= 1
        assert "date" in df.columns and "sales" in df.columns

    # Tests line without date is ignored.
    def test_line_without_date_is_ignored(self, predictor):
        df = predictor.parse_sales("hello 123.45")
        assert df.empty

    # Tests line without number returns dataframe.
    def test_line_without_number_returns_dataframe(self, predictor):
        df = predictor.parse_sales("2024-01-15 nothing numeric")
        assert isinstance(df, pd.DataFrame)

    # Tests empty text returns empty dataframe.
    def test_empty_text_returns_empty_dataframe(self, predictor):
        df = predictor.parse_sales("")
        assert df.empty
        assert list(df.columns) == ["date", "sales"]

    # Tests duplicates removed.
    def test_duplicates_removed(self, predictor):
        text = "2024-01-15 100\n2024-01-15 100"
        df = predictor.parse_sales(text)
        assert len(df) == 1

    # Tests result sorted by date.
    def test_result_sorted_by_date(self, predictor):
        text = "2024-03-01 30\n2024-01-01 10\n2024-02-01 20"
        df = predictor.parse_sales(text)
        dates = df["date"].tolist()
        assert dates == sorted(dates)


class TestTrainForecastBA:
    # Defines the tiny_frame helper.
    def _tiny_frame(self):
        return pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03",
                                    "2024-01-04", "2024-01-05"]),
            "sales": [10.0, 12.0, 14.0, 16.0, 18.0],
        })

    # Tests forecast before training raises.
    def test_forecast_before_training_raises(self, predictor):
        with pytest.raises(RuntimeError):
            predictor.forecast(10)

    # Tests forecast returns exactly n days.
    def test_forecast_returns_exactly_n_days(self, predictor):
        predictor.train(self._tiny_frame())
        out = predictor.forecast(days=7)
        assert len(out) == 7
        assert list(out.columns) == ["date", "sales"]

    # Tests forecast two days returns two rows.
    def test_forecast_two_days_returns_two_rows(self, predictor):
        predictor.train(self._tiny_frame())
        out = predictor.forecast(days=2)
        assert len(out) == 2

    # Tests forecast one day is minimum.
    def test_forecast_one_day_is_minimum(self, predictor):
        predictor.train(self._tiny_frame())
        out = predictor.forecast(days=1)
        assert len(out) == 1
        assert out.iloc[0]["date"] > predictor.df["date"].max()


class TestErrorGuessing:
    # Tests parse sales does not crash on separators.
    def test_parse_sales_does_not_crash_on_separators(self, predictor):
        df = predictor.parse_sales("2024-01-15 12,345")
        assert isinstance(df, pd.DataFrame)

    # Tests parse sales with only numbers but no dates returns empty.
    def test_parse_sales_with_only_numbers_but_no_dates_returns_empty(self, predictor):
        df = predictor.parse_sales("100\n200\n300")
        assert df.empty

    # Tests train drops rows with nat dates.
    def test_train_drops_rows_with_nat_dates(self, predictor):
        df = pd.DataFrame({
            "date": ["2024-01-01", "2024-01-02", "bogus", "2024-01-03"],
            "sales": [1, 2, 3, 4],
        })
        predictor.train(df)
        assert len(predictor.df) == 3

    # Tests train returns the fitted model.
    def test_train_returns_the_fitted_model(self, predictor):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "sales": [1.0, 2.0, 3.0],
        })
        model = predictor.train(df)
        assert model is predictor.model

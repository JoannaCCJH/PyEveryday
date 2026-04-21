"""Whitebox coverage for ``scripts/MachineLearning/prediction.py``.

Trimmed to the essential branches plus the bug-finding test
``test_extracts_date_number_pairs`` which currently fails because
``parse_sales``'s ``NUMBER_PATTERN`` captures ``202`` from ``2024`` instead of
the real sales figure.  Do NOT remove that test — it is documenting a real
SUT bug.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from backend.scripts.MachineLearning import prediction


@pytest.fixture
def predictor():
    return prediction.SalesPredictor()


class TestTryParseDate:
    @pytest.mark.parametrize("text,expected_year", [
        ("2024-01-15", 2024),
        ("15-01-2024", 2024),
    ])
    def test_supported_formats(self, predictor, text, expected_year):
        dt = predictor.try_parse_date(text)
        assert dt is not None and dt.year == expected_year

    def test_invalid_returns_none(self, predictor):
        assert predictor.try_parse_date("nope") is None


class TestParseSales:
    def test_extracts_date_number_pairs(self, predictor):
        """Currently FAILS — documents a real SUT bug in NUMBER_PATTERN."""
        text = "2024-01-15 1000\n2024-02-20 2,000.50"
        df = predictor.parse_sales(text)
        assert len(df) == 2
        assert list(df["sales"]) == [1000.0, 2000.5]

    def test_blank_input_returns_empty(self, predictor, caplog):
        import logging as _logging
        with caplog.at_level(_logging.WARNING):
            df = predictor.parse_sales("\n   \n")
        assert df.empty
        assert any("No sales data found" in rec.message for rec in caplog.records)


class TestTrain:
    def test_fits_model(self, predictor):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "sales": [10.0, 20.0, 30.0],
        })
        model = predictor.train(df)
        assert model is not None
        assert predictor.df is not None and "t" in predictor.df.columns


class TestForecast:
    def test_raises_when_untrained(self, predictor):
        with pytest.raises(RuntimeError):
            predictor.forecast(5)

    def test_returns_expected_shape(self, predictor):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "sales": [10.0, 20.0, 30.0],
        })
        predictor.train(df)
        out = predictor.forecast(7)
        assert len(out) == 7 and {"date", "sales"} <= set(out.columns)


class TestPlotForecast:
    def test_saves_file(self, tmp_path, predictor):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"]),
            "sales": [10.0, 20.0],
        })
        predictor.train(df)
        forecast = predictor.forecast(3)
        out = tmp_path / "f.png"
        predictor.plot_forecast(forecast, output_path=str(out))
        assert out.exists()

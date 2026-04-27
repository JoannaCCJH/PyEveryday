from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import pandas as pd

import pytest

from backend.scripts.MachineLearning import prediction


# Provides the predictor fixture.
@pytest.fixture
def predictor():
    return prediction.SalesPredictor()


class TestParseSales:
    # Tests extracts date number pairs.
    def test_extracts_date_number_pairs(self, predictor):
        text = "2024-01-15 1000\n2024-02-20 2,000.50"
        df = predictor.parse_sales(text)
        assert len(df) == 2
        assert list(df["sales"]) == [1000.0, 2000.5]

    # Tests blank input returns empty.
    def test_blank_input_returns_empty(self, predictor):
        df = predictor.parse_sales("\n   \n")
        assert df.empty


class TestForecast:
    # Tests raises when untrained.
    def test_raises_when_untrained(self, predictor):
        with pytest.raises(RuntimeError):
            predictor.forecast(5)

    # Tests train then forecast.
    def test_train_then_forecast(self, predictor):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "sales": [10.0, 20.0, 30.0],
        })
        predictor.train(df)
        out = predictor.forecast(7)
        assert len(out) == 7 and {"date", "sales"} <= set(out.columns)

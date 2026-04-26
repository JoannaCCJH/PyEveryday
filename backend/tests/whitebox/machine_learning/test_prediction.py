"""Whitebox coverage for ``scripts/MachineLearning/prediction.py``.

Slimmed.  Keeps the bug-finding test ``test_extracts_date_number_pairs``
which currently FAILS because ``parse_sales``'s ``NUMBER_PATTERN``
captures ``202`` from ``2024`` instead of the real sales figure.
Do NOT remove that test — it documents a real SUT bug.
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


class TestParseSales:
    def test_extracts_date_number_pairs(self, predictor):
        """Currently FAILS — documents a real SUT bug in NUMBER_PATTERN."""
        text = "2024-01-15 1000\n2024-02-20 2,000.50"
        df = predictor.parse_sales(text)
        assert len(df) == 2
        assert list(df["sales"]) == [1000.0, 2000.5]

    def test_blank_input_returns_empty(self, predictor):
        df = predictor.parse_sales("\n   \n")
        assert df.empty


class TestForecast:
    def test_raises_when_untrained(self, predictor):
        with pytest.raises(RuntimeError):
            predictor.forecast(5)

    def test_train_then_forecast(self, predictor):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "sales": [10.0, 20.0, 30.0],
        })
        predictor.train(df)
        out = predictor.forecast(7)
        assert len(out) == 7 and {"date", "sales"} <= set(out.columns)

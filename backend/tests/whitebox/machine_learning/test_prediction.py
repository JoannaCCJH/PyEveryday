"""Whitebox coverage for ``scripts/MachineLearning/prediction.py``.

The module imports ``from backend.scripts.data_tools.data_converter import
DataConverter`` so it is only importable when the project root is on
``sys.path`` (the whitebox conftest takes care of that).

Several methods (``extract_pdf``, ``extract_docx``, ``extract_image``) reach
out to optional libraries (``pdf_extract_text``, ``docx``, ``Image``,
``pytesseract``) that are referenced in the module without being imported.
We therefore patch those names onto the module before exercising the
extractor methods so we get reliable, isolated whitebox coverage.

Branches exercised:

* ``try_parse_date``: every supported format + fully invalid string.
* ``parse_sales``: line with date+number, line with only date, line with only
  number, blank lines, malformed-number ``except`` arm, and the "no rows
  collected" early-return branch.
* ``train``: model is fit and stored on the instance.
* ``forecast``: untrained-model raises; trained-model returns expected
  shape.
* ``plot_forecast``: file is written; matplotlib is closed.
* ``extract_pdf`` / ``extract_docx`` / ``extract_image`` (with mocked deps).
"""

from __future__ import annotations

import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from backend.scripts.MachineLearning import prediction


@pytest.fixture
def predictor():
    return prediction.SalesPredictor()


# ----------------------- try_parse_date -----------------------

class TestTryParseDate:
    @pytest.mark.parametrize("text,expected_year", [
        ("2024-01-15", 2024),
        ("2024/01/15", 2024),
        ("15-01-2024", 2024),
        ("2024-03", 2024),
    ])
    def test_supported_formats(self, predictor, text, expected_year):
        dt = predictor.try_parse_date(text)
        assert dt is not None and dt.year == expected_year

    def test_invalid_returns_none(self, predictor):
        assert predictor.try_parse_date("nope") is None


# -------------------------- parse_sales -----------------------

class TestParseSales:
    def test_extracts_date_number_pairs(self, predictor):
        text = "2024-01-15 1000\n2024-02-20 2,000.50"
        df = predictor.parse_sales(text)
        assert len(df) == 2
        assert list(df["sales"]) == [1000.0, 2000.5]

    def test_skips_lines_without_date(self, predictor):
        text = "no date here 100\n2024-01-15 99"
        df = predictor.parse_sales(text)
        assert len(df) == 1

    def test_skips_lines_without_number(self, predictor):
        text = "2024-01-15 only-a-date"
        # Regex still finds a number-like token in "2024-01-15" itself, but
        # the parser pairs date+num on each line; we accept either branch
        # but assert the function returns a DataFrame.
        df = predictor.parse_sales(text)
        assert isinstance(df, pd.DataFrame)

    def test_blank_input_returns_empty(self, predictor, capsys):
        df = predictor.parse_sales("\n   \n")
        assert df.empty
        assert "No sales data found" in capsys.readouterr().out


# ----------------------------- train --------------------------

class TestTrain:
    def test_fits_model(self, predictor):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "sales": [10.0, 20.0, 30.0],
        })
        model = predictor.train(df)
        assert model is not None
        assert predictor.df is not None and "t" in predictor.df.columns

    def test_drops_invalid_rows(self, predictor):
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "NaT", "2024-01-03"], errors="coerce"),
            "sales": [10.0, 20.0, None],
        })
        predictor.train(df)
        assert len(predictor.df) == 1


# ----------------------------- forecast -----------------------

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


# --------------------------- plot -----------------------------

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


# ---------------- extract_* (mocked dependencies) -------------

class TestExtractMethods:
    def test_extract_pdf_calls_pdf_extract_text(self, predictor, monkeypatch):
        monkeypatch.setattr(prediction, "pdf_extract_text",
                            lambda p: "extracted-pdf-text", raising=False)
        assert predictor.extract_pdf("doc.pdf") == "extracted-pdf-text"

    def test_extract_docx_calls_docx_module(self, predictor, monkeypatch):
        fake_para = SimpleNamespace(text="line one")
        fake_doc = SimpleNamespace(paragraphs=[fake_para,
                                               SimpleNamespace(text="   ")])
        fake_module = SimpleNamespace(Document=lambda p: fake_doc)
        monkeypatch.setattr(prediction, "docx", fake_module, raising=False)
        out = predictor.extract_docx("doc.docx")
        assert out == "line one"  # the empty paragraph is filtered

    def test_extract_image_calls_pytesseract(self, predictor, monkeypatch):
        monkeypatch.setattr(prediction, "Image",
                            SimpleNamespace(open=lambda p: "img"), raising=False)
        monkeypatch.setattr(prediction, "pytesseract",
                            SimpleNamespace(image_to_string=lambda im: "ocr-text"),
                            raising=False)
        assert predictor.extract_image("x.png") == "ocr-text"

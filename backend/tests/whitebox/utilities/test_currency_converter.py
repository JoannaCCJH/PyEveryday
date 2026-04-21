"""Whitebox coverage for ``scripts/utilities/currency_converter.py``.

Trimmed to the core branches: API success, API fallback-to-offline, cross-
currency conversion, missing-target short-circuit, historical rate, currency
formatting, and history persistence.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.utilities.currency_converter import CurrencyConverter


@pytest.fixture
def cc():
    return CurrencyConverter()


def _resp(payload, status_code=200):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


class TestGetExchangeRates:
    def test_success(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   return_value=_resp({"rates": {"EUR": 0.9}})):
            assert cc.get_exchange_rates("USD") == {"EUR": 0.9}

    def test_failure_falls_back_to_offline(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   side_effect=RuntimeError("net down")):
            rates = cc.get_exchange_rates("USD")
        assert "EUR" in rates and "GBP" in rates


class TestConvert:
    def test_cross_currency_branch(self, cc):
        with patch.object(CurrencyConverter, "get_exchange_rates",
                          return_value={"EUR": 0.5, "GBP": 0.4}):
            # 100 EUR -> 200 USD -> 80 GBP
            assert cc.convert(100, "EUR", "GBP") == 80.0

    def test_missing_target_returns_none(self, cc, capsys):
        with patch.object(CurrencyConverter, "get_exchange_rates",
                          return_value={"EUR": 0.9}):
            assert cc.convert(100, "USD", "ZZZ") is None
        assert "Conversion not available" in capsys.readouterr().out


class TestHistorical:
    def test_success(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   return_value=_resp({"rates": {"EUR": 0.85}})):
            assert cc.get_historical_rate("2024-01-01", "USD", "EUR") == 0.85


class TestFormatCurrency:
    def test_usd_symbol(self, cc):
        assert cc.format_currency(1234.5, "USD") == "$1,234.50"


class TestSaveHistory:
    def test_creates_new_file(self, tmp_path, cc, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cc.save_conversion_history({"a": 1})
        data = json.loads((tmp_path / "conversion_history.json").read_text())
        assert data == [{"a": 1}]

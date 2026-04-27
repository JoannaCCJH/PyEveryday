from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scripts.utilities.currency_converter import CurrencyConverter


# Provides the cc fixture.
@pytest.fixture
def cc():
    return CurrencyConverter()


# Defines the resp helper.
def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


class TestExchangeRates:
    # Tests failure falls back to offline.
    def test_failure_falls_back_to_offline(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   side_effect=RuntimeError("net down")):
            rates = cc.get_exchange_rates("USD")
        assert "EUR" in rates and "GBP" in rates


class TestConvert:
    # Tests branch coverage.
    def test_branch_coverage(self, cc, capsys):
        with patch.object(CurrencyConverter, "get_exchange_rates",
                          return_value={"EUR": 0.5, "GBP": 0.4}):
            assert cc.convert(50, "USD", "USD") == 50
            assert cc.convert(100, "USD", "EUR") == 50.0
            assert cc.convert(100, "EUR", "USD") == 200.0
            assert cc.convert(100, "EUR", "GBP") == 80.0
            assert cc.convert(100, "USD", "ZZZ") is None
        assert "Conversion not available" in capsys.readouterr().out


class TestFormatCurrency:
    # Tests symbol and decimals.
    @pytest.mark.parametrize("code,amount,expected", [
        ("USD", 1234.5, "$1,234.50"),
        ("JPY", 1234.6, "¥1,235"),
        ("ZZZ", 10, "ZZZ10.00"),
    ])
    def test_symbol_and_decimals(self, cc, code, amount, expected):
        assert cc.format_currency(amount, code) == expected

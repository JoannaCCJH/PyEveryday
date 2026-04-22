"""
Black-box tests for scripts.utilities.currency_converter.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
Network calls are mocked via unittest.mock.
"""
from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.utilities.currency_converter import CurrencyConverter

pytestmark = pytest.mark.blackbox


def _ok_response(payload):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = payload
    m.raise_for_status = MagicMock()
    return m


@pytest.fixture
def cc():
    return CurrencyConverter()


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestConvertEP:
    """EP partitions: same vs different currencies; USD-side vs cross."""

    def test_same_currency_returns_input_amount(self, cc):
        # EP: from == to -> identity, no network call.
        with patch("requests.get") as mock_get:
            assert cc.convert(100, "USD", "USD") == 100
        mock_get.assert_not_called()

    def test_usd_to_other_currency_uses_exchange_rates(self, cc):
        # EP: USD -> foreign -> amount * rate.
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(100, "USD", "EUR") == pytest.approx(85.0)

    def test_other_to_usd_divides_by_rate(self, cc):
        # EP: foreign -> USD -> amount / rate.
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(85, "EUR", "USD") == pytest.approx(100.0)

    def test_cross_currency_pivots_through_usd(self, cc):
        # EP: EUR -> GBP via USD.
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85, "GBP": 0.73}})):
            # 85 EUR -> 100 USD -> 73 GBP.
            assert cc.convert(85, "EUR", "GBP") == pytest.approx(73.0)

    def test_unknown_target_currency_returns_none(self, cc):
        # EP: target not in rates dict -> None.
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(100, "USD", "BOGUS") is None

    def test_case_insensitive_currency_codes(self, cc):
        # EP: currency codes uppercased internally.
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(100, "usd", "eur") == pytest.approx(85.0)


class TestFormatCurrencyEP:
    @pytest.mark.parametrize("currency, symbol", [
        ("USD", "$"),
        ("EUR", "\u20ac"),
        ("GBP", "\u00a3"),
        ("JPY", "\u00a5"),
    ])
    def test_known_symbols(self, cc, currency, symbol):
        # EP: known-currency class -> proper prefix symbol.
        assert cc.format_currency(1000, currency).startswith(symbol)

    def test_unknown_currency_prefixes_code(self, cc):
        # EP: unknown-currency class -> prefixed with the code itself.
        assert cc.format_currency(100, "XYZ").startswith("XYZ")

    def test_jpy_has_no_decimal_places(self, cc):
        # EP: JPY special-cased to 0 decimals.
        assert cc.format_currency(1234.56, "JPY") == "\u00a51,235"

    def test_usd_has_two_decimal_places(self, cc):
        # EP: default class uses 2 decimals.
        assert cc.format_currency(1234.5, "USD") == "$1,234.50"


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_zero_amount(self, cc):
        # BA: 0 amount -> 0 result.
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(0, "USD", "EUR") == 0

    def test_negative_amount_still_converts(self, cc):
        # BA: negative amount passes through multiplication.
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(-100, "USD", "EUR") == pytest.approx(-85.0)

    def test_percentage_change_zero_old_rate(self, cc):
        # BA: old_rate == 0 is falsy -> returns None.
        assert cc.calculate_percentage_change(0, 100) is None

    def test_percentage_change_none_new_rate(self, cc):
        # BA: new_rate is None -> returns None.
        assert cc.calculate_percentage_change(100, None) is None

    def test_percentage_change_positive(self, cc):
        # BA: normal positive change.
        assert cc.calculate_percentage_change(100, 110) == 10.0


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_exchange_rate_fetch_fails_falls_back(self, cc):
        # EG: the primary API raises -> fallback to offline rates.
        def _side_effect(url, **kw):
            raise requests.exceptions.ConnectionError("down")

        with patch("requests.get", side_effect=_side_effect):
            rates = cc.get_exchange_rates("USD")
        # Offline rates are the documented fallback; must contain EUR.
        assert "EUR" in rates

    def test_get_currency_info_known(self, cc):
        # EG: known currency -> documented name.
        assert cc.get_currency_info("USD") == "US Dollar"

    def test_get_currency_info_unknown(self, cc):
        # EG: unknown currency -> "Unknown Currency".
        assert cc.get_currency_info("ZZZ") == "Unknown Currency"

    def test_get_currency_info_lowercase(self, cc):
        # EG: lowercase input is upper-cased internally.
        assert cc.get_currency_info("usd") == "US Dollar"

from unittest.mock import MagicMock, patch

import pytest

import requests

from scripts.utilities.currency_converter import CurrencyConverter

pytestmark = pytest.mark.blackbox


# Defines the ok_response helper.
def _ok_response(payload):
    m = MagicMock()
    m.status_code = 200
    m.json.return_value = payload
    m.raise_for_status = MagicMock()
    return m


# Provides the cc fixture.
@pytest.fixture
def cc():
    return CurrencyConverter()


class TestConvertEP:
    # Tests same currency returns input amount.
    def test_same_currency_returns_input_amount(self, cc):
        with patch("requests.get") as mock_get:
            assert cc.convert(100, "USD", "USD") == 100
        mock_get.assert_not_called()

    # Tests usd to other currency uses exchange rates.
    def test_usd_to_other_currency_uses_exchange_rates(self, cc):
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(100, "USD", "EUR") == pytest.approx(85.0)

    # Tests other to usd divides by rate.
    def test_other_to_usd_divides_by_rate(self, cc):
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(85, "EUR", "USD") == pytest.approx(100.0)

    # Tests cross currency pivots through usd.
    def test_cross_currency_pivots_through_usd(self, cc):
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85, "GBP": 0.73}})):
            assert cc.convert(85, "EUR", "GBP") == pytest.approx(73.0)

    # Tests unknown target currency returns none.
    def test_unknown_target_currency_returns_none(self, cc):
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(100, "USD", "BOGUS") is None

    # Tests case insensitive currency codes.
    def test_case_insensitive_currency_codes(self, cc):
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(100, "usd", "eur") == pytest.approx(85.0)


class TestFormatCurrencyEP:
    # Tests known symbols.
    @pytest.mark.parametrize("currency, symbol", [
        ("USD", "$"),
        ("EUR", "\u20ac"),
        ("GBP", "\u00a3"),
        ("JPY", "\u00a5"),
    ])
    def test_known_symbols(self, cc, currency, symbol):
        assert cc.format_currency(1000, currency).startswith(symbol)

    # Tests unknown currency prefixes code.
    def test_unknown_currency_prefixes_code(self, cc):
        assert cc.format_currency(100, "XYZ").startswith("XYZ")

    # Tests jpy has no decimal places.
    def test_jpy_has_no_decimal_places(self, cc):
        assert cc.format_currency(1234.56, "JPY") == "\u00a51,235"

    # Tests usd has two decimal places.
    def test_usd_has_two_decimal_places(self, cc):
        assert cc.format_currency(1234.5, "USD") == "$1,234.50"


class TestBoundaries:
    # Tests zero amount.
    def test_zero_amount(self, cc):
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(0, "USD", "EUR") == 0

    # Tests negative amount still converts.
    def test_negative_amount_still_converts(self, cc):
        with patch("requests.get", return_value=_ok_response({"rates": {"EUR": 0.85}})):
            assert cc.convert(-100, "USD", "EUR") == pytest.approx(-85.0)

    # Tests percentage change zero old rate.
    def test_percentage_change_zero_old_rate(self, cc):
        assert cc.calculate_percentage_change(0, 100) is None

    # Tests percentage change none new rate.
    def test_percentage_change_none_new_rate(self, cc):
        assert cc.calculate_percentage_change(100, None) is None

    # Tests percentage change positive.
    def test_percentage_change_positive(self, cc):
        assert cc.calculate_percentage_change(100, 110) == 10.0


class TestErrorGuessing:
    # Tests exchange rate fetch fails falls back.
    def test_exchange_rate_fetch_fails_falls_back(self, cc):

        # Defines the side_effect helper.
        def _side_effect(url, **kw):
            raise requests.exceptions.ConnectionError("down")
        with patch("requests.get", side_effect=_side_effect):
            rates = cc.get_exchange_rates("USD")
        assert "EUR" in rates

    # Tests get currency info known.
    def test_get_currency_info_known(self, cc):
        assert cc.get_currency_info("USD") == "US Dollar"

    # Tests get currency info unknown.
    def test_get_currency_info_unknown(self, cc):
        assert cc.get_currency_info("ZZZ") == "Unknown Currency"

    # Tests get currency info lowercase.
    def test_get_currency_info_lowercase(self, cc):
        assert cc.get_currency_info("usd") == "US Dollar"

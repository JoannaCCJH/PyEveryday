"""Whitebox coverage for ``scripts/utilities/currency_converter.py``.

We patch ``requests.get`` so the SUT never touches the network and exercise
every branch:

* ``get_exchange_rates``: success returns rates dict; failure falls back.
* ``get_fallback_rates``: success path (fixer.io shape), failure path falling
  to offline rates, and the ``api_key`` branch.
* ``get_offline_rates``: shape only (constant data).
* ``convert``: same currency short-circuit; from-USD branch; to-USD branch;
  cross-currency branch; missing-currency branch (returns ``None``).
* ``get_currency_info``: known and unknown codes.
* ``list_supported_currencies``: returns list keys.
* ``get_historical_rate``: success and failure (network exception).
* ``calculate_percentage_change``: both inputs truthy and falsy.
* ``format_currency``: JPY/KRW (no decimals); USD (with symbol); unknown
  currency (uses code as prefix).
* ``convert_and_display``: success and failure branches.
* ``compare_multiple_currencies`` and ``save_conversion_history`` (incl. the
  branch where the JSON file does not yet exist).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from scripts.utilities.currency_converter import CurrencyConverter


@pytest.fixture
def cc():
    return CurrencyConverter()


def _resp(payload, status_code=200, raises=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = payload
    if raises is not None:
        r.raise_for_status.side_effect = raises
    else:
        r.raise_for_status.return_value = None
    return r


# ------------------- get_exchange_rates / fallback -------------------

class TestGetExchangeRates:
    def test_success(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   return_value=_resp({"rates": {"EUR": 0.9}})):
            assert cc.get_exchange_rates("USD") == {"EUR": 0.9}

    def test_failure_falls_back(self, cc):
        # The first call (real API) raises; fallback also raises -> offline rates.
        with patch("scripts.utilities.currency_converter.requests.get",
                   side_effect=RuntimeError("net down")):
            rates = cc.get_exchange_rates("USD")
        # Offline rates dict has EUR / GBP keys.
        assert "EUR" in rates and "GBP" in rates


class TestGetFallbackRates:
    def test_success_path(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   return_value=_resp({"success": True, "rates": {"EUR": 0.91}})):
            assert cc.get_fallback_rates("USD") == {"EUR": 0.91}

    def test_failure_returns_offline(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   side_effect=RuntimeError("net")):
            rates = cc.get_fallback_rates("USD")
        assert "EUR" in rates  # offline-rates branch

    def test_api_key_added(self, cc):
        cc.api_key = "deadbeef"
        with patch("scripts.utilities.currency_converter.requests.get",
                   return_value=_resp({"success": True, "rates": {}})) as g:
            cc.get_fallback_rates("USD")
        # Verify the access_key parameter was forwarded.
        args, kwargs = g.call_args
        assert kwargs["params"]["access_key"] == "deadbeef"


# ----------------------------- convert ----------------------------------

class TestConvert:
    def test_same_currency_short_circuits(self, cc):
        assert cc.convert(100, "USD", "USD") == 100

    def test_from_usd_branch(self, cc):
        with patch.object(CurrencyConverter, "get_exchange_rates",
                          return_value={"EUR": 0.9}):
            assert cc.convert(100, "USD", "EUR") == 90.0

    def test_to_usd_branch(self, cc):
        with patch.object(CurrencyConverter, "get_exchange_rates",
                          return_value={"EUR": 0.5}):
            assert cc.convert(100, "EUR", "USD") == 200.0

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


# --------------------------- info / listing -----------------------------

class TestInfoListing:
    def test_known_currency(self, cc):
        assert cc.get_currency_info("usd") == "US Dollar"

    def test_unknown_currency(self, cc):
        assert cc.get_currency_info("ZZZ") == "Unknown Currency"

    def test_list_supported(self, cc):
        with patch.object(CurrencyConverter, "get_exchange_rates",
                          return_value={"EUR": 0.9, "GBP": 0.7}):
            assert set(cc.list_supported_currencies()) == {"EUR", "GBP"}


# ------------------- historical / percentage / format -------------------

class TestHistorical:
    def test_success(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   return_value=_resp({"rates": {"EUR": 0.85}})):
            assert cc.get_historical_rate("2024-01-01", "USD", "EUR") == 0.85

    def test_failure_returns_none(self, cc):
        with patch("scripts.utilities.currency_converter.requests.get",
                   side_effect=RuntimeError("boom")):
            assert cc.get_historical_rate("2024-01-01", "USD", "EUR") is None


class TestPercentageChange:
    def test_normal(self, cc):
        assert cc.calculate_percentage_change(100, 110) == 10.0

    def test_falsy_returns_none(self, cc):
        assert cc.calculate_percentage_change(0, 110) is None
        assert cc.calculate_percentage_change(100, None) is None


class TestFormatCurrency:
    def test_usd_symbol(self, cc):
        assert cc.format_currency(1234.5, "USD") == "$1,234.50"

    def test_jpy_no_decimals(self, cc):
        assert cc.format_currency(1234.5, "JPY") == "¥1,234"

    def test_unknown_uses_code_prefix(self, cc):
        # Unknown codes fall through to ``symbol = currency_symbols.get(currency, currency)``
        assert cc.format_currency(10, "ZZZ").startswith("ZZZ")


# --------------------- convert_and_display / compare --------------------

class TestConvertAndDisplay:
    def test_success_returns_value(self, cc, capsys):
        with patch.object(CurrencyConverter, "convert", return_value=85.0):
            out = cc.convert_and_display(100, "USD", "EUR")
        assert out == 85.0
        text = capsys.readouterr().out
        assert "CURRENCY CONVERSION" in text

    def test_failure_returns_none(self, cc, capsys):
        with patch.object(CurrencyConverter, "convert", return_value=None):
            assert cc.convert_and_display(100, "USD", "ZZZ") is None
        assert "Conversion failed" in capsys.readouterr().out

    def test_compare_multiple(self, cc, capsys):
        with patch.object(CurrencyConverter, "convert",
                          side_effect=[85.0, 73.0, None]):
            cc.compare_multiple_currencies(100, "USD", ["EUR", "GBP", "ZZZ"])
        out = capsys.readouterr().out
        assert "EUR" in out and "GBP" in out


# -------------------- save_conversion_history ---------------------------

class TestSaveHistory:
    def test_creates_new_file(self, tmp_path, cc, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cc.save_conversion_history({"a": 1})
        data = json.loads((tmp_path / "conversion_history.json").read_text())
        assert data == [{"a": 1}]

    def test_appends_to_existing_file(self, tmp_path, cc, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "conversion_history.json").write_text(json.dumps([{"a": 1}]))
        cc.save_conversion_history({"b": 2})
        data = json.loads((tmp_path / "conversion_history.json").read_text())
        assert data == [{"a": 1}, {"b": 2}]

    def test_corrupt_existing_file_resets(self, tmp_path, cc, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "conversion_history.json").write_text("not-json")
        cc.save_conversion_history({"b": 2})
        data = json.loads((tmp_path / "conversion_history.json").read_text())
        assert data == [{"b": 2}]

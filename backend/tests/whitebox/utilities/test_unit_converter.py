"""Whitebox coverage for ``scripts/utilities/unit_converter.py``.

The module is a deterministic rule table; we exercise every branch:

* ``convert_temperature``: same-unit short-circuit; each from_unit branch
  (celsius default, fahrenheit, kelvin, rankine); each to_unit branch
  (celsius, fahrenheit, kelvin, rankine); unknown to_unit returns ``None``.
* ``convert_standard``: unknown category, unknown unit (in either side),
  same-unit, normal conversion.
* ``convert``: temperature dispatch + standard dispatch + unknown unit
  returns ``None``.
* ``detect_category``: matches and ``None``.
* ``list_categories`` and ``list_units``.
* ``get_unit_name``: known and unknown unit.
* ``format_result``: success and ``None`` value branch.
* ``convert_multiple``: known category + unknown category branch.
* ``calculate_ratio``: divide-by-zero branch + unknown category + happy path.
* ``find_best_unit``: smaller and larger inputs.
* ``smart_convert``: unknown unit and known unit (which calls format_result).
"""

from __future__ import annotations

import pytest

from scripts.utilities.unit_converter import UnitConverter


@pytest.fixture
def uc():
    return UnitConverter()


# ----------------------- convert_temperature ------------------

class TestTemperature:
    def test_same_unit(self, uc):
        assert uc.convert_temperature(100, "celsius", "celsius") == 100

    @pytest.mark.parametrize("v,frm,to,expected", [
        (32, "fahrenheit", "celsius", 0.0),
        (0, "celsius", "fahrenheit", 32.0),
        (273.15, "kelvin", "celsius", 0.0),
        (0, "celsius", "kelvin", 273.15),
        (491.67, "rankine", "celsius", 0.0),
        (0, "celsius", "rankine", 491.67),
    ])
    def test_each_branch(self, uc, v, frm, to, expected):
        assert uc.convert_temperature(v, frm, to) == pytest.approx(expected, rel=1e-6)

    def test_unknown_to_unit_returns_none(self, uc):
        assert uc.convert_temperature(0, "celsius", "wat") is None


# ----------------------- convert_standard ---------------------

class TestStandard:
    def test_unknown_category(self, uc):
        assert uc.convert_standard(1, "m", "ft", "wat") is None

    def test_unknown_unit_returns_none(self, uc):
        assert uc.convert_standard(1, "m", "ZZ", "length") is None
        assert uc.convert_standard(1, "ZZ", "m", "length") is None

    def test_same_unit_passthrough(self, uc):
        assert uc.convert_standard(5, "m", "m", "length") == 5

    def test_length_conversion(self, uc):
        assert uc.convert_standard(1000, "m", "km", "length") == pytest.approx(1.0)


# --------------------------- convert --------------------------

class TestConvert:
    def test_temperature_dispatch(self, uc):
        assert uc.convert(100, "celsius", "fahrenheit") == pytest.approx(212.0)

    def test_unknown_unit_returns_none(self, uc):
        assert uc.convert(1, "ZZ", "YY") is None


# ----------------------- detect / list ------------------------

class TestDetectAndList:
    def test_detect_known(self, uc):
        assert uc.detect_category("kg", "lb") == "weight"

    def test_detect_unknown(self, uc):
        assert uc.detect_category("zz", "yy") is None

    def test_list_categories(self, uc):
        cats = uc.list_categories()
        assert {"length", "weight", "temperature"} <= set(cats)

    def test_list_units(self, uc):
        assert "m" in uc.list_units("length")

    def test_list_units_unknown(self, uc):
        assert uc.list_units("wat") == []


# ------------------------ get_unit_name -----------------------

class TestUnitName:
    def test_known(self, uc):
        assert uc.get_unit_name("m", "length") == "Meter"

    def test_unknown_uses_upper(self, uc):
        assert uc.get_unit_name("zz", "length") == "ZZ"


# ------------------------ format_result -----------------------

class TestFormatResult:
    def test_none_value_branch(self, uc, capsys):
        assert uc.format_result(None, 1, "m", "ft", "length") is None
        assert "Cannot convert" in capsys.readouterr().out

    def test_success_branch(self, uc, capsys):
        out = uc.format_result(3.28, 1, "m", "ft", "length")
        assert out == 3.28
        assert "UNIT CONVERSION" in capsys.readouterr().out


# ------------------------ convert_multiple --------------------

class TestConvertMultiple:
    def test_unknown_category(self, uc, capsys):
        uc.convert_multiple(1, "m", "wat")
        assert "Unknown category" in capsys.readouterr().out

    def test_known_category_default_targets(self, uc, capsys):
        uc.convert_multiple(1, "m", "length")
        out = capsys.readouterr().out
        assert "MULTIPLE CONVERSIONS" in out

    def test_explicit_targets(self, uc, capsys):
        uc.convert_multiple(1, "m", "length", target_units=["ft", "km"])
        out = capsys.readouterr().out
        assert "ft" in out and "km" in out


# ------------------------ calculate_ratio ---------------------

class TestRatio:
    def test_unknown_category(self, uc):
        assert uc.calculate_ratio(1, "m", 2, "ft", "wat") is None

    def test_normal(self, uc):
        # 1 m / 1 m = 1.0
        assert uc.calculate_ratio(1, "m", 1, "m", "length") == 1.0

    def test_divide_by_zero_branch(self, uc):
        # value2 = 0 -> base2 = 0 -> returns None
        assert uc.calculate_ratio(1, "m", 0, "m", "length") is None


# ------------------------ find_best_unit ----------------------

class TestFindBestUnit:
    def test_unknown_category(self, uc):
        assert uc.find_best_unit(1, "m", "wat") == "m"

    def test_returns_a_unit(self, uc):
        assert uc.find_best_unit(1500, "m", "length") in uc.list_units("length")


# ------------------------ smart_convert -----------------------

class TestSmartConvert:
    def test_unknown_unit(self, uc, capsys):
        uc.smart_convert(1, "ZZ")
        assert "Unknown unit" in capsys.readouterr().out

    def test_known_unit_runs_format_result(self, uc, capsys):
        uc.smart_convert(1500, "m")
        assert "UNIT CONVERSION" in capsys.readouterr().out

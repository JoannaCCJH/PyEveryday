"""Whitebox coverage for ``scripts/utilities/unit_converter.py``.

Trimmed to one test per public surface: temperature conversions, standard
(length) conversions, unknown-category handling, dispatch, category detection,
result formatting, and ratio edge-case.
"""

from __future__ import annotations

import pytest

from scripts.utilities.unit_converter import UnitConverter


@pytest.fixture
def uc():
    return UnitConverter()


class TestTemperature:
    @pytest.mark.parametrize("v,frm,to,expected", [
        (32, "fahrenheit", "celsius", 0.0),
        (273.15, "kelvin", "celsius", 0.0),
    ])
    def test_each_branch(self, uc, v, frm, to, expected):
        assert uc.convert_temperature(v, frm, to) == pytest.approx(expected, rel=1e-6)


class TestStandard:
    def test_length_conversion(self, uc):
        assert uc.convert_standard(1000, "m", "km", "length") == pytest.approx(1.0)

    def test_unknown_category(self, uc):
        assert uc.convert_standard(1, "m", "ft", "wat") is None


class TestConvert:
    def test_temperature_dispatch(self, uc):
        assert uc.convert(100, "celsius", "fahrenheit") == pytest.approx(212.0)


class TestDetectCategory:
    def test_detect_known(self, uc):
        assert uc.detect_category("kg", "lb") == "weight"


class TestFormatResult:
    def test_success_branch(self, uc, capsys):
        out = uc.format_result(3.28, 1, "m", "ft", "length")
        assert out == 3.28
        assert "UNIT CONVERSION" in capsys.readouterr().out


class TestRatio:
    def test_divide_by_zero_branch(self, uc):
        assert uc.calculate_ratio(1, "m", 0, "m", "length") is None

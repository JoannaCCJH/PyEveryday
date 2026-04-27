import math

import pytest

from scripts.utilities.unit_converter import UnitConverter

pytestmark = pytest.mark.blackbox


# Provides the uc fixture.
@pytest.fixture
def uc():
    return UnitConverter()


class TestConvertStandardEP:
    # Tests known category known units returns conversion.
    def test_known_category_known_units_returns_conversion(self, uc):
        assert uc.convert_standard(1000, "m", "km", "length") == pytest.approx(1.0)

    # Tests unknown category returns none.
    def test_unknown_category_returns_none(self, uc):
        assert uc.convert_standard(1, "m", "km", "fake_category") is None

    # Tests unknown unit returns none.
    def test_unknown_unit_returns_none(self, uc):
        assert uc.convert_standard(1, "banana", "km", "length") is None

    # Tests same unit returns input value.
    def test_same_unit_returns_input_value(self, uc):
        assert uc.convert_standard(42, "kg", "kg", "weight") == 42


class TestConvertTemperatureEP:
    # Tests standard conversions.
    @pytest.mark.parametrize("value, f, t, expected", [
        (100, "celsius",    "fahrenheit", 212),
        (32,  "fahrenheit", "celsius",    0),
        (0,   "celsius",    "kelvin",     273.15),
        (273.15, "kelvin",  "celsius",    0),
    ])
    def test_standard_conversions(self, uc, value, f, t, expected):
        assert uc.convert_temperature(value, f, t) == pytest.approx(expected, abs=1e-6)

    # Tests same unit returns input.
    def test_same_unit_returns_input(self, uc):
        assert uc.convert_temperature(25, "celsius", "celsius") == 25


class TestConvertDispatchEP:
    # Tests auto detect length.
    def test_auto_detect_length(self, uc):
        assert uc.convert(1, "km", "m") == pytest.approx(1000.0)

    # Tests auto detect temperature.
    def test_auto_detect_temperature(self, uc):
        assert uc.convert(0, "celsius", "kelvin") == pytest.approx(273.15)

    # Tests cross category units returns none.
    def test_cross_category_units_returns_none(self, uc):
        assert uc.convert(1, "kg", "m") is None


class TestBoundaries:
    # Tests absolute zero celsius to kelvin.
    def test_absolute_zero_celsius_to_kelvin(self, uc):
        assert uc.convert(-273.15, "celsius", "kelvin") == pytest.approx(0, abs=1e-9)

    # Tests zero length conversion.
    def test_zero_length_conversion(self, uc):
        assert uc.convert(0, "m", "km") == 0

    # Tests negative length value still converts.
    def test_negative_length_value_still_converts(self, uc):
        assert uc.convert(-1000, "m", "km") == pytest.approx(-1.0)

    # Tests very small value.
    def test_very_small_value(self, uc):
        assert uc.convert(0.000001, "km", "mm") == pytest.approx(1.0, rel=1e-6)

    # Tests very large value.
    def test_very_large_value(self, uc):
        assert uc.convert(1, "pb", "b") == pytest.approx(1125899906842624.0)


class TestErrorGuessing:
    # Tests case insensitive temperature units.
    def test_case_insensitive_temperature_units(self, uc):
        assert uc.convert_temperature(0, "CELSIUS", "FAHRENHEIT") == pytest.approx(32)

    # Tests calculate ratio unknown unit should return none.
    def test_calculate_ratio_unknown_unit_should_return_none(self, uc):
        result = uc.calculate_ratio(10, "bogus_unit", 5, "m", "length")
        assert result is None

    # Tests calculate ratio zero divisor returns none.
    def test_calculate_ratio_zero_divisor_returns_none(self, uc):
        assert uc.calculate_ratio(5, "m", 0, "m", "length") is None

    # Tests list units unknown category returns empty list.
    def test_list_units_unknown_category_returns_empty_list(self, uc):
        assert uc.list_units("nonsense") == []

    # Tests detect category cross category returns none.
    def test_detect_category_cross_category_returns_none(self, uc):
        assert uc.detect_category("kg", "m") is None

    # Tests convert with non numeric value raises.
    def test_convert_with_non_numeric_value_raises(self, uc):
        with pytest.raises(TypeError):
            uc.convert("not a number", "m", "km")

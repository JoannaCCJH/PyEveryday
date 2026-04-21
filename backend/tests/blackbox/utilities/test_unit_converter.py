"""
Black-box tests for scripts.utilities.unit_converter.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
"""
import math

import pytest

from scripts.utilities.unit_converter import UnitConverter

pytestmark = pytest.mark.blackbox


@pytest.fixture
def uc():
    return UnitConverter()


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestConvertStandardEP:
    """
    EP partitions for convert_standard:
      category:  known  vs  unknown
      units:     both in category  vs  either missing
      from/to:   same  vs  different
    """

    def test_known_category_known_units_returns_conversion(self, uc):
        # EP: canonical valid class - 1000 m -> 1 km.
        assert uc.convert_standard(1000, "m", "km", "length") == pytest.approx(1.0)

    def test_unknown_category_returns_none(self, uc):
        # EP: unknown category -> None.
        assert uc.convert_standard(1, "m", "km", "fake_category") is None

    def test_unknown_from_unit_returns_none(self, uc):
        # EP: valid category but unknown from_unit -> None.
        assert uc.convert_standard(1, "banana", "km", "length") is None

    def test_unknown_to_unit_returns_none(self, uc):
        # EP: valid category but unknown to_unit -> None.
        assert uc.convert_standard(1, "m", "banana", "length") is None

    def test_same_unit_returns_input_value(self, uc):
        # EP: from==to is identity class.
        assert uc.convert_standard(42, "kg", "kg", "weight") == 42


class TestConvertTemperatureEP:
    """EP classes for temperature: celsius/fahrenheit/kelvin/rankine pairs."""

    @pytest.mark.parametrize("value, f, t, expected", [
        (0,   "celsius",    "fahrenheit", 32),
        (100, "celsius",    "fahrenheit", 212),
        (32,  "fahrenheit", "celsius",    0),
        (0,   "celsius",    "kelvin",     273.15),
        (273.15, "kelvin",  "celsius",    0),
    ])
    def test_standard_conversions(self, uc, value, f, t, expected):
        # EP: one representative per pair-of-units partition.
        assert uc.convert_temperature(value, f, t) == pytest.approx(expected, abs=1e-6)

    def test_same_unit_returns_input(self, uc):
        # EP: from==to identity class.
        assert uc.convert_temperature(25, "celsius", "celsius") == 25


class TestConvertDispatchEP:
    """EP for the top-level convert(): category=None triggers auto-detect."""

    def test_auto_detect_length(self, uc):
        # EP: both units belong to length -> category inferred.
        assert uc.convert(1, "km", "m") == pytest.approx(1000.0)

    def test_auto_detect_temperature(self, uc):
        # EP: auto-detect routes through convert_temperature.
        assert uc.convert(0, "celsius", "kelvin") == pytest.approx(273.15)

    def test_cross_category_units_returns_none(self, uc):
        # EP: kg -> m is invalid class -> None.
        assert uc.convert(1, "kg", "m") is None


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestBoundaries:
    def test_absolute_zero_celsius_to_kelvin(self, uc):
        # BA: physical lower bound of temperature.
        assert uc.convert(-273.15, "celsius", "kelvin") == pytest.approx(0, abs=1e-9)

    def test_absolute_zero_fahrenheit(self, uc):
        # BA: -459.67 F == 0 K.
        assert uc.convert(-459.67, "fahrenheit", "kelvin") == pytest.approx(0, abs=1e-4)

    def test_zero_length_conversion(self, uc):
        # BA: 0 is a natural boundary value for multiplicative conversions.
        assert uc.convert(0, "m", "km") == 0

    def test_negative_length_value_still_converts(self, uc):
        # BA: negative-side probe - convert is purely multiplicative.
        assert uc.convert(-1000, "m", "km") == pytest.approx(-1.0)

    def test_very_small_value(self, uc):
        # BA: below-1 region tests precision path. 0.000001 km == 1 mm.
        assert uc.convert(0.000001, "km", "mm") == pytest.approx(1.0, rel=1e-6)

    def test_very_large_value(self, uc):
        # BA: upper-side probe - petabyte conversion.
        assert uc.convert(1, "pb", "b") == pytest.approx(1125899906842624.0)


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_case_insensitive_temperature_units(self, uc):
        # EG: convert_temperature lowercases from_unit / to_unit internally.
        assert uc.convert_temperature(0, "CELSIUS", "FAHRENHEIT") == pytest.approx(32)

    def test_calculate_ratio_unknown_unit_should_return_none(self, uc):
        # EG / FAULT-HUNTING: calculate_ratio uses .get(u, 0) so an unknown
        # unit silently becomes 0 and returns 0.0 instead of None. Intended
        # contract: unknown unit -> None. See FINDINGS.md FAULT-003.
        result = uc.calculate_ratio(10, "bogus_unit", 5, "m", "length")
        assert result is None

    def test_calculate_ratio_happy_path(self, uc):
        # EG contrast: known-units ratio should compute as expected.
        # 1000 m vs 1 km -> both equal 1000 m in base, ratio = 1.0.
        assert uc.calculate_ratio(1000, "m", 1, "km", "length") == pytest.approx(1.0)

    def test_calculate_ratio_zero_divisor_returns_none(self, uc):
        # EG: 0-denominator case - must not raise ZeroDivisionError.
        assert uc.calculate_ratio(5, "m", 0, "m", "length") is None

    def test_list_units_unknown_category_returns_empty_list(self, uc):
        # EG: unknown category -> empty list (not None).
        assert uc.list_units("nonsense") == []

    def test_detect_category_cross_category_returns_none(self, uc):
        # EG: "kg" and "m" have no shared category.
        assert uc.detect_category("kg", "m") is None

    def test_detect_category_returns_first_match(self, uc):
        # EG: documents first-match behavior. Each unit currently appears in
        # only one category, so this just asserts the contract is deterministic.
        assert uc.detect_category("kg", "g") == "weight"

    def test_convert_with_non_numeric_value_raises(self, uc):
        # EG: non-numeric value propagates the TypeError from multiplication.
        with pytest.raises(TypeError):
            uc.convert("not a number", "m", "km")

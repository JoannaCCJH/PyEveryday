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


class TestGetUnitNameEP:
    def test_known_unit_returns_full_name(self, uc):
        assert uc.get_unit_name("m", "length") == "Meter"

    def test_unknown_unit_falls_back_to_uppercased_code(self, uc):
        assert uc.get_unit_name("zzz", "length") == "ZZZ"


class TestConvertMultipleEG:
    def test_known_category_outputs_target_units(self, uc, capsys):
        uc.convert_multiple(1000, "m", "length", target_units=["km", "cm"])
        out = capsys.readouterr().out
        assert "km" in out and "cm" in out
        assert "Unknown category" not in out

    def test_unknown_category_prints_error_and_returns(self, uc, capsys):
        uc.convert_multiple(1000, "m", "fake_cat")
        assert "Unknown category" in capsys.readouterr().out

    def test_skips_self_conversion_in_loop(self, uc, capsys):
        uc.convert_multiple(1000, "m", "length", target_units=["m", "km"])
        lines = capsys.readouterr().out.splitlines()
        assert [l for l in lines if l.lstrip().startswith("m:")] == []

    def test_invalid_target_unit_skipped_in_output(self, uc, capsys):
        uc.convert_multiple(1000, "m", "length", target_units=["km", "bogus"])
        lines = capsys.readouterr().out.splitlines()
        assert [l for l in lines if l.lstrip().startswith("bogus:")] == []


class TestCalculateRatioBranches:
    def test_known_category_known_units_returns_ratio(self, uc):
        assert uc.calculate_ratio(1000, "m", 1, "km", "length") == pytest.approx(1.0)

    def test_unknown_category_returns_none(self, uc):
        assert uc.calculate_ratio(1, "m", 2, "m", "fake_cat") is None


class TestFindBestUnit:
    def test_known_category_picks_unit_in_one_to_hundred_range(self, uc):
        assert uc.find_best_unit(1000, "mm", "length") == "m"

    def test_unknown_category_returns_input_unit(self, uc):
        assert uc.find_best_unit(1, "anything", "fake_cat") == "anything"


class TestSmartConvertBranches:
    def test_known_unit_dispatches_without_unknown_message(self, uc, capsys):
        uc.smart_convert(1000, "mm")
        out = capsys.readouterr().out
        assert "Unknown unit" not in out
        assert "UNIT CONVERSION" in out

    def test_unknown_unit_prints_unknown_message(self, uc, capsys):
        uc.smart_convert(1, "fakeunit")
        assert "Unknown unit" in capsys.readouterr().out

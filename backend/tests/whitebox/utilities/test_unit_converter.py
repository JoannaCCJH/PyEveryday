from __future__ import annotations

import pytest

from scripts.utilities.unit_converter import UnitConverter


# Provides the uc fixture.
@pytest.fixture
def uc():
    return UnitConverter()


class TestTemperature:
    # Tests conversion branches.
    @pytest.mark.parametrize("v,frm,to,expected", [
        (0, "celsius", "fahrenheit", 32.0),
        (491.67, "rankine", "celsius", 0.0),
    ])
    def test_conversion_branches(self, uc, v, frm, to, expected):
        assert uc.convert_temperature(v, frm, to) == pytest.approx(expected, rel=1e-4, abs=1e-4)


class TestStandard:
    # Tests known unit.
    def test_known_unit(self, uc):
        assert uc.convert_standard(1000, "m", "km", "length") == pytest.approx(1.0)

    # Tests unknown unit returns none.
    def test_unknown_unit_returns_none(self, uc):
        assert uc.convert_standard(1, "flarg", "m", "length") is None


class TestConvert:
    # Tests auto detect and unknown.
    def test_auto_detect_and_unknown(self, uc):
        assert uc.convert(1, "m", "km") == pytest.approx(0.001)
        assert uc.convert(1, "flarg", "quuz") is None

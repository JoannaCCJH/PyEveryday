from __future__ import annotations

import datetime as _dt

import pytest

from scripts.utilities.age_calculator import AgeCalculator


# Provides the ac fixture.
@pytest.fixture
def ac():
    return AgeCalculator()


class TestParseDate:
    # Tests supported and invalid.
    def test_supported_and_invalid(self, ac):
        assert ac.parse_date("1995-06-15").year == 1995
        with pytest.raises(ValueError):
            ac.parse_date("nope")


class TestCalculateAge:
    # Tests birth in future raises.
    def test_birth_in_future_raises(self, ac):
        future = _dt.date.today() + _dt.timedelta(days=10)
        with pytest.raises(ValueError):
            ac.calculate_age(future)

    # Tests birthday already passed branch.
    def test_birthday_already_passed_branch(self, ac):
        out = ac.calculate_age("1995-01-01", current_date="2025-06-15")
        assert out["next_birthday"] == _dt.date(2026, 1, 1)


class TestDisplays:
    # Tests display age info no exception.
    def test_display_age_info_no_exception(self, ac, capsys):
        ac.display_age_info("1995-06-15", current_date="2025-06-15")
        text = capsys.readouterr().out
        assert "AGE CALCULATOR RESULTS" in text

"""Whitebox coverage for ``scripts/utilities/age_calculator.py``.

Trimmed to the essential branches.  Keeps
``TestDisplays::test_display_age_info_no_exception`` which currently FAILS —
it documents a real SUT bug (key mismatch: ``calculate_age`` returns
``days_to_next_birthday`` but ``display_age_info`` reads ``days_to_birthday``).
Do NOT remove that test.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from scripts.utilities.age_calculator import AgeCalculator


@pytest.fixture
def ac():
    return AgeCalculator()


class TestParseDate:
    @pytest.mark.parametrize("text", [
        "1995-06-15",
        "June 15, 1995",
    ])
    def test_supported_formats(self, ac, text):
        d = ac.parse_date(text)
        assert d.year == 1995

    def test_invalid_raises(self, ac):
        with pytest.raises(ValueError):
            ac.parse_date("nope")


class TestCalculateAge:
    def test_birth_in_future_raises(self, ac):
        future = _dt.date.today() + _dt.timedelta(days=10)
        with pytest.raises(ValueError):
            ac.calculate_age(future)

    def test_birthday_already_passed_branch(self, ac):
        out = ac.calculate_age("1995-01-01", current_date="2025-06-15")
        assert out["next_birthday"] == _dt.date(2026, 1, 1)


class TestZodiac:
    def test_capricorn_wrap_around(self, ac):
        assert ac.calculate_zodiac_sign("1995-01-10")["sign"] == "Capricorn"


class TestLifeEvents:
    def test_passed_and_upcoming_branches(self, ac):
        events = ac.calculate_life_events("1995-01-01")
        assert any(e["status"] == "passed" for e in events)
        assert any(e["status"] == "upcoming" for e in events)


class TestDisplays:
    def test_display_age_info_no_exception(self, ac, capsys):
        """Currently FAILS — documents a real SUT bug (KeyError 'days_to_birthday')."""
        ac.display_age_info("1995-06-15", current_date="2025-06-15")
        text = capsys.readouterr().out
        assert "AGE CALCULATOR RESULTS" in text

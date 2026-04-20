"""Whitebox coverage for ``scripts/utilities/age_calculator.py``.

Branches exercised:

* ``parse_date``: every supported format + invalid (raises ``ValueError``).
* ``calculate_age``: birth-as-string, current-as-string, default current,
  birth in the future raises, the "next birthday already passed" branch,
  the "current_date.day < birth_date.day" branch.
* ``get_detailed_age``: ``days < 0`` and ``months < 0`` rollover branches.
* ``calculate_zodiac_sign``: every wrap-around (e.g. Capricorn) and a few
  representative signs.
* ``calculate_chinese_zodiac``: arithmetic round trip.
* ``calculate_life_events``: passed and upcoming branches.
* ``compare_ages``: each name is older.
* ``display_*``: smoke (only ensure no exception, output mentioned).
"""

from __future__ import annotations

import datetime as _dt
from unittest.mock import patch

import pytest

from scripts.utilities.age_calculator import AgeCalculator


@pytest.fixture
def ac():
    return AgeCalculator()


# --------------------------- parse_date -----------------------

class TestParseDate:
    @pytest.mark.parametrize("text", [
        "1995-06-15",
        "15/06/1995",
        "06/15/1995",
        "15-06-1995",
        "1995/06/15",
        "15.06.1995",
        "June 15, 1995",
        "15 June 1995",
    ])
    def test_supported_formats(self, ac, text):
        d = ac.parse_date(text)
        assert d.year == 1995

    def test_invalid_raises(self, ac):
        with pytest.raises(ValueError):
            ac.parse_date("nope")


# --------------------------- calculate_age --------------------

class TestCalculateAge:
    def test_birth_in_future_raises(self, ac):
        future = _dt.date.today() + _dt.timedelta(days=10)
        with pytest.raises(ValueError):
            ac.calculate_age(future)

    def test_default_current_uses_today(self, ac):
        born = _dt.date(2000, 1, 1)
        out = ac.calculate_age(born)
        assert out["years"] >= 25  # any future date will keep this true

    def test_string_inputs_are_parsed(self, ac):
        out = ac.calculate_age("1995-06-15", current_date="2025-06-15")
        assert out["years"] == 30
        assert out["days_to_next_birthday"] == 0  # birthday today branch

    def test_birthday_not_yet_reached_branch(self, ac):
        out = ac.calculate_age("1995-06-15", current_date="2025-04-01")
        assert out["years"] == 29

    def test_birthday_already_passed_branch(self, ac):
        out = ac.calculate_age("1995-01-01", current_date="2025-06-15")
        # Next birthday is in the next calendar year iff this year's already
        # passed:
        assert out["next_birthday"] == _dt.date(2026, 1, 1)


# ------------------------- detailed age -----------------------

class TestDetailedAge:
    def test_negative_days_rollover(self, ac):
        out = ac.get_detailed_age("1995-01-15", current_date="2025-02-10")
        assert out["years"] == 30 and out["months"] == 0 and out["days"] >= 25

    def test_negative_months_rollover(self, ac):
        out = ac.get_detailed_age("1995-06-15", current_date="2025-04-10")
        assert out["years"] == 29 and out["months"] >= 9


# ----------------------------- zodiac -------------------------

class TestZodiac:
    @pytest.mark.parametrize("date,sign", [
        ("1995-06-15", "Gemini"),
        ("1995-12-25", "Capricorn"),
        ("1995-01-10", "Capricorn"),  # wrap-around branch
        ("1995-03-21", "Aries"),
        ("1995-11-22", "Sagittarius"),
    ])
    def test_signs(self, ac, date, sign):
        assert ac.calculate_zodiac_sign(date)["sign"] == sign


class TestChineseZodiac:
    def test_returns_animal_and_element(self, ac):
        out = ac.calculate_chinese_zodiac("2000-01-01")
        assert "animal" in out and "element" in out and out["year"] == 2000


# ------------------------ life events -------------------------

class TestLifeEvents:
    def test_passed_and_upcoming_branches(self, ac):
        events = ac.calculate_life_events("1995-01-01")
        assert any(e["status"] == "passed" for e in events)
        assert any(e["status"] == "upcoming" for e in events)


# ------------------------- compare ----------------------------

class TestCompareAges:
    def test_first_person_older(self, ac, capsys):
        ac.compare_ages("1990-01-01", "2000-01-01", "Older", "Younger")
        out = capsys.readouterr().out
        assert "Older person: Older" in out

    def test_second_person_older(self, ac, capsys):
        ac.compare_ages("2000-01-01", "1990-01-01", "Younger", "Older")
        out = capsys.readouterr().out
        assert "Older person: Older" in out


# -------------------------- display ---------------------------

class TestDisplays:
    def test_display_age_info_no_exception(self, ac, capsys):
        ac.display_age_info("1995-06-15", current_date="2025-06-15")
        text = capsys.readouterr().out
        assert "AGE CALCULATOR RESULTS" in text

    def test_display_life_events_no_exception(self, ac, capsys):
        ac.display_life_events("1995-06-15")
        assert "LIFE MILESTONES" in capsys.readouterr().out

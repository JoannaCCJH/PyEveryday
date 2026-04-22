"""
Black-box tests for scripts.utilities.age_calculator.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
"""
import datetime

import pytest

from scripts.utilities.age_calculator import AgeCalculator

pytestmark = pytest.mark.blackbox


@pytest.fixture
def ac():
    return AgeCalculator()


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestParseDateEP:
    """EP partitions for parse_date: each documented format class + invalid class."""

    @pytest.mark.parametrize("s, expected", [
        ("2000-06-15",   datetime.date(2000, 6, 15)),  # %Y-%m-%d
        ("15/06/2000",   datetime.date(2000, 6, 15)),  # %d/%m/%Y (first match)
        ("15-06-2000",   datetime.date(2000, 6, 15)),  # %d-%m-%Y
        ("2000/06/15",   datetime.date(2000, 6, 15)),  # %Y/%m/%d
        ("15.06.2000",   datetime.date(2000, 6, 15)),  # %d.%m.%Y
        ("June 15, 2000", datetime.date(2000, 6, 15)), # %B %d, %Y
        ("15 June 2000", datetime.date(2000, 6, 15)),  # %d %B %Y
    ])
    def test_accepted_formats(self, ac, s, expected):
        # EP: one representative per accepted format class.
        assert ac.parse_date(s) == expected

    def test_unparseable_string_raises(self, ac):
        # EP: invalid class -> ValueError.
        with pytest.raises(ValueError):
            ac.parse_date("not-a-date-at-all")


class TestCalculateAgeEP:
    def test_valid_birth_past_returns_positive_age(self, ac):
        # EP: valid class (birth < current).
        result = ac.calculate_age("2000-01-01", "2020-01-01")
        assert result["years"] == 20

    def test_same_day_zero_age(self, ac):
        # EP: birth == current -> age 0.
        result = ac.calculate_age("2020-06-15", "2020-06-15")
        assert result["years"] == 0
        assert result["days"] == 0

    def test_future_birth_date_raises(self, ac):
        # EP: invalid class -> ValueError.
        with pytest.raises(ValueError):
            ac.calculate_age("2099-01-01", "2020-01-01")


class TestZodiacEP:
    """
    EP: each zodiac sign is an equivalence class. Test one representative
    day for each of the 12 western signs (mid-range, not boundary days
    which are covered in BA).
    """
    @pytest.mark.parametrize("date_str, expected_sign", [
        ("2000-02-05", "Aquarius"),
        ("2000-03-05", "Pisces"),
        ("2000-04-05", "Aries"),
        ("2000-05-05", "Taurus"),
        ("2000-06-05", "Gemini"),
        ("2000-07-05", "Cancer"),
        ("2000-08-05", "Leo"),
        ("2000-09-05", "Virgo"),
        ("2000-10-05", "Libra"),
        ("2000-11-05", "Scorpio"),
        ("2000-12-05", "Sagittarius"),
        ("2000-01-05", "Capricorn"),
    ])
    def test_zodiac_sign_per_sign(self, ac, date_str, expected_sign):
        assert ac.calculate_zodiac_sign(date_str)["sign"] == expected_sign


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestCalculateAgeBA:
    def test_age_on_day_before_birthday(self, ac):
        # BA: one day before birthday -> age not yet incremented.
        result = ac.calculate_age("2000-06-15", "2020-06-14")
        assert result["years"] == 19

    def test_age_on_birthday(self, ac):
        # BA: exact birthday anniversary -> age incremented.
        result = ac.calculate_age("2000-06-15", "2020-06-15")
        assert result["years"] == 20

    def test_age_on_day_after_birthday(self, ac):
        # BA: one day after birthday -> age still the same (no double-count).
        result = ac.calculate_age("2000-06-15", "2020-06-16")
        assert result["years"] == 20

    def test_birth_one_day_before_current_has_one_day_total(self, ac):
        # BA: minimum positive difference.
        result = ac.calculate_age("2020-06-14", "2020-06-15")
        assert result["days"] == 1
        assert result["years"] == 0


class TestZodiacBoundariesBA:
    """
    BA: zodiac sign boundaries. Each boundary day is the most fault-prone
    input. Example: Gemini spans May 21 - Jun 20. Test May 20 (Taurus) and
    May 21 (Gemini), Jun 20 (Gemini) and Jun 21 (Cancer).
    """

    @pytest.mark.parametrize("date_str, expected_sign", [
        # Aries / Taurus boundary (Apr 19 / Apr 20)
        ("2000-04-19", "Aries"),
        ("2000-04-20", "Taurus"),
        # Taurus / Gemini boundary (May 20 / May 21)
        ("2000-05-20", "Taurus"),
        ("2000-05-21", "Gemini"),
        # Gemini / Cancer boundary (Jun 20 / Jun 21)
        ("2000-06-20", "Gemini"),
        ("2000-06-21", "Cancer"),
        # Sagittarius / Capricorn boundary (Dec 21 / Dec 22)
        ("2000-12-21", "Sagittarius"),
        ("2000-12-22", "Capricorn"),
        # Capricorn / Aquarius boundary (Jan 19 / Jan 20)
        ("2000-01-19", "Capricorn"),
        ("2000-01-20", "Aquarius"),
    ])
    def test_zodiac_boundary_days(self, ac, date_str, expected_sign):
        assert ac.calculate_zodiac_sign(date_str)["sign"] == expected_sign


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_leap_day_birth_in_non_leap_current_year_does_not_crash(self, ac):
        # EG / FAULT-HUNTING: Feb 29 birthday + non-leap current year.
        # Intended contract: calculate_age returns a full dict for any valid
        # birth+current pair. Expected to FAIL until leap-day edge is handled.
        # See FINDINGS.md FAULT-004.
        result = ac.calculate_age("2000-02-29", "2021-03-01")
        assert result["years"] == 21

    def test_ambiguous_date_dd_mm_wins_over_mm_dd(self, ac):
        # EG: the DD/MM/YYYY format is tried before MM/DD/YYYY, so
        # "03/04/2020" resolves to 3 April 2020, not 4 March 2020. This test
        # documents the first-match contract.
        assert ac.parse_date("03/04/2020") == datetime.date(2020, 4, 3)

    def test_chinese_zodiac_returns_animal_and_element(self, ac):
        # EG: contract check - dict has both keys.
        z = ac.calculate_chinese_zodiac("2000-01-01")
        assert "animal" in z and "element" in z

    def test_calculate_zodiac_never_returns_unknown_for_valid_date(self, ac):
        # EG / FAULT-HUNTING: the zodiac function has an "Unknown" fallback
        # that should never fire for a valid date. Iterate every day of a
        # year and ensure no "Unknown" surfaces.
        start = datetime.date(2000, 1, 1)
        for offset in range(366):  # 2000 is a leap year
            d = start + datetime.timedelta(days=offset)
            sign = ac.calculate_zodiac_sign(d)["sign"]
            assert sign != "Unknown", f"zodiac returned 'Unknown' for {d}"

    def test_parse_date_empty_string_raises(self, ac):
        # EG: empty input -> ValueError.
        with pytest.raises(ValueError):
            ac.parse_date("")

    def test_parse_date_whitespace_only_raises(self, ac):
        # EG: whitespace-only input -> ValueError.
        with pytest.raises(ValueError):
            ac.parse_date("   ")

    def test_life_events_returns_eight_milestones(self, ac):
        # EG: contract - 8 milestone ages.
        events = ac.calculate_life_events("2000-01-01")
        assert len(events) == 8
        ages = [e["age"] for e in events]
        assert ages == [18, 21, 25, 30, 40, 50, 65, 100]

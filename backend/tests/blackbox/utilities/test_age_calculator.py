import datetime

import pytest

from scripts.utilities.age_calculator import AgeCalculator

pytestmark = pytest.mark.blackbox


# Provides the ac fixture.
@pytest.fixture
def ac():
    return AgeCalculator()


class TestParseDateEP:
    # Tests accepted formats.
    @pytest.mark.parametrize("s, expected", [
        ("2000-06-15",   datetime.date(2000, 6, 15)),
        ("15/06/2000",   datetime.date(2000, 6, 15)),
        ("15-06-2000",   datetime.date(2000, 6, 15)),
        ("2000/06/15",   datetime.date(2000, 6, 15)),
        ("15.06.2000",   datetime.date(2000, 6, 15)),
        ("June 15, 2000", datetime.date(2000, 6, 15)),
        ("15 June 2000", datetime.date(2000, 6, 15)),
    ])
    def test_accepted_formats(self, ac, s, expected):
        assert ac.parse_date(s) == expected

    # Tests unparseable string raises.
    def test_unparseable_string_raises(self, ac):
        with pytest.raises(ValueError):
            ac.parse_date("not-a-date-at-all")


class TestCalculateAgeEP:
    # Tests valid birth past returns positive age.
    def test_valid_birth_past_returns_positive_age(self, ac):
        result = ac.calculate_age("2000-01-01", "2020-01-01")
        assert result["years"] == 20

    # Tests same day zero age.
    def test_same_day_zero_age(self, ac):
        result = ac.calculate_age("2020-06-15", "2020-06-15")
        assert result["years"] == 0
        assert result["days"] == 0

    # Tests future birth date raises.
    def test_future_birth_date_raises(self, ac):
        with pytest.raises(ValueError):
            ac.calculate_age("2099-01-01", "2020-01-01")


class TestZodiacEP:
    # Tests zodiac sign per sign.
    @pytest.mark.parametrize("date_str, expected_sign", [
        ("2000-06-05", "Gemini"),
        ("2000-10-05", "Libra"),
        ("2000-01-05", "Capricorn"),
    ])
    def test_zodiac_sign_per_sign(self, ac, date_str, expected_sign):
        assert ac.calculate_zodiac_sign(date_str)["sign"] == expected_sign


class TestCalculateAgeBA:
    # Tests age on day before birthday.
    def test_age_on_day_before_birthday(self, ac):
        result = ac.calculate_age("2000-06-15", "2020-06-14")
        assert result["years"] == 19

    # Tests age on birthday.
    def test_age_on_birthday(self, ac):
        result = ac.calculate_age("2000-06-15", "2020-06-15")
        assert result["years"] == 20

    # Tests age on day after birthday.
    def test_age_on_day_after_birthday(self, ac):
        result = ac.calculate_age("2000-06-15", "2020-06-16")
        assert result["years"] == 20

    # Tests birth one day before current has one day total.
    def test_birth_one_day_before_current_has_one_day_total(self, ac):
        result = ac.calculate_age("2020-06-14", "2020-06-15")
        assert result["days"] == 1
        assert result["years"] == 0


class TestZodiacBoundariesBA:
    # Tests zodiac boundary days.
    @pytest.mark.parametrize("date_str, expected_sign", [
        ("2000-04-19", "Aries"),
        ("2000-04-20", "Taurus"),
        ("2000-05-20", "Taurus"),
        ("2000-05-21", "Gemini"),
        ("2000-06-20", "Gemini"),
        ("2000-06-21", "Cancer"),
        ("2000-12-21", "Sagittarius"),
        ("2000-12-22", "Capricorn"),
        ("2000-01-19", "Capricorn"),
        ("2000-01-20", "Aquarius"),
    ])
    def test_zodiac_boundary_days(self, ac, date_str, expected_sign):
        assert ac.calculate_zodiac_sign(date_str)["sign"] == expected_sign


class TestErrorGuessing:
    # Tests leap day birth in non leap current year does not crash.
    def test_leap_day_birth_in_non_leap_current_year_does_not_crash(self, ac):
        result = ac.calculate_age("2000-02-29", "2021-03-01")
        assert result["years"] == 21

    # Tests calculate zodiac never returns unknown for valid date.
    def test_calculate_zodiac_never_returns_unknown_for_valid_date(self, ac):
        start = datetime.date(2000, 1, 1)
        for offset in range(366):
            d = start + datetime.timedelta(days=offset)
            sign = ac.calculate_zodiac_sign(d)["sign"]
            assert sign != "Unknown", f"zodiac returned 'Unknown' for {d}"

    # Tests parse date empty string raises.
    def test_parse_date_empty_string_raises(self, ac):
        with pytest.raises(ValueError):
            ac.parse_date("")


class TestCalculateAgeBoundariesBA:
    def test_birthday_today_has_zero_days_to_next_birthday(self, ac):
        result = ac.calculate_age("2000-06-15", "2020-06-15")
        assert result['days_to_next_birthday'] == 0

    def test_total_months_at_same_day_of_month_no_decrement(self, ac):
        result = ac.calculate_age("2000-01-15", "2020-01-15")
        assert result['months'] == 240


class TestGetDetailedAgeBA:
    def test_uses_explicit_current_date_not_today(self, ac):
        result = ac.get_detailed_age("2000-06-15", "2020-06-15")
        assert result == {'years': 20, 'months': 0, 'days': 0}

    def test_same_day_of_month_no_borrow_into_months(self, ac):
        result = ac.get_detailed_age("2000-06-15", "2001-06-15")
        assert result == {'years': 1, 'months': 0, 'days': 0}

    def test_same_month_no_borrow_into_years(self, ac):
        result = ac.get_detailed_age("2000-06-15", "2010-06-15")
        assert result['years'] == 10
        assert result['months'] == 0


class TestLifeEventsBA:
    def test_milestone_falling_exactly_today_counts_as_passed(self, ac):
        today = datetime.date.today()
        try:
            birth = datetime.date(today.year - 18, today.month, today.day)
        except ValueError:
            birth = datetime.date(today.year - 18, today.month, today.day - 1)
        events = ac.calculate_life_events(birth)
        age_18 = next(e for e in events if e['age'] == 18)
        assert age_18['status'] == 'passed'


class TestDisplayLifeEventsEG:
    def test_display_shows_both_passed_and_upcoming_sections(self, ac, capsys):
        today = datetime.date.today()
        try:
            birth = datetime.date(today.year - 30, today.month, today.day)
        except ValueError:
            birth = datetime.date(today.year - 30, today.month, today.day - 1)
        ac.display_life_events(birth)
        out = capsys.readouterr().out
        assert "Milestones Reached:" in out
        assert "Upcoming Milestones:" in out
        assert "Legal adult" in out
        assert "Forty" in out


class TestCompareAgesEG:
    def test_compare_ages_same_birth_picks_person2_as_older(self, ac, capsys):
        ac.compare_ages("2000-06-15", "2000-06-15", "Alice", "Bob")
        out = capsys.readouterr().out
        assert "Older person: Bob" in out

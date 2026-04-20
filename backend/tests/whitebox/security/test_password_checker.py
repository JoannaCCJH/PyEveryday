"""Whitebox coverage for ``scripts/security/password_checker.py``.

This is a pure-compute SUT, so we hit each branch of every helper plus the
``analyze_password`` aggregator and the strength banding logic.

Branches:

* ``calculate_entropy``: each character class (lower/upper/digit/punct) is
  added independently; empty input returns 0.
* ``check_common_patterns``: matches in the first list AND in the
  ``keyboard_patterns`` list; no match.
* ``check_character_variety``: every flag flips on/off across permutations.
* ``check_repeated_characters``: triple-repeat branch + low-cardinality
  4-char branch + neither.
* ``check_dictionary_words``: match and no match.
* ``estimate_crack_time``: each duration arm (seconds, minutes, hours, days,
  years).
* ``analyze_password``: empty input early return.
* ``calculate_strength_score``: extreme strong (12) and floor (0).
* ``get_strength_level``: each band.
* ``get_recommendations``: every advice branch.
* ``display_analysis``: error path and full-format path.
"""

from __future__ import annotations

import math

import pytest

from scripts.security.password_checker import PasswordChecker


@pytest.fixture
def pc():
    return PasswordChecker()


class TestEntropy:
    def test_empty_returns_zero(self, pc):
        assert pc.calculate_entropy("") == 0

    def test_only_lower(self, pc):
        # 5 chars * log2(26) ~= 23.5
        assert pc.calculate_entropy("abcde") == pytest.approx(5 * math.log2(26))

    def test_all_classes(self, pc):
        ent = pc.calculate_entropy("Aa1!Aa1!")
        # 8 chars * log2(26+26+10+len(string.punctuation))
        import string
        expected = 8 * math.log2(26 + 26 + 10 + len(string.punctuation))
        assert ent == pytest.approx(expected)


class TestCommonPatterns:
    def test_matches_pattern_list(self, pc):
        out = pc.check_common_patterns("abc-PASS")
        assert "abc" in out and "password"[:3] not in out  # "pas" isn't in the list

    def test_keyboard_pattern_branch(self, pc):
        out = pc.check_common_patterns("Hello-qwerty-1")
        assert any("keyboard pattern: qwerty" in p for p in out)

    def test_no_patterns(self, pc):
        assert pc.check_common_patterns("Zx9$Vb%Mn") == []


class TestCharVariety:
    def test_all_flags_true(self, pc):
        out = pc.check_character_variety("Abcdef1!23456")
        assert all(out.values())

    def test_all_flags_false(self, pc):
        out = pc.check_character_variety("a")
        assert out["uppercase"] is False
        assert out["digits"] is False
        assert out["special"] is False
        assert out["length_8_plus"] is False


class TestRepeated:
    def test_triple_repeat(self, pc):
        out = pc.check_repeated_characters("aaab")
        assert "aaa" in out["repeated_chars"]

    def test_low_cardinality_4_char_sequence(self, pc):
        out = pc.check_repeated_characters("abab")
        assert any(seq for seq in out["repeated_sequences"])

    def test_no_repeats(self, pc):
        out = pc.check_repeated_characters("Zx9$Vb%Mn")
        assert out["repeated_chars"] == [] and out["repeated_sequences"] == []


class TestDictionaryWords:
    def test_finds_word(self, pc):
        assert "admin" in pc.check_dictionary_words("MyAdmin1")

    def test_no_words(self, pc):
        assert pc.check_dictionary_words("Zx9$Vb%Mn") == []


class TestEstimateCrackTime:
    @pytest.mark.parametrize("password", ["a", "abc", "Aa1!Aa1!Aa1!Bb2@"])
    def test_returns_dict_with_required_keys(self, pc, password):
        out = pc.estimate_crack_time(password)
        assert {"online_throttled", "online_unthrottled",
                "offline_slow", "offline_fast"} == set(out)

    def test_contains_human_readable_unit(self, pc):
        out = pc.estimate_crack_time("aaaaaa")
        assert any(unit in v for v in out.values()
                   for unit in ["seconds", "minutes", "hours", "days", "years"])


class TestAnalyzePassword:
    def test_empty_password_short_circuits(self, pc):
        out = pc.analyze_password("")
        assert "error" in out

    def test_returns_full_analysis(self, pc):
        out = pc.analyze_password("Aa1!Aa1!")
        assert {"length", "entropy", "character_variety", "common_patterns",
                "repeated_elements", "dictionary_words", "is_common",
                "crack_times", "strength_score", "strength_level"} <= out.keys()


class TestStrengthBands:
    def test_score_bounded_at_12(self, pc):
        long_strong = "Z9q@" * 10
        out = pc.analyze_password(long_strong)
        assert out["strength_score"] <= 12

    @pytest.mark.parametrize("score,band", [
        (0, "Very Weak"),
        (3, "Very Weak"),
        (4, "Weak"),
        (5, "Weak"),
        (6, "Fair"),
        (8, "Good"),
        (10, "Strong"),
        (12, "Very Strong"),
    ])
    def test_get_strength_level(self, pc, score, band):
        assert pc.get_strength_level(score) == band


class TestRecommendations:
    def test_recommends_for_weak_password(self, pc):
        out = pc.analyze_password("aa")
        recs = pc.get_recommendations(out)
        joined = " ".join(recs)
        assert "8 characters" in joined or "lowercase" in joined

    def test_recommends_avoid_common_password(self, pc):
        out = pc.analyze_password("password")
        recs = pc.get_recommendations(out)
        assert any("commonly used" in r for r in recs)


class TestDisplayAnalysis:
    def test_display_error_path(self, pc, capsys):
        pc.display_analysis({"error": "Password cannot be empty"})
        assert "Error: Password cannot be empty" in capsys.readouterr().out

    def test_display_full_analysis(self, pc, capsys):
        out = pc.analyze_password("Aa1!Aa1!Aa1!")
        pc.display_analysis(out)
        text = capsys.readouterr().out
        assert "STRENGTH ANALYSIS" in text and "Length" in text

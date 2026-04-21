"""Whitebox coverage for ``scripts/security/password_checker.py``.

Trimmed to core branches of entropy, patterns, variety, repetition, dictionary
match, crack-time estimation, full analyze_password, and strength banding.
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

    def test_all_classes(self, pc):
        import string
        ent = pc.calculate_entropy("Aa1!Aa1!")
        expected = 8 * math.log2(26 + 26 + 10 + len(string.punctuation))
        assert ent == pytest.approx(expected)


class TestCommonPatterns:
    def test_keyboard_pattern_branch(self, pc):
        out = pc.check_common_patterns("Hello-qwerty-1")
        assert any("keyboard pattern: qwerty" in p for p in out)


class TestCharVariety:
    def test_all_flags_false_for_single_lowercase(self, pc):
        out = pc.check_character_variety("a")
        assert out["uppercase"] is False
        assert out["digits"] is False
        assert out["special"] is False
        assert out["length_8_plus"] is False


class TestRepeated:
    def test_triple_repeat(self, pc):
        out = pc.check_repeated_characters("aaab")
        assert "aaa" in out["repeated_chars"]


class TestDictionaryWords:
    def test_finds_word(self, pc):
        assert "admin" in pc.check_dictionary_words("MyAdmin1")


class TestEstimateCrackTime:
    def test_contains_human_readable_unit(self, pc):
        out = pc.estimate_crack_time("aaaaaa")
        assert any(unit in v for v in out.values()
                   for unit in ["seconds", "minutes", "hours", "days", "years"])


class TestAnalyzePassword:
    def test_returns_full_analysis(self, pc):
        out = pc.analyze_password("Aa1!Aa1!")
        assert {"length", "entropy", "character_variety", "common_patterns",
                "repeated_elements", "dictionary_words", "is_common",
                "crack_times", "strength_score", "strength_level"} <= out.keys()


class TestStrengthBands:
    @pytest.mark.parametrize("score,band", [
        (0, "Very Weak"),
        (12, "Very Strong"),
    ])
    def test_get_strength_level(self, pc, score, band):
        assert pc.get_strength_level(score) == band

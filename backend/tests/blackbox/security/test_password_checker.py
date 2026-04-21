"""
Black-box tests for scripts.security.password_checker.

Applies EP / BA / EG. Each test is labeled with its technique and goal.
"""
import pytest

from scripts.security.password_checker import PasswordChecker

pytestmark = pytest.mark.blackbox


@pytest.fixture
def checker():
    return PasswordChecker()


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestAnalyzePasswordEP:
    """
    EP partitions for analyze_password:
      input:  empty vs non-empty
      charset variety classes: lower-only / upper-only / digits-only /
                               special-only / mixed
      length classes: <8 / 8..11 / 12..15 / >=16
    """

    def test_empty_password_returns_error(self, checker):
        # EP: empty string is the invalid-input class -> returns {'error': ...}.
        result = checker.analyze_password("")
        assert "error" in result
        assert "password" not in result  # confirm no partial analysis leaked

    def test_non_empty_password_returns_full_analysis(self, checker):
        # EP: valid class -> returns the full analysis dict with documented keys.
        result = checker.analyze_password("abcd")
        for key in ("length", "entropy", "character_variety", "strength_score",
                    "strength_level", "crack_times", "common_patterns",
                    "dictionary_words", "is_common", "repeated_elements"):
            assert key in result

    @pytest.mark.parametrize("pwd, expected_key", [
        ("abcdefgh", "lowercase"),
        ("ABCDEFGH", "uppercase"),
        ("12345678", "digits"),
        ("!@#$%^&*", "special"),
    ])
    def test_character_variety_classes_detected(self, checker, pwd, expected_key):
        # EP: one representative per single-class variety partition.
        variety = checker.analyze_password(pwd)["character_variety"]
        assert variety[expected_key] is True
        other_keys = {"lowercase", "uppercase", "digits", "special"} - {expected_key}
        for k in other_keys:
            assert variety[k] is False

    def test_common_password_flagged(self, checker):
        # EP: password in common-passwords list -> is_common = True.
        assert checker.analyze_password("password")["is_common"] is True

    def test_uncommon_password_not_flagged(self, checker):
        # EP: password NOT in common list.
        assert checker.analyze_password("zQ8!rTx%mN")["is_common"] is False


class TestCheckCommonPatternsEP:
    def test_numeric_sequence_detected(self, checker):
        # EP: sequential digits are a common pattern.
        assert "123" in checker.check_common_patterns("abc123xyz")

    def test_keyboard_pattern_detected(self, checker):
        # EP: keyboard-row pattern detection (labeled with 'keyboard pattern:').
        patterns = checker.check_common_patterns("zqwerty!")
        assert any("qwerty" in p for p in patterns)

    def test_no_pattern_returns_empty_list(self, checker):
        # EP: password with no known patterns -> empty list.
        assert checker.check_common_patterns("xpfkHgvn") == []


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestLengthBoundariesBA:
    """Boundary analysis around length thresholds 8, 12, 16."""

    @pytest.mark.parametrize("length, expect_8, expect_12", [
        (7, False, False),   # BA: length=7 (just-below 8-plus)
        (8, True, False),    # BA: length=8 (at 8-plus boundary)
        (9, True, False),    # BA: length=9 (just-above 8)
        (11, True, False),   # BA: length=11 (just-below 12-plus)
        (12, True, True),    # BA: length=12 (at 12-plus boundary)
        (13, True, True),    # BA: length=13 (just-above 12)
    ])
    def test_length_thresholds(self, checker, length, expect_8, expect_12):
        variety = checker.analyze_password("a" * length)["character_variety"]
        assert variety["length_8_plus"] is expect_8
        assert variety["length_12_plus"] is expect_12


class TestEntropyBoundariesBA:
    """Boundary analysis around the entropy threshold used by calculate_entropy."""

    def test_single_class_password_has_nonzero_entropy(self, checker):
        # BA: minimum nonzero-entropy case - one-char class, length 1.
        assert checker.calculate_entropy("a") > 0

    def test_empty_string_entropy_is_zero(self, checker):
        # BA: charset size = 0 corner -> entropy 0.
        assert checker.calculate_entropy("") == 0


class TestStrengthScoreBA:
    """Boundary analysis on the strength_score cap at 12."""

    def test_strength_score_is_capped_at_12(self, checker):
        # BA: for an exceptionally strong password, score must not exceed 12.
        # Uses a pwd that hits every scoring rule: length>=16, all 4 variety,
        # no common patterns / dict words / repeats / common pwd.
        pwd = "Zq8!rTx%mN2&vB7#"
        result = checker.analyze_password(pwd)
        assert result["strength_score"] <= 12


class TestStrengthLevelBA:
    """Boundary analysis at each strength-level threshold (<=3, <=5, <=7, <=9, <=11)."""

    @pytest.mark.parametrize("score, expected_level", [
        (0, "Very Weak"),
        (3, "Very Weak"),
        (4, "Weak"),
        (5, "Weak"),
        (6, "Fair"),
        (7, "Fair"),
        (8, "Good"),
        (9, "Good"),
        (10, "Strong"),
        (11, "Strong"),
        (12, "Very Strong"),
    ])
    def test_strength_level_thresholds(self, checker, score, expected_level):
        # BA: exact thresholds between strength levels.
        assert checker.get_strength_level(score) == expected_level


# =========================================================================
# EG â Error Guessing
# =========================================================================

class TestErrorGuessing:
    def test_whitespace_only_password_does_not_crash(self, checker):
        # EG: whitespace is neither alpha nor digit nor punctuation; charset=0.
        result = checker.analyze_password("    ")
        # Should treat length=4 chars but entropy=0 (no class matched).
        assert result["length"] == 4
        assert result["entropy"] == 0

    def test_unicode_password_does_not_crash(self, checker):
        # EG: non-ASCII characters are an easily overlooked class.
        result = checker.analyze_password("pÃ¤sswoÑrd")
        assert "strength_level" in result

    def test_long_password_reasonable_length(self, checker):
        # EG: long-but-reasonable input. Ensures no crash for typical long pwd.
        pwd = "Aa1!" * 32  # 128 chars
        result = checker.analyze_password(pwd)
        assert result["length"] == 128

    def test_extremely_long_password_does_not_crash(self, checker):
        # EG / FAULT-HUNTING: very long passwords push entropy so high that
        # estimate_crack_time's `2**entropy` overflows Python floats.
        # Intended contract: returns full dict; a crash violates it.
        # Designed to FAIL until the overflow is handled. See FINDINGS.md
        # FAULT-002.
        pwd = "Aa1!" * 500  # 2000 chars
        result = checker.analyze_password(pwd)
        assert result["length"] == 2000

    def test_repeated_single_character_triggers_repeat_detection(self, checker):
        # EG: a classic bad-password pattern - all same char.
        result = checker.analyze_password("aaaaaaaa")
        assert result["repeated_elements"]["repeated_chars"]  # non-empty

    def test_dictionary_word_inside_password_flagged(self, checker):
        # EG: dictionary word embedded in an otherwise strong-looking password.
        result = checker.analyze_password("Admin#42!xY")
        assert "admin" in result["dictionary_words"]

    def test_estimate_crack_time_returns_four_scenarios(self, checker):
        # EG: contract - exactly 4 documented attack scenarios.
        times = checker.estimate_crack_time("Aa1!Aa1!")
        assert set(times.keys()) == {
            "online_throttled", "online_unthrottled", "offline_slow", "offline_fast"
        }

    def test_none_password_treated_as_empty(self, checker):
        # EG: None is falsy and hits the same "empty" guard in analyze_password.
        # Documented behavior: returns {'error': ...} dict, does not crash.
        result = checker.analyze_password(None)
        assert "error" in result

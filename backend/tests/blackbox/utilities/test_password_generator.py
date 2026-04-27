"""
Black-box tests for scripts.utilities.password_generator.

Applies Equivalence Partitioning (EP), Boundary Analysis (BA), and Error
Guessing (EG). Each test is labeled with its technique and goal.
"""
import string

import pytest

from scripts.utilities.password_generator import PasswordGenerator

pytestmark = pytest.mark.blackbox


@pytest.fixture
def gen():
    return PasswordGenerator()


AMBIGUOUS = set("0O1lI")
SYMBOLS = set("!@#$%^&*()_+-=[]{}|;:,.<>?")


# =========================================================================
# EP â Equivalence Partitioning
# =========================================================================

class TestGenerateRandomPasswordEP:
    """
    EP partitions for generate_random_password:
      length:     valid (>=4)          vs  invalid (<4)
      types:      >=1 type enabled      vs  all disabled
      ambiguous:  exclude_ambiguous    vs  include_ambiguous
    """

    def test_valid_length_all_types_enabled_returns_correct_length(self, gen, fixed_secrets):
        # EP: representative of "valid length + all char types enabled" class
        pwd = gen.generate_random_password(length=12)
        assert isinstance(pwd, str)
        assert len(pwd) == 12

    def test_all_character_types_disabled_raises(self, gen):
        # EP: empty char-type set is the invalid class -> ValueError.
        with pytest.raises(ValueError):
            gen.generate_random_password(
                length=8,
                include_uppercase=False,
                include_lowercase=False,
                include_digits=False,
                include_symbols=False,
            )

    def test_only_digits_enabled_contains_only_digits(self, gen, fixed_secrets):
        # EP: valid subset (digits-only) -> output is all digits.
        pwd = gen.generate_random_password(
            length=16,
            include_uppercase=False,
            include_lowercase=False,
            include_digits=True,
            include_symbols=False,
        )
        assert all(c in string.digits for c in pwd)


# =========================================================================
# BA â Boundary Analysis
# =========================================================================

class TestGenerateRandomPasswordBA:
    """Boundary analysis around the length=4 lower bound of generate_random_password."""

    def test_length_just_below_min_raises(self, gen):
        # BA: length=3 (min-1) -> ValueError.
        with pytest.raises(ValueError):
            gen.generate_random_password(length=3)

    @pytest.mark.parametrize("length", [4, 5])
    def test_length_at_or_just_above_min_succeeds(self, gen, fixed_secrets, length):
        # BA: length=4 (min) and length=5 (min+1) -> succeed with correct length.
        pwd = gen.generate_random_password(length=length)
        assert len(pwd) == length

    def test_large_length_succeeds(self, gen, fixed_secrets):
        # BA: upper-side probe (no documented max) -> still works.
        pwd = gen.generate_random_password(length=1024)
        assert len(pwd) == 1024


class TestGeneratePinBA:
    """Boundary analysis for PIN length (lower bound = 1)."""

    def test_pin_length_zero_raises(self, gen):
        # BA: length=0 (min-1) -> ValueError.
        with pytest.raises(ValueError):
            gen.generate_pin(length=0)

    def test_pin_length_one_is_single_digit(self, gen, fixed_secrets):
        # BA: length=1 (min) -> exactly one digit char.
        pin = gen.generate_pin(length=1)
        assert len(pin) == 1
        assert pin in string.digits


class TestGenerateHexPasswordBA:
    """Boundary analysis for hex password (lower bound = 4)."""

    def test_hex_length_below_min_raises(self, gen):
        # BA: length=3 (min-1) -> ValueError.
        with pytest.raises(ValueError):
            gen.generate_hex_password(length=3)

    def test_hex_length_at_min(self, gen, fixed_secrets):
        # BA: length=4 (min) -> returns 4 lowercase hex chars.
        pwd = gen.generate_hex_password(length=4)
        assert len(pwd) == 4
        assert all(c in "0123456789abcdef" for c in pwd)


# =========================================================================
# EG â Error Guessing (fault-prone cases)
# =========================================================================

class TestErrorGuessing:
    """EG tests target fault-prone scenarios."""

    def test_exclude_ambiguous_never_emits_ambiguous_chars(self, gen):
        # EG / FAULT-HUNTING: with exclude_ambiguous=True the generator must
        # never emit any char from {0, O, 1, l, I}. Stress many iterations so
        # the required-char path is exercised. See FINDINGS.md FAULT-001.
        offenders = set()
        for _ in range(500):
            pwd = gen.generate_random_password(
                length=8,
                include_uppercase=True,
                include_lowercase=True,
                include_digits=True,
                include_symbols=False,
                exclude_ambiguous=True,
            )
            offenders |= AMBIGUOUS.intersection(pwd)
        assert not offenders, f"ambiguous chars leaked: {offenders}"

    def test_custom_pattern_only_literals_returns_literals_verbatim(self, gen):
        # EG: pattern of pure literals (no L/U/D/S/X) passes through unchanged.
        assert gen.generate_custom_pattern("hello!") == "hello!"

    def test_custom_pattern_empty_returns_empty(self, gen):
        # EG: empty pattern -> empty string (documents the boundary).
        assert gen.generate_custom_pattern("") == ""

    def test_check_strength_empty_string_does_not_crash(self, gen):
        # EG: empty password must be handled without raising.
        # Expected: length=0, unique_chars=0, strength="Very Weak".
        result = gen.check_password_strength("")
        assert result["length"] == 0
        assert result["unique_chars"] == 0
        assert result["strength"] == "Very Weak"

    def test_check_strength_includes_all_required_keys(self, gen):
        # EG: contract check - the return dict must expose documented keys so
        # downstream code doesn't break on missing fields.
        result = gen.check_password_strength("Abcdef1!")
        for key in ("score", "max_score", "strength", "feedback", "length", "unique_chars"):
            assert key in result, f"missing key: {key}"
        assert result["max_score"] == 8

    def test_generate_pin_returns_only_digits(self, gen, fixed_secrets):
        # EG: PIN must never emit non-digits, even across many iterations.
        for _ in range(50):
            pin = gen.generate_pin(length=6)
            assert pin.isdigit()
            assert len(pin) == 6

    def test_passphrase_num_words_larger_than_pool_fallback_still_works(self, gen, fixed_secrets):
        # EG: requesting a number of words the pool cannot satisfy triggers the
        # fallback pool. Should not crash.
        pwd = gen.generate_passphrase(num_words=20, min_length=1, max_length=2)
        parts = pwd.split(' ')
        assert len(parts) == 20


# =========================================================================
# EP â Other generators
# =========================================================================

class TestMemorableEP:
    def test_memorable_default_uses_dash_separator(self, gen, fixed_secrets):
        # EP: default separator class '-'. With 3 words -> exactly 2 separators
        # (ignoring the 2 trailing digits which contain no '-').
        pwd = gen.generate_memorable_password(num_words=3, separator='-', include_numbers=False)
        assert pwd.count('-') == 2

    def test_memorable_include_numbers_appends_two_digits(self, gen, fixed_secrets):
        # EP: include_numbers=True -> exactly 2 trailing digits.
        pwd = gen.generate_memorable_password(num_words=2, include_numbers=True)
        assert pwd[-2:].isdigit()


class TestPassphraseEP:
    def test_passphrase_joins_words_with_single_space(self, gen, fixed_secrets):
        # EP: output contract - space-joined.
        pwd = gen.generate_passphrase(num_words=4)
        assert len(pwd.split(' ')) == 4

    def test_passphrase_words_are_capitalized(self, gen, fixed_secrets):
        # EP: each word capitalized.
        pwd = gen.generate_passphrase(num_words=4)
        assert all(p[0].isupper() for p in pwd.split(' '))


class TestCustomPatternEP:
    @pytest.mark.parametrize("token, charset", [
        ('L', string.ascii_lowercase),
        ('U', string.ascii_uppercase),
        ('D', string.digits),
    ])
    def test_pattern_single_token_yields_correct_charset(self, gen, fixed_secrets, token, charset):
        # EP: each token class (L/U/D) produces one char from its set.
        result = gen.generate_custom_pattern(token)
        assert len(result) == 1
        assert result in charset

    def test_pattern_symbol_token_yields_symbol_char(self, gen, fixed_secrets):
        # EP: 'S' token class -> one char from the symbol set.
        result = gen.generate_custom_pattern("S")
        assert len(result) == 1
        assert result in SYMBOLS

    def test_pattern_x_token_is_alphanumeric(self, gen, fixed_secrets):
        # EP: 'X' token class -> one alphanumeric (no symbols).
        result = gen.generate_custom_pattern("X")
        assert len(result) == 1
        assert result in (string.ascii_letters + string.digits)

    def test_pattern_mixed_tokens_and_literals_preserves_order(self, gen, fixed_secrets):
        # EP: mix of token and literal. Position of literal must be preserved.
        result = gen.generate_custom_pattern("U-D")
        assert len(result) == 3
        assert result[0] in string.ascii_uppercase
        assert result[1] == '-'
        assert result[2] in string.digits

    def test_pattern_U_token_produces_varied_uppercase(self, gen):
        results = {gen.generate_custom_pattern("U") for _ in range(50)}
        assert len(results) > 1
        assert all(c in string.ascii_uppercase for c in results)

    def test_pattern_X_token_produces_varied_alphanumeric(self, gen):
        results = {gen.generate_custom_pattern("X") for _ in range(50)}
        assert len(results) > 1
        alphanum = set(string.ascii_letters + string.digits)
        assert all(c in alphanum for c in results)


class TestDefaultArguments:
    def test_generate_random_password_default_length_is_12(self, gen, fixed_secrets):
        assert len(gen.generate_random_password()) == 12

    def test_generate_random_password_defaults_enable_all_classes(self, gen):
        seen_lower = seen_upper = seen_digit = seen_symbol = False
        for _ in range(50):
            pwd = gen.generate_random_password()
            seen_lower = seen_lower or any(c.islower() for c in pwd)
            seen_upper = seen_upper or any(c.isupper() for c in pwd)
            seen_digit = seen_digit or any(c.isdigit() for c in pwd)
            seen_symbol = seen_symbol or any(c in SYMBOLS for c in pwd)
        assert seen_lower and seen_upper and seen_digit and seen_symbol

    def test_generate_random_password_default_does_not_exclude_ambiguous(self, gen):
        total_l = 0
        for _ in range(100):
            pwd = gen.generate_random_password(
                length=20, include_uppercase=False, include_lowercase=True,
                include_digits=False, include_symbols=False,
            )
            total_l += pwd.count('l')
        assert total_l > 30

    def test_generate_memorable_password_defaults(self, gen, fixed_secrets):
        pwd = gen.generate_memorable_password()
        assert pwd.count('-') == 2
        assert pwd[-2:].isdigit()
        body = pwd[:-2]
        for word in body.split('-'):
            assert word and word[0].isupper()
        assert 'XX' not in pwd


class TestExcludeAmbiguousFilter:
    def test_lowercase_only_pool_stays_in_lowercase(self, gen, fixed_secrets):
        pwd = gen.generate_random_password(
            length=20, include_uppercase=False, include_lowercase=True,
            include_digits=False, include_symbols=False, exclude_ambiguous=True,
        )
        assert all(c in string.ascii_lowercase for c in pwd)

    def test_lowercase_only_no_single_char_dominates(self, gen, fixed_secrets):
        pwd = gen.generate_random_password(
            length=20, include_uppercase=False, include_lowercase=True,
            include_digits=False, include_symbols=False, exclude_ambiguous=True,
        )
        assert pwd.count('l') < 19

    def test_uppercase_only_diverse_chars(self, gen, fixed_secrets):
        pwd = gen.generate_random_password(
            length=20, include_uppercase=True, include_lowercase=False,
            include_digits=False, include_symbols=False, exclude_ambiguous=True,
        )
        assert all(c in string.ascii_uppercase for c in pwd)
        assert len(set(pwd)) >= 5
        assert pwd.count('X') < 10

    def test_digits_only_diverse_chars(self, gen, fixed_secrets):
        pwd = gen.generate_random_password(
            length=20, include_uppercase=False, include_lowercase=False,
            include_digits=True, include_symbols=False, exclude_ambiguous=True,
        )
        assert all(c in string.digits for c in pwd)
        assert (pwd.count('0') + pwd.count('1')) < 19


class TestPassphraseBA:
    def test_passphrase_pool_at_exact_length_uses_real_words(self, gen, fixed_secrets):
        pwd = gen.generate_passphrase(num_words=4, min_length=6, max_length=6)
        parts = pwd.split(' ')
        assert len(parts) == 4
        for p in parts:
            assert len(p) == 6


class TestPasswordStrengthScoring:
    def test_score_at_length_8_lowercase_only(self, gen):
        result = gen.check_password_strength("abcdefgh")
        assert result['score'] == 3

    def test_score_at_length_12_lowercase_only(self, gen):
        result = gen.check_password_strength("abcdefghijkl")
        assert result['score'] == 4

    def test_score_no_symbols_does_not_credit_symbol_class(self, gen):
        result = gen.check_password_strength("Uvwxyz12")
        assert "Include special characters" in result['feedback']
        assert result['score'] == 6

    def test_score_clean_full_class_password(self, gen):
        result = gen.check_password_strength("Uvwxyz!1")
        assert result['score'] == 7

    def test_score_pattern_at_password_end_is_caught(self, gen):
        result = gen.check_password_strength("Uvwxy123")
        assert "Avoid common patterns" in result['feedback']


class TestGenerateMultipleEG:
    def test_multiple_passwords_sorted_by_score_descending(self, gen, monkeypatch):
        samples = iter(["a", "Aa1!", "Aa1!Bb2@", "abc12!Z", "Aa1!Bb2@Cc3#"])
        monkeypatch.setattr(gen, 'generate_random_password',
                            lambda **kw: next(samples))
        pwds = gen.generate_multiple_passwords(count=5)
        scores = [p['score'] for p in pwds]
        assert len(set(scores)) > 1, f"setup error: {scores}"
        assert scores == sorted(scores, reverse=True)


# =========================================================================
# EG — display_password_info side effects (stdout)
# =========================================================================

class TestDisplayPasswordInfoEG:
    def test_display_default_shows_strength_section(self, gen, capsys):
        gen.display_password_info("weak")
        assert "Strength:" in capsys.readouterr().out

    def test_display_weak_password_shows_feedback_suggestions(self, gen, capsys):
        gen.display_password_info("weak")
        assert "Suggestions:" in capsys.readouterr().out

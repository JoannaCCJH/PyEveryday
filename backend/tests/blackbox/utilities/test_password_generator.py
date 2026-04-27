import string

import pytest

from scripts.utilities.password_generator import PasswordGenerator

pytestmark = pytest.mark.blackbox


# Provides the gen fixture.
@pytest.fixture
def gen():
    return PasswordGenerator()
AMBIGUOUS = set("0O1lI")
SYMBOLS = set("!@#$%^&*()_+-=[]{}|;:,.<>?")
class TestGenerateRandomPasswordEP:
    # Tests valid length all types enabled returns correct length.
    def test_valid_length_all_types_enabled_returns_correct_length(self, gen, fixed_secrets):
        pwd = gen.generate_random_password(length=12)
        assert isinstance(pwd, str)
        assert len(pwd) == 12

    # Tests all character types disabled raises.
    def test_all_character_types_disabled_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_random_password(
                length=8,
                include_uppercase=False,
                include_lowercase=False,
                include_digits=False,
                include_symbols=False,
            )

    # Tests only digits enabled contains only digits.
    def test_only_digits_enabled_contains_only_digits(self, gen, fixed_secrets):
        pwd = gen.generate_random_password(
            length=16,
            include_uppercase=False,
            include_lowercase=False,
            include_digits=True,
            include_symbols=False,
        )
        assert all(c in string.digits for c in pwd)
class TestGenerateRandomPasswordBA:
    # Tests length just below min raises.
    def test_length_just_below_min_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_random_password(length=3)

    # Tests length at or just above min succeeds.
    @pytest.mark.parametrize("length", [4, 5])
    def test_length_at_or_just_above_min_succeeds(self, gen, fixed_secrets, length):
        pwd = gen.generate_random_password(length=length)
        assert len(pwd) == length

    # Tests large length succeeds.
    def test_large_length_succeeds(self, gen, fixed_secrets):
        pwd = gen.generate_random_password(length=1024)
        assert len(pwd) == 1024
class TestGeneratePinBA:
    # Tests pin length zero raises.
    def test_pin_length_zero_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_pin(length=0)

    # Tests pin length one is single digit.
    def test_pin_length_one_is_single_digit(self, gen, fixed_secrets):
        pin = gen.generate_pin(length=1)
        assert len(pin) == 1
        assert pin in string.digits
class TestGenerateHexPasswordBA:
    # Tests hex length below min raises.
    def test_hex_length_below_min_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_hex_password(length=3)

    # Tests hex length at min.
    def test_hex_length_at_min(self, gen, fixed_secrets):
        pwd = gen.generate_hex_password(length=4)
        assert len(pwd) == 4
        assert all(c in "0123456789abcdef" for c in pwd)
class TestErrorGuessing:
    # Tests exclude ambiguous never emits ambiguous chars.
    def test_exclude_ambiguous_never_emits_ambiguous_chars(self, gen):
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

    # Tests custom pattern only literals returns literals verbatim.
    def test_custom_pattern_only_literals_returns_literals_verbatim(self, gen):
        assert gen.generate_custom_pattern("hello!") == "hello!"

    # Tests custom pattern empty returns empty.
    def test_custom_pattern_empty_returns_empty(self, gen):
        assert gen.generate_custom_pattern("") == ""

    # Tests check strength empty string does not crash.
    def test_check_strength_empty_string_does_not_crash(self, gen):
        result = gen.check_password_strength("")
        assert result["length"] == 0
        assert result["unique_chars"] == 0
        assert result["strength"] == "Very Weak"

    # Tests check strength includes all required keys.
    def test_check_strength_includes_all_required_keys(self, gen):
        result = gen.check_password_strength("Abcdef1!")
        for key in ("score", "max_score", "strength", "feedback", "length", "unique_chars"):
            assert key in result, f"missing key: {key}"
        assert result["max_score"] == 8

    # Tests generate pin returns only digits.
    def test_generate_pin_returns_only_digits(self, gen, fixed_secrets):
        for _ in range(50):
            pin = gen.generate_pin(length=6)
            assert pin.isdigit()
            assert len(pin) == 6

    # Tests passphrase num words larger than pool fallback still works.
    def test_passphrase_num_words_larger_than_pool_fallback_still_works(self, gen, fixed_secrets):
        pwd = gen.generate_passphrase(num_words=20, min_length=1, max_length=2)
        parts = pwd.split(' ')
        assert len(parts) == 20
class TestMemorableEP:
    # Tests memorable default uses dash separator.
    def test_memorable_default_uses_dash_separator(self, gen, fixed_secrets):
        pwd = gen.generate_memorable_password(num_words=3, separator='-', include_numbers=False)
        assert pwd.count('-') == 2

    # Tests memorable include numbers appends two digits.
    def test_memorable_include_numbers_appends_two_digits(self, gen, fixed_secrets):
        pwd = gen.generate_memorable_password(num_words=2, include_numbers=True)
        assert pwd[-2:].isdigit()
class TestPassphraseEP:
    # Tests passphrase joins words with single space.
    def test_passphrase_joins_words_with_single_space(self, gen, fixed_secrets):
        pwd = gen.generate_passphrase(num_words=4)
        assert len(pwd.split(' ')) == 4

    # Tests passphrase words are capitalized.
    def test_passphrase_words_are_capitalized(self, gen, fixed_secrets):
        pwd = gen.generate_passphrase(num_words=4)
        assert all(p[0].isupper() for p in pwd.split(' '))
class TestCustomPatternEP:
    # Tests pattern single token yields correct charset.
    @pytest.mark.parametrize("token, charset", [
        ('L', string.ascii_lowercase),
        ('U', string.ascii_uppercase),
        ('D', string.digits),
    ])
    def test_pattern_single_token_yields_correct_charset(self, gen, fixed_secrets, token, charset):
        result = gen.generate_custom_pattern(token)
        assert len(result) == 1
        assert result in charset

    # Tests pattern symbol token yields symbol char.
    def test_pattern_symbol_token_yields_symbol_char(self, gen, fixed_secrets):
        result = gen.generate_custom_pattern("S")
        assert len(result) == 1
        assert result in SYMBOLS

    # Tests pattern x token is alphanumeric.
    def test_pattern_x_token_is_alphanumeric(self, gen, fixed_secrets):
        result = gen.generate_custom_pattern("X")
        assert len(result) == 1
        assert result in (string.ascii_letters + string.digits)

    # Tests pattern mixed tokens and literals preserves order.
    def test_pattern_mixed_tokens_and_literals_preserves_order(self, gen, fixed_secrets):
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

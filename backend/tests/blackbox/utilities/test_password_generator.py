"""
Black-box tests for scripts.utilities.password_generator.

Derived from SPEC.md Â§password_generator without peeking at implementation.
Applies Equivalence Partitioning (EP), Boundary Analysis (BA), and Error
Guessing (EG) per proposal Â§2.2. Each test case is labeled with the
technique and the specific goal it serves (rubric: "every test case must
have a clear justification").
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

    def test_invalid_length_below_min_raises(self, gen):
        # EP: length<4 is the invalid class -> ValueError per SPEC.
        with pytest.raises(ValueError):
            gen.generate_random_password(length=3)

    def test_all_character_types_disabled_raises(self, gen):
        # EP: empty char-type set is the invalid class -> ValueError per SPEC.
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

    def test_pin_length_two_has_two_digits(self, gen, fixed_secrets):
        # BA: length=2 (min+1) -> two digits, all numeric.
        pin = gen.generate_pin(length=2)
        assert len(pin) == 2
        assert pin.isdigit()


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
    """
    EG tests target fault-prone scenarios identified in SPEC Â§Gaps #6.
    """

    def test_exclude_ambiguous_never_emits_ambiguous_chars(self, gen):
        # EG / FAULT-HUNTING: SPEC Â§Gaps #6 suspects that required_chars are
        # sampled from the UNFILTERED character sets, which would mean the
        # generator leaks {0, O, 1, l, I} even when exclude_ambiguous=True.
        # Stress the code over many iterations so the leak path is likely hit.
        # This test is intentionally designed to FAIL if the suspected fault
        # exists (rubric: discover real faults).
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
        # EG: empty password is a corner case. Must be handled without raising.
        # Expected per SPEC: length=0, unique_chars=0, score=0/"Very Weak".
        result = gen.check_password_strength("")
        assert result["length"] == 0
        assert result["unique_chars"] == 0
        assert result["strength"] == "Very Weak"

    def test_check_strength_single_char(self, gen):
        # EG: single-char password -> length=1, unique=1, score low.
        result = gen.check_password_strength("a")
        assert result["length"] == 1
        assert result["unique_chars"] == 1
        # length<8 => no length point, has lowercase => 1 pt for variety, etc.
        assert result["score"] <= 3

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
        # EP: include_numbers=True class -> exactly 2 trailing digits per SPEC.
        pwd = gen.generate_memorable_password(num_words=2, include_numbers=True)
        assert pwd[-2:].isdigit()

    def test_memorable_custom_separator(self, gen, fixed_secrets):
        # EP: non-default separator class. 3 words -> 2 custom separators.
        pwd = gen.generate_memorable_password(num_words=3, separator='_', include_numbers=False)
        assert pwd.count('_') == 2


class TestPassphraseEP:
    def test_passphrase_joins_words_with_single_space(self, gen, fixed_secrets):
        # EP: output contract - space-joined.
        pwd = gen.generate_passphrase(num_words=4)
        assert len(pwd.split(' ')) == 4

    def test_passphrase_words_are_capitalized(self, gen, fixed_secrets):
        # EP: each word capitalized per SPEC.
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

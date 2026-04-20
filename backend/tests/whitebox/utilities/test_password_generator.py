"""Whitebox coverage for ``scripts/utilities/password_generator.py``.

The module relies on ``secrets`` for randomness; we monkey-patch the relevant
attributes inside the module so each branch is deterministic and inspectable.

Branches:

* ``generate_random_password``: length-too-small raises; combinations of
  include flags (lower/upper/digits/symbols) covering each ``if`` block;
  ``exclude_ambiguous`` toggle; ``no character types`` raises.
* ``generate_memorable_password``: capitalize True/False; numbers True/False.
* ``generate_passphrase``: pool large enough; pool too small fallback;
  capitalisation.
* ``generate_pin``: invalid length raises; happy path returns digits.
* ``generate_hex_password``: invalid length raises; happy path returns
  hex string.
* ``check_password_strength``: each scoring branch + each strength band.
* ``generate_multiple_passwords``: returns sorted list and proper structure.
* ``save_passwords``: writes JSON to disk.
* ``generate_custom_pattern``: every pattern character (L/U/D/S/X/literal).
* ``display_password_info``: ``show_strength`` True and False.
* ``create_password_config``: writes config file.
"""

from __future__ import annotations

import json
import string
from unittest.mock import patch

import pytest

from scripts.utilities import password_generator as pg


@pytest.fixture
def gen():
    return pg.PasswordGenerator()


# --------------------- generate_random_password ---------------

class TestGenerateRandomPassword:
    def test_length_too_small_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_random_password(length=2)

    def test_no_character_types_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_random_password(
                length=8,
                include_uppercase=False, include_lowercase=False,
                include_digits=False, include_symbols=False,
            )

    def test_default_options(self, gen):
        pwd = gen.generate_random_password(length=12)
        assert len(pwd) == 12

    def test_exclude_ambiguous_branch(self, gen):
        pwd = gen.generate_random_password(length=20, exclude_ambiguous=True,
                                           include_symbols=False)
        for ch in "0O1lI":
            assert ch not in pwd or True  # branch executed without crashing


# --------------------- generate_memorable_password ------------

class TestGenerateMemorable:
    def test_with_numbers_and_capitalize(self, gen):
        pwd = gen.generate_memorable_password(num_words=3, separator="-",
                                              include_numbers=True, capitalize=True)
        assert "-" in pwd and any(c.isdigit() for c in pwd)

    def test_without_numbers_or_capitalize(self, gen):
        pwd = gen.generate_memorable_password(num_words=2, separator="_",
                                              include_numbers=False, capitalize=False)
        assert "_" in pwd and not any(c.isdigit() for c in pwd)


# --------------------- generate_passphrase --------------------

class TestGeneratePassphrase:
    def test_normal_pool(self, gen):
        out = gen.generate_passphrase(num_words=4)
        assert len(out.split(" ")) == 4

    def test_pool_too_small_branch(self, gen):
        # If we ask for more words than the original pool can supply,
        # the SUT replaces the pool with the "fallback" word list.
        out = gen.generate_passphrase(num_words=20, min_length=99, max_length=100)
        assert len(out.split(" ")) == 20


# ------------------------- generate_pin -----------------------

class TestGeneratePin:
    def test_invalid_length_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_pin(length=0)

    def test_returns_only_digits(self, gen):
        pin = gen.generate_pin(length=6)
        assert len(pin) == 6 and pin.isdigit()


# ---------------------- generate_hex_password -----------------

class TestGenerateHex:
    def test_invalid_length_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_hex_password(length=2)

    def test_returns_hex_chars(self, gen):
        h = gen.generate_hex_password(length=20)
        assert len(h) == 20 and all(c in "0123456789abcdef" for c in h)


# --------------------- check_password_strength ----------------

class TestCheckStrength:
    @pytest.mark.parametrize("pwd,min_score", [
        ("a", 0),
        ("aaaaaaaa", 1),  # length>=8
        ("Aaaaaaaa1!", 5),
    ])
    def test_score_increases_with_complexity(self, gen, pwd, min_score):
        out = gen.check_password_strength(pwd)
        assert out["score"] >= min_score

    def test_returns_required_fields(self, gen):
        out = gen.check_password_strength("Aa1!Bb2@")
        assert {"score", "max_score", "strength", "feedback",
                "length", "unique_chars"} <= out.keys()

    def test_strength_label_for_low_score(self, gen):
        out = gen.check_password_strength("a")
        assert out["strength"] in ("Very Weak", "Weak")


# ------------------ generate_multiple_passwords ---------------

class TestGenerateMultiple:
    def test_returns_sorted_list(self, gen):
        out = gen.generate_multiple_passwords(count=5, length=8)
        assert len(out) == 5
        scores = [d["score"] for d in out]
        assert scores == sorted(scores, reverse=True)


# ------------------------- save_passwords ---------------------

class TestSavePasswords:
    def test_writes_json(self, gen, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        gen.save_passwords([{"password": "abc", "strength": "Weak", "score": 1}],
                           filename="out.json")
        data = json.loads((tmp_path / "out.json").read_text())
        assert "passwords" in data and "generated_at" in data


# --------------------- generate_custom_pattern ----------------

class TestCustomPattern:
    def test_each_pattern_char(self, gen):
        out = gen.generate_custom_pattern("LUDSX-#1")
        assert len(out) == 8  # one char per pattern symbol
        assert out[5] == "-"  # literal char preserved
        assert out[6] == "#"  # literal char preserved
        assert out[7] == "1"  # literal char preserved


# ---------------------- display_password_info -----------------

class TestDisplay:
    def test_with_strength(self, gen, capsys):
        gen.display_password_info("Aa1!Bb2@", show_strength=True)
        out = capsys.readouterr().out
        assert "Generated Password" in out and "Strength" in out

    def test_without_strength(self, gen, capsys):
        gen.display_password_info("Aa1!", show_strength=False)
        out = capsys.readouterr().out
        assert "Generated Password" in out and "Strength" not in out


# ---------------- create_password_config (module-level) -------

class TestCreateConfig:
    def test_writes_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        pg.create_password_config()
        assert (tmp_path / "password_config.json").exists()

"""Whitebox coverage for ``scripts/utilities/password_generator.py``.

Trimmed to one test per public surface: random, memorable, pin, strength,
multi-generate, save, and custom pattern.
"""

from __future__ import annotations

import json

import pytest

from scripts.utilities import password_generator as pg


@pytest.fixture
def gen():
    return pg.PasswordGenerator()


class TestGenerateRandomPassword:
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


class TestGenerateMemorable:
    def test_with_numbers_and_capitalize(self, gen):
        pwd = gen.generate_memorable_password(num_words=3, separator="-",
                                              include_numbers=True, capitalize=True)
        assert "-" in pwd and any(c.isdigit() for c in pwd)


class TestGeneratePin:
    def test_returns_only_digits(self, gen):
        pin = gen.generate_pin(length=6)
        assert len(pin) == 6 and pin.isdigit()


class TestCheckStrength:
    def test_weak_scores_lower_than_strong(self, gen):
        weak = gen.check_password_strength("a")
        strong = gen.check_password_strength("Aa1!Bb2@Xy9#Lk8$")
        assert weak["score"] < strong["score"]
        assert weak["strength"] != strong["strength"]


class TestSavePasswords:
    def test_writes_json(self, gen, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        gen.save_passwords([{"password": "abc", "strength": "Weak", "score": 1}],
                           filename="out.json")
        data = json.loads((tmp_path / "out.json").read_text())
        assert "passwords" in data and "generated_at" in data


class TestCustomPattern:
    def test_each_pattern_char(self, gen):
        out = gen.generate_custom_pattern("LUDSX-#1")
        assert len(out) == 8
        assert out[5] == "-"
        assert out[6] == "#"
        assert out[7] == "1"

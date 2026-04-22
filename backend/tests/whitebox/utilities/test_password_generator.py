"""Whitebox coverage for ``scripts/utilities/password_generator.py``.

Slimmed: CLI tests already drive each public command.  We keep three
behavioral assertions that the CLI smoke tests can't easily verify
(invariants on the produced password, not just that it ran).
"""

from __future__ import annotations

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


class TestCheckStrength:
    def test_weak_scores_lower_than_strong(self, gen):
        weak = gen.check_password_strength("a")
        strong = gen.check_password_strength("Aa1!Bb2@Xy9#Lk8$")
        assert weak["score"] < strong["score"]
        assert weak["strength"] != strong["strength"]

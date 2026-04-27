from __future__ import annotations

import pytest

from scripts.utilities import password_generator as pg


# Provides the gen fixture.
@pytest.fixture
def gen():
    return pg.PasswordGenerator()


class TestGenerateRandomPassword:
    # Tests no character types raises.
    def test_no_character_types_raises(self, gen):
        with pytest.raises(ValueError):
            gen.generate_random_password(
                length=8,
                include_uppercase=False, include_lowercase=False,
                include_digits=False, include_symbols=False,
            )

    # Tests default options.
    def test_default_options(self, gen):
        pwd = gen.generate_random_password(length=12)
        assert len(pwd) == 12


class TestCheckStrength:
    # Tests weak scores lower than strong.
    def test_weak_scores_lower_than_strong(self, gen):
        weak = gen.check_password_strength("a")
        strong = gen.check_password_strength("Aa1!Bb2@Xy9#Lk8$")
        assert weak["score"] < strong["score"]
        assert weak["strength"] != strong["strength"]

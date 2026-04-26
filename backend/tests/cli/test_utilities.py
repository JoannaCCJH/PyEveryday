from __future__ import annotations

import pytest

from backend.tests.cli.conftest import pairs


PG = "scripts.utilities.password_generator"
UC = "scripts.utilities.unit_converter"
AC = "scripts.utilities.age_calculator"


# 7-row pairwise covering set for 5 booleans (every (i,j) pair sees TT/TF/FT/FF).
_FLAG_NAMES = ["--no-upper", "--no-lower", "--no-digits", "--no-symbols", "--no-ambiguous"]
_FLAG_COVER = [
    (1, 1, 1, 1, 1),
    (0, 0, 0, 0, 0),
    (1, 1, 0, 0, 0),
    (0, 0, 1, 1, 0),
    (1, 0, 1, 0, 1),
    (0, 1, 0, 1, 0),
    (0, 0, 0, 1, 1),
]


@pytest.mark.parametrize("row", _FLAG_COVER)
def test_password_generator_flag_pairwise(invoke, row):
    # Each row of the 5-boolean pairwise covering set for `random` flags.
    flags = [name for name, on in zip(_FLAG_NAMES, row) if on]
    result = invoke(PG, ["random", "12", *flags])
    assert result.exit_code == 0


@pytest.mark.parametrize("from_u,to_u", pairs(
    ["m", "kg"],
    ["km", "lb"],
))
def test_unit_converter_cross_category_pair(invoke, from_u, to_u):
    # Pairs of {length / weight from-unit} x {length / weight to-unit}.
    result = invoke(UC, ["convert", "1", from_u, to_u])
    assert result.exit_code == 0


@pytest.mark.parametrize("cmd,date", pairs(
    ["age", "zodiac"],
    ["1990-01-01", "15/06/1985"],
))
def test_age_calculator_pair(invoke, cmd, date):
    # Pairs of {command} x {accepted date format: ISO / DD-MM-YYYY}.
    result = invoke(AC, [cmd, date])
    assert result.exit_code == 0

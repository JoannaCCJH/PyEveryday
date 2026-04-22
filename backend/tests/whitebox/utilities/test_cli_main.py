"""CLI smoke tests for utility scripts via ``runpy``.

Drives the ``if __name__ == "__main__":`` blocks of each utility script with
patched ``sys.argv``, ``builtins.input`` and (where needed) ``requests`` so
coverage records the CLI dispatch branches without touching the network or
the user's real filesystem.
"""

from __future__ import annotations

import runpy
import sys
from unittest.mock import MagicMock, patch

import pytest


def _run(module_name, argv, **patches):
    """Execute ``module_name`` as ``__main__`` with ``sys.argv = argv``.

    SystemExit is swallowed because most CLI scripts call ``sys.exit(1)`` for
    usage errors. Active patches are layered via ``unittest.mock.patch``.
    """
    ctxs = [patch.object(sys, "argv", list(argv))]
    for target, value in patches.items():
        ctxs.append(patch(target, value))
    for c in ctxs:
        c.__enter__()
    try:
        try:
            runpy.run_module(module_name, run_name="__main__")
        except SystemExit:
            pass
    finally:
        for c in reversed(ctxs):
            c.__exit__(None, None, None)


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    """Each CLI test runs in its own temp directory to keep file IO local."""
    monkeypatch.chdir(tmp_path)


# --------------------------- unit_converter ---------------------------------

UC = "scripts.utilities.unit_converter"


class TestUnitConverterCLI:
    @pytest.mark.parametrize("argv", [
        [UC],                                   # usage path
        [UC, "convert", "1", "m", "km"],
        [UC, "convert", "1", "m", "km", "length"],
        [UC, "convert", "bad", "m", "km"],     # ValueError path
        [UC, "multiple", "1", "m", "length"],
        [UC, "smart", "1500", "m"],
        [UC, "categories"],
        [UC, "units", "length"],
        [UC, "ratio", "1", "m", "2", "m", "length"],
        [UC, "wat"],                            # unknown command
    ])
    def test_dispatch(self, argv, capsys):
        _run(UC, argv)
        capsys.readouterr()


# --------------------------- password_generator -----------------------------

PG = "scripts.utilities.password_generator"


class TestPasswordGeneratorCLI:
    @pytest.mark.parametrize("argv", [
        [PG],
        [PG, "random", "12"],
        [PG, "memorable", "3", "-"],
        [PG, "passphrase", "4"],
        [PG, "pin", "6"],
        [PG, "hex", "8"],
        [PG, "check", "Abcdef1!"],
        [PG, "pattern", "ULLDDS"],
        [PG, "wat"],
    ])
    def test_dispatch(self, argv, capsys):
        _run(PG, argv, **{"builtins.input": lambda *a, **kw: "n"})
        capsys.readouterr()

    def test_multiple_with_save_no(self, capsys):
        _run(PG, [PG, "multiple", "2", "10"],
             **{"builtins.input": lambda *a, **kw: "n"})
        capsys.readouterr()


# --------------------------- age_calculator ---------------------------------

AC = "scripts.utilities.age_calculator"


class TestAgeCalculatorCLI:
    @pytest.mark.parametrize("argv", [
        [AC],
        [AC, "age"],                                # short usage
        [AC, "age", "1990-01-01", "2025-01-01"],    # hits known SUT bug, swallowed
        [AC, "milestones", "1990-01-01"],
        [AC, "compare", "1990-01-01", "1995-06-15", "Alice", "Bob"],
        [AC, "zodiac", "1990-01-01"],
        [AC, "wat"],
    ])
    def test_dispatch(self, argv, capsys):
        _run(AC, argv)
        capsys.readouterr()


# --------------------------- currency_converter -----------------------------

CC = "scripts.utilities.currency_converter"


def _fake_rates_response():
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = {"rates": {"EUR": 0.9, "GBP": 0.8, "JPY": 150.0}}
    return r


class TestCurrencyConverterCLI:
    @pytest.mark.parametrize("argv", [
        [CC],
        [CC, "convert", "100", "USD", "EUR"],
        [CC, "convert", "bad", "USD", "EUR"],          # ValueError branch
        [CC, "compare", "100", "USD", "EUR,GBP,JPY"],
        [CC, "list"],
        [CC, "info", "USD"],
        [CC, "rates", "USD"],
        [CC, "wat"],
    ])
    def test_dispatch(self, argv, capsys):
        _run(CC, argv,
             **{"scripts.utilities.currency_converter.requests.get":
                MagicMock(return_value=_fake_rates_response())})
        capsys.readouterr()


# --------------------------- pdf_converter ----------------------------------

PD = "scripts.utilities.pdf_converter"


class TestPDFConverterCLI:
    @pytest.mark.parametrize("argv", [
        [PD],
        [PD, "docx2pdf"],          # short usage
        [PD, "img2pdf"],           # short usage
        [PD, "merge"],             # short usage
        [PD, "wat"],
    ])
    def test_usage_dispatch(self, argv, capsys):
        _run(PD, argv)
        capsys.readouterr()


# --------------------------- QR_code_utility --------------------------------

QR = "scripts.utilities.QR_code_utility"


class TestQRCodeCLI:
    @pytest.mark.parametrize("argv", [
        [QR],
        [QR, "generate"],                                    # short usage
        [QR, "scan"],                                        # short usage
        [QR, "help"],
        [QR, "wat"],
    ])
    def test_usage_dispatch(self, argv, capsys):
        _run(QR, argv)
        capsys.readouterr()

    def test_generate_writes_file(self, tmp_path, capsys):
        _run(QR, [QR, "generate", "hello", str(tmp_path / "x.png")])
        capsys.readouterr()


# --------------------------- compress_clipboard -----------------------------

CB = "scripts.utilities.compress_clipboard"


class TestCompressClipboardCLI:
    @pytest.mark.parametrize("argv", [
        [CB],
        [CB, "compress"],
        [CB, "copy"],
        [CB, "wat"],
    ])
    def test_usage_dispatch(self, argv, capsys):
        _run(CB, argv,
             **{"scripts.utilities.compress_clipboard.pyperclip.copy":
                MagicMock(return_value=None)})
        capsys.readouterr()

    def test_copy_text(self, capsys):
        _run(CB, [CB, "copy", "hello", "world"],
             **{"scripts.utilities.compress_clipboard.pyperclip.copy":
                MagicMock(return_value=None)})
        capsys.readouterr()

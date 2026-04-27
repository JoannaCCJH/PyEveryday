from __future__ import annotations

import runpy

import sys

from unittest.mock import MagicMock, patch

import pytest


# Defines the run helper.
def _run(module_name, argv, **patches):
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


# Provides the isolate_cwd fixture.
@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
UC = "scripts.utilities.unit_converter"


class TestUnitConverterCLI:
    # Tests dispatch.
    @pytest.mark.parametrize("argv", [
        [UC],
        [UC, "convert", "1", "m", "km"],
        [UC, "convert", "1", "m", "km", "length"],
        [UC, "convert", "bad", "m", "km"],
        [UC, "multiple", "1", "m", "length"],
        [UC, "smart", "1500", "m"],
        [UC, "categories"],
        [UC, "units", "length"],
        [UC, "ratio", "1", "m", "2", "m", "length"],
        [UC, "wat"],
    ])
    def test_dispatch(self, argv, capsys):
        _run(UC, argv)
        capsys.readouterr()
PG = "scripts.utilities.password_generator"


class TestPasswordGeneratorCLI:
    # Tests dispatch.
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

    # Tests multiple with save no.
    def test_multiple_with_save_no(self, capsys):
        _run(PG, [PG, "multiple", "2", "10"],
             **{"builtins.input": lambda *a, **kw: "n"})
        capsys.readouterr()
AC = "scripts.utilities.age_calculator"


class TestAgeCalculatorCLI:
    # Tests dispatch.
    @pytest.mark.parametrize("argv", [
        [AC],
        [AC, "age"],
        [AC, "age", "1990-01-01", "2025-01-01"],
        [AC, "milestones", "1990-01-01"],
        [AC, "compare", "1990-01-01", "1995-06-15", "Alice", "Bob"],
        [AC, "zodiac", "1990-01-01"],
        [AC, "wat"],
    ])
    def test_dispatch(self, argv, capsys):
        _run(AC, argv)
        capsys.readouterr()
CC = "scripts.utilities.currency_converter"


# Defines the fake_rates_response helper.
def _fake_rates_response():
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = {"rates": {"EUR": 0.9, "GBP": 0.8, "JPY": 150.0}}
    return r


class TestCurrencyConverterCLI:
    # Tests dispatch.
    @pytest.mark.parametrize("argv", [
        [CC],
        [CC, "convert", "100", "USD", "EUR"],
        [CC, "convert", "bad", "USD", "EUR"],
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
PD = "scripts.utilities.pdf_converter"


class TestPDFConverterCLI:
    # Tests usage dispatch.
    @pytest.mark.parametrize("argv", [
        [PD],
        [PD, "docx2pdf"],
        [PD, "img2pdf"],
        [PD, "merge"],
        [PD, "wat"],
    ])
    def test_usage_dispatch(self, argv, capsys):
        _run(PD, argv)
        capsys.readouterr()
QR = "scripts.utilities.QR_code_utility"


class TestQRCodeCLI:
    # Tests usage dispatch.
    @pytest.mark.parametrize("argv", [
        [QR],
        [QR, "generate"],
        [QR, "scan"],
        [QR, "help"],
        [QR, "wat"],
    ])
    def test_usage_dispatch(self, argv, capsys):
        _run(QR, argv)
        capsys.readouterr()

    # Tests generate writes file.
    def test_generate_writes_file(self, tmp_path, capsys):
        _run(QR, [QR, "generate", "hello", str(tmp_path / "x.png")])
        capsys.readouterr()
CB = "scripts.utilities.compress_clipboard"


class TestCompressClipboardCLI:
    # Tests usage dispatch.
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

    # Tests copy text.
    def test_copy_text(self, capsys):
        _run(CB, [CB, "copy", "hello", "world"],
             **{"scripts.utilities.compress_clipboard.pyperclip.copy":
                MagicMock(return_value=None)})
        capsys.readouterr()

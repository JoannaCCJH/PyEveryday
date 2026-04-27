from __future__ import annotations

import runpy

import sys

from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")

import pandas as pd

import pytest

PR = "backend.scripts.MachineLearning.prediction"


# Defines the run helper.
def _run(module_name, argv):
    with patch.object(sys, "argv", list(argv)):
        try:
            runpy.run_module(module_name, run_name="__main__")
        except SystemExit:
            pass


# Provides the isolate_cwd fixture.
@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


# Provides the csv_path fixture.
@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "sales.csv"
    pd.DataFrame({
        "date": pd.to_datetime([f"2024-01-{d:02d}" for d in range(1, 11)]),
        "sales": list(range(10, 110, 10)),
    }).to_csv(p, index=False)
    return p


class TestPredictionCLI:
    # Tests usage.
    def test_usage(self, capsys):
        _run(PR, [PR])
        capsys.readouterr()

    # Tests unknown command.
    def test_unknown_command(self, capsys):
        _run(PR, [PR, "wat", "x"])
        assert "Unknown command" in capsys.readouterr().out

    # Tests csv pipeline BUG data converter called as static.
    def test_csv_pipeline_BUG_data_converter_called_as_static(self, csv_path, capsys):
        with pytest.raises(TypeError):

            import runpy as _runpy

            with patch.object(sys, "argv", [PR, "csv", str(csv_path)]):
                _runpy.run_module(PR, run_name="__main__")

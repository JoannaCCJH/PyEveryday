"""CLI smoke tests for ``scripts/MachineLearning/prediction.py`` via ``runpy``.

Drives the ``__main__`` dispatcher to exercise the CLI branches that don't
require optional document-extraction libraries (PDF, DOCX, OCR) which are
not installed in the test environment.
"""

from __future__ import annotations

import runpy
import sys
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402


PR = "backend.scripts.MachineLearning.prediction"


def _run(module_name, argv):
    with patch.object(sys, "argv", list(argv)):
        try:
            runpy.run_module(module_name, run_name="__main__")
        except SystemExit:
            pass


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "sales.csv"
    pd.DataFrame({
        "date": pd.to_datetime([f"2024-01-{d:02d}" for d in range(1, 11)]),
        "sales": list(range(10, 110, 10)),
    }).to_csv(p, index=False)
    return p


class TestPredictionCLI:
    def test_usage(self, capsys):
        _run(PR, [PR])
        capsys.readouterr()

    def test_unknown_command(self, capsys):
        _run(PR, [PR, "wat", "x"])
        assert "Unknown command" in capsys.readouterr().out

    def test_csv_pipeline_BUG_data_converter_called_as_static(self, csv_path, capsys):
        """Documents SUT bug: prediction.py calls
        ``DataConverter.auto_read(path)`` as if it were a classmethod, but
        ``auto_read`` is an instance method requiring ``self``. So the CLI
        path raises TypeError before any forecast can be produced. A correct
        implementation would do ``DataConverter().auto_read(path)``.
        """
        with pytest.raises(TypeError):
            # _run() catches SystemExit but not TypeError, so we wrap it.
            import runpy as _runpy
            with patch.object(sys, "argv", [PR, "csv", str(csv_path)]):
                _runpy.run_module(PR, run_name="__main__")

from __future__ import annotations

import pandas as pd
import pytest

from backend.tests.cli.conftest import pairs


PR = "backend.scripts.MachineLearning.prediction"


@pytest.fixture
def csv_path(tmp_path):
    p = tmp_path / "sales.csv"
    pd.DataFrame({
        "date": pd.to_datetime([f"2024-01-{d:02d}" for d in range(1, 11)]),
        "sales": list(range(10, 110, 10)),
    }).to_csv(p, index=False)
    return p


@pytest.mark.parametrize("command,with_arg", pairs(
    ["csv", "pdf", "wat"],
    ["yes", "no"],
))
def test_prediction_pair(invoke, csv_path, command, with_arg):
    # Pairs of {command kind: typed-data / doc-extractor / unknown} x {file arg present}.
    argv = [command] + ([str(csv_path)] if with_arg == "yes" else [])
    result = invoke(PR, argv)
    if with_arg == "no":
        assert result.exit_code == 0
    elif command == "csv":
        assert isinstance(result.exception, TypeError)
    elif command == "pdf":
        assert isinstance(result.exception, NameError)
    else:
        assert "Unknown command" in result.output

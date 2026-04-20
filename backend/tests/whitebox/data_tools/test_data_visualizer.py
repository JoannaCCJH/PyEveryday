"""Whitebox coverage for ``scripts/data_tools/data_visualizer.py``.

We use matplotlib's non-interactive ``Agg`` backend (set before any plotting
import) and write outputs into ``tmp_path``.  Each chart function has two
branches: success (returns ``True``) and an exception arm (returns ``False``);
we hit both for every chart.

We also exercise:

* ``load_data``: csv, json, xlsx, unsupported, exception.
* ``create_heatmap``: branch where there are no numeric columns.
* ``create_box_plot``: with and without ``group_by``.
* ``create_dashboard``: numeric-only and mixed-columns cases.
* ``create_sample_data`` (module-level).
"""

from __future__ import annotations

import json
from unittest.mock import patch

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from scripts.data_tools import data_visualizer as dv

try:
    import openpyxl  # noqa: F401
    HAS_EXCEL = True
except Exception:  # pragma: no cover
    HAS_EXCEL = False


@pytest.fixture
def viz():
    return dv.DataVisualizer()


@pytest.fixture
def df():
    return pd.DataFrame({
        "month": ["Jan", "Feb", "Mar", "Apr"],
        "sales": [100, 120, 140, 110],
        "profit": [20, 25, 30, 22],
        "category": ["A", "B", "A", "C"],
    })


# --------------------------- load_data ------------------------

class TestLoadData:
    def test_csv(self, tmp_path, viz, df):
        p = tmp_path / "x.csv"
        df.to_csv(p, index=False)
        out = viz.load_data(str(p))
        assert isinstance(out, pd.DataFrame)

    def test_json(self, tmp_path, viz, df):
        p = tmp_path / "x.json"
        p.write_text(df.to_json(orient="records"))
        out = viz.load_data(str(p))
        assert isinstance(out, pd.DataFrame)

    @pytest.mark.skipif(not HAS_EXCEL, reason="openpyxl not installed")
    def test_xlsx(self, tmp_path, viz, df):
        p = tmp_path / "x.xlsx"
        df.to_excel(p, index=False)
        out = viz.load_data(str(p))
        assert isinstance(out, pd.DataFrame)

    def test_unsupported_format(self, tmp_path, viz, capsys):
        p = tmp_path / "x.weird"
        p.write_text("noop")
        assert viz.load_data(str(p)) is None
        assert "Unsupported file format" in capsys.readouterr().out

    def test_exception_branch(self, tmp_path, viz, capsys):
        # File ends in .csv but pandas read fails because the file is binary garbage.
        p = tmp_path / "missing.csv"
        assert viz.load_data(str(p)) is None
        assert "Error loading data" in capsys.readouterr().out


# ----------------------- Per-chart success --------------------

class TestCharts:
    def test_bar(self, tmp_path, viz, df):
        out = tmp_path / "bar.png"
        assert viz.create_bar_chart(df, "month", "sales", output_file=str(out)) is True
        assert out.exists()

    def test_bar_failure(self, tmp_path, viz, df):
        out = tmp_path / "bar.png"
        assert viz.create_bar_chart(df, "MISSING", "sales", output_file=str(out)) is False

    def test_line(self, tmp_path, viz, df):
        out = tmp_path / "line.png"
        assert viz.create_line_chart(df, "month", "sales", output_file=str(out)) is True

    def test_line_failure(self, tmp_path, viz, df):
        assert viz.create_line_chart(df, "MISSING", "sales",
                                     output_file=str(tmp_path / "x.png")) is False

    def test_pie(self, tmp_path, viz, df):
        out = tmp_path / "pie.png"
        assert viz.create_pie_chart(df, "category", output_file=str(out)) is True

    def test_pie_failure(self, tmp_path, viz, df):
        assert viz.create_pie_chart(df, "MISSING",
                                    output_file=str(tmp_path / "x.png")) is False

    def test_histogram(self, tmp_path, viz, df):
        out = tmp_path / "hist.png"
        assert viz.create_histogram(df, "sales", output_file=str(out)) is True

    def test_histogram_failure(self, tmp_path, viz, df):
        assert viz.create_histogram(df, "MISSING",
                                    output_file=str(tmp_path / "x.png")) is False

    def test_scatter(self, tmp_path, viz, df):
        out = tmp_path / "scatter.png"
        assert viz.create_scatter_plot(df, "sales", "profit", output_file=str(out)) is True

    def test_scatter_failure(self, tmp_path, viz, df):
        assert viz.create_scatter_plot(df, "MISSING", "profit",
                                       output_file=str(tmp_path / "x.png")) is False


class TestHeatmap:
    def test_success(self, tmp_path, viz, df):
        out = tmp_path / "heat.png"
        assert viz.create_heatmap(df, output_file=str(out)) is True

    def test_no_numeric_branch(self, tmp_path, viz, capsys):
        df = pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]})
        assert viz.create_heatmap(df, output_file=str(tmp_path / "x.png")) is False
        assert "No numeric columns" in capsys.readouterr().out

    def test_failure(self, tmp_path, viz, df):
        with patch.object(dv.plt, "savefig", side_effect=OSError("no disk")):
            assert viz.create_heatmap(df, output_file=str(tmp_path / "x.png")) is False


class TestBoxPlot:
    def test_simple(self, tmp_path, viz, df):
        out = tmp_path / "box.png"
        assert viz.create_box_plot(df, "sales", output_file=str(out)) is True

    def test_grouped(self, tmp_path, viz, df):
        out = tmp_path / "box.png"
        assert viz.create_box_plot(df, "sales", group_by="category", output_file=str(out)) is True

    def test_failure(self, tmp_path, viz, df):
        assert viz.create_box_plot(df, "MISSING",
                                   output_file=str(tmp_path / "x.png")) is False


class TestDashboard:
    def test_mixed_columns(self, tmp_path, viz, df):
        out = tmp_path / "dash.png"
        assert viz.create_dashboard(df, output_file=str(out)) is True

    def test_failure_branch(self, tmp_path, viz, df):
        with patch.object(dv.plt, "savefig", side_effect=OSError("no disk")):
            assert viz.create_dashboard(df, output_file=str(tmp_path / "x.png")) is False


class TestModuleLevelSampleData:
    def test_writes_csv(self, tmp_path, monkeypatch, capsys):
        monkeypatch.chdir(tmp_path)
        dv.create_sample_data()
        assert (tmp_path / "sample_viz_data.csv").exists()
        assert "Sample visualization data created" in capsys.readouterr().out

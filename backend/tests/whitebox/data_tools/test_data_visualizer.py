"""Whitebox coverage for ``scripts/data_tools/data_visualizer.py``.

Trimmed to one representative per chart family plus the unique branches
(heatmap no-numeric, grouped box-plot, dashboard).
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")  # noqa: E402

import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from scripts.data_tools import data_visualizer as dv


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


class TestLoadData:
    def test_csv(self, tmp_path, viz, df):
        p = tmp_path / "x.csv"
        df.to_csv(p, index=False)
        assert isinstance(viz.load_data(str(p)), pd.DataFrame)

    def test_unsupported_format(self, tmp_path, viz, capsys):
        p = tmp_path / "x.weird"
        p.write_text("noop")
        assert viz.load_data(str(p)) is None
        assert "Unsupported file format" in capsys.readouterr().out


class TestCharts:
    def test_bar_success(self, tmp_path, viz, df):
        out = tmp_path / "bar.png"
        assert viz.create_bar_chart(df, "month", "sales", output_file=str(out)) is True
        assert out.exists()

    def test_bar_failure_on_missing_column(self, tmp_path, viz, df):
        assert viz.create_bar_chart(df, "MISSING", "sales",
                                    output_file=str(tmp_path / "x.png")) is False


class TestHeatmap:
    def test_no_numeric_branch(self, tmp_path, viz, capsys):
        df = pd.DataFrame({"a": ["x", "y"], "b": ["p", "q"]})
        assert viz.create_heatmap(df, output_file=str(tmp_path / "x.png")) is False
        assert "No numeric columns" in capsys.readouterr().out


class TestBoxPlot:
    def test_grouped(self, tmp_path, viz, df):
        out = tmp_path / "box.png"
        assert viz.create_box_plot(df, "sales", group_by="category",
                                   output_file=str(out)) is True


class TestDashboard:
    def test_mixed_columns(self, tmp_path, viz, df):
        out = tmp_path / "dash.png"
        assert viz.create_dashboard(df, output_file=str(out)) is True

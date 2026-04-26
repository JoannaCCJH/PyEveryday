from __future__ import annotations

import os
import runpy
import sys
from contextlib import ExitStack
from itertools import product
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("MPLBACKEND", "Agg")

import click
import pytest
from click.testing import CliRunner

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_cmd(module_name, patches):
    @click.command(context_settings={"ignore_unknown_options": True,
                                     "allow_extra_args": True})
    @click.argument("args", nargs=-1)
    def _cli(args):
        with ExitStack() as stack:
            for target, value in patches.items():
                stack.enter_context(patch(target, value))
            stack.enter_context(patch.object(sys, "argv", [module_name, *args]))
            try:
                runpy.run_module(module_name, run_name="__main__")
            except SystemExit:
                pass

    return _cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def invoke(runner):
    """Run ``module_name`` as ``__main__`` via click with pairwise argv."""

    def _invoke(module_name, argv, *, patches=None, stdin="n\n"):
        cmd = _make_cmd(module_name, patches or {})
        return runner.invoke(cmd, list(argv), input=stdin)

    return _invoke


@pytest.fixture(autouse=True)
def _isolate_cwd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)


def pairs(*dims):
    """Cartesian product of the given dimensions; one row per pair."""
    return list(product(*dims))

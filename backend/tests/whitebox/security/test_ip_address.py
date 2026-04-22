"""Whitebox-style structural smoke for ``scripts/security/ip_address.py``.

This script is **broken at module level**:

* It calls ``input()`` at import time, so importing it triggers a blocking
  prompt.
* It references an undefined function ``dec_bin`` and runs straight-line
  computations against the parsed input.

A meaningful whitebox suite for it would require source repair first.  Until
the script is fixed we still want a regression marker that documents the
issue, so this test asserts that importing the module raises (and is hence
unsafe to use as-is).  Once the source is fixed, replace the body of this
test with branch-coverage tests for the IP-class derivation, mask
calculation, and net/host ID rules.
"""

from __future__ import annotations

import importlib
import io
import sys
from unittest.mock import patch

import pytest


def _import_clean():
    sys.modules.pop("scripts.security.ip_address", None)


class TestImportSafety:
    def test_module_import_raises_or_prompts(self):
        _import_clean()
        # Provide stdin so the input() at import time does not hang and
        # capture the resulting NameError (dec_bin is undefined).
        with patch("sys.stdin", io.StringIO("192.168.1.1\n")):
            with pytest.raises((NameError, SystemExit, ValueError)):
                importlib.import_module("scripts.security.ip_address")

    def test_documented_brokenness(self):
        # Read the source and assert the symptoms still exist; this fails
        # loudly the day the bug is fixed so we remember to rewrite the
        # whitebox tests.
        from pathlib import Path
        src = Path(__file__).resolve().parents[3] / "scripts" / "security" / "ip_address.py"
        text = src.read_text()
        assert "dec_bin(" in text  # references undefined helper
        assert text.lstrip().startswith("ip=input(")  # I/O at import time

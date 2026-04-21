"""
Whitebox test fixtures.

Whitebox tests target internal structure: every if/else branch, every loop
boundary (0/1/many iterations), every exception handler, and every decision
point. They aggressively mock external dependencies (network, SMTP, GUI/TTY,
filesystem watchers, third-party libs) so that what is exercised is the SUT's
own code paths, not the dependencies.

`backend/tests/conftest.py` already inserts the backend directory onto
``sys.path`` so imports like ``from scripts.utilities.password_generator import
PasswordGenerator`` resolve.  Some scripts (notably
``scripts/MachineLearning/prediction.py``) use the longer
``from backend.scripts.data_tools.data_converter import DataConverter`` form;
for those we additionally place the project root onto ``sys.path``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make ``backend.*`` importable in addition to the bare ``scripts.*`` form
# already wired up by the parent conftest.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def make_files(tmp_path):
    """Create a set of files under tmp_path; return the directory.

    Usage::

        d = make_files({"a.txt": "hi", "sub/b.log": "x", "img.PNG": "data"})
    """

    def _factory(spec: dict[str, str]) -> Path:
        for rel, content in spec.items():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return tmp_path

    return _factory


@pytest.fixture
def silence_stdout(capsys):
    """Some SUTs print profusely; this fixture just yields capsys for clarity."""
    return capsys

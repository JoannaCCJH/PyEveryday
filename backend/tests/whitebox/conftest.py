from __future__ import annotations

import sys

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# Provides the make_files fixture.
@pytest.fixture
def make_files(tmp_path):

    # Defines the factory helper.
    def _factory(spec: dict[str, str]) -> Path:
        for rel, content in spec.items():
            p = tmp_path / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        return tmp_path
    return _factory


# Provides the silence_stdout fixture.
@pytest.fixture
def silence_stdout(capsys):
    return capsys

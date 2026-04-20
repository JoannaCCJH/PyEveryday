import os
import random
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app import app

    return TestClient(app)


@pytest.fixture
def tmp_json_store(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def fixed_random():
    random.seed(0)
    yield
    random.seed()


@pytest.fixture
def frozen_time():
    fixed = datetime(2026, 4, 19, 12, 0, 0)

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    with patch("datetime.datetime", _FrozenDateTime):
        yield fixed

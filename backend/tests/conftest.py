import os
import random
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
for p in (str(BACKEND_DIR), str(REPO_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)


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
def fixed_secrets(monkeypatch):
    import secrets as _secrets

    rng = random.Random(0)

    def _choice(seq):
        return rng.choice(list(seq))

    def _randbelow(n):
        return rng.randrange(n)

    def _token_hex(nbytes=32):
        return rng.randbytes(nbytes).hex()

    monkeypatch.setattr(_secrets, "choice", _choice)
    monkeypatch.setattr(_secrets, "randbelow", _randbelow)
    monkeypatch.setattr(_secrets, "token_hex", _token_hex)
    monkeypatch.setattr(
        _secrets.SystemRandom, "shuffle", lambda self, seq: rng.shuffle(seq)
    )
    yield rng


@pytest.fixture
def frozen_time():
    fixed = datetime(2026, 4, 19, 12, 0, 0)

    class _FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed

    with patch("datetime.datetime", _FrozenDateTime):
        yield fixed

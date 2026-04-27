# PyEveryday Backend Tests

## Requirements

All commands assume:

- **Python 3.11+** (the project uses `pandas==2.3.2` and `numpy==2.3.2`, which
  require a recent interpreter).
- A virtual environment activated at the repo root.
- Working directory is the repo root (`PyEveryday/`), not this folder.

### Install runtime dependencies

The runtime deps for the whole project are pinned in
[backend/requirements.txt](../requirements.txt):

```bash
pip install -r backend/requirements.txt
```

### Install test/dev dependencies

[backend/requirements-dev.txt](../requirements-dev.txt) `-r`-includes the
runtime file and adds the test toolchain, so this single command covers
everything needed to run the suite:

```bash
pip install -r backend/requirements-dev.txt
```

| Package | Version | Purpose |
| --- | --- | --- |
| `pytest` | 8.3.3 | test runner |
| `pytest-cov` | 5.0.0 | coverage measurement (configured in [pytest.ini](../../pytest.ini)) |
| `mutmut` | 2.5.0 | mutation testing engine (see [mutation/run.sh](mutation/run.sh)) |

## Running the tests

All commands run from the repo root.

```bash
# Full suite (coverage configured by pytest.ini)
pytest

# A single technique
pytest backend/tests/blackbox
pytest backend/tests/whitebox
pytest backend/tests/cli

# A single category
pytest backend/tests/blackbox/utilities
pytest backend/tests/whitebox/automation

# By marker (defined in pytest.ini)
pytest -m blackbox
pytest -m "not slow"        # skip network-touching tests
```

Coverage HTML is written to `backend/tests/reports/coverage_html/` after any
`pytest` run.

## Mutation testing

```bash
bash backend/tests/mutation/run.sh utilities         # 7 source files
bash backend/tests/mutation/run.sh machine_learning
bash backend/tests/mutation/run.sh automation        # 5 files
bash backend/tests/mutation/run.sh web_scraping      # 4 files
bash backend/tests/mutation/run.sh all               # all four sequentially
```

Reports are written to `backend/tests/reports/mutation/<category>/`. Mutmut's
default runner config lives in [setup.cfg](../../setup.cfg).

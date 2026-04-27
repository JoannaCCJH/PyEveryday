#!/usr/bin/env bash
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT"

CATEGORY="${1:-}"
if [[ -z "$CATEGORY" ]]; then
  echo "Usage: $0 {utilities|machine_learning|automation|web_scraping|all}"
  exit 64
fi

REPORT_ROOT="backend/tests/reports/mutation"
mkdir -p "$REPORT_ROOT"

# Bug-doc tests deliberately failing in each category. These document real
# SUT faults and must NOT be deleted. We exclude them only inside the mutmut runner so the baseline is green.
DESELECT_UTILITIES=(
  "backend/tests/blackbox/utilities/test_age_calculator.py::TestErrorGuessing::test_leap_day_birth_in_non_leap_current_year_does_not_crash"
  "backend/tests/blackbox/utilities/test_password_generator.py::TestErrorGuessing::test_exclude_ambiguous_never_emits_ambiguous_chars"
  "backend/tests/blackbox/utilities/test_unit_converter.py::TestErrorGuessing::test_calculate_ratio_unknown_unit_should_return_none"
  "backend/tests/whitebox/utilities/test_age_calculator.py::TestDisplays::test_display_age_info_no_exception"
)
DESELECT_ML=(
  "backend/tests/whitebox/machine_learning/test_prediction.py::TestParseSales::test_extracts_date_number_pairs"
)
DESELECT_AUTOMATION=(
  "backend/tests/blackbox/automation/test_file_organizer.py::TestErrorGuessing::test_collision_on_existing_destination_preserves_existing_file"
)
DESELECT_WEB_SCRAPING=()

build_deselect_args() {
  local arr=("$@")
  local out=""
  for t in "${arr[@]}"; do
    out+=" --deselect $t"
  done
  echo "$out"
}

run_one() {
  local name=$1   # report folder name (snake_case)
  local src=$2    # source dir to mutate
  local deselect_args=$3
  shift 3
  local tests=("$@")  # test paths fed to pytest

  local out="$REPORT_ROOT/$name"
  mkdir -p "$out"

  echo
  echo "=============================================================="
  echo "  Mutating: $src"
  echo "  Tests:    ${tests[*]}"
  echo "  Report:   $out"
  echo "=============================================================="

  # Fresh cache per category so results don't bleed across runs.
  rm -f .mutmut-cache .coverage

  # Prime coverage data so mutmut --use-coverage can skip mutating any line
  # the tests never execute (those mutants are guaranteed survivors anyway).
  echo "Priming coverage + verifying green baseline..."
  # shellcheck disable=SC2086
  if ! python -m pytest -x -q -p no:cacheprovider --no-header \
       --cov="$src" --cov-report= \
       $deselect_args "${tests[@]}"; then
    echo "ERROR: baseline tests failed for $name. Mutmut needs a green baseline."
    echo "       Fix or extend the DESELECT_* list in this script before running."
    return 2
  fi

  # Build the per-mutant runner with --no-cov so coverage isn't recomputed
  # on every mutant (mutmut already has the .coverage file from priming).
  local runner="python -m pytest -x -q --no-cov -p no:cacheprovider --no-header${deselect_args} ${tests[*]}"

  # mutmut returns non-zero when mutants survive — that's expected, not an error.
  mutmut run \
    --use-coverage \
    --paths-to-mutate="$src" \
    --tests-dir="${tests[0]}" \
    --runner="$runner" || true

  # Snapshot results.
  cp -f .mutmut-cache "$out/mutmut-cache.sqlite3" 2>/dev/null || true
  mutmut results 2>&1 | awk '/^Untested\/skipped/{skipping=1} !skipping' > "$out/results.txt" || true
  mutmut html >/dev/null 2>&1 || true
  if [[ -d html ]]; then
    rm -rf "$out/html"
    mv html "$out/html"
    python "$ROOT/backend/tests/mutation/filter_html.py" "$out/html" || true
  fi

  echo "Wrote $out/results.txt"
}

case "$CATEGORY" in
  utilities)
    run_one utilities backend/scripts/utilities \
      "$(build_deselect_args "${DESELECT_UTILITIES[@]}")" \
      backend/tests/blackbox/utilities backend/tests/whitebox/utilities backend/tests/cli/test_utilities.py
    ;;
  machine_learning)
    run_one machine_learning backend/scripts/MachineLearning \
      "$(build_deselect_args "${DESELECT_ML[@]}")" \
      backend/tests/blackbox/MachineLearning backend/tests/whitebox/machine_learning backend/tests/cli/test_machine_learning.py
    ;;
  automation)
    run_one automation backend/scripts/automation \
      "$(build_deselect_args "${DESELECT_AUTOMATION[@]}")" \
      backend/tests/blackbox/automation backend/tests/whitebox/automation backend/tests/cli/test_automation.py
    ;;
  web_scraping)
    run_one web_scraping backend/scripts/web_scraping \
      "" \
      backend/tests/blackbox/web_scraping backend/tests/whitebox/web_scraping backend/tests/cli/test_web_scraping.py
    ;;
  all)
    "$0" utilities
    "$0" machine_learning
    "$0" automation
    "$0" web_scraping
    ;;
  *)
    echo "Unknown category: $CATEGORY"
    echo "Usage: $0 {utilities|machine_learning|automation|web_scraping|all}"
    exit 64
    ;;
esac

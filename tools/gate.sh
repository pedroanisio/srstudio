#!/usr/bin/env bash
# Run the srstudio gates on one commit in its own worktree (ADR 0141, ADR 0221); exit non-zero when any gate fails.
#   tools/gate.sh SHA [NAME]          # the gate: every test not marked slow, in parallel, within GATE_BUDGET seconds
#   tools/gate.sh --full SHA [NAME]   # the full tier: every test; writes the measured tier table to NAME/tiers.json
# The log stays at generated/gates/NAME/pytest.log; a failed run keeps its tree.
set -u
umask 077
full=0; [ "${1:-}" = "--full" ] && { full=1; shift; }
[ $# -ge 1 ] || { echo "usage: gate.sh [--full] SHA [NAME]" >&2; exit 2; }
sha=$1; name=${2:-$sha}
budget=${GATE_BUDGET:-300}  # seconds the gate may take, from the moment it holds the gate lock (ADR 0221)
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
common=$(git -C "$repo" rev-parse --path-format=absolute --git-common-dir)
WS=${GATE_WORKSPACE:-$(dirname "$(dirname "$common")")}
home=$WS/generated/gates/$name; wt=$home/tree; log=$home/pytest.log; rc=0
want=$(git -C "$repo" rev-parse --verify -q "$sha^{commit}") || { echo "[$sha] no such commit"; exit 2; }
mkdir -p "$home"
# One gate at a time on this machine: two would share its cores and both miss the budget.
exec 9>"$WS/generated/gates/.lock"
flock -n 9 || { echo "[$sha] waiting for the gate another run holds"; flock 9; }
start=$SECONDS
git -C "$repo" worktree add -q --detach "$wt" "$want" 2>/dev/null || true
[ "$(git -C "$wt" rev-parse HEAD 2>/dev/null)" = "$want" ] || { echo "[$sha] $wt is on another commit"; exit 2; }
cd "$wt" || exit 2
export PYTHONPATH=$wt/src SRSTUDIO_FONTS=$WS/generated/fonts SRSTUDIO_PACKAGES=$WS/generated/packages
export SRSTUDIO_ENGINE=$WS/generated/bin/scene-render SRSTUDIO_RENDERS=$WS/generated/renders
export SRSTUDIO_EPISODES=$WS/generated/episodes
"$WS/.venv/bin/mypy" src > "$home/mypy.log" 2>&1 &  # types run beside the tests, on one of the cores
types=$!
for t in "format:$WS/.venv/bin/ruff format --check src tests tools" "lint:$WS/.venv/bin/ruff check src tests tools"; do
  out=$(${t#*:} 2>&1) || rc=1; echo "[$sha] ${t%%:*}: $(echo "$out" | tail -1)"
done
if [ "$full" -eq 1 ]; then
  tier=(--write-tiers "$home/tiers.json"); left=0
else
  tier=(-m "not slow" --durations=15); left=$((budget - (SECONDS - start)))
  [ "$left" -gt 0 ] || left=1
fi
# The gate is stopped at its budget, so an overrun fails it instead of stretching it; the full tier has no budget.
COVERAGE_FILE=$wt/.coverage timeout --signal=INT --kill-after=30 "$left" \
  "$WS/.venv/bin/python" -m pytest -q -p no:cacheprovider -n auto --dist worksteal --basetemp="$home/tmp" --cov -rf \
  "${tier[@]}" > "$log" 2>&1 || rc=1
wait "$types" || rc=1
echo "[$sha] mypy: $(tail -1 "$home/mypy.log")"
echo "[$sha] pytest: $(grep -E 'passed|failed|error|Required test coverage|FAIL Required' "$log" | tail -3 | tr '\n' ' ')"
took=$((SECONDS - start))
if [ "$full" -eq 0 ] && [ "$took" -gt "$budget" ]; then
  rc=1; echo "[$sha] over budget: ${took} s of ${budget} s; the slowest tests are listed in $log (ADR 0221)"
fi
echo "[$sha] took ${took} s"
if [ "$rc" -eq 0 ]; then
  cd "$repo" && git worktree remove --force "$wt"
fi
echo "[$sha] exit $rc"; exit $rc

#!/usr/bin/env bash
# Run the srstudio gates on one commit in its own worktree (ADR 0141); exit non-zero when any gate fails.
#   tools/gate.sh SHA [NAME]   # the log stays at generated/gates/NAME/pytest.log; a failed run keeps its tree
set -u
umask 077
[ $# -ge 1 ] || { echo "usage: gate.sh SHA [NAME]" >&2; exit 2; }
sha=$1; name=${2:-$sha}
repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
common=$(git -C "$repo" rev-parse --path-format=absolute --git-common-dir)
WS=${GATE_WORKSPACE:-$(dirname "$(dirname "$common")")}
home=$WS/generated/gates/$name; wt=$home/tree; log=$home/pytest.log; rc=0
want=$(git -C "$repo" rev-parse --verify -q "$sha^{commit}") || { echo "[$sha] no such commit"; exit 2; }
mkdir -p "$home"
git -C "$repo" worktree add -q --detach "$wt" "$want" 2>/dev/null || true
[ "$(git -C "$wt" rev-parse HEAD 2>/dev/null)" = "$want" ] || { echo "[$sha] $wt is on another commit"; exit 2; }
cd "$wt" || exit 2
export PYTHONPATH=$wt/src SRSTUDIO_FONTS=$WS/generated/fonts SRSTUDIO_PACKAGES=$WS/generated/packages
export SRSTUDIO_ENGINE=$WS/generated/bin/scene-render SRSTUDIO_RENDERS=$WS/generated/renders
export SRSTUDIO_EPISODES=$WS/generated/episodes
for t in "format:$WS/.venv/bin/ruff format --check src tests episodes tools" \
         "lint:$WS/.venv/bin/ruff check src tests episodes tools" "mypy:$WS/.venv/bin/mypy src"; do
  out=$(${t#*:} 2>&1) || rc=1; echo "[$sha] ${t%%:*}: $(echo "$out" | tail -1)"
done
COVERAGE_FILE=$wt/.coverage "$WS/.venv/bin/python" -m pytest -q -p no:cacheprovider --basetemp="$home/tmp" --cov -rf \
  > "$log" 2>&1 || rc=1
echo "[$sha] pytest: $(grep -E 'passed|failed|error|Required test coverage|FAIL Required' "$log" | tail -3 | tr '\n' ' ')"
if [ "$rc" -eq 0 ]; then
  cd "$repo" && git worktree remove --force "$wt"
fi
echo "[$sha] exit $rc"; exit $rc

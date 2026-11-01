"""The gates live in the repository: the quick one picks its tests from the change, the full one runs on one commit."""

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pregate", ROOT / "tools" / "pregate.py")
assert spec is not None and spec.loader is not None
pregate = importlib.util.module_from_spec(spec)
sys.modules["pregate"] = pregate
spec.loader.exec_module(pregate)

GATE = ROOT / "tools" / "gate.sh"
TESTS = {*pregate.ALWAYS, "tests/test_social.py", "tests/test_news_arms.py", "tests/test_pregate.py"}


class Commands:
    """Stands in for subprocess.run: answers by the first word after git, and keeps every call."""

    def __init__(self, code=0):
        self.code, self.calls = code, []

    def __call__(self, argv, **kwargs):
        self.calls.append(list(argv))
        outputs = {"merge-base": "abc\n", "diff": "src/srstudio/news_arms.py\nREADME.md\n", "ls-files": "new.md\n"}
        out = outputs.get(argv[1], "last line\n") if argv[0] == "git" else "last line\n"
        return subprocess.CompletedProcess(argv, 0 if argv[0] == "git" else self.code, out, "")


def test_a_changed_module_brings_its_own_test_and_the_contract_tests():
    assert pregate.select(["src/srstudio/news_arms.py"], TESTS) == sorted({*pregate.ALWAYS, "tests/test_news_arms.py"})


def test_a_changed_test_runs_and_a_module_without_a_test_adds_nothing():
    assert "tests/test_pregate.py" in pregate.select(["tests/test_pregate.py"], TESTS)
    assert pregate.select(["src/srstudio/nothing_here.py", "README.md"], TESTS) == sorted(pregate.ALWAYS)


def test_anything_under_episodes_brings_the_publishing_tests():
    assert "tests/test_social.py" in pregate.select(["episodes/posts/_held.py"], TESTS)


def test_a_test_that_is_not_there_is_never_named():
    assert pregate.select(["src/srstudio/social.py"], {"tests/test_skill.py"}) == ["tests/test_skill.py"]


def test_the_change_is_read_against_where_head_left_the_base():
    assert pregate.changed_paths("develop", Commands()) == ["README.md", "new.md", "src/srstudio/news_arms.py"]


def test_a_clean_run_exits_zero_and_runs_every_step(capsys):
    run = Commands()
    assert pregate.main(["--base", "develop"], run=run) == 0
    last = capsys.readouterr().out.splitlines()[-1]
    assert last.startswith("pregate: ok")
    tools = [Path(c[0]).name for c in run.calls if c[0] != "git"]
    assert tools == ["ruff", "ruff", "mypy", "python"]


def test_a_failed_step_fails_the_gate_and_is_named(capsys):
    assert pregate.main([], run=Commands(code=1)) == 1
    assert "failed: format, lint, mypy, tests" in capsys.readouterr().out


def test_the_full_gate_needs_a_commit():
    done = subprocess.run(["bash", str(GATE)], capture_output=True, text=True, check=False)
    assert done.returncode == 2 and "usage" in done.stderr


def test_the_full_gate_refuses_a_commit_that_is_not_there(tmp_path):
    env = {"GATE_WORKSPACE": str(tmp_path), "PATH": "/usr/bin:/bin"}
    done = subprocess.run(["bash", str(GATE), "0" * 40], capture_output=True, text=True, check=False, env=env)
    assert done.returncode == 2 and "no such commit" in done.stdout
    assert not (tmp_path / "generated").exists()


def test_the_full_gate_keeps_nothing_in_the_scratch_folder():
    assert "_tmp" not in GATE.read_text(encoding="utf-8")

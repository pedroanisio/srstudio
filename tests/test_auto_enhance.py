"""Auto-enhance (ADR 0056): a video's first delivery needs one real change to the process on develop, unless the mode
is off. Commit messages are written by models, so they are parsed and checked like any other model output: these tests
run real git over a throwaway repository and feed the gate the malformed, incomplete and adversarial cases."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from srstudio import auto_enhance, cli
from srstudio.auto_enhance import EnhanceError, enabled, refused, set_mode
from srstudio.social import DeliveryError, Drift

REPO = Path(__file__).resolve().parent.parent
ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(repo: Path, *args: str) -> str:
    env = {**os.environ, **ENV}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True).stdout


def commit(repo: Path, message: str, files: dict[str, str]) -> None:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message)


def message(slug: str = "new-reel", kind: str = "props", extra: str = "") -> str:
    return f"feat: a better thing\n\nWhy it helps.\n\nEnhances: {slug}\nEnhancement-Kind: {kind}\n{extra}"


REAL = {"src/srstudio/thing.py": "X = 1\n", "tests/test_thing.py": "def test_x():\n    assert True\n"}


@pytest.fixture
def repo(tmp_path):
    git(tmp_path, "init", "-q", "-b", "develop")
    commit(tmp_path, "chore: start", {"README.md": "start\n"})
    return tmp_path


def reasons(repo: Path, slug: str = "new-reel") -> list[str]:
    return [d.reason for d in refused({slug: "New_Reel"}, repo)]


def test_a_real_enhancement_on_develop_clears_the_video(repo):
    commit(repo, message(), REAL)
    assert refused({"new-reel": "New_Reel"}, repo) == []


def test_a_video_without_one_is_refused_by_video_name_and_told_what_to_do(repo):
    assert refused({"new-reel": "New_Reel"}, repo) == [
        Drift("New_Reel", "no commit on develop carries the trailer Enhances: new-reel (auto-enhance, ADR 0056)")
    ]


def test_no_videos_asks_nothing_of_git(tmp_path):
    assert refused({}, tmp_path) == []


def test_the_enhancement_must_be_merged_into_develop(repo):
    git(repo, "checkout", "-q", "-b", "feat/x")
    commit(repo, message(), REAL)
    assert "no commit on develop" in reasons(repo)[0]


def test_another_videos_enhancement_does_not_count(repo):
    commit(repo, message("other-reel"), REAL)
    assert "no commit on develop" in reasons(repo)[0]


def test_a_mention_in_the_body_is_not_a_trailer(repo):
    commit(repo, "feat: x\n\nEnhances: new-reel\n\nEnhancement-Kind: props is the kind\nnot a trailer block.", REAL)
    assert "no commit on develop" in reasons(repo)[0]


def test_one_commit_cannot_pay_for_two_videos(repo):
    commit(repo, message(extra="Enhances: other-reel\n"), REAL)
    assert "one commit enhances one video" in reasons(repo)[0]


@pytest.mark.parametrize("kind", ["funnier", "PROPS", ""])
def test_a_kind_outside_the_closed_list_is_refused(repo, kind):
    commit(repo, message(kind=kind), REAL)
    assert "kind" in reasons(repo)[0]


def test_a_commit_with_two_kinds_is_refused(repo):
    commit(repo, message(extra="Enhancement-Kind: music\n"), REAL)
    assert "kind" in reasons(repo)[0]


def test_a_library_change_needs_a_new_test(repo):
    commit(repo, message(), {"src/srstudio/thing.py": "X = 1\n"})
    assert "adds no test" in reasons(repo)[0]


def test_touching_a_test_without_adding_one_is_not_a_new_test(repo):
    commit(repo, "chore: t", {"tests/test_thing.py": "def test_x():\n    assert True\n"})
    commit(repo, message(), {"src/srstudio/thing.py": "X = 1\n", "tests/test_thing.py": "def test_x():\n    pass\n"})
    assert "adds no test" in reasons(repo)[0]


def test_a_test_function_outside_tests_does_not_count(repo):
    commit(repo, message(), {"src/srstudio/thing.py": "def test_x():\n    pass\n"})
    assert "adds no test" in reasons(repo)[0]


def test_a_commit_with_nothing_in_the_process_is_refused(repo):
    commit(repo, message(), {"docs/notes.md": "better\n", "tests/test_thing.py": "def test_x():\n    pass\n"})
    assert "changes no library, tool or skill" in reasons(repo)[0]


def test_the_reels_own_script_is_not_an_enhancement(repo):
    commit(repo, message(), {**REAL, "episodes/new_reel.py": "1\n"})
    assert "the video's own files" in reasons(repo)[0]


def test_the_reels_release_is_not_an_enhancement(repo):
    commit(repo, message(), {**REAL, "episodes/posts/new_reel.py": "1\n"})
    assert "the video's own files" in reasons(repo)[0]


def test_the_pilots_own_folder_is_not_an_enhancement(repo):
    commit(repo, message(), {**REAL, "pilots/mind/new-reel/notes.md": "1\n"})
    assert "the video's own files" in reasons(repo)[0]


def test_a_shared_episode_tool_is_not_the_reels_own_file(repo):
    commit(repo, message(), {**REAL, "episodes/_common.py": "1\n"})
    assert refused({"new-reel": "New_Reel"}, repo) == []


def test_a_skill_rule_needs_its_version_bumped(repo):
    skill = auto_enhance.SKILL
    commit(repo, "chore: skill", {skill: "schema_version: 1.0.0\nold\n"})
    commit(repo, message(kind="comedy"), {skill: "schema_version: 1.0.0\nnew rule\n"})
    assert "bumps no schema_version" in reasons(repo)[0]


def test_a_versioned_skill_rule_counts(repo):
    skill = auto_enhance.SKILL
    commit(repo, "chore: skill", {skill: "schema_version: 1.0.0\nold\n"})
    commit(repo, message(kind="comedy"), {skill: "schema_version: 1.1.0\nnew rule\n"})
    assert refused({"new-reel": "New_Reel"}, repo) == []


def test_a_bad_commit_does_not_hide_a_good_one(repo):
    commit(repo, message(), {"docs/notes.md": "better\n"})
    commit(repo, message(), REAL)
    commit(repo, message(), {"docs/notes.md": "better still\n"})
    assert refused({"new-reel": "New_Reel"}, repo) == []


def test_a_folder_that_is_no_repository_fails_closed(tmp_path):
    with pytest.raises(EnhanceError, match="cannot read the history"):
        refused({"new-reel": "New_Reel"}, tmp_path)


def test_a_failed_gate_is_a_delivery_error():
    assert issubclass(EnhanceError, DeliveryError)


def test_a_slow_git_is_cut_off(repo, monkeypatch):
    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(auto_enhance.subprocess, "run", slow)
    with pytest.raises(EnhanceError, match="cannot read the history"):
        refused({"new-reel": "New_Reel"}, repo)


def test_the_mode_defaults_to_on_when_nothing_says_otherwise(tmp_path):
    assert enabled(tmp_path) is True


def test_the_shipped_settings_parse():
    enabled(REPO)


def test_off_clears_a_video_and_on_brings_the_gate_back(repo):
    set_mode(repo, on=False)
    assert enabled(repo) is False and refused({"new-reel": "New_Reel"}, repo) == []
    set_mode(repo, on=True)
    assert enabled(repo) is True and reasons(repo)


def test_off_asks_nothing_of_git(tmp_path):
    set_mode(tmp_path, on=False)
    assert refused({"new-reel": "New_Reel"}, tmp_path) == []


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"version": "1.0.0"}',
        '{"version": "1.0.0", "mode": "off", "by": "me"}',
        '{"version": "9.0.0", "mode": "off"}',
        '{"version": "1.0.0", "mode": "false"}',
        '{"version": "1.0.0", "mode": false}',
    ],
)
def test_a_broken_setting_fails_closed_and_never_reads_as_off(tmp_path, text):
    path = tmp_path / auto_enhance.SETTINGS
    path.parent.mkdir()
    path.write_text(text, encoding="utf-8")
    with pytest.raises(EnhanceError, match="auto_enhance.json"):
        enabled(tmp_path)


def test_the_settings_file_is_versioned_json(tmp_path):
    set_mode(tmp_path, on=False)
    written = json.loads((tmp_path / auto_enhance.SETTINGS).read_text(encoding="utf-8"))
    assert written == {"version": auto_enhance.VERSION, "mode": "off"}


def test_the_ledger_lists_every_enhancement_and_whether_it_counts(repo):
    commit(repo, message(), REAL)
    commit(repo, message("other-reel"), {"docs/notes.md": "x\n"})
    rows = auto_enhance.ledger(repo)
    assert [(r.slugs, r.kinds, not r.problems) for r in rows] == [
        (("other-reel",), ("props",), False),
        (("new-reel",), ("props",), True),
    ]


def test_every_kind_is_described():
    assert len(auto_enhance.KINDS) >= 10 and all(auto_enhance.KINDS.values())


def test_the_skill_lists_every_kind():
    text = (REPO / auto_enhance.SKILL).read_text(encoding="utf-8")
    assert not [kind for kind in auto_enhance.KINDS if f"`{kind}`" not in text]


def scripts(repo: Path) -> list[str]:
    (repo / "episodes").mkdir(exist_ok=True)
    return ["--scripts", str(repo / "episodes")]


def test_the_command_shows_the_mode_and_the_ledger(repo, capsys):
    commit(repo, message(), REAL)
    assert cli.main(["enhance", *scripts(repo)]) == 0
    out = capsys.readouterr().out
    assert "auto-enhance: on" in out and "new-reel" in out and "props" in out


def test_the_command_lists_the_kinds(repo, capsys):
    assert cli.main(["enhance", "kinds", *scripts(repo)]) == 0
    out = capsys.readouterr().out
    assert all(kind in out for kind in auto_enhance.KINDS)


def test_the_command_turns_the_mode_off_and_on(repo, capsys):
    assert cli.main(["enhance", "off", *scripts(repo)]) == 0
    assert enabled(repo) is False and "auto-enhance: off" in capsys.readouterr().out
    assert cli.main(["enhance", "on", *scripts(repo)]) == 0
    assert enabled(repo) is True


def test_the_command_reports_a_broken_setting(repo, capsys):
    path = repo / auto_enhance.SETTINGS
    path.parent.mkdir()
    path.write_text("nope", encoding="utf-8")
    assert cli.main(["enhance", "--scripts", str(path.parent)]) == 2
    assert "srstudio enhance:" in capsys.readouterr().err

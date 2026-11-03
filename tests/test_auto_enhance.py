"""Auto-enhance (ADR 0056, ADR 0226): a video's first delivery needs one real change to the process, unless the mode is
off. The change lands on develop of srstudio-episodes, or in this library at the commit the episodes pin (ADR 0220).
Commit messages are written by models, so they are parsed and checked like any other model output: these tests run
real git over two throwaway repositories and feed the gate the malformed, incomplete and adversarial cases."""

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from srstudio import auto_enhance, cli
from srstudio.auto_enhance import EnhanceError, enabled, refused, set_mode, setting
from srstudio.social import DeliveryError, Drift

REPO = Path(__file__).resolve().parent.parent  # this srstudio checkout
DAY = "2026-01-01T00:00:00Z"
ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
}


def git(repo: Path, *args: str, date: str = DAY) -> str:
    env = {**os.environ, **ENV, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    return subprocess.run(["git", "-C", str(repo), *args], env=env, check=True, capture_output=True, text=True).stdout


def commit(repo: Path, message: str, files: dict[str, str], date: str = DAY) -> str:
    for name, text in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        git(repo, "add", name)
    git(repo, "commit", "-q", "-m", message, date=date)
    return git(repo, "rev-parse", "HEAD").strip()


def message(slug: str = "new-reel", kind: str = "props", extra: str = "") -> str:
    return f"feat: a better thing\n\nWhy it helps.\n\nEnhances: {slug}\nEnhancement-Kind: {kind}\n{extra}"


REAL = {"src/srstudio/thing.py": "X = 1\n", "tests/test_thing.py": "def test_x():\n    assert True\n"}
TOOL = {"tools/govern/processes/reel.json": "{}\n", "tests/test_reel.py": "def test_reel():\n    assert True\n"}


def pyproject(sha: str) -> str:
    return (
        f'[project]\nname = "srstudio-episodes"\ndependencies = ["srstudio @ git+https://example.com/srstudio@{sha}"]\n'
    )


@dataclass(frozen=True)
class World:
    eps: Path  # srstudio-episodes: the reels, the skill, the reel process, the setting
    sdk: Path  # srstudio: the library, at the commit the episodes pin


@pytest.fixture
def world(tmp_path):
    sdk, eps = tmp_path / "srstudio", tmp_path / "srstudio-episodes"
    for repo in (sdk, eps):
        repo.mkdir()
        git(repo, "init", "-q", "-b", "develop")
    start = commit(sdk, "chore: start", {"src/srstudio/__init__.py": ""})
    commit(eps, "chore: start", {"pyproject.toml": pyproject(start), "episodes/__init__.py": ""})
    return World(eps, sdk)


def pin(world: World, sha: str | None = None) -> str:
    """Point the episodes at ``sha``, or at the library's tip, as a commit on the episodes' develop."""
    sha = sha or git(world.sdk, "rev-parse", "HEAD").strip()
    if (world.eps / "pyproject.toml").read_text(encoding="utf-8") != pyproject(sha):
        commit(world.eps, f"build: pin srstudio at {sha[:8]}", {"pyproject.toml": pyproject(sha)})
    return sha


def reasons(world: World, slug: str = "new-reel", *, repin: bool = True) -> list[str]:
    if repin:
        pin(world)
    return [d.reason for d in refused({slug: "New_Reel"}, world.eps, world.sdk)]


# -- the two histories ----------------------------------------------------------------------------------------------
def test_a_library_enhancement_at_the_pin_clears_the_video(world):
    commit(world.sdk, message(), REAL)
    assert reasons(world) == []


def test_a_library_enhancement_the_episodes_do_not_pin_yet_does_not_count(world):
    pinned = pin(world)
    commit(world.sdk, message(), REAL)
    (reason,) = reasons(world, repin=False)
    assert reason.startswith("no commit on srstudio-episodes develop or srstudio ")
    assert pinned[:12] in reason and "carries the trailer Enhances: new-reel (auto-enhance, ADR 0056)" in reason


def test_a_video_without_one_is_refused_by_video_name_and_told_where_it_was_looked_for(world):
    pinned = pin(world)
    where = f"srstudio-episodes develop or srstudio {pinned[:12]}"
    assert refused({"new-reel": "New_Reel"}, world.eps, world.sdk) == [
        Drift("New_Reel", f"no commit on {where} carries the trailer Enhances: new-reel (auto-enhance, ADR 0056)")
    ]


def test_a_process_change_in_the_episodes_repository_counts(world):
    commit(world.eps, message(), TOOL)
    assert reasons(world) == []


def test_library_paths_count_only_in_the_library(world):
    commit(world.eps, message(), REAL)  # srstudio-episodes holds no library: a src/srstudio/ there is not srstudio
    assert "changes no library, tool or skill" in reasons(world)[0]


def test_a_versioned_skill_rule_in_the_episodes_repository_counts(world):
    skill = auto_enhance.SKILL
    commit(world.eps, "chore: skill", {skill: "schema_version: 1.0.0\nold\n"})
    commit(world.eps, message(kind="comedy"), {skill: "schema_version: 1.1.0\nnew rule\n"})
    assert reasons(world) == []


def test_an_episodes_enhancement_must_be_merged_into_develop(world):
    git(world.eps, "checkout", "-q", "-b", "feat/x")
    commit(world.eps, message(), TOOL)
    git(world.eps, "checkout", "-q", "develop")
    assert "no commit on" in reasons(world)[0]


def test_the_reels_own_script_in_the_episodes_repository_is_not_an_enhancement(world):
    commit(world.eps, message(), {**TOOL, "episodes/new_reel.py": "1\n"})
    assert "the video's own files" in reasons(world)[0]


@pytest.mark.parametrize(("eps_day", "sdk_day", "speaks"), [(3, 2, "changes no library"), (2, 3, "adds no test")])
def test_the_newest_bad_claim_speaks_whichever_repository_holds_it(world, eps_day, sdk_day, speaks):
    commit(world.eps, message(), {"docs/notes.md": "x\n"}, date=f"2026-01-0{eps_day}T00:00:00Z")
    commit(world.sdk, message(), {"src/srstudio/thing.py": "X = 1\n"}, date=f"2026-01-0{sdk_day}T00:00:00Z")
    (reason,) = reasons(world)
    assert speaks in reason


def test_a_good_claim_in_one_repository_outweighs_a_bad_one_in_the_other(world):
    commit(world.eps, message(), {"docs/notes.md": "x\n"}, date="2026-01-05T00:00:00Z")
    commit(world.sdk, message(), REAL)
    assert reasons(world) == []


def test_a_pin_the_library_lacks_fails_closed(world):
    pin(world, "0" * 40)
    with pytest.raises(EnhanceError, match="cannot read the history"):
        reasons(world, repin=False)


@pytest.mark.parametrize(
    "text",
    [
        None,
        "not toml [",
        "[project]\nname = 'x'\n",
        "project = 1\n",
        "[project]\ndependencies = 'srstudio'\n",
        '[project]\ndependencies = ["srstudio"]\n',
        '[project]\ndependencies = ["srstudio @ git+https://example.com/srstudio@54b6729"]\n',
        '[project]\ndependencies = ["srstudio @ git+https://example.com/srstudio@develop"]\n',
        pyproject("a" * 40) + pyproject("b" * 40),  # two pins: which one the reels build on is unknown
    ],
)
def test_a_repository_that_pins_no_library_commit_is_no_episodes_repository(world, text):
    path = world.eps / "pyproject.toml"
    path.unlink()
    if text is not None:
        path.write_text(text, encoding="utf-8")
    with pytest.raises(EnhanceError, match="is no episodes repository"):
        refused({"new-reel": "New_Reel"}, world.eps, world.sdk)


def test_the_pin_is_read_from_the_episodes_pyproject(world):
    assert auto_enhance.pin(world.eps) == git(world.sdk, "rev-parse", "HEAD").strip()


def test_a_folder_that_is_no_library_checkout_is_refused(world, tmp_path):
    for folder in (tmp_path / "missing", world.eps):
        with pytest.raises(EnhanceError, match="no srstudio checkout"):
            refused({"new-reel": "New_Reel"}, world.eps, folder)


def test_without_a_name_the_library_is_the_checkout_this_package_came_from():
    assert auto_enhance.checkout(None) == REPO


def test_the_histories_are_classified_per_repository(world):
    eps, sdk = auto_enhance.histories(world.eps, world.sdk)
    assert (eps.repo, eps.revisions, eps.layout) == (world.eps, "develop", auto_enhance.EPISODES_REPO)
    assert (sdk.repo, sdk.revisions, sdk.layout) == (world.sdk, auto_enhance.pin(world.eps), auto_enhance.SDK_REPO)
    assert "src/srstudio/" in sdk.layout.library and "src/srstudio/" not in eps.layout.library
    assert "tools/" in eps.layout.library and "tools/" in sdk.layout.library


# -- what one commit must be ----------------------------------------------------------------------------------------
def test_no_videos_asks_nothing_of_git(tmp_path):
    assert refused({}, tmp_path, tmp_path) == []


def test_another_videos_enhancement_does_not_count(world):
    commit(world.sdk, message("other-reel"), REAL)
    assert "no commit on" in reasons(world)[0]


def test_a_mention_in_the_body_is_not_a_trailer(world):
    commit(
        world.sdk, "feat: x\n\nEnhances: new-reel\n\nEnhancement-Kind: props is the kind\nnot a trailer block.", REAL
    )
    assert "no commit on" in reasons(world)[0]


STRANDED = "feat: x\n\nWhy.\n\nEnhances: new-reel\nEnhancement-Kind: props\n\nCo-Authored-By: A <a@example.com>"


def test_trailers_stranded_above_the_co_author_are_refused_with_the_reason(world):
    commit(world.sdk, STRANDED, REAL)
    (reason,) = reasons(world)
    assert "does not count" in reason and "middle paragraph" in reason


def test_the_pregate_catches_stranded_trailers_before_the_merge(world):
    git(world.sdk, "checkout", "-q", "-b", "feat/x")
    commit(world.sdk, STRANDED, REAL)
    _, sdk = auto_enhance.histories(world.eps, world.sdk)
    (row,) = auto_enhance.unsound(sdk)
    assert row.slugs == ("new-reel",) and any("middle paragraph" in p for p in row.problems)


def test_one_commit_cannot_pay_for_two_videos(world):
    commit(world.sdk, message(extra="Enhances: other-reel\n"), REAL)
    assert "one commit enhances one video" in reasons(world)[0]


@pytest.mark.parametrize("kind", ["funnier", "PROPS", ""])
def test_a_kind_outside_the_closed_list_is_refused(world, kind):
    commit(world.sdk, message(kind=kind), REAL)
    assert "kind" in reasons(world)[0]


def test_a_commit_with_two_kinds_is_refused(world):
    commit(world.sdk, message(extra="Enhancement-Kind: music\n"), REAL)
    assert "kind" in reasons(world)[0]


def test_a_library_change_needs_a_new_test(world):
    commit(world.sdk, message(), {"src/srstudio/thing.py": "X = 1\n"})
    assert "adds no test" in reasons(world)[0]


def test_a_process_change_needs_a_new_test(world):
    commit(world.eps, message(), {"tools/govern/processes/reel.json": "{}\n"})
    assert "adds no test" in reasons(world)[0]


def test_touching_a_test_without_adding_one_is_not_a_new_test(world):
    commit(world.sdk, "chore: t", {"tests/test_thing.py": "def test_x():\n    assert True\n"})
    files = {"src/srstudio/thing.py": "X = 1\n", "tests/test_thing.py": "def test_x():\n    pass\n"}
    commit(world.sdk, message(), files)
    assert "adds no test" in reasons(world)[0]


def test_a_test_function_outside_tests_does_not_count(world):
    commit(world.sdk, message(), {"src/srstudio/thing.py": "def test_x():\n    pass\n"})
    assert "adds no test" in reasons(world)[0]


def test_a_commit_with_nothing_in_the_process_is_refused(world):
    commit(world.sdk, message(), {"docs/notes.md": "better\n", "tests/test_thing.py": "def test_x():\n    pass\n"})
    assert "changes no library, tool or skill" in reasons(world)[0]


def test_the_reels_own_script_is_not_an_enhancement(world):
    commit(world.sdk, message(), {**REAL, "episodes/new_reel.py": "1\n"})  # the library's history before the split
    assert "the video's own files" in reasons(world)[0]


def test_the_reels_release_is_not_an_enhancement(world):
    commit(world.sdk, message(), {**REAL, "episodes/posts/new_reel.py": "1\n"})
    assert "the video's own files" in reasons(world)[0]


def test_the_pilots_own_folder_is_not_an_enhancement(world):
    commit(world.eps, message(), {**TOOL, "pilots/mind/new-reel/notes.md": "1\n"})
    assert "the video's own files" in reasons(world)[0]


def test_a_shared_episode_tool_is_not_the_reels_own_file(world):
    commit(world.sdk, message(), {**REAL, "episodes/_common.py": "1\n"})
    assert reasons(world) == []


def test_a_skill_rule_needs_its_version_bumped(world):
    skill = auto_enhance.SKILL
    commit(world.eps, "chore: skill", {skill: "schema_version: 1.0.0\nold\n"})
    commit(world.eps, message(kind="comedy"), {skill: "schema_version: 1.0.0\nnew rule\n"})
    assert "bumps no schema_version" in reasons(world)[0]


def test_a_versioned_skill_rule_from_before_the_split_still_counts(world):
    skill = auto_enhance.SKILL
    commit(world.sdk, "chore: skill", {skill: "schema_version: 1.0.0\nold\n"})
    commit(world.sdk, message(kind="comedy"), {skill: "schema_version: 1.1.0\nnew rule\n"})
    assert reasons(world) == []


def test_a_bad_commit_does_not_hide_a_good_one(world):
    commit(world.sdk, message(), {"docs/notes.md": "better\n"})
    commit(world.sdk, message(), REAL)
    commit(world.sdk, message(), {"docs/notes.md": "better still\n"})
    assert reasons(world) == []


def test_a_folder_that_is_no_repository_fails_closed(world, tmp_path):
    sdk = tmp_path / "copy"
    (sdk / "src" / "srstudio").mkdir(parents=True)
    (sdk / "src" / "srstudio" / "__init__.py").write_text("")
    (sdk / ".git").write_text("gitdir: /nowhere\n")
    with pytest.raises(EnhanceError, match="cannot read the history"):
        refused({"new-reel": "New_Reel"}, world.eps, sdk)


def test_a_failed_gate_is_a_delivery_error():
    assert issubclass(EnhanceError, DeliveryError)


def test_a_slow_git_is_cut_off(world, monkeypatch):
    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw["timeout"])

    monkeypatch.setattr(auto_enhance.subprocess, "run", slow)
    with pytest.raises(EnhanceError, match="cannot read the history"):
        refused({"new-reel": "New_Reel"}, world.eps, world.sdk)


# -- the mode -------------------------------------------------------------------------------------------------------
def test_the_mode_defaults_to_on_and_says_it_was_not_read(tmp_path):
    found = setting(tmp_path)
    assert (found.on, found.read, found.path) == (True, False, tmp_path / auto_enhance.SETTINGS)
    assert str(found) == f"on (the default: {tmp_path / auto_enhance.SETTINGS} does not exist)"
    assert enabled(tmp_path) is True


def test_a_mode_read_from_its_file_names_the_file(tmp_path):
    set_mode(tmp_path, on=False)
    found = setting(tmp_path)
    assert (found.on, found.read) == (False, True)
    assert str(found) == f"off (read from {tmp_path / auto_enhance.SETTINGS})"


def test_this_library_ships_no_setting():
    assert setting(REPO).read is False  # the mode is the episodes' (ADR 0220): nothing here can turn it off


def test_off_clears_a_video_and_on_brings_the_gate_back(world):
    set_mode(world.eps, on=False)
    assert enabled(world.eps) is False and refused({"new-reel": "New_Reel"}, world.eps, world.sdk) == []
    set_mode(world.eps, on=True)
    assert enabled(world.eps) is True and reasons(world)


def test_off_asks_nothing_of_git_nor_of_the_library(tmp_path):
    set_mode(tmp_path, on=False)
    assert refused({"new-reel": "New_Reel"}, tmp_path, tmp_path / "no-library") == []


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


def test_the_ledger_lists_every_enhancement_newest_first_with_its_repository(world):
    commit(world.sdk, message(), REAL, date="2026-01-02T00:00:00Z")
    commit(world.eps, message("other-reel"), {"docs/notes.md": "x\n"}, date="2026-01-03T00:00:00Z")
    pin(world)
    rows = auto_enhance.ledgers(auto_enhance.histories(world.eps, world.sdk))
    assert [(r.source, r.slugs, r.kinds, not r.problems) for r in rows] == [
        ("srstudio-episodes", ("other-reel",), ("props",), False),
        ("srstudio", ("new-reel",), ("props",), True),
    ]


def test_every_kind_is_described():
    assert len(auto_enhance.KINDS) >= 10 and all(auto_enhance.KINDS.values())


# -- the command ----------------------------------------------------------------------------------------------------
def enhance(world: World, *args: str) -> int:
    return cli.main(["enhance", *args, "--scripts", str(world.eps / "episodes"), "--sdk", str(world.sdk)])


def test_the_command_says_where_it_read_the_mode_and_shows_both_ledgers(world, capsys):
    commit(world.sdk, message(), REAL)
    commit(world.eps, message("other-reel"), TOOL)
    pin(world)
    set_mode(world.eps, on=True)
    assert enhance(world) == 0
    out = capsys.readouterr().out
    assert f"auto-enhance: on (read from {world.eps / auto_enhance.SETTINGS})" in out
    assert "srstudio-episodes " in out and "other-reel" in out
    assert "\nsrstudio " in out and "new-reel" in out and "props" in out


def test_the_command_never_reports_the_default_as_read(world, capsys):
    assert enhance(world) == 0
    out = capsys.readouterr().out
    assert f"auto-enhance: on (the default: {world.eps / auto_enhance.SETTINGS} does not exist)" in out
    assert "read from" not in out


def test_the_command_finds_the_library_through_srstudio_sdk(world, monkeypatch, capsys):
    commit(world.sdk, message(), REAL)
    pin(world)
    monkeypatch.setenv("SRSTUDIO_SDK", str(world.sdk))
    assert cli.main(["enhance", "--scripts", str(world.eps / "episodes")]) == 0
    assert "new-reel" in capsys.readouterr().out


def test_the_command_outside_an_episodes_repository_reports_no_mode(capsys):
    assert cli.main(["enhance", "--scripts", str(REPO / "episodes"), "--sdk", str(REPO)]) == 2
    captured = capsys.readouterr()
    assert "auto-enhance:" not in captured.out and "is no episodes repository" in captured.err


@pytest.mark.parametrize("action", ["on", "off"])
def test_the_switch_writes_nothing_outside_an_episodes_repository(tmp_path, capsys, action):
    for folder in (REPO, tmp_path):
        assert cli.main(["enhance", action, "--scripts", str(folder / "episodes")]) == 2
        assert not (folder / auto_enhance.SETTINGS).exists()
        assert "is no episodes repository" in capsys.readouterr().err


def test_the_command_lists_the_kinds(world, capsys):
    assert enhance(world, "kinds") == 0
    out = capsys.readouterr().out
    assert all(kind in out for kind in auto_enhance.KINDS)


def test_the_command_turns_the_mode_off_and_on(world, capsys):
    assert enhance(world, "off") == 0
    assert enabled(world.eps) is False
    assert f"auto-enhance: off (read from {world.eps / auto_enhance.SETTINGS})" in capsys.readouterr().out
    assert enhance(world, "on") == 0
    assert enabled(world.eps) is True


def test_the_command_reports_a_broken_setting(world, capsys):
    (world.eps / auto_enhance.SETTINGS).write_text("nope", encoding="utf-8")
    assert enhance(world) == 2
    assert "srstudio enhance:" in capsys.readouterr().err


def test_check_names_a_bad_trailer_while_it_is_still_on_its_branch(world, capsys):
    git(world.eps, "checkout", "-q", "-b", "feat/next")
    commit(world.eps, message(kind="framing"), TOOL)
    assert enhance(world, "check") == 1
    assert "Enhancement-Kind must be one of" in capsys.readouterr().out


def test_check_names_a_bad_trailer_on_the_library_branch_it_is_given(world, capsys):
    git(world.sdk, "checkout", "-q", "-b", "feat/next")
    commit(world.sdk, message(kind="framing"), REAL)
    assert enhance(world, "check") == 1
    out = capsys.readouterr().out
    assert out.startswith("srstudio ") and "Enhancement-Kind must be one of" in out


def test_check_passes_a_sound_trailer_and_leaves_develops_history_alone(world):
    commit(world.sdk, message(slug="old-reel", kind="framing"), REAL)  # already landed, so no branch can fix it
    commit(world.eps, message(slug="old-reel", kind="framing"), TOOL)
    pin(world)
    git(world.eps, "checkout", "-q", "-b", "feat/next")
    other = {"tools/other.py": "Y = 1\n", "tests/test_other.py": "def test_y():\n    assert True\n"}
    commit(world.eps, message(), other)
    assert [auto_enhance.unsound(h) for h in auto_enhance.histories(world.eps, world.sdk)] == [[], []]
    assert enhance(world, "check") == 0

"""The pilots' road to Drive: a folder of finished pilots goes to gdrive:srstudio/pilots/ and can never reach the
folder that posts to @tuxmeme. Everything refused is refused before anything is staged or uploaded; rclone is faked."""

import hashlib
import json
import re
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from srstudio import outbox

REPO = Path(__file__).resolve().parent.parent
FILES = ("cover.jpg", "ig.txt", "vpkg.zip", "sources.md", "notes.md")


@pytest.fixture
def tool(monkeypatch, tmp_path):
    sys.path.insert(0, str(REPO / "episodes"))
    try:
        import publish_pilots
    finally:
        sys.path.pop(0)
    monkeypatch.setattr(publish_pilots.posts, "VIDEOS", {"i-cleaned": "i-cleaned", "the-report": "The_Report"})
    monkeypatch.setattr(publish_pilots, "REPO", tmp_path / "repo")
    publish_pilots.auto_enhance.set_mode(tmp_path / "repo", on=False)  # auto-enhance has its own tests below
    return publish_pilots


class Runner:
    """Records rclone calls and answers with ``codes`` in turn."""

    def __init__(self, *codes):
        self.codes = list(codes)
        self.calls = []

    def __call__(self, cmd, **_):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, self.codes.pop(0), "", "rclone: quota exceeded\n")


def pilot(root: Path, slug: str = "the-tell", package: str = "vpkg.zip") -> Path:
    folder = root / slug
    folder.mkdir(parents=True)
    (folder / f"{slug}.mp4").write_bytes(b"video")
    for name in FILES:
        (folder / (package if name == "vpkg.zip" else name)).write_text(f"{name}\n")
    return folder


@pytest.fixture
def world(tmp_path):
    """The input, and a workspace whose @tuxmeme folders hold something a stray write would change."""
    pilot(tmp_path / "in")
    pilot(tmp_path / "in", "second-pilot")
    for name in ("generated/renders/ig/old-reel/ig.txt", "generated/outbox/outbox.json"):
        (tmp_path / name).parent.mkdir(parents=True)
        (tmp_path / name).write_text("theirs\n")
    return tmp_path


def args(world: Path, *extra: str) -> list[str]:
    return [
        str(world / "in"),
        "--stage", str(world / "generated/pilots/mind"),
        "--deliveries", str(world / "generated/renders/ig"),
        *extra,
    ]  # fmt: skip


def tree(folder: Path) -> dict[str, tuple[bytes | None, int]]:
    """Every path under ``folder`` with its content and modification time."""
    return {str(p): (p.read_bytes() if p.is_file() else None, p.stat().st_mtime_ns) for p in sorted(folder.rglob("*"))}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- the remote: the refusal that keeps a pilot off @tuxmeme ----------------------------------------------------------
@pytest.mark.parametrize(
    "remote",
    [
        "gdrive:srstudio/ready-to-publish",
        "gdrive:/srstudio/ready-to-publish",
        "gdrive:srstudio//ready-to-publish/",
        "gdrive:srstudio/./ready-to-publish",
        "gdrive:srstudio/pilots/../ready-to-publish",
        "gdrive:srstudio/pilots/mind/../../ready-to-publish",
        "gdrive:srstudio/pilots/mind/../../../srstudio/ready-to-publish",
        "gdrive:srstudio/pilots/ready-to-publish",
        "gdrive:srstudio/pilots/mind/Ready-To-Publish",
        "gdrive:srstudio\\ready-to-publish",
        "gdrive:srstudio/pilots\\..\\ready-to-publish",
        " gdrive:srstudio/ready-to-publish",
        "gdrive:srstudio/ready-to-publish ",
    ],
)
def test_ready_to_publish_is_refused_however_it_is_spelled(tool, remote):
    with pytest.raises(tool.PilotError):
        tool.pilots_remote(remote)


@pytest.mark.parametrize(
    "remote",
    [
        "gdrive:",
        "gdrive:srstudio",
        "gdrive:srstudio/pilots",
        "gdrive:srstudio/pilots/",
        "gdrive:srstudio/pilots/..",
        "gdrive:srstudio/pilotsx/mind",
        "gdrive:pilots/mind",
        "gdrive:SRSTUDIO/PILOTS/mind",
        "other:srstudio/pilots/mind",
        "gdrive,root_folder_id=abc:srstudio/pilots/mind",
        ":drive:srstudio/pilots/mind",
        "srstudio/pilots/mind",
        "/srstudio/pilots/mind",
        "",
    ],
)
def test_anything_outside_the_pilots_root_is_refused(tool, remote):
    with pytest.raises(tool.PilotError):
        tool.pilots_remote(remote)


@pytest.mark.parametrize(
    "remote, normal",
    [
        ("gdrive:srstudio/pilots/mind", "gdrive:srstudio/pilots/mind"),
        ("gdrive:/srstudio//pilots/./mind/", "gdrive:srstudio/pilots/mind"),
        ("gdrive:srstudio/pilots/x/../mind", "gdrive:srstudio/pilots/mind"),
    ],
)
def test_rclone_is_given_the_normal_form_that_was_checked(tool, remote, normal):
    assert tool.pilots_remote(remote) == normal


def test_the_default_remote_is_under_the_root(tool):
    assert tool.pilots_remote(tool.REMOTE) == "gdrive:srstudio/pilots/mind"


def test_a_refused_remote_stages_and_uploads_nothing(tool, world, monkeypatch, capsys):
    run = Runner()
    monkeypatch.setattr(tool.outbox, "_run", run)
    assert tool.main(args(world, "--remote", "gdrive:srstudio/pilots/../ready-to-publish")) == 2
    assert run.calls == []
    assert not (world / "generated/pilots").exists()
    assert "ready-to-publish" in capsys.readouterr().err


# -- a pilot folder ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["the-tell.mp4", *FILES])
def test_a_folder_missing_any_file_is_refused_by_name(tool, world, name):
    (world / "in/the-tell" / name).unlink()
    with pytest.raises(tool.PilotError, match=r"the-tell.*" + name.replace(".", r"\.")):
        tool.bundle(world / "in", "the-tell", set())


@pytest.mark.parametrize("name", ["sources.md", "notes.md"])
@pytest.mark.parametrize("text", ["", " \n\t\n"])
def test_an_empty_sources_or_notes_is_refused(tool, world, name, text):
    (world / "in/the-tell" / name).write_text(text)
    with pytest.raises(tool.PilotError, match=rf"the-tell.*{name}"):
        tool.bundle(world / "in", "the-tell", set())


@pytest.mark.parametrize("name", ["the-tell.mp4", "cover.jpg", "ig.txt", "vpkg.zip"])
def test_an_empty_file_of_any_kind_is_refused(tool, world, name):
    (world / "in/the-tell" / name).write_bytes(b"")
    with pytest.raises(tool.PilotError, match="empty"):
        tool.bundle(world / "in", "the-tell", set())


def test_a_linked_file_is_refused(tool, world):
    target = world / "in/the-tell/cover.jpg"
    target.unlink()
    target.symlink_to(world / "in/second-pilot/cover.jpg")
    with pytest.raises(tool.PilotError, match="cover.jpg"):
        tool.bundle(world / "in", "the-tell", set())


@pytest.mark.parametrize(
    "slug", ["a/b", "a\\b", "../the-tell", "..", ".", "/etc", "the-tell/", ".hidden", "", "Upper", "the tell", "a..b"]
)
def test_a_slug_that_is_not_one_plain_name_is_refused(tool, world, slug):
    with pytest.raises(tool.PilotError, match="slug"):
        tool.bundle(world / "in", slug, set())


@pytest.mark.parametrize("slug", ["i-cleaned", "the-report"])
def test_a_released_tuxmeme_slug_is_refused(tool, world, slug):
    pilot(world / "in", slug)
    with pytest.raises(tool.PilotError, match="Okayville"):
        tool.bundle(world / "in", slug, tool.released(world / "generated/renders/ig"))


def test_a_released_video_counts_by_its_slug_its_video_name_and_its_delivery_folder(tool, world):
    assert {"i-cleaned", "the-report", "the_report", "old-reel"} <= tool.released(world / "generated/renders/ig")


def test_a_slug_already_delivered_to_tuxmeme_is_refused_by_the_command(tool, world, capsys):
    (world / "generated/renders/ig/the-tell").mkdir()
    assert tool.main(args(world, "--stage-only")) == 2
    assert "the-tell" in capsys.readouterr().err
    assert not (world / "generated/pilots").exists()


def test_with_no_list_of_released_videos_nothing_can_be_cleared(tool, world, monkeypatch):
    monkeypatch.setattr(tool.posts, "VIDEOS", {})
    with pytest.raises(tool.PilotError, match="released"):
        tool.released(world / "nowhere")


def test_a_versioned_package_is_delivered_as_vpkg_zip(tool, world):
    pilot(world / "in", "third", "third-1.0.2.vpkg.zip")
    (world / "in/third/third-1.0.10.vpkg.zip").write_text("newest\n")
    bundle = tool.bundle(world / "in", "third", set())
    assert dict(zip(bundle.names, (f.name for f in bundle.files), strict=True))["vpkg.zip"] == "third-1.0.10.vpkg.zip"


def test_two_kinds_of_package_are_refused_as_ambiguous(tool, world):
    (world / "in/the-tell/the-tell-1.0.0.vpkg.zip").write_text("other\n")
    with pytest.raises(tool.PilotError, match="package"):
        tool.bundle(world / "in", "the-tell", set())


def test_an_input_with_no_pilots_or_a_stray_file_is_refused(tool, tmp_path):
    (tmp_path / "in").mkdir()
    with pytest.raises(tool.PilotError, match="no pilots"):
        tool.bundles(tmp_path / "in", set())
    (tmp_path / "in/loose.mp4").write_text("x")
    with pytest.raises(tool.PilotError, match="loose.mp4"):
        tool.bundles(tmp_path / "in", set())
    with pytest.raises(tool.PilotError, match="not a folder"):
        tool.bundles(tmp_path / "nowhere", set())


def test_a_file_outside_the_list_is_reported_and_not_delivered(tool, world, monkeypatch, capsys):
    (world / "in/the-tell/draft.mp4").write_text("x")
    assert tool.main(args(world, "--stage-only")) == 0
    assert "the-tell/draft.mp4" in capsys.readouterr().out
    assert not (world / "generated/pilots/mind/the-tell/draft.mp4").exists()


# -- staging ----------------------------------------------------------------------------------------------------------
def test_staging_writes_the_folders_and_a_manifest_of_hashes_beside_them(tool, world):
    (world / "in/second-pilot/vpkg.zip").rename(world / "in/second-pilot/second-pilot-1.0.0.vpkg.zip")
    assert tool.main(args(world, "--stage-only")) == 0
    stage = world / "generated/pilots/mind"
    document = json.loads((stage / tool.MANIFEST).read_text())
    assert set(document) == {"version", "videos"} and document["version"] == outbox.MANIFEST_VERSION
    for slug in ("the-tell", "second-pilot"):
        names = {f"{slug}.mp4", *FILES}
        assert {p.name for p in (stage / slug).iterdir()} == names
        assert document["videos"][slug] == {name: sha(stage / slug / name) for name in names}
    assert not (stage / outbox.MANIFEST).exists()


def test_every_staged_folder_is_700_and_every_file_600(tool, world):
    assert tool.main(args(world, "--stage-only")) == 0
    stage = world / "generated/pilots/mind"
    assert stat.S_IMODE((world / "generated/pilots").stat().st_mode) == 0o700
    assert stat.S_IMODE(stage.stat().st_mode) == 0o700
    for path in stage.rglob("*"):
        assert stat.S_IMODE(path.stat().st_mode) == (0o700 if path.is_dir() else 0o600), path


def test_a_run_writes_nothing_under_the_folders_that_reach_tuxmeme(tool, world, monkeypatch):
    monkeypatch.setattr(tool.outbox, "_run", Runner(0, 0))
    ig, box = world / "generated/renders/ig", world / "generated/outbox"
    before = tree(ig), tree(box), ig.stat().st_mtime_ns, box.stat().st_mtime_ns
    assert tool.main(args(world)) == 0
    assert (tree(ig), tree(box), ig.stat().st_mtime_ns, box.stat().st_mtime_ns) == before


@pytest.mark.parametrize(
    "stage",
    [
        "generated/renders/ig",
        "generated/renders/ig/pilots",
        "generated/outbox",
        "generated/outbox/generated/pilots/mind",
        "generated/renders/ig/generated/pilots/mind",
        "generated/renders",
        "generated",
        "generated/pilots/mind/../../renders/ig",
        "generated/pilots/other",
    ],
)
def test_any_staging_folder_but_generated_pilots_mind_is_refused(tool, world, stage, capsys):
    ig, box = world / "generated/renders/ig", world / "generated/outbox"
    before = tree(ig), tree(box)
    argv = args(world, "--stage-only")
    argv[argv.index("--stage") + 1] = str(world / stage)
    assert tool.main(argv) == 2
    assert "staging folder" in capsys.readouterr().err
    assert (tree(ig), tree(box)) == before


def test_a_link_cannot_carry_the_staging_folder_into_a_watched_one(tool, world, capsys):
    (world / "generated/pilots").mkdir()
    (world / "generated/pilots/mind").symlink_to(world / "generated/renders/ig")
    assert tool.main(args(world, "--stage-only")) == 2
    assert "staging folder" in capsys.readouterr().err


def test_the_input_cannot_overlap_the_staging_folder(tool, world, capsys):
    stage = world / "generated/pilots/mind"
    pilot(stage, "the-tell")
    argv = args(world, "--stage-only")
    argv[0] = str(stage)
    assert tool.main(argv) == 2
    assert "overlap" in capsys.readouterr().err
    assert (stage / "the-tell/notes.md").is_file()


def test_a_refused_pilot_leaves_the_last_stage_as_it_was(tool, world):
    assert tool.main(args(world, "--stage-only")) == 0
    stage = world / "generated/pilots/mind"
    before = tree(stage)
    (world / "in/the-tell/notes.md").write_text("")
    assert tool.main(args(world, "--stage-only")) == 2
    assert tree(stage) == before


# -- the upload -------------------------------------------------------------------------------------------------------
def test_the_upload_copies_then_checks_and_never_deletes(tool, world, monkeypatch):
    run = Runner(0, 0)
    monkeypatch.setattr(tool.outbox, "_run", run)
    assert tool.main(args(world)) == 0
    stage = str(world / "generated/pilots/mind")
    assert run.calls == [
        ["rclone", "copy", stage, "gdrive:srstudio/pilots/mind", "--checksum"],
        ["rclone", "check", stage, "gdrive:srstudio/pilots/mind", "--one-way"],
    ]
    assert not {"sync", "delete", "deletefile", "purge", "move", "--delete-excluded"} & {
        word for call in run.calls for word in call
    }


def test_a_dry_run_stages_and_only_previews(tool, world, monkeypatch):
    run = Runner(0)
    monkeypatch.setattr(tool.outbox, "_run", run)
    assert tool.main(args(world, "--dry-run")) == 0
    assert run.calls == [
        ["rclone", "copy", str(world / "generated/pilots/mind"), tool.REMOTE, "--checksum", "--dry-run"]
    ]
    assert (world / "generated/pilots/mind" / tool.MANIFEST).is_file()


def test_stage_only_uploads_nothing(tool, world, monkeypatch):
    run = Runner()
    monkeypatch.setattr(tool.outbox, "_run", run)
    assert tool.main(args(world, "--stage-only")) == 0
    assert run.calls == []


def test_dry_run_and_stage_only_exclude_each_other(tool, world):
    with pytest.raises(SystemExit):
        tool.main(args(world, "--dry-run", "--stage-only"))


@pytest.mark.parametrize("codes", [(1,), (0, 1)])
def test_a_failed_copy_or_check_is_exit_2_with_rclones_reason(tool, world, monkeypatch, capsys, codes):
    monkeypatch.setattr(tool.outbox, "_run", Runner(*codes))
    assert tool.main(args(world)) == 2
    assert "quota exceeded" in capsys.readouterr().err


# -- the unit that uploads to ready-to-publish ------------------------------------------------------------------------
def watched(unit: str) -> list[Path]:
    """The paths a ``.path`` unit watches, read from its file, under an invented workspace ``/w``."""
    keys = ("PathExists=", "PathExistsGlob=", "PathChanged=", "PathModified=", "DirectoryNotEmpty=")
    lines = (REPO / "tools/systemd" / unit).read_text().splitlines()
    return [Path(line.split("=", 1)[1].replace("%h/worskpace/", "/w/")) for line in lines if line.startswith(keys)]


@pytest.mark.parametrize("unit", ["srstudio-drive.path", "srstudio-catalog.path"])
def test_the_staging_folder_is_outside_every_path_a_unit_watches(tool, unit):
    paths = watched(unit)
    assert paths
    stage = Path("/w") / tool.STAGE
    for path in paths:
        assert not stage.is_relative_to(path) and not path.is_relative_to(stage), path


def test_the_drive_unit_watches_the_delivery_folder_this_tool_stays_out_of():
    assert Path("/w/generated/renders/ig") in watched("srstudio-drive.path")


def test_the_tool_is_not_wired_to_any_unit():
    for unit in (REPO / "tools/systemd").iterdir():
        assert "publish_pilots" not in unit.read_text(), unit


class Manifest:
    """Answers rclone's ``cat`` with ``text`` (or ``code``), and every other call with success."""

    def __init__(self, text="", code=0):
        self.text, self.code, self.calls = text, code, []

    def __call__(self, cmd, **_):
        self.calls.append(cmd)
        if cmd[1] == "cat":
            return subprocess.CompletedProcess(cmd, self.code, self.text, "rclone: broken\n")
        return subprocess.CompletedProcess(cmd, 0, "", "")


def gate_on(tool, monkeypatch, answer, drift=()):
    tool.auto_enhance.set_mode(tool.REPO, on=True)
    asked = {}

    def refused(videos, repo):
        asked.update(videos)
        return list(drift)

    monkeypatch.setattr(tool.auto_enhance, "refused", refused)
    monkeypatch.setattr(tool.outbox, "_run", answer)
    return asked


def test_a_new_pilot_without_an_enhancement_is_refused_before_anything_is_staged(tool, world, monkeypatch, capsys):
    drift = [outbox_drift("the-tell")]
    gate_on(tool, monkeypatch, Manifest(code=3), drift)
    assert tool.main(args(world)) == 2
    assert "the-tell: no enhancement" in capsys.readouterr().err
    assert not (world / "generated/pilots/mind").exists()


def outbox_drift(name):
    from srstudio.social import Drift

    return Drift(name, "no enhancement")


def test_a_pilot_already_on_drive_owes_no_enhancement(tool, world, monkeypatch):
    text = json.dumps({"version": "1.0.0", "videos": {"the-tell": {}}})
    asked = gate_on(tool, monkeypatch, Manifest(text))
    assert tool.main(args(world)) == 0
    assert asked == {"second-pilot": "second-pilot"}


def test_the_first_delivery_of_all_owes_one_for_every_pilot(tool, world, monkeypatch):
    asked = gate_on(tool, monkeypatch, Manifest(code=3))
    assert tool.main(args(world)) == 0
    assert set(asked) == {"the-tell", "second-pilot"}


@pytest.mark.parametrize("text", ["not json", "[]", '{"version": "1.0.0"}'])
def test_an_unreadable_drive_manifest_fails_closed(tool, world, monkeypatch, capsys, text):
    gate_on(tool, monkeypatch, Manifest(text))
    assert tool.main(args(world)) == 2
    assert "manifest" in capsys.readouterr().err


def test_a_failed_read_of_drive_fails_closed(tool, world, monkeypatch, capsys):
    gate_on(tool, monkeypatch, Manifest(code=1))
    assert tool.main(args(world)) == 2
    assert "rclone: broken" in capsys.readouterr().err


def test_rclone_absent_fails_closed(tool, world, monkeypatch, capsys):
    def absent(cmd, **_):
        raise FileNotFoundError(cmd[0])

    gate_on(tool, monkeypatch, absent)
    assert tool.main(args(world)) == 2
    assert "rclone" in capsys.readouterr().err


def test_auto_enhance_off_reads_nothing_and_just_delivers(tool, world, monkeypatch, capsys):
    run = Manifest()
    monkeypatch.setattr(tool.outbox, "_run", run)
    assert tool.main(args(world)) == 0
    assert not [c for c in run.calls if c[1] == "cat"]
    assert "auto-enhance off" in capsys.readouterr().out


# -- series: each has its own stage and remote, and neither reaches the other ------------------------------------------
def maps_args(world: Path, *extra: str) -> list[str]:
    argv = args(world, "--series", "maps", *extra)
    argv[argv.index("--stage") + 1] = str(world / "generated/pilots/maps")
    return argv


def test_the_maps_series_stages_in_its_own_folder_and_pushes_to_its_own_remote(tool, world, monkeypatch):
    runner = Runner(0, 0)
    monkeypatch.setattr(tool.outbox, "_run", runner)
    assert tool.main(maps_args(world)) == 0
    assert (world / "generated/pilots/maps/the-tell/the-tell.mp4").is_file()
    assert not (world / "generated/pilots/mind").exists()
    assert "gdrive:srstudio/pilots/maps" in runner.calls[0]
    assert all("gdrive:srstudio/pilots/mind" not in call for call in runner.calls)


def test_the_default_series_stays_mind(tool, world, monkeypatch):
    runner = Runner(0, 0)
    monkeypatch.setattr(tool.outbox, "_run", runner)
    assert tool.main(args(world)) == 0
    assert (world / "generated/pilots/mind/the-tell/the-tell.mp4").is_file()
    assert "gdrive:srstudio/pilots/mind" in runner.calls[0]


def test_each_series_defaults_to_its_own_stage_and_remote(tool):
    assert (tool.stage_of("mind"), tool.remote_of("mind")) == (tool.STAGE, tool.REMOTE)
    assert tool.stage_of("maps") == Path("generated/pilots/maps")
    assert tool.remote_of("maps") == "gdrive:srstudio/pilots/maps"
    assert tool.stage_of("news") == Path("generated/pilots/news")
    assert tool.remote_of("news") == "gdrive:srstudio/pilots/news"


@pytest.mark.parametrize(
    "series, remote",
    [
        ("maps", "gdrive:srstudio/pilots/mind"),
        ("mind", "gdrive:srstudio/pilots/maps"),
        ("maps", "gdrive:srstudio/pilots/maps/../mind"),
        ("mind", "gdrive:srstudio/pilots/other"),
        ("maps", "gdrive:srstudio/pilots"),
        ("maps", "gdrive:srstudio/ready-to-publish"),
        ("maps", "gdrive:srstudio/pilots/maps/ready-to-publish"),
    ],
)
def test_a_remote_of_another_series_is_refused(tool, series, remote):
    with pytest.raises(tool.PilotError):
        tool.pilots_remote(remote, series)


def test_a_folder_below_a_series_remote_stays_in_the_series(tool):
    assert tool.pilots_remote("gdrive:srstudio/pilots/maps/round-2", "maps") == "gdrive:srstudio/pilots/maps/round-2"


def test_the_stage_of_another_series_is_refused_before_anything_is_written(tool, world, capsys):
    mind_stage = world / "generated/pilots/mind"
    assert tool.main(args(world, "--series", "maps", "--stage-only")) == 2  # args() points --stage at mind
    assert "staging folder" in capsys.readouterr().err
    assert not mind_stage.exists()
    assert tool.main([*args(world, "--stage-only"), "--stage", str(world / "generated/pilots/maps")]) == 2
    assert "staging folder" in capsys.readouterr().err
    assert not (world / "generated/pilots/maps").exists()


def test_a_remote_of_another_series_stages_and_uploads_nothing(tool, world, monkeypatch, capsys):
    runner = Runner()
    monkeypatch.setattr(tool.outbox, "_run", runner)
    assert tool.main(maps_args(world, "--remote", "gdrive:srstudio/pilots/mind")) == 2
    assert not runner.calls
    assert not (world / "generated/pilots/maps").exists()


def test_an_unknown_series_is_refused(tool, world):
    with pytest.raises(SystemExit):
        tool.main(args(world, "--series", "ready-to-publish"))
    with pytest.raises(tool.PilotError):
        tool.stage_of("other")


def test_a_pilot_of_another_series_cannot_ride_this_one(tool, world, capsys):
    (tool.REPO / "pilots/mind/the-tell").mkdir(parents=True)
    assert tool.main(maps_args(world, "--stage-only")) == 2
    assert "the-tell belongs to the mind series" in capsys.readouterr().err
    assert not (world / "generated/pilots/maps").exists()


def test_a_pilot_of_its_own_series_passes(tool, world):
    (tool.REPO / "pilots/maps/the-tell").mkdir(parents=True)
    assert tool.main(maps_args(world, "--stage-only")) == 0


def test_the_released_list_still_binds_the_maps_series(tool, world, capsys):
    pilot(world / "in", "i-cleaned")
    assert tool.main(maps_args(world, "--stage-only")) == 2
    assert "released" in capsys.readouterr().err


# -- the comedy floor: news owes two scores, Mind and Maps owe none (ADR 0064) -----------------------------------------
def news_args(world: Path, *extra: str) -> list[str]:
    argv = args(world, "--series", "news", *extra)
    argv[argv.index("--stage") + 1] = str(world / "generated/pilots/news")
    return argv


def scored(world: Path, slug: str, *lines: str) -> None:
    (world / "in" / slug / "notes.md").write_text("\n".join(("---", f"pilot: {slug}", *lines, "---", "", "# Notes\n")))


def both_scored(world: Path, author: int = 15, reviewer: int = 14) -> None:
    for slug in ("the-tell", "second-pilot"):
        scored(world, slug, f"comedy-author: {author}", f"comedy-reviewer: {reviewer}")


def test_only_news_owes_the_floor(tool):
    assert set(tool.SERIES) - tool.NOT_COMEDY == {"news"}
    assert tool.NOT_COMEDY == {"mind", "maps"}


def test_scored_news_stages_in_its_own_folder_pushes_to_its_own_remote_and_never_reads_drive(tool, world, monkeypatch):
    both_scored(world)
    runner = Runner(0, 0)
    monkeypatch.setattr(tool.outbox, "_run", runner)
    assert tool.main(news_args(world)) == 0
    assert (world / "generated/pilots/news/the-tell/the-tell.mp4").is_file()
    assert [call[1] for call in runner.calls] == ["copy", "check"]
    assert all("gdrive:srstudio/pilots/news" in call for call in runner.calls)


@pytest.mark.parametrize(
    "lines, says",
    [
        ((), "the-tell: .*comedy-author is missing"),
        (("comedy-author: 15",), "the-tell: .*comedy-reviewer is missing"),
        (("comedy-reviewer: 15",), "the-tell: .*comedy-author is missing"),
        (("comedy-author: 15", "comedy-reviewer: 14/20"), "the-tell: .*comedy-reviewer .*not a whole number"),
        (("comedy-author: 15", "comedy-reviewer: 21"), "the-tell: .*comedy-reviewer 21 is not between 0 and 20"),
        (("comedy-author: 15", "comedy-reviewer: 13"), "the-tell: .*comedy score 13 .*below the floor of 14"),
        (("comedy-author: 13", "comedy-reviewer: 20"), "the-tell: .*comedy score 13 .*below the floor of 14"),
    ],
)
def test_news_short_of_the_floor_stages_and_uploads_nothing(tool, world, monkeypatch, capsys, lines, says):
    both_scored(world)
    scored(world, "the-tell", *lines)
    answer = Manifest(code=3)  # no manifest on Drive yet: everything is new
    monkeypatch.setattr(tool.outbox, "_run", answer)
    assert tool.main(news_args(world)) == 2
    err = capsys.readouterr().err
    assert re.search(says, err), err
    assert "second-pilot" not in err
    assert [call[1] for call in answer.calls] == ["cat"]
    assert not (world / "generated/pilots").exists()


def test_notes_that_are_not_text_are_refused_for_news(tool, world, monkeypatch, capsys):
    both_scored(world)
    (world / "in/the-tell/notes.md").write_bytes(b"\xff\xfe not text\n")
    monkeypatch.setattr(tool.outbox, "_run", Manifest(code=3))
    assert tool.main(news_args(world, "--stage-only")) == 2
    assert "the-tell" in capsys.readouterr().err
    assert not (world / "generated/pilots").exists()


def test_news_already_on_drive_owes_no_score_and_a_new_one_still_does(tool, world, monkeypatch, capsys):
    text = json.dumps({"version": "1.0.0", "videos": {"the-tell": {}}})
    monkeypatch.setattr(tool.outbox, "_run", Manifest(text))
    assert tool.main(news_args(world, "--stage-only")) == 2
    err = capsys.readouterr().err
    assert "second-pilot" in err and "the-tell" not in err
    both_scored(world)
    scored(world, "the-tell", "comedy-author: 1", "comedy-reviewer: 1")
    assert tool.main(news_args(world, "--stage-only")) == 0


@pytest.mark.parametrize("answer", [Manifest("not json"), Manifest(code=1)])
def test_a_drive_that_cannot_be_read_clears_no_short_pilot(tool, world, monkeypatch, capsys, answer):
    monkeypatch.setattr(tool.outbox, "_run", answer)
    assert tool.main(news_args(world, "--stage-only")) == 2
    assert not (world / "generated/pilots").exists()


@pytest.mark.parametrize("series", ["mind", "maps"])
@pytest.mark.parametrize("lines", [(), ("comedy-author: 2", "comedy-reviewer: 2"), ("comedy-author: nonsense",)])
def test_mind_and_maps_are_exempt_whatever_their_notes_say(tool, world, monkeypatch, series, lines):
    scored(world, "the-tell", *lines)
    runner = Runner()
    monkeypatch.setattr(tool.outbox, "_run", runner)
    argv = args(world, "--series", series, "--stage-only")
    argv[argv.index("--stage") + 1] = str(world / "generated/pilots" / series)
    assert tool.main(argv) == 0
    assert runner.calls == []
    assert (world / "generated/pilots" / series / "the-tell/the-tell.mp4").is_file()


def test_a_series_added_later_owes_the_floor_until_someone_says_otherwise(tool, world, monkeypatch):
    monkeypatch.setattr(tool, "SERIES", (*tool.SERIES, "sport"))
    monkeypatch.setattr(tool.outbox, "_run", Manifest(code=3))
    with pytest.raises(tool.PilotError, match="comedy floor refuses"):
        tool.unfunny(tool.bundles(world / "in", set()), "sport", "gdrive:srstudio/pilots/sport", "rclone")


def test_an_unknown_series_is_refused_with_scores_in_order(tool, world):
    both_scored(world)
    with pytest.raises(SystemExit):
        tool.main(args(world, "--series", "sport", "--stage-only"))
    assert not (world / "generated/pilots").exists()

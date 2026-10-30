"""The outbox: the videos that passed the publish gate, bundled with their caption, cover and package, and pushed."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from srstudio.outbox import MANIFEST, NO_PACKAGE, Bundle, OutboxError, latest_package, push, ready, stage
from srstudio.social import MANIFEST as DELIVERY
from srstudio.social import Item, fingerprint, publish
from support.package import project
from support.social import FONT, engine, post, tall

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture
def delivered(tmp_path):
    """Two videos through the publish gate, and the package of each."""
    renders = tmp_path / "renders"
    renders.mkdir()
    items = {"a": Item(post("A"), tall(renders / "a.mp4")), "b": Item(post("B"), tall(renders / "b.mp4"))}
    out = tmp_path / "ig"
    publish(items, out, font=FONT, engine=engine())
    packages = {"a": tmp_path / "a-1.0.0.vpkg.zip", "b": tmp_path / "b-2.0.0.vpkg.zip"}
    for path in packages.values():
        path.write_bytes(b"PK\x05\x06" + b"\0" * 18)
    return items, out, packages


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# -- what is ready -------------------------------------------------------------------------------------------------
def test_every_current_delivery_is_a_bundle_of_video_caption_cover_and_package(delivered):
    items, out, pk = delivered
    bundles, drift = ready(items, out, font=FONT, packages=pk)
    assert drift == []
    assert bundles == [
        Bundle("a", (items["a"][1], out / "a" / "ig.txt", out / "a" / "cover.jpg", pk["a"])),
        Bundle("b", (items["b"][1], out / "b" / "ig.txt", out / "b" / "cover.jpg", pk["b"])),
    ]


def test_a_video_without_its_package_is_held_back(delivered):
    items, out, pk = delivered
    bundles, drift = ready(items, out, font=FONT, packages={"a": pk["a"]})
    assert [b.name for b in bundles] == ["a"]
    assert [str(d) for d in drift] == [f"b: {NO_PACKAGE}"]
    bundles, drift = ready(items, out, font=FONT)
    assert bundles == [] and [d.name for d in drift] == ["a", "b"]


def test_a_drifted_video_is_left_out_and_reported(delivered):
    items, out, pk = delivered
    items["b"][1].write_bytes(items["b"][1].read_bytes() + b"\0")  # re-rendered after its cover was made
    bundles, drift = ready(items, out, font=FONT, packages=pk)
    assert [b.name for b in bundles] == ["a"]
    assert [d.name for d in drift] == ["b"]


def test_a_frozen_video_is_ready_at_the_drawing_it_was_frozen_at(delivered):
    items, out, pk = delivered
    items = {**items, "b": Item(post("B2"), items["b"].video)}  # its post changed after it was published
    bundles, drift = ready(items, out, font=FONT, packages=pk)
    assert [b.name for b in bundles] == ["a"] and [d.name for d in drift] == ["b"]
    accepted = fingerprint(post("B2"), items["b"].video, FONT)
    bundles, drift = ready(items, out, font=FONT, packages=pk, frozen={"b": accepted})
    assert [b.name for b in bundles] == ["a", "b"] and drift == []


def test_an_untrustworthy_delivery_manifest_makes_nothing_ready(delivered):
    items, out, _ = delivered
    (out / DELIVERY).write_text("{")
    bundles, drift = ready(items, out, font=FONT)
    assert bundles == [] and [d.name for d in drift] == ["*"]


def test_a_package_named_for_a_video_must_exist(delivered, tmp_path):
    items, out, _ = delivered
    with pytest.raises(OutboxError, match="package"):
        ready(items, out, font=FONT, packages={"a": tmp_path / "missing.vpkg.zip"})
    with pytest.raises(OutboxError, match="not published"):
        ready(items, out, font=FONT, packages={"nobody": tmp_path / "x.vpkg.zip"})


def test_the_latest_package_version_wins_by_number_not_by_text(tmp_path):
    for name in ("show-1.9.0", "show-1.10.0", "show-0.1.0", "show-2.0", "showcase-9.0.0", "show-1.10.0.tmp"):
        (tmp_path / f"{name}.vpkg.zip").write_bytes(b"")
    assert latest_package(tmp_path, "show") == tmp_path / "show-1.10.0.vpkg.zip"
    assert latest_package(tmp_path, "absent") is None
    assert latest_package(tmp_path / "no-such-folder", "show") is None


# -- the staged folder ---------------------------------------------------------------------------------------------
def test_stage_writes_one_private_folder_per_video_and_a_manifest_of_hashes(delivered, tmp_path):
    items, out, pk = delivered
    bundles, _ = ready(items, out, font=FONT, packages=pk)
    folder = tmp_path / "outbox"
    manifest = stage(bundles, folder)
    assert manifest == folder / MANIFEST
    assert sorted(p.name for p in (folder / "a").iterdir()) == ["a-1.0.0.vpkg.zip", "a.mp4", "cover.jpg", "ig.txt"]
    assert sorted(p.name for p in (folder / "b").iterdir()) == ["b-2.0.0.vpkg.zip", "b.mp4", "cover.jpg", "ig.txt"]
    data = json.loads(manifest.read_text())
    assert data["version"] == "1.0.0"
    assert data["videos"]["a"]["a.mp4"] == sha(items["a"][1]) and data["videos"]["a"]["ig.txt"] == sha(
        out / "a" / "ig.txt"
    )
    for path in [folder, *folder.rglob("*")]:
        assert path.stat().st_mode & 0o777 == (0o700 if path.is_dir() else 0o600), path
    assert items["a"][1].stat().st_nlink == 1  # copies, not links: the staged file never aliases the render


def test_restaging_holds_exactly_what_is_ready_now(delivered, tmp_path):
    items, out, pk = delivered
    folder = tmp_path / "outbox"
    stage(ready(items, out, font=FONT, packages=pk)[0], folder)
    items["b"][1].write_bytes(items["b"][1].read_bytes() + b"\0")
    stage(ready(items, out, font=FONT, packages=pk)[0], folder)
    assert sorted(p.name for p in folder.iterdir()) == ["a", MANIFEST]
    assert list(json.loads((folder / MANIFEST).read_text())["videos"]) == ["a"]


def test_restaging_keeps_the_operators_dot_files_and_nothing_else_of_theirs(delivered, tmp_path):
    """A dot-file the operator keeps in the outbox (``.ignore``) survives every restage, byte for byte and mode, so
    the next push uploads it with the videos."""
    items, out, pk = delivered
    folder = tmp_path / "outbox"
    stage(ready(items, out, font=FONT, packages=pk)[0], folder)
    note = folder / ".ignore"
    note.write_text("/somewhere/outbox/b")
    note.chmod(0o664)
    (folder / ".cache").mkdir()  # a dot-folder is not the operator's note: it goes with the old outbox
    stage(ready(items, out, font=FONT, packages=pk)[0], folder)
    assert note.read_text() == "/somewhere/outbox/b" and note.stat().st_mode & 0o777 == 0o664
    assert sorted(p.name for p in folder.iterdir()) == [".ignore", "a", "b", MANIFEST]
    assert ".ignore" not in json.loads((folder / MANIFEST).read_text())["videos"]


def test_stage_refuses_a_folder_it_did_not_make_and_leaves_it_alone(delivered, tmp_path):
    items, out, pk = delivered
    folder = tmp_path / "mine"
    folder.mkdir()
    (folder / "notes.txt").write_text("keep me")
    with pytest.raises(OutboxError, match="not an outbox"):
        stage(ready(items, out, font=FONT, packages=pk)[0], folder)
    assert (folder / "notes.txt").read_text() == "keep me" and not (tmp_path / "mine.tmp").exists()


def test_two_bundles_with_one_name_or_a_bad_name_are_refused(tmp_path):
    clip = tmp_path / "a.mp4"
    clip.write_bytes(b"v")
    with pytest.raises(OutboxError, match="twice"):
        stage([Bundle("a", (clip,)), Bundle("a", (clip,))], tmp_path / "outbox")
    with pytest.raises(OutboxError, match="name"):
        stage([Bundle("../up", (clip,))], tmp_path / "outbox")
    with pytest.raises(OutboxError, match="twice"):
        stage([Bundle("a", (clip, clip))], tmp_path / "outbox")
    assert not (tmp_path / "outbox").exists()


# -- pushing -------------------------------------------------------------------------------------------------------
class Runner:
    """Records rclone calls and answers with ``codes`` in turn."""

    def __init__(self, *codes: int):
        self.codes, self.calls = list(codes), []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        return subprocess.CompletedProcess(cmd, self.codes.pop(0), "", "rclone: quota exceeded\n")


def test_push_copies_then_checks_every_file_arrived(tmp_path):
    run = Runner(0, 0)
    push(tmp_path, "gdrive:srstudio/ready", rclone="rclone", run=run)
    assert run.calls == [
        ["rclone", "copy", str(tmp_path), "gdrive:srstudio/ready", "--checksum"],
        ["rclone", "check", str(tmp_path), "gdrive:srstudio/ready", "--one-way"],
    ]


def test_a_dry_run_only_previews_the_copy(tmp_path):
    run = Runner(0)
    push(tmp_path, "gdrive:x", run=run, dry_run=True)
    assert run.calls == [["rclone", "copy", str(tmp_path), "gdrive:x", "--checksum", "--dry-run"]]


def test_a_failed_copy_or_check_is_a_typed_error_with_rclones_reason(tmp_path):
    with pytest.raises(OutboxError, match="copy.*quota exceeded"):
        push(tmp_path, "gdrive:x", run=Runner(1))
    with pytest.raises(OutboxError, match="check.*quota exceeded"):
        push(tmp_path, "gdrive:x", run=Runner(0, 1))


@pytest.mark.parametrize("remote", ["", "gdrive", "/local/path", "-x:foo", "g drive:x"])
def test_push_refuses_anything_but_a_named_remote(tmp_path, remote):
    run = Runner()
    with pytest.raises(OutboxError, match="remote"):
        push(tmp_path, remote, run=run)
    assert run.calls == []


def test_push_refuses_a_missing_rclone(tmp_path):
    with pytest.raises(OutboxError, match="rclone"):
        push(tmp_path, "gdrive:x", rclone=str(tmp_path / "no-rclone"))


# -- the command ---------------------------------------------------------------------------------------------------
def command(monkeypatch, items, frozen=None):
    """``episodes/publish_drive.py`` with the posts replaced by ``items`` and the frozen releases by ``frozen``."""
    sys.path.insert(0, str(EPISODES))
    try:
        import publish_drive
    finally:
        sys.path.remove(str(EPISODES))
    monkeypatch.setattr(publish_drive.posts, "items", lambda renders: items)
    monkeypatch.setattr(publish_drive.posts, "font_file", lambda folder: FONT)
    monkeypatch.setattr(publish_drive.posts, "FROZEN", dict(frozen or {}))
    return publish_drive


def where(out, tmp_path, received):
    return [
        *("--deliveries", str(out), "--renders", str(tmp_path), "--fonts", str(tmp_path)),
        *("--packages", str(received), "--episodes", str(tmp_path / "episodes"), "--vpkg", str(tmp_path / "vpkg")),
        *("--outbox", str(tmp_path / "outbox")),
    ]


def test_the_command_stages_what_is_ready_and_pushes_it(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    publish_drive = command(monkeypatch, items)
    run = Runner(0, 0)
    monkeypatch.setattr(publish_drive.outbox, "_run", run)
    folder = tmp_path / "outbox"
    args = where(out, tmp_path, tmp_path)  # the fixture's packages are in tmp_path
    assert publish_drive.main([*args, "--remote", "gdrive:test"]) == 0
    assert sorted(p.name for p in folder.iterdir()) == ["a", "b", MANIFEST]
    assert [c[1] for c in run.calls] == ["copy", "check"]
    assert "2 ready, 0 held back" in capsys.readouterr().out
    items["b"][1].write_bytes(items["b"][1].read_bytes() + b"\0")
    assert publish_drive.main([*args, "--stage-only"]) == 1  # something was held back
    printed = capsys.readouterr().out
    assert "b: the video was re-rendered" in printed and "1 ready, 1 held back" in printed
    assert len(run.calls) == 2  # --stage-only pushes nothing


def test_the_command_stages_a_frozen_video_at_the_drawing_it_was_frozen_at(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    items = {**items, "b": Item(post("B2"), items["b"].video)}  # its post changed after it was published
    args = [*where(out, tmp_path, tmp_path), "--stage-only"]
    assert command(monkeypatch, items).main(args) == 1
    assert "1 ready, 1 held back" in capsys.readouterr().out
    accepted = fingerprint(post("B2"), items["b"].video, FONT)
    assert command(monkeypatch, items, frozen={"b": accepted}).main(args) == 0
    assert "2 ready, 0 held back" in capsys.readouterr().out


def test_the_command_packs_each_original_episode_and_holds_back_one_it_cannot_pack(
    delivered, tmp_path, monkeypatch, capsys
):
    items, out, _ = delivered
    publish_drive = command(monkeypatch, items)
    project(tmp_path, "a")  # an original episode: tmp_path/episodes/a/a.scene.xml
    broken = tmp_path / "episodes" / "b"
    broken.mkdir()
    (broken / "b.scene.xml").write_text("<scene>not a scene")
    received = tmp_path / "received"
    received.mkdir()
    assert publish_drive.main([*where(out, tmp_path, received), "--stage-only"]) == 1
    printed = capsys.readouterr().out
    assert "not packed: b: " in printed and f"held back: b: {NO_PACKAGE}" in printed
    assert "1 ready, 1 held back" in printed
    staged = sorted(p.name for p in (tmp_path / "outbox" / "a").iterdir())
    assert staged == ["a-1.0.0.vpkg.zip", "a.mp4", "cover.jpg", "ig.txt"]
    assert (tmp_path / "vpkg" / "a-1.0.0.vpkg.zip").is_file()


def test_a_received_package_wins_over_packing_the_project(delivered, tmp_path, monkeypatch, capsys):
    items, out, pk = delivered
    publish_drive = command(monkeypatch, items)
    project(tmp_path, "a")
    assert publish_drive.main([*where(out, tmp_path, tmp_path), "--stage-only"]) == 0
    assert not (tmp_path / "vpkg").exists()  # nothing was packed: the fixture's packages were received
    assert (tmp_path / "outbox" / "a" / pk["a"].name).is_file()


def test_the_command_reports_a_failed_upload_as_exit_2_not_a_traceback(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    publish_drive = command(monkeypatch, items)
    monkeypatch.setattr(publish_drive.outbox, "_run", Runner(1))
    assert publish_drive.main(where(out, tmp_path, tmp_path)) == 2
    assert "rclone copy failed (1): rclone: quota exceeded" in capsys.readouterr().err


def test_a_failed_stage_keeps_the_previous_outbox_and_leaves_no_scratch(delivered, tmp_path, monkeypatch):
    items, out, pk = delivered
    folder = tmp_path / "outbox"
    stage(ready(items, out, font=FONT, packages=pk)[0], folder)
    before = (folder / MANIFEST).read_text()
    with pytest.raises(FileNotFoundError):
        stage([Bundle("a", (tmp_path / "vanished.mp4",))], folder)
    import srstudio.outbox as box

    def corrupt(src, dst):
        Path(dst).write_bytes(b"not the render")

    monkeypatch.setattr(box.shutil, "copyfile", corrupt)
    with pytest.raises(OutboxError, match="changed while it was staged"):
        stage(ready(items, out, font=FONT, packages=pk)[0], folder)
    assert (folder / MANIFEST).read_text() == before
    assert sorted(p.name for p in tmp_path.iterdir()) == [
        "a-1.0.0.vpkg.zip",
        "b-2.0.0.vpkg.zip",
        "ig",
        "outbox",
        "renders",
    ]

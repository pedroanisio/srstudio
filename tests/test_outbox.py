"""The outbox: the videos that passed the publish gate, bundled with their caption, cover and package, and pushed."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from srstudio import show_numbers
from srstudio.outbox import (
    AB_NAME,
    EPISODE_NAME,
    MANIFEST,
    NO_PACKAGE,
    Arm,
    Bundle,
    OutboxError,
    delivered_names,
    latest_package,
    push,
    ready,
    stage,
)
from srstudio.show_numbers import Claim
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


def test_a_video_in_an_ab_test_is_staged_with_its_arm_in_ab_json(delivered, tmp_path):
    """The posting job reads a reel's A/B arm from ``ab.json`` beside the video; it is hashed like every staged
    file, and a video outside a test gets no ``ab.json``."""
    items, out, pk = delivered
    bundles, _ = ready(items, out, font=FONT, packages=pk, ab={"a": Arm("sp-hook_motion", "b")})
    assert [b.ab for b in bundles] == [Arm("sp-hook_motion", "b"), None]
    folder = tmp_path / "outbox"
    manifest = stage(bundles, folder)
    assert json.loads((folder / "a" / AB_NAME).read_text()) == {"test": "sp-hook_motion", "arm": "b"}
    assert (folder / "a" / AB_NAME).stat().st_mode & 0o777 == 0o600
    assert not (folder / "b" / AB_NAME).exists()
    assert json.loads(manifest.read_text())["videos"]["a"][AB_NAME] == sha(folder / "a" / AB_NAME)


@pytest.mark.parametrize(
    ("arm", "document"),
    [
        (Arm("sp-hook_motion", "a"), {"test": "sp-hook_motion", "arm": "a"}),
        (Arm("sp-hook_motion", "a", "a"), {"test": "sp-hook_motion", "arm": "a", "recipient": "a"}),
        (
            Arm("sp-hook_motion", "a", "b", "family"),
            {"test": "sp-hook_motion", "arm": "a", "recipient": "b", "to": "family"},
        ),
        (
            Arm("sp-length", "short", also=(("sp-speakers", "a"),)),
            {"test": "sp-length", "arm": "short", "also": [{"test": "sp-speakers", "arm": "a"}]},
        ),
        (
            Arm("sp-speakers", "b", also=(("sp-length", "natural"),)),
            {"test": "sp-speakers", "arm": "b", "also": [{"test": "sp-length", "arm": "natural"}]},
        ),
    ],
)
def test_both_tests_go_in_one_ab_json(delivered, tmp_path, arm, document):
    items, out, pk = delivered
    bundles, _ = ready(items, out, font=FONT, packages=pk, ab={"a": arm})
    folder = tmp_path / "staged"
    stage(bundles, folder)
    assert json.loads((folder / "a" / AB_NAME).read_text()) == document


def test_a_release_with_one_test_keeps_its_ab_json_byte_for_byte(delivered, tmp_path):
    items, out, pk = delivered
    bundles, _ = ready(items, out, font=FONT, packages=pk, ab={"a": Arm("sp-hook_motion", "a")})
    stage(bundles, tmp_path / "staged")
    assert (tmp_path / "staged" / "a" / AB_NAME).read_text() == '{"test": "sp-hook_motion", "arm": "a"}\n'


@pytest.mark.parametrize(
    ("ab", "match"),
    [
        ({"nobody": Arm("sp-hook_motion", "a")}, "not published"),
        ({"a": Arm("sp-length", "a")}, "arm 'a'"),
        ({"a": Arm("sp-hook_motion", "short")}, "arm 'short'"),
        ({"a": Arm("sp-length", "short", also=(("sp-speakers", "c"),))}, "arm 'c'"),
        ({"a": Arm("sp-speakers", "a", also=(("sp-length", "b"),))}, "arm 'b'"),
        ({"a": Arm("sp-length", "short", also=(("", "a"),))}, "test"),
        ({"a": Arm("sp-length", "short", also=(("sp-length", "natural"),))}, "twice"),
        ({"a": Arm("sp-length", "short", also=(("sp-speakers", "a"), ("sp-speakers", "b")))}, "twice"),
        ({"a": Arm("sp-hook_motion", "c")}, "arm"),
        ({"a": Arm("", "a")}, "test"),
        ({"a": Arm("sp-hook_motion", "a", "c")}, "recipient"),
        ({"a": Arm("sp-hook_motion", "a", "b")}, "names who"),
        ({"a": Arm("sp-hook_motion", "a", "a", "family")}, "names who"),
        ({"a": Arm("sp-hook_motion", "a", to="family")}, "names who"),
    ],
)
def test_an_ab_arm_must_name_a_published_video_a_test_and_arm_a_or_b(delivered, ab, match):
    items, out, pk = delivered
    with pytest.raises(OutboxError, match=match):
        ready(items, out, font=FONT, packages=pk, ab=ab)


def test_stage_refuses_a_bundle_whose_own_file_is_named_ab_json(tmp_path):
    clash = tmp_path / AB_NAME
    clash.write_text("{}")
    with pytest.raises(OutboxError, match=AB_NAME):
        stage([Bundle("a", (clash,), ("sp-hook_motion", "a"))], tmp_path / "outbox")


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
    it stays beside the outbox it was left in; :func:`push` never uploads it."""
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
    """Records rclone calls and answers with ``codes`` in turn; a read of ``.ignore`` finds none and takes no code."""

    def __init__(self, *codes: int):
        self.codes, self.calls = list(codes), []

    def __call__(self, cmd, **kw):
        self.calls.append(cmd)
        if cmd[1] == "cat":
            return subprocess.CompletedProcess(cmd, 3, "", "directory not found\n")
        return subprocess.CompletedProcess(cmd, self.codes.pop(0), "", "rclone: quota exceeded\n")


class Drive:
    """A remote with a real ``.ignore``: ``copy`` overwrites it from a local file unless the file is excluded, as
    rclone does; ``fail`` makes the numbered call to a verb exit 1 (``{"cat": 2}`` is the second read); ``midway`` is
    what someone else does to the file during the push; ``kept`` is what a write really leaves, from what was sent and
    what was there."""

    def __init__(self, text=None, fail=None, midway=lambda text: text, kept=lambda sent, was: sent):
        self.text, self.fail, self.midway, self.kept = text, dict(fail or {}), midway, kept
        self.calls, self.written = [], []

    def verbs(self) -> list[str]:
        return [c[1] for c in self.calls]

    def __call__(self, cmd, input=None, **kw):
        self.calls.append(cmd)
        verb = cmd[1]
        if self.fail.get(verb) == self.verbs().count(verb):
            return subprocess.CompletedProcess(cmd, 1, "", "rclone: quota exceeded\n")
        if verb == "cat":
            if cmd[2].rpartition("/")[2] != ".ignore":
                raise AssertionError(f"read of {cmd[2]}")
            if self.text is None:
                return subprocess.CompletedProcess(cmd, 3, "", "directory not found\n")
            return subprocess.CompletedProcess(cmd, 0, self.text, "")
        if verb == "rcat":
            self.written.append(input)
            self.text = self.kept(input, self.text)
        if verb == "copy" and "/.ignore" not in cmd:
            stale = Path(cmd[2]) / ".ignore"
            if stale.is_file():
                self.text = stale.read_text()
        if verb == "check":
            self.text = self.midway(self.text)
        return subprocess.CompletedProcess(cmd, 0, "", "")


def test_push_copies_then_checks_every_file_arrived(tmp_path):
    run = Runner(0, 0)
    push(tmp_path, "gdrive:srstudio/ready", rclone="rclone", run=run)
    assert run.calls == [
        ["rclone", "cat", "gdrive:srstudio/ready/.ignore"],
        ["rclone", "copy", str(tmp_path), "gdrive:srstudio/ready", "--checksum", "--exclude", "/.ignore"],
        ["rclone", "check", str(tmp_path), "gdrive:srstudio/ready", "--one-way", "--exclude", "/.ignore"],
        ["rclone", "cat", "gdrive:srstudio/ready/.ignore"],
    ]


def test_a_dry_run_reads_what_is_held_and_only_previews_the_copy(tmp_path):
    run = Runner(0)
    push(tmp_path, "gdrive:x", run=run, dry_run=True)
    assert run.calls == [
        ["rclone", "cat", "gdrive:x/.ignore"],
        ["rclone", "copy", str(tmp_path), "gdrive:x", "--checksum", "--exclude", "/.ignore", "--dry-run"],
    ]


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
    def absent(cmd, **kw):
        return subprocess.run(cmd, **kw)  # a path that does not exist: raises as a missing rclone does

    with pytest.raises(OutboxError, match="rclone"):
        push(tmp_path, "gdrive:x", rclone=str(tmp_path / "no-rclone"), run=absent)


# -- .ignore, Drive's record of reels held out of the queue -----------------------------------------------------------
HELD = "honesty-interview-recreated\ntake-my-phone\nwhat-my-dad-does\ntext-me\ngloss-fewer-meetings\n"


def outbox_of(tmp_path, *names):
    folder = tmp_path / "outbox"
    for name in names:
        (folder / name).mkdir(parents=True)
    folder.mkdir(exist_ok=True)
    return folder


def test_a_stale_local_ignore_never_reaches_drive(tmp_path):
    """The incident of 1793530547.658369: a push put a local copy with one line over Drive's five."""
    folder = outbox_of(tmp_path, "a")
    (folder / ".ignore").write_text("honesty-interview-recreated\n")
    drive = Drive(HELD)
    push(folder, "gdrive:x", run=drive)
    assert drive.text == HELD
    assert drive.verbs() == ["cat", "copy", "check", "cat"]


def test_the_check_skips_ignore_too_so_a_differing_local_copy_cannot_fail_it(tmp_path):
    drive = Drive(HELD)
    push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive)
    check = next(c for c in drive.calls if c[1] == "check")
    assert check[-2:] == ["--exclude", "/.ignore"]


def test_a_line_that_goes_missing_during_a_push_is_an_error_naming_it(tmp_path):
    with pytest.raises(OutboxError, match=r"\.ignore.*text-me"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=Drive(HELD, midway=lambda text: "take-my-phone\n"))


def test_a_vanished_ignore_is_every_line_missing_not_an_empty_list(tmp_path):
    with pytest.raises(OutboxError, match="take-my-phone"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=Drive(HELD, midway=lambda text: None))


def test_ignore_may_grow_during_a_push(tmp_path):
    drive = Drive(HELD, midway=lambda text: text + "new-hold\n")
    push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive)
    assert drive.text == HELD + "new-hold\n"


def test_no_ignore_on_the_remote_is_an_empty_list(tmp_path):
    drive = Drive(None)
    push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive)
    assert drive.verbs() == ["cat", "copy", "check", "cat"]
    assert drive.text is None  # nothing wrote one


def test_a_failed_first_read_uploads_nothing(tmp_path):
    drive = Drive(HELD, fail={"cat": 1})
    with pytest.raises(OutboxError, match=r"\.ignore.*quota exceeded"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive)
    assert drive.verbs() == ["cat"]


def test_a_failed_read_after_the_copy_is_an_error_not_an_empty_list(tmp_path):
    drive = Drive(HELD, fail={"cat": 2})
    with pytest.raises(OutboxError, match=r"\.ignore.*quota exceeded"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive)
    assert drive.verbs() == ["cat", "copy", "check", "cat"]


def test_a_release_removes_exactly_those_lines_and_keeps_the_order(tmp_path):
    folder = outbox_of(tmp_path, "take-my-phone", "text-me", "a")
    drive = Drive(HELD)
    push(folder, "gdrive:x", run=drive, release=("take-my-phone", "text-me"))
    assert drive.text == "honesty-interview-recreated\nwhat-my-dad-does\ngloss-fewer-meetings\n"
    assert drive.verbs() == ["cat", "copy", "check", "cat", "rcat", "cat"]
    assert drive.calls[4] == ["rclone", "rcat", "gdrive:x/.ignore"]


def test_a_release_keeps_a_line_drive_gained_during_the_push(tmp_path):
    drive = Drive("a\nb\n", midway=lambda text: text + "new-hold\n")
    push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive, release=("a",))
    assert drive.text == "b\nnew-hold\n"


def test_releasing_the_last_line_leaves_an_empty_file(tmp_path):
    drive = Drive("a\n")
    push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive, release=("a",))
    assert drive.written == [""] and drive.text == ""


@pytest.mark.parametrize(
    ("slug", "match"),
    [
        ("not-held", "not held"),  # in this push, but Drive does not hold it
        ("take-my-phone", "not in this push"),  # held, but this push does not carry it
        ("..", "not held"),
    ],
)
def test_a_refused_release_touches_nothing(tmp_path, slug, match):
    drive = Drive(HELD)
    with pytest.raises(OutboxError, match=match):
        push(outbox_of(tmp_path, "not-held"), "gdrive:x", run=drive, release=(slug,))
    assert drive.verbs() == ["cat"] and drive.text == HELD


def test_a_slug_only_a_file_of_the_outbox_carries_is_not_in_the_push(tmp_path):
    folder = outbox_of(tmp_path, "a")
    (folder / "take-my-phone").write_text("not a video's folder")
    with pytest.raises(OutboxError, match="not in this push"):
        push(folder, "gdrive:x", run=Drive(HELD), release=("take-my-phone",))


def test_a_release_is_held_until_the_copy_is_checked(tmp_path):
    for fail in ({"copy": 1}, {"check": 1}):
        drive = Drive("a\n", fail=fail)
        with pytest.raises(OutboxError, match="quota exceeded"):
            push(outbox_of(tmp_path / str(fail), "a"), "gdrive:x", run=drive, release=("a",))
        assert "rcat" not in drive.verbs() and drive.text == "a\n"


def test_a_failed_write_of_a_release_is_a_typed_error(tmp_path):
    drive = Drive("a\nb\n", fail={"rcat": 1})
    with pytest.raises(OutboxError, match="rcat.*quota exceeded"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive, release=("a",))


def test_a_failed_read_back_of_a_release_is_a_typed_error(tmp_path):
    drive = Drive("a\nb\n", fail={"cat": 3})
    with pytest.raises(OutboxError, match=r"\.ignore.*quota exceeded"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive, release=("a",))


def test_a_read_back_that_lost_a_kept_line_is_an_error(tmp_path):
    drive = Drive("a\nb\n", kept=lambda sent, was: "")
    with pytest.raises(OutboxError, match="lost b"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive, release=("a",))


def test_a_read_back_that_still_holds_a_released_line_is_an_error(tmp_path):
    drive = Drive("a\nb\n", kept=lambda sent, was: was)
    with pytest.raises(OutboxError, match="still holds a"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive, release=("a",))


def test_a_dry_run_writes_nothing_and_still_refuses_a_bad_release(tmp_path):
    drive = Drive("a\n")
    push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive, dry_run=True, release=("a",))
    assert drive.verbs() == ["cat", "copy"] and "--dry-run" in drive.calls[1] and drive.text == "a\n"
    with pytest.raises(OutboxError, match="not held"):
        push(tmp_path / "outbox", "gdrive:x", run=Drive(""), dry_run=True, release=("a",))


def test_rcat_writes_through_stdin_never_a_local_file(tmp_path):
    drive = Drive("a\nb\n")
    push(outbox_of(tmp_path, "a"), "gdrive:x", run=drive, release=("a",))
    assert drive.written == ["b\n"]
    assert ["rclone", "rcat", "gdrive:x/.ignore"] in drive.calls


def test_a_missing_rclone_at_the_write_is_a_typed_error(tmp_path):
    class Gone(Drive):
        def __call__(self, cmd, input=None, **kw):
            if cmd[1] == "rcat":
                raise FileNotFoundError(cmd[0])
            return super().__call__(cmd, input=input, **kw)

    with pytest.raises(OutboxError, match="rclone was not found"):
        push(outbox_of(tmp_path, "a"), "gdrive:x", run=Gone("a\n"), release=("a",))


# -- the command ---------------------------------------------------------------------------------------------------
def command(monkeypatch, items, frozen=None, ab=None):
    """``episodes/publish_drive.py`` with the posts replaced by ``items``, the frozen releases by ``frozen`` and the
    A/B arms by ``ab``."""
    sys.path.insert(0, str(EPISODES))
    try:
        import publish_drive
    finally:
        sys.path.remove(str(EPISODES))
    monkeypatch.setattr(publish_drive.posts, "items", lambda renders: items)
    monkeypatch.setattr(publish_drive.posts, "font_file", lambda folder: FONT)
    monkeypatch.setattr(publish_drive.posts, "FROZEN", dict(frozen or {}))
    monkeypatch.setattr(publish_drive.posts, "AB", dict(ab or {}))
    monkeypatch.setattr(publish_drive.posts, "NUMBERS", {})
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
    assert [c[1] for c in run.calls] == ["cat", "copy", "check", "cat"]
    assert "2 ready, 0 held back" in capsys.readouterr().out
    items["b"][1].write_bytes(items["b"][1].read_bytes() + b"\0")
    assert publish_drive.main([*args, "--stage-only"]) == 1  # something was held back
    printed = capsys.readouterr().out
    assert "b: the video was re-rendered" in printed and "1 ready, 1 held back" in printed
    assert len(run.calls) == 4  # --stage-only pushes nothing


def test_the_command_releases_a_held_reel_in_the_same_push(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    publish_drive = command(monkeypatch, items)
    drive = Drive("a\nb\nc\n")
    monkeypatch.setattr(publish_drive.outbox, "_run", drive)
    args = where(out, tmp_path, tmp_path)
    assert publish_drive.main([*args, "--remote", "gdrive:t", "--release", "a", "--release", "b"]) == 0
    assert drive.text == "c\n"
    assert "released: a, b" in capsys.readouterr().out


def test_the_command_reports_a_refused_release_as_exit_2(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    publish_drive = command(monkeypatch, items)
    drive = Drive("c\n")
    monkeypatch.setattr(publish_drive.outbox, "_run", drive)
    assert publish_drive.main([*where(out, tmp_path, tmp_path), "--remote", "gdrive:t", "--release", "c"]) == 2
    assert "not in this push" in capsys.readouterr().err
    assert drive.text == "c\n" and drive.verbs() == ["cat"]


def test_the_command_says_a_dry_run_released_nothing(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    publish_drive = command(monkeypatch, items)
    drive = Drive("a\n")
    monkeypatch.setattr(publish_drive.outbox, "_run", drive)
    args = [*where(out, tmp_path, tmp_path), "--remote", "gdrive:t", "--dry-run", "--release", "a"]
    assert publish_drive.main(args) == 0
    assert drive.text == "a\n" and "rcat" not in drive.verbs()
    assert "would release: a" in capsys.readouterr().out


def test_a_release_cannot_ride_on_a_stage_only_run(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    publish_drive = command(monkeypatch, items)
    with pytest.raises(SystemExit) as stop:
        publish_drive.main([*where(out, tmp_path, tmp_path), "--stage-only", "--release", "a"])
    assert stop.value.code == 2
    assert "--release needs a push" in capsys.readouterr().err


def test_the_command_stages_a_frozen_video_at_the_drawing_it_was_frozen_at(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    items = {**items, "b": Item(post("B2"), items["b"].video)}  # its post changed after it was published
    args = [*where(out, tmp_path, tmp_path), "--stage-only"]
    assert command(monkeypatch, items).main(args) == 1
    assert "1 ready, 1 held back" in capsys.readouterr().out
    accepted = fingerprint(post("B2"), items["b"].video, FONT)
    assert command(monkeypatch, items, frozen={"b": accepted}).main(args) == 0
    assert "2 ready, 0 held back" in capsys.readouterr().out


def test_the_command_stages_each_released_arm_beside_its_video(delivered, tmp_path, monkeypatch, capsys):
    items, out, _ = delivered
    args = [*where(out, tmp_path, tmp_path), "--stage-only"]
    assert command(monkeypatch, items, ab={"b": Arm("sp-hook_motion", "a")}).main(args) == 0
    folder = tmp_path / "outbox"
    assert json.loads((folder / "b" / AB_NAME).read_text()) == {"test": "sp-hook_motion", "arm": "a"}
    assert not (folder / "a" / AB_NAME).exists()


def test_a_numbered_video_is_staged_with_its_place_and_a_plain_one_as_it_always_was(delivered, tmp_path):
    """The posting job orders numbered reels by ``episode.json``; a video with no number stages the same bytes."""
    items, out, pk = delivered
    plain, _ = ready(items, out, font=FONT, packages=pk)
    before = json.loads(stage(plain, tmp_path / "plain").read_text())
    bundles, _ = ready(items, out, font=FONT, packages=pk, numbers={"a": Claim(212, "Saga", 19)})
    folder = tmp_path / "outbox"
    manifest = json.loads(stage(bundles, folder).read_text())
    assert json.loads((folder / "a" / EPISODE_NAME).read_text()) == {
        "number": 212,
        "series": "saga",
        "series_number": 19,
    }
    assert (folder / "a" / EPISODE_NAME).stat().st_mode & 0o777 == 0o600
    assert manifest["videos"]["a"][EPISODE_NAME] == sha(folder / "a" / EPISODE_NAME)
    assert manifest["videos"]["b"] == before["videos"]["b"]
    assert not (tmp_path / "plain" / "a" / EPISODE_NAME).exists()


def test_a_brief_goes_in_episode_json_only_when_set(delivered, tmp_path):
    items, out, pk = delivered
    numbers = {"a": Claim(212, brief="send-v1"), "b": Claim(213)}
    folder = tmp_path / "outbox"
    stage(ready(items, out, font=FONT, packages=pk, numbers=numbers)[0], folder)
    assert json.loads((folder / "a" / EPISODE_NAME).read_text())["brief"] == "send-v1"
    assert (folder / "b" / EPISODE_NAME).read_text() == '{"number": 213, "series": "", "series_number": 0}\n'


def test_numbers_take_each_reels_brief_from_the_ledger(tmp_path, monkeypatch):
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts as posts
    finally:
        sys.path.remove(str(EPISODES))
    renders = tmp_path / "generated" / "renders"
    ledger = show_numbers.ledger_path(renders)
    show_numbers.set_base(ledger, 192)
    show_numbers.claim(ledger, "send-reel", brief="send-v1")
    show_numbers.claim(ledger, "plain-reel")
    monkeypatch.setattr(posts, "VIDEOS", {"send-reel": "Send_Reel", "plain-reel": "plain-reel", "gone-reel": "gone"})
    monkeypatch.setattr(posts, "NUMBERS", {"Send_Reel": Claim(193), "plain-reel": Claim(194), "gone": Claim(195)})
    assert posts.numbers(renders) == {
        "Send_Reel": Claim(193, brief="send-v1"),
        "plain-reel": Claim(194),
        "gone": Claim(195),
    }


def test_numbers_carry_each_reels_posting_days_from_the_ledger(tmp_path, monkeypatch):
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts as posts
    finally:
        sys.path.remove(str(EPISODES))
    renders = tmp_path / "generated" / "renders"
    ledger = show_numbers.ledger_path(renders)
    show_numbers.set_base(ledger, 200)
    show_numbers.claim(ledger, "dated-reel", brief="send-v1", post_by="2026-11-27", not_before="2026-11-20")
    monkeypatch.setattr(posts, "VIDEOS", {"dated-reel": "dated-reel"})
    monkeypatch.setattr(posts, "NUMBERS", {"dated-reel": Claim(201)})
    assert posts.numbers(renders) == {
        "dated-reel": Claim(201, brief="send-v1", post_by="2026-11-27", not_before="2026-11-20")
    }


def test_no_numbered_reel_means_the_ledger_is_never_read(tmp_path, monkeypatch):
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts as posts
    finally:
        sys.path.remove(str(EPISODES))
    ledger = show_numbers.ledger_path(tmp_path / "renders")
    ledger.parent.mkdir(parents=True)
    ledger.write_text("not json")
    monkeypatch.setattr(posts, "NUMBERS", {})
    assert posts.numbers(tmp_path / "renders") == {}


def test_every_folder_and_manifest_entry_counts_as_delivered(tmp_path):
    deliveries, box = tmp_path / "ig", tmp_path / "outbox"
    (deliveries / "in-ig").mkdir(parents=True)
    (box / "in-outbox").mkdir(parents=True)
    (box / ".ignore").write_text("held\n")
    (box / MANIFEST).write_text("{}")
    assert delivered_names(deliveries, box) == {"in-ig", "in-outbox"}


@pytest.mark.parametrize("gone", ["ig", "outbox"])
def test_a_missing_folder_clears_nobody(tmp_path, gone):
    (tmp_path / "ig").mkdir()
    (tmp_path / "outbox").mkdir()
    (tmp_path / gone).rmdir()
    with pytest.raises(OutboxError, match="not a folder"):
        delivered_names(tmp_path / "ig", tmp_path / "outbox")


def test_a_number_for_a_video_that_is_not_published_is_refused(delivered):
    items, out, pk = delivered
    with pytest.raises(OutboxError, match="not published: ghost"):
        ready(items, out, font=FONT, packages=pk, numbers={"ghost": Claim(1)})


def test_stage_refuses_a_bundle_whose_own_file_is_named_episode_json(tmp_path):
    source = tmp_path / EPISODE_NAME
    source.write_text("{}")
    with pytest.raises(OutboxError, match=EPISODE_NAME):
        stage([Bundle("a", (source,), episode=Claim(1))], tmp_path / "outbox")


def test_a_reel_in_no_series_writes_all_three_fields_with_an_empty_series_and_zero(delivered, tmp_path):
    """The posting job's contract is three fields on every numbered reel: none is left out."""
    items, out, pk = delivered
    bundles, _ = ready(items, out, font=FONT, packages=pk, numbers={"a": Claim(193)})
    folder = tmp_path / "outbox"
    stage(bundles, folder)
    assert (folder / "a" / EPISODE_NAME).read_text() == '{"number": 193, "series": "", "series_number": 0}\n'


def test_no_reel_published_before_the_numbers_has_one_so_its_outbox_stays_the_same():
    """Batch E is the first with numbered releases, so the list of what may not have one is the closed published one."""
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts as posts
    finally:
        sys.path.remove(str(EPISODES))
    numbered = {slug for slug, video in posts.VIDEOS.items() if video in posts.NUMBERS}
    assert numbered.isdisjoint(posts.GRANDFATHERED)


def test_ab_mirrors_the_test_and_arm_of_every_release_in_a_test():
    sys.path.insert(0, str(EPISODES))
    try:
        import instagram_posts as posts
    finally:
        sys.path.remove(str(EPISODES))
    expected = {
        r.video_name: Arm(r.tags.test, r.tags.arm, r.tags.recipient, r.tags.to, r.tags.also)
        for r in posts.RELEASES.values()
        if r.tags and r.tags.test
    }
    assert posts.AB == expected


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


def test_a_bundle_can_stage_a_file_under_another_name(tmp_path):
    source = tmp_path / "pilot-1.0.0.vpkg.zip"
    source.write_text("package\n")
    manifest = stage([Bundle("pilot", (source,), names=("vpkg.zip",))], tmp_path / "out")
    assert (manifest.parent / "pilot/vpkg.zip").read_text() == "package\n"
    assert not (manifest.parent / "pilot" / source.name).exists()
    assert list(json.loads(manifest.read_text())["videos"]["pilot"]) == ["vpkg.zip"]


def test_staged_names_must_match_the_files_and_each_other(tmp_path):
    one, two = tmp_path / "one.txt", tmp_path / "two.txt"
    one.write_text("1\n")
    two.write_text("2\n")
    with pytest.raises(OutboxError, match="names"):
        stage([Bundle("pilot", (one, two), names=("only.txt",))], tmp_path / "out")
    with pytest.raises(OutboxError, match="share one name"):
        stage([Bundle("pilot", (one, two), names=("same.txt", "same.txt"))], tmp_path / "out")


@pytest.mark.parametrize("name", ["a/b.txt", "../b.txt", "..", ""])
def test_a_staged_name_cannot_leave_its_folder(tmp_path, name):
    source = tmp_path / "one.txt"
    source.write_text("1\n")
    with pytest.raises(OutboxError, match="file name"):
        stage([Bundle("pilot", (source,), names=(name,))], tmp_path / "out")


def test_the_manifest_can_have_another_name_and_a_restage_recognises_it(tmp_path):
    source = tmp_path / "one.txt"
    source.write_text("1\n")
    manifest = stage([Bundle("pilot", (source,))], tmp_path / "out", manifest="manifest.json")
    assert manifest == tmp_path / "out/manifest.json" and not (tmp_path / "out" / MANIFEST).exists()
    assert stage([Bundle("pilot", (source,))], tmp_path / "out", manifest="manifest.json") == manifest
    with pytest.raises(OutboxError, match="not an outbox"):
        stage([Bundle("pilot", (source,))], tmp_path / "out")


def test_a_files_own_name_is_not_judged_only_a_chosen_one(tmp_path):
    source = tmp_path / "Printer Recreation (1).mp4"
    source.write_text("video\n")
    manifest = stage([Bundle("printer", (source,))], tmp_path / "out")
    assert (manifest.parent / "printer" / source.name).is_file()

"""Approved files are write-once (ADR 0170): the check and the create are one operation, a symbolic link counts as a
file, two processes cannot both win a path, and a refused write leaves nothing behind."""

from __future__ import annotations

import multiprocessing
import os
from pathlib import Path

import pytest

from srstudio import files
from srstudio.errors import SrstudioError


def _leftovers(folder: Path) -> list[str]:
    return sorted(p.name for p in folder.iterdir() if p.name.startswith("."))


def test_write_once_writes_bytes_or_text_and_returns_the_path(tmp_path):
    assert files.write_once(tmp_path / "a.bin", b"\x00\x01") == tmp_path / "a.bin"
    assert (tmp_path / "a.bin").read_bytes() == b"\x00\x01"
    files.write_once(tmp_path / "a.txt", "olá")
    assert (tmp_path / "a.txt").read_bytes() == "olá".encode()
    assert _leftovers(tmp_path) == []


def test_write_once_refuses_an_existing_file_and_keeps_its_bytes(tmp_path):
    path = tmp_path / "take.mp3"
    path.write_bytes(b"approved")
    with pytest.raises(files.WriteOnceError, match="take.mp3 exists") as raised:
        files.write_once(path, b"a re-run")
    assert path.read_bytes() == b"approved"
    assert isinstance(raised.value, FileExistsError) and isinstance(raised.value, SrstudioError)
    assert raised.value.to_dict()["code"] == "files.exists"
    assert _leftovers(tmp_path) == []


def test_a_symbolic_link_counts_as_a_file_even_when_it_dangles(tmp_path):
    away = tmp_path / "nowhere" / "target.mp4"
    link = tmp_path / "master.mp4"
    link.symlink_to(away)
    with pytest.raises(files.WriteOnceError):
        files.write_once(link, b"new")
    assert link.is_symlink() and not away.exists() and not away.parent.exists()
    with pytest.raises(files.WriteOnceError):
        files.install_once(_staged(tmp_path, b"new"), link)
    assert not away.exists()


def test_a_folder_in_the_way_is_refused(tmp_path):
    (tmp_path / "x").mkdir()
    with pytest.raises(files.WriteOnceError):
        files.write_once(tmp_path / "x", b"new")


def test_the_mode_is_applied_to_the_new_file(tmp_path):
    files.write_once(tmp_path / "p.zip", b"z", mode=0o600)
    assert (tmp_path / "p.zip").stat().st_mode & 0o777 == 0o600


def test_a_failed_write_leaves_no_file_and_no_stage(tmp_path, monkeypatch):
    def broken(*_args: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(files.os, "fsync", broken)
    with pytest.raises(OSError, match="No space"):
        files.write_once(tmp_path / "a.wav", b"data")
    assert list(tmp_path.iterdir()) == []


def test_write_same_accepts_identical_bytes_and_refuses_others(tmp_path):
    path = tmp_path / "derived.wav"
    assert files.write_same(path, b"pcm") == path
    assert files.write_same(path, b"pcm") == path
    with pytest.raises(files.WriteOnceError, match="other bytes"):
        files.write_same(path, b"different")
    assert path.read_bytes() == b"pcm"
    link = tmp_path / "link.wav"
    link.symlink_to(path)
    with pytest.raises(files.WriteOnceError):
        files.write_same(link, b"pcm")


def test_must_be_free_names_a_taken_path_before_any_work(tmp_path):
    assert files.must_be_free(tmp_path / "m.mp4") == tmp_path / "m.mp4"
    (tmp_path / "m.mp4").symlink_to(tmp_path / "gone")
    with pytest.raises(files.WriteOnceError, match="m.mp4 exists"):
        files.must_be_free(tmp_path / "m.mp4")


def test_next_free_counts_past_taken_names_and_dangling_links(tmp_path):
    base = tmp_path / "excerpt.wav"
    assert files.next_free(base) == base
    base.write_bytes(b"1")
    assert files.next_free(base) == tmp_path / "excerpt-v2.wav"
    (tmp_path / "excerpt-v2.wav").symlink_to(tmp_path / "gone")
    assert files.next_free(base) == tmp_path / "excerpt-v3.wav"
    assert files.next_free(tmp_path / "a.scene.mp4") == tmp_path / "a.scene.mp4"
    (tmp_path / "a.scene.mp4").write_bytes(b"1")
    assert files.next_free(tmp_path / "a.scene.mp4", suffix="-take") == tmp_path / "a.scene-take2.mp4"


def test_write_next_and_install_next_never_replace(tmp_path):
    base = tmp_path / "m.mp4"
    assert files.write_next(base, b"1") == base
    assert files.write_next(base, b"2") == tmp_path / "m-v2.mp4"
    assert files.install_next(_staged(tmp_path, b"3"), base) == tmp_path / "m-v3.mp4"
    assert [p.read_bytes() for p in (base, tmp_path / "m-v2.mp4", tmp_path / "m-v3.mp4")] == [b"1", b"2", b"3"]


def test_the_search_for_a_free_name_is_bounded(tmp_path, monkeypatch):
    monkeypatch.setattr(files, "MOST", 3)
    base = tmp_path / "m.mp4"
    for name in ("m.mp4", "m-v2.mp4", "m-v3.mp4", "m-v4.mp4"):
        (tmp_path / name).write_bytes(b"x")
    with pytest.raises(files.WriteOnceError, match="no free name"):
        files.next_free(base)


def _staged(folder: Path, data: bytes) -> Path:
    staged = folder / f".staged-{len(list(folder.iterdir()))}.mp4"
    staged.write_bytes(data)
    return staged


def test_install_once_moves_a_finished_file_to_a_free_path(tmp_path):
    staged = _staged(tmp_path, b"master")
    assert files.install_once(staged, tmp_path / "slug.mp4") == tmp_path / "slug.mp4"
    assert (tmp_path / "slug.mp4").read_bytes() == b"master" and not staged.exists()


def test_install_once_refuses_a_taken_path_and_leaves_both_files(tmp_path):
    good = tmp_path / "slug.mp4"
    good.write_bytes(b"the good master")
    staged = _staged(tmp_path, b"a failed re-run")
    with pytest.raises(files.WriteOnceError):
        files.install_once(staged, good)
    assert good.read_bytes() == b"the good master" and staged.read_bytes() == b"a failed re-run"


def test_install_once_refuses_a_source_that_is_not_a_regular_file(tmp_path):
    (tmp_path / "real").write_bytes(b"x")
    (tmp_path / "link").symlink_to(tmp_path / "real")
    with pytest.raises(files.WriteOnceError, match="not a regular file"):
        files.install_once(tmp_path / "link", tmp_path / "out")
    assert not (tmp_path / "out").exists()


def test_without_hard_links_the_write_still_never_replaces(tmp_path, monkeypatch):
    def no_links(*_args: object, **_kw: object) -> None:
        raise OSError(1, "Operation not permitted")

    monkeypatch.setattr(files.os, "link", no_links)
    path = tmp_path / "a.json"
    files.write_once(path, b"{}")
    assert path.read_bytes() == b"{}"
    with pytest.raises(files.WriteOnceError):
        files.write_once(path, b"[]")
    staged = _staged(tmp_path, b"m")
    files.install_once(staged, tmp_path / "m.mp4")
    assert (tmp_path / "m.mp4").read_bytes() == b"m" and not staged.exists()
    assert _leftovers(tmp_path) == []


def _race(path: str, payload: bytes, start: object, results: object) -> None:
    start.wait()  # type: ignore[attr-defined]
    try:
        files.write_once(path, payload)
        results.put(("won", payload))  # type: ignore[attr-defined]
    except files.WriteOnceError:
        results.put(("lost", payload))  # type: ignore[attr-defined]


def _race_next(path: str, payload: bytes, start: object, results: object) -> None:
    start.wait()  # type: ignore[attr-defined]
    results.put((str(files.write_next(path, payload)), payload))  # type: ignore[attr-defined]


def _run_race(target: object, path: Path, count: int) -> list[tuple[str, bytes]]:
    context = multiprocessing.get_context("fork")
    start, results = context.Barrier(count), context.Queue()
    payloads = [bytes([i]) * (64 * 1024) for i in range(count)]
    workers = [context.Process(target=target, args=(str(path), p, start, results)) for p in payloads]
    for w in workers:
        w.start()
    got = [results.get(timeout=60) for _ in workers]
    for w in workers:
        w.join(timeout=60)
        assert w.exitcode == 0
    return got


def test_two_processes_cannot_both_win_a_path(tmp_path):
    path = tmp_path / "approved.wav"
    got = _run_race(_race, path, 8)
    winners = [payload for outcome, payload in got if outcome == "won"]
    assert len(winners) == 1
    assert path.read_bytes() == winners[0]  # whole: no reader sees a half-written file under the final name
    assert _leftovers(tmp_path) == []


def test_racing_write_next_gives_every_process_its_own_whole_file(tmp_path):
    got = _run_race(_race_next, tmp_path / "take.wav", 6)
    paths = [Path(p) for p, _ in got]
    assert len(set(paths)) == 6
    assert all(p.read_bytes() == payload for p, payload in zip(paths, (payload for _, payload in got), strict=True))
    assert os.path.basename(min(map(str, paths), key=len)) == "take.wav"

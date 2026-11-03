"""No test can reach the operator's Drive. Real rclone was reached once, by a test that faked ``subprocess.run`` when
``outbox._run`` had already been bound to it: this holds whatever a test forgets (``rclone_is_unreachable``)."""

import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import RCLONE_REFUSED
from srstudio import outbox

REPO = Path(__file__).resolve().parent.parent
ROADS = {"src/srstudio/outbox.py"}  # the delivery commands and their guards are checked in srstudio-episodes
REFUSED = "a test reached real rclone"


def test_a_push_nobody_faked_fails_the_test(tmp_path):
    with pytest.raises(pytest.fail.Exception, match=REFUSED):
        outbox.push(tmp_path, "gdrive:srstudio/pilots/test")


def test_a_read_nobody_faked_fails_the_test():
    with pytest.raises(pytest.fail.Exception, match=REFUSED):
        outbox.fetch("gdrive:srstudio/pilots/test", "manifest.json")


def test_the_mistake_that_reached_drive_now_fails_the_test(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(outbox.subprocess, "run", lambda cmd, **_: calls.append(cmd))
    with pytest.raises(pytest.fail.Exception, match=REFUSED):
        outbox.push(tmp_path, "gdrive:srstudio/pilots/test")
    assert not calls


def test_no_except_in_the_code_under_test_can_swallow_the_refusal():
    assert not issubclass(pytest.fail.Exception, Exception)


def test_a_test_s_own_fake_still_wins(tmp_path, monkeypatch):
    calls = []

    def fake(cmd, **_):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, "", "")

    monkeypatch.setattr(outbox, "_run", fake)
    outbox.push(tmp_path, "gdrive:x")
    assert [cmd[1] for cmd in calls] == ["cat", "copy", "check", "cat"]


def test_a_child_process_finds_the_stand_in_and_not_rclone():
    assert "no-rclone" in shutil.which("rclone")
    done = subprocess.run(["rclone", "copy", "a", "gdrive:b"], capture_output=True, text=True, check=False)
    assert done.returncode == RCLONE_REFUSED
    assert "a test reached rclone" in done.stderr


@pytest.mark.static  # a source scan: its time is the processor's (ADR 0225)
def test_every_road_to_rclone_is_guarded():
    """A new module that names rclone has to come through ``outbox._run``, or be added here with a guard of its own."""
    named = {
        str(path.relative_to(REPO))
        for folder in ("src", "tools")
        for path in (REPO / folder).rglob("*.py")
        if "rclone" in path.read_text(encoding="utf-8")
    }
    assert named == ROADS

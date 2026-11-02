"""tools/dance_views.py: front, left and top orthographic views of dances on the shared skeleton, for review."""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from srstudio import dance, music
from srstudio import skeleton as sk

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "dance_views.py"
spec = importlib.util.spec_from_file_location("dance_views", TOOL)
assert spec is not None and spec.loader is not None
views = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = views
spec.loader.exec_module(views)

GROOVE = music.Groove(129.0)


def test_each_view_keeps_its_two_axes():
    point = sk.Vec3(1.0, 2.0, 3.0)
    assert views.flat("front", point) == (1.0, 2.0)
    assert views.flat("left", point) == (3.0, 2.0)  # seen from the character's left, forward is screen right
    assert views.flat("top", point) == (1.0, 3.0)  # seen from above, forward is screen down


def test_a_plan_gives_each_move_its_bars_in_order():
    plan = views.plan(["bob", "sway"], bars_each=2)
    assert plan == (("bob", 0, 2), ("sway", 2, 4))
    assert views.at_bar(plan, 3.5) == ("sway", 2)
    assert views.at_bar(plan, 99.0) == ("sway", 2)


def test_every_preset_is_the_default_plan():
    assert [name for name, _, _ in views.plan(None, bars_each=1)] == list(dance.moves())


def test_a_frame_is_one_cell_per_character_and_view():
    sheet = views.Sheet(("realistic", "stick"), ("front", "top"))
    image = views.render_frame(sheet, views.plan(["bob"], 1), GROOVE, 0.2)
    assert image.size == (2 * views.CELL, views.TOP_BAR + 2 * views.CELL + views.BOTTOM_BAR)


def test_a_frame_is_the_same_picture_each_time_and_moves_with_the_dance():
    sheet = views.Sheet(("cartoon",), views.VIEWS)
    plan = views.plan(["arm-wave-overhead"], 2)
    first = views.render_frame(sheet, plan, GROOVE, 0.3).tobytes()
    assert views.render_frame(sheet, plan, GROOVE, 0.3).tobytes() == first
    assert views.render_frame(sheet, plan, GROOVE, 0.3 + GROOVE.beat / 2).tobytes() != first


def test_a_raised_arm_draws_above_the_head_in_the_front_view():
    sheet = views.Sheet(("realistic",), ("front",))
    profile = sk.preset("realistic")
    posed = sk.add(profile, sk.rest_pose(profile), {"right_upper_arm.down_up": 2.5}, clamp=True)
    hand, head = views.screen(sheet, profile, posed, "front", row=0, col=0, names=("right_hand", "head"))
    assert hand[1] < head[1]


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"moves": ["no-such-move"]}, "unknown move"),
        ({"characters": ("giant",)}, "unknown character"),
        ({"views": ("back",)}, "unknown view"),
        ({"characters": ()}, "at least one"),
        ({"bars_each": 0}, "bars"),
        ({"fps": 0}, "fps"),
        ({"fps": 61}, "fps"),
        ({"bpm": 10}, "bpm"),
        ({"moves": ["bob"] * 40, "bars_each": 2}, "bars"),
    ],
)
def test_bad_settings_are_refused(tmp_path, kw, match):
    with pytest.raises(views.ViewsError, match=match):
        views.write(tmp_path / "out.mp4", **kw)


TINY = {"moves": ["head-nod"], "characters": ("stick",), "views": ("top",), "bars_each": 1, "fps": 2}


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_write_returns_the_private_video_and_leaves_no_scratch(tmp_path):
    out = views.write(tmp_path / "made" / "views.mp4", **TINY)
    assert out == tmp_path / "made" / "views.mp4" and out.stat().st_size > 0
    assert sorted(p.name for p in out.parent.iterdir()) == ["views.mp4"]


def test_an_encoder_that_fails_is_reported(tmp_path):
    with pytest.raises(views.ViewsError, match="failed to encode"):
        views.write(tmp_path / "views.mp4", ffmpeg="false", **TINY)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_main_prints_the_video_and_refuses_bad_settings(tmp_path, capsys):
    out = tmp_path / "views.mp4"
    assert views.main([str(out), "--moves", "bob", "--bars-each", "1", "--fps", "2", "--characters", "stick"]) == 0
    assert capsys.readouterr().out.strip() == str(out)
    assert views.main([str(out), "--moves", "moonwalk"]) == 2
    assert "unknown move" in capsys.readouterr().err


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_the_tool_writes_a_video_with_sound(tmp_path):
    out = tmp_path / "views.mp4"
    done = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            str(out),
            "--moves",
            "head-nod",
            "--bars-each",
            "1",
            "--fps",
            "5",
            "--characters",
            "stick",
            "--views",
            "front,left",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert done.returncode == 0, done.stderr
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(out)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert sorted(probe.stdout.split()) == ["audio", "video"]
    assert oct(out.stat().st_mode & 0o777) == "0o600"

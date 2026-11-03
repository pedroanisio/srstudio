"""tools/dance_views.py: orthographic views of dances on the shared skeleton, for review: moves and phrases (ADR 0194)
in the volume look (ADR 0202) or as lines."""

import importlib.util
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import ImageChops

from srstudio import dance, dance_floor, music
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


@pytest.mark.parametrize("look", views.LOOKS)
def test_a_move_cell_is_the_whole_pose_where_the_screen_says(look):
    """Each cell of the moves sheet draws in its own picture: its corner is the picture's corner, so the feet and the
    cell's own frame are inside it, and the joints land where ``screen`` puts them."""
    sheet = views.Sheet(("realistic",), ("front", "left"))
    profile = sk.preset("realistic")
    t = 0.4
    frame = dance.sample(dance.moves()["bob"], GROOVE, t)
    posed = views.dance_pose(profile, frame, base=sk.rest_pose(profile), clamp=True).pose
    image = views.render_frame(sheet, views.plan(["bob"], 1), GROOVE, t, look=look)
    alone = views.pose_image(profile, posed, sheet.views, look=look)
    cells = (0, views.TOP_BAR, 2 * views.CELL, views.TOP_BAR + views.CELL)
    assert ImageChops.difference(image.crop(cells), alone.crop(cells)).getbbox() is None
    for col, view in enumerate(sheet.views):
        (foot,) = views.screen(sheet, profile, posed, view, row=0, col=col, names=("right_foot",))
        assert views.TOP_BAR < foot[1] < views.TOP_BAR + views.CELL
        assert image.getpixel((round(foot[0]), round(foot[1]))) != views.BG


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


# --- the volume look (ADR 0202) -------------------------------------------------------------------------------------

# Hands with no fingers, so nothing but the forearm's own drawing could show its roll.
PLAIN = sk.SkeletonProfile("plain", sk.preset("realistic").proportions, hands=("none", "none"))


def _twisted(turn):
    return sk.add(PLAIN, sk.pose(PLAIN), {"right_lower_arm.twist_in_out": turn})


def test_the_line_look_cannot_show_a_forearm_twist_and_the_volume_look_can():
    plain, twisted = _twisted(0.0), _twisted(math.pi / 2)
    lines = [views.pose_image(PLAIN, p, ("front",), look="lines").tobytes() for p in (plain, twisted)]
    assert lines[0] == lines[1]
    volume = [views.pose_image(PLAIN, p, ("front",), look="volume") for p in (plain, twisted)]
    changed = ImageChops.difference(volume[0], volume[1]).getbbox()
    assert changed is not None
    # Nothing on the body's side of the elbow changes: the roll shows on the forearm and the hand it carries. The
    # margin is half the widest stroke the look draws, rounded up.
    (elbow,) = views.cell_points(PLAIN, plain, "front", ("right_lower_arm",))
    assert changed[0] >= elbow[0] - math.ceil(max(views.STROKES.values()) / 2)


def test_the_volume_look_is_the_default_and_a_look_must_be_known(tmp_path):
    sheet = views.Sheet(("stick",), ("front",))
    plan = views.plan(["bob"], 1)
    default = views.render_frame(sheet, plan, GROOVE, 0.2)
    assert default.tobytes() == views.render_frame(sheet, plan, GROOVE, 0.2, look="volume").tobytes()
    assert default.tobytes() != views.render_frame(sheet, plan, GROOVE, 0.2, look="lines").tobytes()
    with pytest.raises(views.ViewsError, match="unknown look"):
        views.write(tmp_path / "out.mp4", look="clay", **TINY)
    with pytest.raises(views.ViewsError, match="unknown look"):
        views.pose_image(PLAIN, _twisted(0.0), ("front",), look="clay")


@pytest.mark.parametrize("view", views.VIEWS)
def test_the_volume_look_draws_every_view_on_the_axes_the_lines_use(view):
    """The three-quarter view (ADR 0194) is a skeleton view too: the volume model projects each point where ``flat``
    puts it, so both looks put a joint on the same pixel."""
    for point in (sk.Vec3(1.0, 2.0, 3.0), sk.Vec3(-0.3, 0.8, -1.1)):
        assert views.SK_VIEWS[view].flat(point) == pytest.approx(views.flat(view, point))
    profile = sk.preset("realistic")
    posed = sk.add(profile, sk.rest_pose(profile), {"right_upper_arm.down_up": 1.2}, clamp=True)
    (wrist,) = views.cell_points(profile, posed, view, ("right_hand",))
    for look in views.LOOKS:
        image = views.pose_image(profile, posed, (view,), look=look)
        x, y = round(wrist[0]), round(wrist[1])
        box = image.crop((x - 4, y - 4, x + 5, y + 5))
        assert any(box.getpixel((i, j)) != views.BG for i in range(9) for j in range(9)), (view, look)


def test_a_zoomed_pose_image_is_the_same_drawing_larger():
    profile = sk.preset("stick")
    posed = sk.rest_pose(profile)
    one, two = (views.pose_image(profile, posed, ("front", "three-quarter"), zoom=z) for z in (1, 2))
    assert two.size == (2 * views.CELL * 2, views.TOP_BAR + 2 * views.CELL)
    assert one.size == (2 * views.CELL, views.TOP_BAR + views.CELL)
    with pytest.raises(views.ViewsError, match="zoom"):
        views.pose_image(profile, posed, ("front",), zoom=5)
    with pytest.raises(views.ViewsError, match="unknown view"):
        views.pose_image(profile, posed, ("back",))


# --- phrases on a fixed floor, an ensemble, characters beyond the presets (ADR 0194) --------------------------------

CLASS = music.Groove(122.65)


def test_the_three_quarter_view_turns_the_floor_toward_the_camera():
    assert "three-quarter" in views.VIEWS
    near, far = views.flat("three-quarter", sk.Vec3(0, 0, 1)), views.flat("three-quarter", sk.Vec3(0, 0, -1))
    assert near[1] > far[1]  # the floor in front of the dancer lies lower on the screen: seen from above
    assert near[0] != far[0]  # and to one side: seen from a corner
    up = views.flat("three-quarter", sk.Vec3(0, -1, 0))
    assert up[1] < 0 and up[0] == 0  # up is still up the screen


def test_a_character_is_a_preset_or_a_profile_record_and_may_sit(tmp_path):
    record = tmp_path / "tall.json"
    record.write_text(json.dumps(sk.preset("realistic").record() | {"name": "tall"}))
    sheet = views.Sheet((str(record), "stick@seated"), ("front",))
    tall, stick = sheet.cast
    assert tall.profile.name == "tall" and tall.label == "tall" and tall.base_name == "standing"
    assert stick.label == "stick · seated"
    hips = sk.world(stick.profile, stick.base())["hips"].origin.y
    assert hips > sk.world(stick.profile, sk.rest_pose(stick.profile))["hips"].origin.y  # lower: y points down


@pytest.mark.parametrize(
    "spec, match", [("stick@lying", "base"), ("nowhere.json", "unknown character"), ("@seated", "unknown character")]
)
def test_a_character_that_cannot_be_read_is_refused(tmp_path, spec, match):
    with pytest.raises(views.ViewsError, match=match):
        views.Sheet((spec,), ("front",))


def test_a_profile_record_that_does_not_parse_is_refused(tmp_path):
    record = tmp_path / "bad.json"
    record.write_text('{"name": "bad"}')
    with pytest.raises(views.ViewsError, match="bad.json"):
        views.Sheet((str(record),), ("front",))


def test_a_character_may_stand_in_the_class_stance():
    low = views.Sheet(("cartoon@stance",), ("front",)).cast[0]
    assert low.label == "cartoon · stance" and low.base_name == "stance"
    assert dance_floor.knee_bend(low.profile, low.base()) == pytest.approx(dance_floor.STANCE_BEND, abs=1e-3)
    rest = sk.rest_pose(low.profile)
    assert dance_floor.knee_bend(low.profile, rest) < 0.1 < dance_floor.STANCE_BEND  # the rest pose stands straight


def test_a_seated_row_dances_a_seat_move_from_the_seat():
    sheet = views.Sheet(("stick@seated",), ("left",))
    plan = views.plan(["seat-groove"], 1)
    image = views.render_frame(sheet, plan, GROOVE, 0.4)
    standing = views.render_frame(views.Sheet(("stick",), ("left",)), plan, GROOVE, 0.4)
    assert image.tobytes() != standing.tobytes()


def test_a_stage_dances_phrases_in_order_on_a_fixed_floor():
    sheet = views.Sheet(("stick",), ("front", "top"))
    stage = views.stage(sheet, ["groove-step", "kick-ball-change"], CLASS)
    assert stage.parts == (("groove-step", 0, 2), ("kick-ball-change", 2, 4)) and stage.bars == 4
    assert views.at_bar(stage.parts, 2.5) == ("kick-ball-change", 2)
    start = views.render_frame(sheet, stage, CLASS, 0.0)
    assert start.size == sheet.size
    run = stage.rows[0][0]
    later = run.pose(CLASS.offset + 4 * CLASS.beat).root.origin.x
    assert later - run.pose(run.start_s).root.origin.x > 0.1  # the body travels on the floor, the floor stays put
    assert views.render_frame(sheet, stage, CLASS, 4 * CLASS.beat).tobytes() != start.tobytes()


def test_an_ensemble_dances_every_character_in_one_row():
    sheet = views.Sheet(sk.PRESETS, ("front",), ensemble=True)
    assert sheet.size == (views.CELL, views.TOP_BAR + views.CELL + views.BOTTOM_BAR)
    stage = views.stage(sheet, ["groove-step"], CLASS, canon_beats=0.5, seed=4)
    (row,) = stage.rows
    assert len(row) == 3  # a canon, half a beat apart, give or take each dancer's own timing
    assert [r.delay_s / CLASS.beat for r in row] == pytest.approx([0.0, 0.5, 1.0], abs=0.05)
    xs = [r.pose(r.start_s).root.origin.x for r in row]
    assert xs == sorted(xs) and xs[0] < 0 < xs[2]  # standing in a line across the floor
    tallest = max(sk.preset(p).stature for p in sk.PRESETS)
    assert min(b - a for a, b in zip(xs, xs[1:], strict=False)) >= 0.85 * tallest  # an arm's span apart
    assert views.render_frame(sheet, stage, CLASS, 1.0).size == sheet.size


@pytest.mark.parametrize(
    "kw, match",
    [
        ({"phrases": ["no-such-phrase"]}, "unknown phrase"),
        ({"phrases": ["groove-step"], "moves": ["bob"]}, "moves or phrases"),
        ({"phrases": ["groove-step"], "formation": "circle"}, "formation"),
        ({"phrases": ["groove-step"], "canon_beats": -1}, "canon"),
        ({"phrases": ["groove-step"] * 40}, "bars"),
        ({"ensemble": True}, "phrases"),
    ],
)
def test_bad_stage_settings_are_refused(tmp_path, kw, match):
    with pytest.raises(views.ViewsError, match=match):
        views.write(tmp_path / "out.mp4", **kw)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")
def test_main_writes_an_ensemble_of_phrases(tmp_path, capsys):
    out = tmp_path / "trio.mp4"
    argv = [
        str(out),
        "--phrases",
        "groove-step",
        "--ensemble",
        "--canon",
        "0.5",
        "--fps",
        "2",
        "--bpm",
        "122.65",
        "--characters",
        "stick,cartoon",
        "--views",
        "front,three-quarter",
    ]
    assert views.main(argv) == 0
    assert capsys.readouterr().out.strip() == str(out) and out.stat().st_size > 0

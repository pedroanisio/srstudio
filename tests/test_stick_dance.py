"""The Stick style dances (``srstudio.stick_dance``): a dance on the shared skeleton, read as stick.rig draws it,
held to the groove it was measured from on the drawing's own head and hips, with the face held per phrase."""

import math
import struct
import subprocess
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, dance, flat_counter, gpu, stick
from srstudio import skeleton as sk
from srstudio import stick_dance as sd
from srstudio.errors import SrstudioError
from srstudio.limbs.math3d import Vec3
from srstudio.music import Groove

GROOVE = Groove(129)
MOVES = dance.moves()
RAISED = (("left_upper_arm.down_up", 2.0), ("left_lower_arm.stretch", 0.8))


def canvas(duration: float = 4.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="25", duration=duration, background="#bda77a")
    return Canvas(scene, DAYLIGHT, font_asset=None, namer=flat_counter("n"))


def routine(*entries: dance.Entry, bars: int = 8) -> dance.Routine:
    return dance.Routine(bars, entries)


def flat(points) -> tuple[float, ...]:
    return tuple(v for point in points for v in point)


def seat_groove(bars: float = 8) -> sd.StickDance:
    return sd.perform(MOVES["seat-groove"], GROOVE, 0.0, bars * GROOVE.bar)


# The profile


def test_the_default_profile_is_the_stick_preset_with_the_cast_s_bones():
    px = stick.HEAD_R / sd.PROFILE.proportions.head_radius_m
    assert sd.PROFILE == sk.preset("stick")
    assert sd.PROFILE.length("upper_arm") * px == pytest.approx(stick.ARM, abs=0.1)
    assert sd.PROFILE.length("forearm") * px == pytest.approx(stick.ARM, abs=0.1)


def test_a_standing_figure_stands_as_tall_as_the_cast_s_stand():
    """stick.STANDING "stand": head at 750, neck 857, hips 1190, feet 1700. The base pose softens the knees."""
    stand = sd.perform(MOVES["head-nod"], GROOVE, 0.0, 0.04, seated=False).poses[0]
    drawn = stick.STANDING["stand"]
    assert stand.hip[1] - stand.neck[1] == pytest.approx(drawn.hip[1] - drawn.neck[1], abs=1)
    assert stand.feet[0][1] == stand.feet[1][1] == sd.FLOOR
    assert stand.head[1] == pytest.approx(drawn.head[1], abs=25)


def test_the_seated_figure_sits_where_the_windshield_s_front_poses_sit():
    first = sd.perform(MOVES["seat-groove"], GROOVE, 0.0, 0.04, base=sd.SEATED, seated=True).poses[0]
    sit = sd.perform(MOVES["head-nod"], GROOVE, 0.0, 0.04, seated=True).poses[0]
    shoulder = (sit.neck[0] - 4, sit.neck[1] + 34)
    assert sit.neck[1] - sit.head[1] == pytest.approx(110, abs=3)  # FRONT "sit": 107
    assert sit.hip[1] - sit.neck[1] == pytest.approx(333, abs=1)  # the cast's torso; FRONT "sit" draws 383
    assert sit.neck[1] == pytest.approx(1037, abs=3)  # FRONT "sit"'s neck: the head sits where the cast's does
    near = (sit.elbows[1][0] - shoulder[0], sit.elbows[1][1] - shoulder[1])
    far = (sit.elbows[0][0] - shoulder[0], sit.elbows[0][1] - shoulder[1])
    assert near[0] > 40 and far[0] < -40 and near[0] == pytest.approx(-far[0]) and near[1] == pytest.approx(far[1])
    assert first.hip != sit.hip  # seat-groove's first picture is already off the seat's mark by its sway and bob


# The groove, read on the drawing


def test_seat_groove_drawn_bobs_the_head_and_sways_the_hips_as_the_reel_measured():
    performance = seat_groove()
    bob = dance.measure_dance(performance.track("head", "up"), 25, GROOVE)
    sway = dance.measure_dance(performance.track("hip", "right"), 25, GROOVE)
    assert dance.SEAT_GROOVE_BOB.misses(bob) == ()
    assert dance.SEAT_GROOVE_SWAY.misses(sway) == ()


def test_the_drawn_head_bobs_by_the_dance_s_head_radii_in_the_rig_s_head_pixels():
    performance = seat_groove(4)
    up = performance.track("head", "up")
    root = [f.root[1] for f in dance.frames(MOVES["seat-groove"], GROOVE, 0.0, 4 * GROOVE.bar, 25)]
    assert max(up) - min(up) == pytest.approx(max(root) - min(root), rel=1e-6)


def test_a_raised_arm_rides_the_body_with_no_lag():
    performance = sd.perform(routine(dance.Entry(0, 8, MOVES["seat-groove"], hold=RAISED)), GROOVE, 0.0, 8 * GROOVE.bar)
    head = performance.track("head", "up")
    hand = [-p.hands[0][1] / stick.HEAD_R for p in performance.poses]
    assert all(p.hands[0][1] < p.head[1] for p in performance.poses)  # raised above the head's centre
    head_reading, hand_reading = (dance.measure_dance(s, 25, GROOVE) for s in (head, hand))
    assert hand_reading.cycles_per_beat == pytest.approx(1.0, abs=0.02)
    assert hand_reading.hit_offset == pytest.approx(head_reading.hit_offset, abs=0.02)
    # the arm held up does not take seat-groove's shrug: the hand moves as the head does, not 0.70 against its 0.38
    assert hand_reading.peak_to_peak == pytest.approx(head_reading.peak_to_peak, abs=0.01)


def test_the_shrug_fades_on_an_arm_held_past_horizontal_and_stays_on_an_arm_held_low():
    frame = next(iter(dance.frames(MOVES["seat-groove"], GROOVE, 0.0, 0.04, 25)))
    shrug = frame.joints["left_shoulder.down_up"]
    assert shrug != 0
    low = {"left_upper_arm.down_up": -1.1, "right_upper_arm.down_up": -1.1}
    assert sd._carried(frame, low) is frame
    half = {"left_upper_arm.down_up": sd.RAISED_FULL / 2, "right_upper_arm.down_up": -1.1}
    faded = sd._carried(frame, half)
    assert faded.joints["left_shoulder.down_up"] == pytest.approx(shrug / 2)
    assert faded.joints["right_shoulder.down_up"] == frame.joints["right_shoulder.down_up"]
    up = sd._carried(frame, {"left_upper_arm.down_up": 2.0})
    assert up.joints["left_shoulder.down_up"] == 0.0 and up.root == frame.root


def test_the_head_never_turns_within_a_beat_and_the_face_holds_for_the_phrase():
    performance = seat_groove()
    assert performance.faces == ((0, sd.EXPRESSIONS["neutral"]),)
    assert {performance.face_at(n) for n in range(len(performance.poses))} == {sd.EXPRESSIONS["neutral"]}


# Standing


def test_a_standing_bob_keeps_both_feet_on_their_marks_on_the_floor():
    performance = sd.perform(MOVES["bob"], GROOVE, 0.0, 4 * GROOVE.bar)
    assert all(flat(p.feet) == pytest.approx(flat(performance.poses[0].feet)) for p in performance.poses)
    assert all(y == pytest.approx(sd.FLOOR) for y in (performance.poses[0].feet[0][1], performance.poses[0].feet[1][1]))
    assert performance.reach == 0  # the soft knees reach the marks at the top of the bob
    up = performance.track("head", "up")
    assert max(up) - min(up) > 0.1


def test_a_step_touch_lifts_a_foot_only_when_it_is_not_planted_and_never_through_the_floor():
    move = MOVES["step-touch"]
    sampled = list(dance.frames(move, GROOVE, 0.0, 4 * GROOVE.bar, 25))
    performance = sd.perform(move, GROOVE, 0.0, 4 * GROOVE.bar)
    for i, side in enumerate(("left", "right")):  # the stick rig's far foot is the skeleton's left
        held = None
        for frame, pose in zip(sampled, performance.poses, strict=True):
            foot = pose.feet[i]
            assert foot[1] <= sd.FLOOR + 1e-6
            if f"{side}_foot" in frame.planted:
                assert held is None or foot == pytest.approx(held)
                held = foot
            else:
                held = None
    assert min(p.feet[0][1] for p in performance.poses) < sd.FLOOR - 10  # a foot does leave the floor


def test_seated_feet_stay_on_the_car_floor():
    performance = seat_groove(2)
    assert all(flat(p.feet) == pytest.approx(flat(performance.poses[0].feet)) for p in performance.poses)


def test_a_standing_routine_of_four_moves_dances_every_picture():
    entries = (
        dance.Entry(0, 2, MOVES["bob"], expression="smile"),
        dance.Entry(2, 4, MOVES["sway"], transition_beats=1, expression="cool"),
        dance.Entry(4, 6, MOVES["arm-pump"], transition_beats=1, expression="grin"),
        dance.Entry(6, 8, MOVES["step-touch"], transition_beats=1, expression="smirk"),
    )
    performance = sd.perform(routine(*entries), GROOVE, 0.0, 8 * GROOVE.bar)
    assert len(performance.poses) == math.ceil(8 * GROOVE.bar * 25)
    switches = [n for n, _ in performance.faces]
    assert switches == [0] + [math.ceil(GROOVE.at(bar) * 25) for bar in (2, 4, 6)]
    assert [f.mouth for _, f in performance.faces] == ["smile", "smirk", "smile", "smirk"]


def test_a_move_the_routine_calls_either_stands_unless_asked_to_sit():
    standing = sd.perform(MOVES["arm-pump"], GROOVE, 0.0, 0.2)
    sitting = sd.perform(MOVES["arm-pump"], GROOVE, 0.0, 0.2, seated=True)
    assert standing.poses[0].feet[0][1] == pytest.approx(sd.FLOOR)
    assert sitting.poses[0].hip == pytest.approx(sd.SEAT)


def test_hip_places_the_figure_and_a_custom_base_and_profile_are_used():
    moved = sd.perform(MOVES["arm-pump"], GROOVE, 0.0, 0.04, seated=True, hip=(300.0, 1400.0))
    assert moved.poses[0].hip == pytest.approx((300.0, 1400.0))
    cartoon = sd.perform(MOVES["arm-pump"], GROOVE, 0.0, 0.04, seated=True, profile=sk.preset("stick"), base={})
    assert cartoon.poses[0] != moved.poses[0]


def test_a_dance_on_a_hand_the_profile_lacks_names_what_it_dropped():
    move = dance.parse_moves(
        '{"schema": "srstudio.dance-moves/1.0.0", "moves": [{"name": "wiggle", "support": "either", "patterns": ['
        '{"target": "left_index_proximal.stretched", "waveform": "sine", "cycles": 1, "per": "beat", "phase": 0,'
        ' "amplitude": 0.2, "snap": 0.5}]}]}'
    )["wiggle"]
    assert "left_index_proximal.stretched" in sd.perform(move, GROOVE, 0.0, 0.2).dropped


# Expressions


def test_every_expression_is_a_face_the_rig_draws_looking_at_the_viewer():
    for face in sd.EXPRESSIONS.values():
        stick.check_face(face)
        assert face.look == (0.0, 0.0)
    assert {"neutral", "grin", "eyes-closed"} <= set(sd.EXPRESSIONS)


def test_an_unknown_expression_is_refused_before_anything_is_danced():
    bad = routine(dance.Entry(0, 2, MOVES["seat-groove"]), dance.Entry(4, 6, MOVES["seat-groove"], expression="smug"))
    with pytest.raises(sd.ExpressionError, match="entry 1 holds the expression 'smug'") as caught:
        sd.perform(bad, GROOVE, 0.0, GROOVE.bar)
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, ValueError)
    with pytest.raises(sd.ExpressionError, match="rest_face"):
        sd.perform(MOVES["seat-groove"], GROOVE, 0.0, 1.0, rest_face="smug")


def test_faces_switch_only_where_a_phrase_opens_and_a_held_head_turn_turns_the_look():
    entries = (
        dance.Entry(0, 2, MOVES["seat-groove"], expression="grin"),
        dance.Entry(2, 4, MOVES["seat-groove"], transition_beats=2, hold=(("head.turn_left_right", 0.3),)),
        dance.Entry(5, 6, MOVES["seat-groove"], expression="surprised", hold=(("neck.nod_down_up", -0.2),)),
    )
    performance = sd.perform(routine(*entries, bars=6), GROOVE, 0.0, 6 * GROOVE.bar, rest_face="cool")
    opens = [math.ceil(GROOVE.at(bar) * 25 - 1e-9) for bar in (2, 4, 5)]
    assert [n for n, _ in performance.faces] == [0, *opens]
    grin, turned, rest, surprised = (face for _, face in performance.faces)
    assert grin == sd.EXPRESSIONS["grin"]
    assert turned.look == pytest.approx((0.3 / (math.pi / 4), 0.0)) and turned.eyes == "half"  # the rest face
    assert rest == sd.EXPRESSIONS["cool"]
    assert surprised.look == pytest.approx((0.0, 0.2 / (math.pi / 6)))


def test_a_look_past_the_side_of_the_eyes_stops_at_the_side():
    entry = dance.Entry(0, 1, MOVES["seat-groove"], hold=(("head.turn_left_right", 0.7), ("neck.turn_left_right", 0.7)))
    performance = sd.perform(routine(entry, bars=1), GROOVE, 0.0, 0.2, clamp=True)
    assert performance.faces[0][1].look == (1.0, 0.0)


def test_face_at_names_a_picture_inside_the_dance():
    performance = seat_groove(1)
    for picture in (-1, len(performance.poses), 1.5):
        with pytest.raises(sd.StickDanceError, match="picture"):
            performance.face_at(picture)


# Drawing


def test_draw_keys_every_picture_and_draws_one_face_per_phrase():
    entries = (
        dance.Entry(0, 1, MOVES["seat-groove"], expression="grin"),
        dance.Entry(1, 2, MOVES["seat-groove"], expression="neutral"),
    )
    performance = sd.perform(routine(*entries, bars=2), GROOVE, 0.0, 2 * GROOVE.bar)
    cv = canvas()
    figure = sd.draw(cv, cv.comp, performance, blinks=(0.5, GROOVE.bar + 0.5), prefix="noor")
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty")).find(f".//*[@id='{figure.id}']")
    bodies = [g for g in root.findall("group") if g.find("shape[@shape='ellipse']") is None]
    head = next(g for g in root.findall("group") if g.find("shape[@shape='ellipse']") is not None)
    faces = [g for g in head.findall("group") if g.find("group") is not None and g.find("shape") is not None]
    assert len(bodies) == len(performance.poses) and len(faces) == 2
    blinks = [a for a in root.iter("animate") if a.get("property") == "scaleY"]
    assert len(blinks) == 1  # the open eyes blink; the grin's happy eyes do not


def test_a_dance_that_begins_later_holds_its_first_picture_from_zero():
    performance = seat_groove(1)
    poses, keys = performance.keys(begin=2.0)
    assert keys[0].start == 0 and keys[0].pose == keys[1].pose and keys[1].start == 2.0
    assert len(keys) == len(performance.poses) + 1 and len(poses) == len(performance.poses)
    assert keys[-1].start == pytest.approx(2.0 + (len(performance.poses) - 1) / 25)
    cv = canvas(6.0)
    sd.draw(cv, cv.comp, performance, begin=2.0, end=6.0)
    with pytest.raises(sd.StickDanceError, match="begin"):
        performance.keys(begin=-1)
    with pytest.raises(sd.StickDanceError, match="end"):
        sd.draw(cv, cv.comp, performance, end=1.0)
    with pytest.raises(sd.StickDanceError, match="StickDance"):
        sd.draw(cv, cv.comp, performance.poses)


def test_times_and_duration_follow_the_pictures():
    performance = sd.perform(MOVES["seat-groove"], GROOVE, 1.0, 2.0, fps=10)
    assert performance.times == pytest.approx(tuple(1.0 + n / 10 for n in range(10)))
    assert performance.duration == pytest.approx(1.0)


# Bounds and refusals


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"max_frames": 0}, "max_frames"),
        ({"max_frames": 20_000}, "max_frames"),
        ({"max_frames": 10}, "exceed max_frames=10"),
        ({"fps": 0}, "fps"),
        ({"fps": 25.0}, "fps"),
        ({"seated": "yes"}, "seated"),
        ({"clamp": 1}, "clamp"),
        ({"hip": (1.0,)}, "hip"),
        ({"hip": (1.0, math.nan)}, "hip"),
        ({"profile": "stick"}, "SkeletonProfile"),
        ({"base": {"left_upper_arm.down_up": 9.0}}, "base pose"),
    ],
)
def test_perform_refuses_what_it_cannot_dance(kwargs, message):
    with pytest.raises(sd.StickDanceError, match=message):
        sd.perform(MOVES["seat-groove"], GROOVE, 0.0, 1.0, **kwargs)


@pytest.mark.parametrize(("start", "end"), [(-1.0, 1.0), (1.0, 1.0), (0.0, math.inf), ("0", 1.0)])
def test_perform_refuses_a_span_it_cannot_sample(start, end):
    with pytest.raises(sd.StickDanceError, match="span"):
        sd.perform(MOVES["seat-groove"], GROOVE, start, end)


def test_perform_dances_only_a_move_or_a_routine():
    with pytest.raises(sd.StickDanceError, match="Move or a dance.Routine"):
        sd.perform("seat-groove", GROOVE, 0.0, 1.0)


@pytest.mark.parametrize(("point", "axis"), [("hand", "up"), ("head", "forward")])
def test_a_track_follows_the_head_or_the_hips_up_or_right(point, axis):
    with pytest.raises(sd.StickDanceError, match="track"):
        seat_groove(1).track(point, axis)


def test_the_knee_bends_forward_when_the_hint_lies_on_the_leg_and_stops_at_full_reach():
    hip = Vec3(0.0, 0.0, 0.0)
    knee, ankle, short = sd._knee(hip, Vec3(0.0, 0.5, 0.0), 0.3, 0.3, Vec3(0.0, 0.25, 0.0))
    assert knee.z > 0 and ankle == Vec3(0.0, 0.5, 0.0) and short == 0
    knee, ankle, short = sd._knee(hip, Vec3(0.0, 0.8, 0.0), 0.3, 0.3, Vec3(0.0, 0.3, 0.1))
    assert ankle.y == pytest.approx(0.6) and short == pytest.approx(0.2) and knee.y == pytest.approx(0.3)
    knee, ankle, short = sd._knee(hip, hip, 0.3, 0.2, Vec3(0.0, 0.1, 0.0))
    assert short == pytest.approx(0.1) and (ankle - hip).length == pytest.approx(0.1)


# Rendered frames


def _png(path: Path, width: int, height: int, paint) -> Path:
    rows = b"".join(b"\x00" + b"".join(bytes(paint(x, y)) for x in range(width)) for y in range(height))
    chunk = lambda kind, body: struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body))  # noqa: E731
    head = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
    )
    return path


def _ffmpeg() -> str:
    import shutil

    found = shutil.which("ffmpeg")
    if found is None:
        pytest.skip("ffmpeg decodes the frames")
    return found


def test_head_centroids_read_the_centre_of_the_skin_coloured_pixels(tmp_path):
    _ffmpeg()
    skin = tuple(int(stick.SKIN[i : i + 2], 16) for i in (1, 3, 5))
    shade = tuple(int(stick.SKIN_SHADE[i : i + 2], 16) for i in (1, 3, 5))

    def disc(cx, cy):
        return lambda x, y: (skin if x < cx else shade) if (x - cx) ** 2 + (y - cy) ** 2 <= 36 else (40, 90, 160)

    paths = [_png(tmp_path / f"{n}.png", 40, 30, disc(10 + n, 12)) for n in range(3)]
    centres = sd.head_centroids(paths)
    assert [c[0] for c in centres] == pytest.approx([10, 11, 12], abs=0.01)
    assert all(c[1] == pytest.approx(12, abs=0.01) for c in centres)


def test_head_centroids_refuse_frames_they_cannot_read(tmp_path):
    _ffmpeg()
    blank = _png(tmp_path / "blank.png", 8, 8, lambda x, y: (0, 0, 0))
    with pytest.raises(sd.RenderedTrackError, match="no head"):
        sd.head_centroids([blank])
    (tmp_path / "text.png").write_text("not a png at all, long enough for a header")
    with pytest.raises(sd.RenderedTrackError, match="not a PNG"):
        sd.head_centroids([tmp_path / "text.png"])
    with pytest.raises(sd.RenderedTrackError, match="cannot read"):
        sd.head_centroids([tmp_path / "missing.png"])
    broken = tmp_path / "broken.png"
    broken.write_bytes(blank.read_bytes()[:40])
    with pytest.raises(sd.RenderedTrackError, match="cannot decode"):
        sd.head_centroids([broken])
    huge = tmp_path / "huge.png"
    huge.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 5000, 5000) + bytes(9))
    with pytest.raises(sd.RenderedTrackError, match="at most"):
        sd.head_centroids([huge])
    with pytest.raises(sd.RenderedTrackError, match="frames"):
        sd.head_centroids([])
    with pytest.raises(sd.RenderedTrackError, match="frames"):
        sd.head_centroids([blank, blank], max_frames=1)
    with pytest.raises(sd.RenderedTrackError, match="tolerance"):
        sd.head_centroids([blank], tolerance=-1)
    with pytest.raises(sd.RenderedTrackError, match="no no-such-ffmpeg"):
        sd.head_centroids([blank], ffmpeg="no-such-ffmpeg")


RENDER_SCALE = 0.25
RENDER_TOLERANCE = 0.02  # seconds: the drop and the snap land within half a picture of the beat at 25 pictures a second


def test_the_rendered_head_bobs_once_a_beat_and_drops_on_the_beat(scene_render, tmp_path):
    """The engine's own frames, read back: the head's centre of skin pixels cycles once a beat and its low point lands
    on the beat, so nothing between the numbers and the picture (keys, gates, scale) bends the groove."""
    _ffmpeg()
    bars = 2
    performance = seat_groove(bars)
    scene = Scene(version="auto")
    scene.add_project(width=270, height=480, fps="25", duration=performance.duration, background="#204060")
    cv = Canvas(scene, DAYLIGHT, font_asset=None, namer=flat_counter("n"))
    sd.draw(cv, cv.comp, performance, scale=RENDER_SCALE)
    path = tmp_path / "groove.xml"
    path.write_bytes(scene.to_bytes())
    count = len(performance.poses)
    with gpu.held():
        done = subprocess.run(
            [
                str(scene_render),
                "render",
                str(path),
                "--frames",
                f"0..{count}",
                "--output",
                str(tmp_path / "f%04d.png"),
            ],
            capture_output=True,
            text=True,
        )
    assert done.returncode == 0, done.stderr
    frames = sorted(tmp_path.glob("f*.png"))
    assert len(frames) == count
    centres = sd.head_centroids(frames)
    radius = stick.HEAD_R * RENDER_SCALE
    up = [-y / radius for _, y in centres]
    right = [x / radius for x, _ in centres]
    bob = dance.measure_dance(up, 25, GROOVE)
    sway = dance.measure_dance(right, 25, GROOVE)
    drawn = dance.measure_dance(performance.track("head", "up"), 25, GROOVE)
    assert bob.cycles_per_beat == pytest.approx(1.0, abs=0.02)
    assert sway.cycles_per_beat == pytest.approx(1.0, abs=0.02)
    assert bob.hit == "min" and abs(bob.hit_offset) * GROOVE.beat < RENDER_TOLERANCE
    assert sway.hit == "max" and abs(sway.hit_offset) * GROOVE.beat < RENDER_TOLERANCE
    assert bob.peak_to_peak == pytest.approx(drawn.peak_to_peak, abs=0.05)


def test_the_guide_s_car_recipe_runs():
    guide = (Path(__file__).resolve().parent.parent / "docs" / "authoring-stick-dance.md").read_text()
    block = guide.split("<!-- stick-dance:start -->")[1].split("<!-- stick-dance:end -->")[0]
    code = block.split("```python\n", 1)[1].rsplit("```", 1)[0]
    exec(compile(code, "authoring-stick-dance.md", "exec"), {})

"""Swing (ADR 0201): followers that ride a source late through a damped spring, the measures that read a head's path,
lag, follow-through and roll back off any skeleton, and the seat-groove held to the car reel's curve."""

import functools
import json
import math

import numpy as np
import pytest

from srstudio import dance, dance_pose
from srstudio import skeleton as sk
from srstudio._dance_model import MAX_FOLLOWS, MAX_GAIN, SPRING_SPAN, SPRING_TAPS
from srstudio.dance import (
    SEAT_GROOVE_BOB,
    SEAT_GROOVE_SWAY,
    SEAT_GROOVE_SWING,
    ChainLag,
    DanceDataError,
    DanceError,
    DanceMeasureError,
    DanceTarget,
    Entry,
    Follow,
    Move,
    MoveError,
    PathReading,
    PathTarget,
    Pattern,
    Routine,
    SwingReading,
    SwingTarget,
    frames,
    measure_dance,
    measure_lag,
    measure_path,
    measure_swing,
    parse_moves,
    sample,
    spring,
)
from srstudio.dance_pose import BodySeries, body_series
from srstudio.music import Groove

REEL = Groove(129)
FPS = 50
SPAN = 16 * REEL.beat

# The seat-groove as ADR 0186 shipped it: a bob and a snap on the root, the neck and head held.
DRY = Move(
    "seat-groove",
    "seat",
    (
        Pattern("root.up", -0.19, snap=0.422),
        Pattern("root.right", 0.1, snap=0.278),
        Pattern("left_shoulder.down_up", -0.05, snap=0.422),
        Pattern("right_shoulder.down_up", -0.05, snap=0.422),
    ),
    lags=(("left_arm", 0.0), ("right_arm", 0.0)),
)


SNAP = (Pattern("root.right", 0.1, snap=0.278),)


def swung(*follows, patterns=SNAP):
    return Move("probe", "seat", patterns, follows=tuple(follows))


def channel(move, target, fps=FPS, span=SPAN):
    return [f.value(target) for f in frames(move, REEL, 0.0, span, fps)]


@functools.cache
def body(which, preset):
    move = DRY if which == "dry" else dance.moves()[which]
    return body_series(sk.preset(preset), frames(move, REEL, 0.0, SPAN, FPS))


def swing(which, preset):
    b = body(which, preset)
    return measure_swing(b.across, b.up, b.roll, b.lean, FPS, REEL)


# --- the spring -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(("frequency", "damping"), [(3.0, 0.6), (4.0, 0.75), (2.0, 1.0), (1.0, 1.6), (8.0, 0.1)])
def test_a_spring_is_a_bounded_response_that_sums_to_one(frequency, damping):
    taps = spring(frequency, damping)
    assert len(taps) == SPRING_TAPS
    assert sum(w for _, w in taps) == pytest.approx(1.0)
    assert all(0 < back <= SPRING_SPAN for back, _ in taps)
    assert spring(frequency, damping) is taps  # computed once, the same for every frame


def test_an_underdamped_spring_overshoots_and_a_damped_one_does_not():
    assert any(w < 0 for _, w in spring(3.0, 0.4))
    assert all(w >= 0 for _, w in spring(3.0, 1.0))
    assert all(w >= 0 for _, w in spring(3.0, 1.5))


@pytest.mark.parametrize(("frequency", "damping"), [(0.4, 0.8), (9.0, 0.5), (3.0, 0.05), (3.0, 2.5), (1.0, 0.2)])
def test_a_spring_out_of_range_or_ringing_past_its_span_is_refused(frequency, damping):
    with pytest.raises(MoveError):
        spring(frequency, damping)


def test_a_ringing_spring_names_its_rule():
    with pytest.raises(MoveError) as caught:
        spring(1.0, 0.2)
    assert caught.value.to_dict()["code"] == "dance.spring"


# --- a follower -------------------------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"target": "spine.left_right", "source": "spine.left_right", "gain": 1.0},
        {"target": "spine.left_right", "source": "root.right", "gain": 0.0},
        {"target": "spine.left_right", "source": "root.right", "gain": MAX_GAIN + 1},
        {"target": "spine.left_right", "source": "root.right", "gain": 1.0, "lag": -0.1},
        {"target": "spine.left_right", "source": "root.right", "gain": 1.0, "lag": 1.5},
        {"target": "tail.wag", "source": "root.right", "gain": 1.0},
        {"target": "spine.left_right", "source": "root.sideways", "gain": 1.0},
        {"target": "spine.left_right", "source": "root.right", "gain": 1.0, "frequency": 1.0, "damping": 0.2},
        {"target": "spine.left_right", "source": "root.right", "gain": math.nan},
    ],
)
def test_a_follower_that_cannot_move_is_refused(kwargs):
    with pytest.raises(DanceError):
        Follow(**kwargs)


def test_a_follower_trails_its_source_by_its_lag():
    move = swung(Follow("spine.left_right", "root.right", 0.5, lag=0.25, frequency=8.0, damping=1.0))
    reading = measure_lag(channel(move, "root.right"), channel(move, "spine.left_right"), FPS, REEL)
    assert isinstance(reading, ChainLag)
    assert reading.cycles_per_beat == pytest.approx(1, abs=0.01)
    assert 0.25 <= reading.lag <= 0.32  # its lag, and a little more for the spring
    assert reading.gain == pytest.approx(0.5, abs=0.05)


SLOW_SNAP = (Pattern("root.right", 0.1, snap=0.1, cycles=0.25),)  # a quick hit once a bar, then a long glide


def sprung(damping):
    move = Move(
        "probe",
        "seat",
        SLOW_SNAP,
        loop_beats=4,
        follows=(Follow("spine.left_right", "root.right", 1.0, 0, 1.5, damping),),
    )
    return channel(move, "spine.left_right", fps=25, span=40 * REEL.beat)


def test_an_underdamped_follower_overshoots_and_settles():
    assert measure_dance(sprung(0.25), 25, REEL).rebound > 0.05
    assert measure_dance(sprung(1.2), 25, REEL).rebound < 0.005
    assert max(sprung(0.25)) > 0.1 + 0.02  # past its source's own top


def test_a_follower_adds_nothing_to_its_source_and_is_deterministic():
    move = swung(Follow("spine.left_right", "root.right", 0.5, lag=0.1))
    assert channel(move, "root.right") == channel(swung(), "root.right")
    assert sample(move, REEL, 1.234) == sample(move, REEL, 1.234)


def test_a_follower_is_bounded_by_its_gain_times_its_source():
    move = swung(Follow("spine.left_right", "root.right", 0.5, frequency=3.0, damping=0.3))
    spine = channel(move, "spine.left_right")
    taps = spring(3.0, 0.3)
    bound = 0.5 * 0.1 * sum(abs(w) for _, w in taps)
    assert max(abs(v) for v in spine) <= bound + 1e-12


def test_a_move_checks_its_followers():
    lean = Follow("spine.left_right", "root.right", 0.5)
    with pytest.raises(MoveError, match="which nothing moves"):
        swung(Follow("spine.left_right", "root.up", 0.5))
    with pytest.raises(MoveError, match="one pattern or one follower"):
        swung(
            Follow("root.right", "spine.left_right", 0.5),
            patterns=(Pattern("root.right", 0.1), Pattern("spine.left_right", 0.1)),
        )
    with pytest.raises(MoveError, match="one pattern or one follower"):
        swung(lean, lean)
    with pytest.raises(MoveError, match="at most"):
        Move("probe", "seat", (Pattern("root.right", 0.1),), follows=[lean])
    with pytest.raises(MoveError, match="at most"):
        swung(*([lean] * (MAX_FOLLOWS + 1)))
    with pytest.raises(MoveError, match="every follower"):
        Move("probe", "seat", (Pattern("root.right", 0.1),), follows=("spine.left_right",))


def test_a_move_with_followers_is_no_held_pose():
    move = Move("still", "seat", (Pattern("spine.left_right", 0.0, bias=0.1),))
    assert move.held() == (("spine.left_right", 0.1),)
    moving = Move("still", "seat", move.patterns, follows=(Follow("neck.tilt_left_right", "spine.left_right", 1.0),))
    with pytest.raises(MoveError, match="no held pose"):
        moving.held()


def test_a_follower_turns_round_with_its_move():
    follow = Follow("left_shoulder.down_up", "root.right", 0.5, lag=0.1)
    turned = follow.mirror()
    assert (turned.target, turned.source, turned.lag) == ("right_shoulder.down_up", "root.right", 0.1)
    assert turned.gain == pytest.approx(-0.5)  # root.right turns round, the shoulder's lift does not
    groove = dance.moves()["seat-groove"]
    ahead, back = sample(groove, REEL, 0.8), sample(groove.mirror(), REEL, 0.8)
    assert back.value("neck.tilt_left_right") == pytest.approx(-ahead.value("neck.tilt_left_right"))
    assert back.value("head.tilt_left_right") == pytest.approx(-ahead.value("head.tilt_left_right"))


def test_a_transition_blends_the_followers_of_both_moves():
    groove, nod = dance.moves()["seat-groove"], dance.moves()["head-nod"]
    routine = Routine(8, (Entry(0, 4, groove), Entry(4, 8, nod, transition_beats=2)))
    t = REEL.at(4, 1)  # half way through the transition
    neck = sample(routine, REEL, t).value("neck.tilt_left_right")
    assert 0 < abs(neck) < abs(sample(groove, REEL, t).value("neck.tilt_left_right")) + 1e-9
    assert sample(routine, REEL, REEL.at(6)).value("neck.tilt_left_right") == 0.0


# --- the schema -------------------------------------------------------------------------------------------------------


def moves_text(schema="srstudio.dance-moves/1.1.0", **follow):
    item = {"target": "spine.left_right", "source": "root.right", "gain": 0.5} | follow
    move = {
        "name": "probe",
        "support": "seat",
        "patterns": [
            {
                "target": "root.right",
                "waveform": "sine",
                "cycles": 1,
                "per": "beat",
                "phase": 0,
                "amplitude": 0.1,
                "snap": 0.5,
            }
        ],
        "follow": [item],
    }
    return json.dumps({"schema": schema, "moves": [move]})


def test_a_follow_list_reads_from_a_one_one_document():
    move = parse_moves(moves_text(lag=0.1, frequency=4, damping=0.7))["probe"]
    assert move.follows == (Follow("spine.left_right", "root.right", 0.5, 0.1, 4, 0.7),)
    assert parse_moves(moves_text(schema="srstudio.dance-moves/1.4.0"))["probe"].follows[0].lag == 0.0


def test_a_one_zero_document_reads_and_refuses_a_follow_list():
    with pytest.raises(DanceDataError) as caught:
        parse_moves(moves_text(schema="srstudio.dance-moves/1.0.0"))
    assert caught.value.to_dict()["code"] == "dance.unknown"
    plain = json.loads(moves_text(schema="srstudio.dance-moves/1.0.0"))
    del plain["moves"][0]["follow"]
    assert parse_moves(json.dumps(plain))["probe"].follows == ()


@pytest.mark.parametrize(
    "follow",
    [
        {"gain": "0.5"},
        {"gain": True},
        {"lag": math.inf},
        {"swing": 0.2},
        {"gain": 0.0},
        {"source": "spine.left_right"},
        {"frequency": 1, "damping": 0.2},
    ],
)
def test_a_follow_that_is_not_one_is_refused(follow):
    with pytest.raises(
        DanceError, match=r"\$\.moves\[0\]|JSON number"
    ):  # the text's own error, or the model's at its path
        parse_moves(moves_text(**follow))


def test_a_follow_list_is_bounded_and_complete():
    doc = json.loads(moves_text())
    doc["moves"][0]["follow"] = [{"target": "spine.left_right", "source": "root.right"}]
    with pytest.raises(DanceDataError, match="lacks"):
        parse_moves(json.dumps(doc))
    doc["moves"][0]["follow"] = [{"target": "spine.left_right", "source": "root.right", "gain": 1}] * (MAX_FOLLOWS + 1)
    with pytest.raises(DanceDataError, match="at most"):
        parse_moves(json.dumps(doc))


def test_the_shipped_moves_carry_followers():
    assert dance.MOVES_SCHEMA == "srstudio.dance-moves/1.2.0"
    assert all(dance.moves()[name].follows for name in ("seat-groove", "bob", "sway", "head-nod"))


# --- reading a path, a lag and a swing --------------------------------------------------------------------------------


def waves(across, up, n=400, fps=FPS):
    t = np.arange(n) / fps / REEL.beat  # beats
    return [across(b) for b in t], [up(b) for b in t]


def test_a_path_in_step_is_a_line_and_a_quarter_round_is_a_loop():
    line = measure_path(
        *waves(lambda b: 0.5 * math.sin(2 * math.pi * b), lambda b: math.sin(2 * math.pi * b)), FPS, REEL
    )
    assert isinstance(line, PathReading)
    assert line.shape == "line" and line.openness < 0.05 and line.lead == pytest.approx(0, abs=0.01)
    assert line.ratio == pytest.approx(0.5, abs=0.01) and line.cycles_per_beat == pytest.approx(1, abs=0.01)
    loop = measure_path(
        *waves(lambda b: math.sin(2 * math.pi * (b + 0.25)), lambda b: math.sin(2 * math.pi * b)), FPS, REEL
    )
    assert loop.shape == "loop" and loop.openness == pytest.approx(1, abs=0.02)
    assert loop.lead == pytest.approx(0.25, abs=0.01)  # across peaks a quarter beat first


@pytest.mark.parametrize(("phase", "shape"), [(0.0, "U"), (0.125, "figure-8")])
def test_a_path_whose_across_runs_at_half_rate_is_a_u_or_a_figure_eight(phase, shape):
    reading = measure_path(
        *waves(lambda b: math.sin(math.pi * b + 2 * math.pi * phase), lambda b: math.cos(2 * math.pi * b), n=800),
        FPS,
        REEL,
    )
    assert reading.shape == shape


def test_a_path_target_names_each_miss_and_accepts_a_turned_round_lead():
    target = PathTarget(1.0, lead=0.18, ratio=(0.38, 0.56), openness=(0.4, 1.0))
    good = PathReading(1.0, 0.4, 0.84, 0.48, 0.18, 0.6, "loop")
    assert target.misses(good) == ()
    assert target.misses(PathReading(1.0, 0.4, 0.84, 0.48, 0.18 - 0.5, 0.6, "loop")) == ()
    unturned = PathTarget(1.0, lead=0.18, ratio=(0.38, 0.56), openness=(0.4, 1.0), mirrored=False)
    assert len(unturned.misses(PathReading(1.0, 0.4, 0.84, 0.48, -0.32, 0.6, "loop"))) == 1
    misses = target.misses(PathReading(2.0, 0.4, 0.2, 2.0, 0.0, 0.1, "line"))
    assert len(misses) == 4 and any("0.4..1" in m for m in misses)


@pytest.mark.parametrize(
    "changes",
    [
        {"cycles_per_beat": 0},
        {"lead": 0.6},
        {"ratio": (0.5, 0.2)},
        {"openness": (0.2, 1.5)},
        {"lead_tolerance": math.nan},
        {"mirrored": 1},
    ],
)
def test_a_path_target_is_checked_when_built(changes):
    base = {"cycles_per_beat": 1.0, "lead": 0.18, "ratio": (0.38, 0.56), "openness": (0.4, 1.0)}
    with pytest.raises(DanceMeasureError):
        PathTarget(**(base | changes))


@pytest.mark.parametrize(
    ("a", "b", "fps", "groove"),
    [
        ([math.sin(k / 3) for k in range(400)], [0.0] * 400, FPS, REEL),  # flat
        ([math.sin(k / 3) for k in range(400)], [math.sin(k / 3) for k in range(300)], FPS, REEL),
        ([math.sin(k / 3) for k in range(400)], "a series", FPS, REEL),
        ([math.sin(k / 3) for k in range(400)], [math.cos(k / 3) for k in range(400)], 0, REEL),
        ([math.sin(k / 3) for k in range(400)], [math.cos(k / 3) for k in range(400)], FPS, 129),
        ([math.sin(k / 40) for k in range(60)], [math.cos(k / 40) for k in range(60)], FPS, REEL),  # under two cycles
    ],
)
def test_a_pair_that_cannot_be_read_is_refused(a, b, fps, groove):
    with pytest.raises(DanceMeasureError):
        measure_path(a, b, fps, groove)
    with pytest.raises(DanceMeasureError):
        measure_lag(b, a, fps, groove)


def test_a_swing_reads_no_lag_off_a_neck_that_does_not_lean():
    across, up = waves(lambda b: 0.2 * math.sin(2 * math.pi * b), lambda b: 0.4 * math.cos(2 * math.pi * b))
    reading = measure_swing(across, up, [0.0] * 400, [0.0] * 400, FPS, REEL)
    assert isinstance(reading, SwingReading)
    assert reading.lag is None and reading.lean == 0 and reading.roll == 0
    assert any("nothing to follow" in m for m in SwingTarget(lag=(0.0, 0.1)).misses(reading))


@pytest.mark.parametrize(
    ("roll", "lean"),
    [([math.nan] * 400, [0.0] * 400), ([0.0] * 400, [True] * 400), ([0.0] * 300, [0.0] * 400), ([0.0] * 400, "x")],
)
def test_a_swing_refuses_angles_that_are_not_numbers_sampled_together(roll, lean):
    across, up = waves(lambda b: 0.2 * math.sin(2 * math.pi * b), lambda b: 0.4 * math.cos(2 * math.pi * b))
    with pytest.raises(DanceMeasureError):
        measure_swing(across, up, roll, lean, FPS, REEL)


def test_a_swing_target_names_each_miss():
    path = PathReading(1.0, 0.4, 0.84, 0.48, 0.18, 0.6, "loop")
    reading = SwingReading(path, 0.1, ChainLag(1.0, 0.3, 0.5), 0.5, 0.2)
    target = SwingTarget(lean=(0.3, 0.5), lag=(0.0, 0.1), rebound=(0.0, 0.2), roll=0.05)
    misses = target.misses(reading)
    assert len(misses) == 4
    assert SwingTarget().misses(reading) == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"path": "loop"},
        {"lean": (0.5, 0.1)},
        {"lag": (0.2, 0.1)},
        {"lag": (-0.7, 0.1)},
        {"lag": (0.1,)},
        {"rebound": (0.0, 2.0)},
        {"roll": -0.1},
        {"roll": math.nan},
    ],
)
def test_a_swing_target_is_checked_when_built(changes):
    with pytest.raises(DanceMeasureError):
        SwingTarget(**changes)


def test_a_reading_reports_the_rebound_and_a_target_can_hold_it():
    reading = measure_dance(sprung(0.25), 25, REEL)
    assert reading.rebound > 0.05
    held = DanceTarget(1.0, onto=0.2, away=0.3, peak_to_peak=(0, 1), hit="either", rebound=(0.0, 0.01))
    assert any("rebound" in m for m in held.misses(reading))
    with pytest.raises(DanceMeasureError):
        DanceTarget(1.0, onto=0.2, away=0.3, peak_to_peak=(0, 1), rebound=(0.5, 0.1))


# --- the body a dance shows -------------------------------------------------------------------------------------------


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_a_body_at_rest_has_its_head_level_over_its_hips(preset):
    profile = sk.preset(preset)
    shrug = Move("shrug", "seat", (Pattern("left_shoulder.down_up", 0.02),))  # nothing above the shoulders moves
    still = body_series(profile, frames(shrug, REEL, 0.0, 0.2, 25))
    assert isinstance(still, BodySeries)
    assert set(still.across) == {0.0} and set(still.roll) == {0.0} and set(still.lean) == {0.0}
    world = sk.world(profile, sk.rest_pose(profile))
    head_height = (world["hips"].origin.y - world["head"].origin.y) / profile.proportions.head_radius_m
    assert head_height < still.up[0] < head_height + 2


def test_a_body_series_refuses_what_is_not_a_bounded_run_of_frames(monkeypatch):
    profile = sk.preset("realistic")
    with pytest.raises(DanceError, match="at least one"):
        body_series(profile, [])
    with pytest.raises(DanceError, match="DanceFrame"):
        body_series(profile, ["a frame"])
    monkeypatch.setattr(dance_pose, "MAX_FRAMES", 3)
    with pytest.raises(DanceError, match="at most 3"):
        body_series(profile, frames(DRY, REEL, 0.0, 1.0, 25))


# --- the seat-groove against the car reel -----------------------------------------------------------------------------


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_the_dry_seat_groove_misses_the_reel_swing(preset):
    misses = SEAT_GROOVE_SWING.misses(swing("dry", preset))
    assert any("leads up" in m for m in misses)  # its head path runs the wrong way round the loop
    assert any("neck lean" in m for m in misses)  # the neck never leans
    assert any("rebound" in m for m in misses)  # and nothing follows through


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_the_seat_groove_swings_like_the_reel(preset):
    reading = swing("seat-groove", preset)
    assert SEAT_GROOVE_SWING.misses(reading) == ()
    assert reading.path.shape == "loop"
    assert math.degrees(reading.roll) < 0.5  # the head stays level while the neck leans


def test_the_seat_groove_still_bobs_and_sways_as_measured():
    groove = dance.moves()["seat-groove"]
    assert SEAT_GROOVE_BOB.misses(measure_dance(channel(groove, "root.up", 25, 32 * REEL.beat), 25, REEL)) == ()
    assert SEAT_GROOVE_SWAY.misses(measure_dance(channel(groove, "root.right", 25, 32 * REEL.beat), 25, REEL)) == ()


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_the_seat_groove_head_trails_the_hips(preset):
    def trail(which):
        b, hips = body(which, preset), channel(DRY if which == "dry" else dance.moves()[which], "root.right")
        return measure_lag(hips, b.across, FPS, REEL).lag

    assert trail("dry") == pytest.approx(0, abs=0.01)  # the head rides the hips rigidly
    assert trail("seat-groove") >= 0.15


# --- timing: speed and acceleration over the beat ---------------------------------------------------------------------


def _folded(series, harmonics=8, size=400):
    """One beat of ``series`` as a smooth curve: its cycle's harmonics fitted over every beat sampled."""
    beats = np.arange(len(series)) / FPS / REEL.beat

    def basis(b):
        return np.column_stack(
            [np.ones_like(b)] + [f(2 * np.pi * h * b) for h in range(1, harmonics + 1) for f in (np.cos, np.sin)]
        )

    grid = np.arange(size) / size
    return basis(grid) @ np.linalg.lstsq(basis(beats), np.asarray(series), rcond=None)[0]


def _velocity(curve):
    return (np.roll(curve, -1) - np.roll(curve, 1)) / 2


def timing(which, preset):
    """Where the head's sideways speed peaks in each sideways stroke (a share of the stroke, 0.5 for a plain ease), and
    how far that peak sits from the bottom of the bob (beats, either side)."""
    b = body(which, preset)
    x, up = _folded(b.across), _folded(b.up)
    speed, n = np.abs(_velocity(x)), len(x)
    low, high = int(np.argmin(x)), int(np.argmax(x))
    strokes = []
    for a, z in ((high, low), (low, high)):
        size = (z - a) % n
        strokes.append(int(np.argmax(speed[(a + np.arange(size + 1)) % n])) / size)
    away = ((int(np.argmax(speed)) - int(np.argmin(up))) % n) / n
    return strokes, abs((away + 0.5) % 1 - 0.5)


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_the_dry_seat_groove_eases_every_stroke_evenly(preset):
    strokes, _ = timing("dry", preset)
    assert strokes == pytest.approx([0.5, 0.5], abs=0.01)


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_the_seat_groove_strokes_build_late_as_the_reel_does(preset):
    # The reel's head peaks its sideways speed 0.72 of the way through one stroke and 0.53 through the other (medians).
    strokes, _ = timing("seat-groove", preset)
    assert max(strokes) >= 0.65 and min(strokes) >= 0.45
    assert max(timing("dry", preset)[0]) < 0.65


@pytest.mark.parametrize("preset", sk.PRESETS)
def test_the_seat_groove_peaks_its_sideways_speed_where_the_reel_does(preset):
    # The reel's fastest sideways travel is 0.20..0.25 beats from the bottom of its bob in seven shots of eight.
    _, retuned = timing("seat-groove", preset)
    _, dry = timing("dry", preset)
    assert 0.17 <= retuned <= 0.30
    assert not 0.17 <= dry <= 0.30


# --- every swung preset on every character ----------------------------------------------------------------------------


@pytest.mark.parametrize("preset", sk.PRESETS)
@pytest.mark.parametrize("name", ["seat-groove", "bob", "sway", "head-nod"])
def test_a_swung_preset_stays_within_every_joint_limit(name, preset):
    move = dance.moves()[name]
    span = 2 * move.loop_beats * REEL.beat + 2 * SPRING_SPAN * REEL.beat
    b = body_series(sk.preset(preset), frames(move, REEL, 0.0, span, 25))  # refuses a joint past its limit
    assert len(b.across) > 0


@pytest.mark.parametrize(
    ("name", "source", "follower"),
    [
        ("bob", "root.up", "neck.nod_down_up"),
        ("sway", "root.right", "neck.tilt_left_right"),
        ("head-nod", "neck.nod_down_up", "upper_chest.front_back"),
        ("seat-groove", "root.right", "neck.tilt_left_right"),
    ],
)
def test_a_swung_preset_follows_late(name, source, follower):
    move = dance.moves()[name]
    span = 16 * move.loop_beats * REEL.beat
    reading = measure_lag(channel(move, source, span=span), channel(move, follower, span=span), FPS, REEL)
    assert reading.lag > 0.02

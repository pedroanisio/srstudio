"""A gesture's own timing: the ``curve`` waveform holds one cycle's motion as samples, read strictly, and plays them
back through a periodic cubic spline whose velocity and acceleration are continuous everywhere, the loop's seam
included (ADR 0204)."""

import copy
import json
import math

import pytest

from srstudio import dance
from srstudio.dance import Curve, DanceDataError, Move, MoveError, Pattern, parse_moves, sample, wave
from srstudio.music import Groove


def cosine(n=16):
    return tuple(math.cos(2 * math.pi * k / n) for k in range(n))


def seam_twice():
    raw = cosine(15)
    return tuple(-1 + 2 * (y - min(raw)) / (1 - min(raw)) for y in raw)


def whip(n=24):
    """A slow lift away from the hit and a quick strike back onto it: the hit lands fast, not eased."""
    out = []
    for k in range(n):
        u = k / n
        out.append(math.cos(math.pi * u / 0.75) if u < 0.75 else -math.cos(math.pi * (u - 0.75) / 0.25))
    return tuple(out)


def test_a_curve_passes_through_its_samples_and_hits_at_zero():
    shape = Curve(whip())
    for k, y in enumerate(whip()):
        assert shape.value(k / 24) == pytest.approx(y, abs=1e-12)
    assert shape.value(0.0) == 1.0 and shape.value(1.0) == pytest.approx(1.0, abs=1e-12)
    assert wave("curve", 0.5, 0.25, shape) == pytest.approx(shape.value(0.25))


@pytest.mark.parametrize("points", [cosine(), whip(), cosine(64)])
def test_position_velocity_and_acceleration_are_continuous_at_every_knot_and_across_the_seam(points):
    shape = Curve(points)
    n, eps = len(points), 1e-9
    for k in range(n + 1):
        u = k / n
        for read in (shape.value, shape.velocity, shape.acceleration):
            left, right = read(u - eps), read(u + eps)
            scale = max(1.0, abs(left), abs(right))
            assert abs(left - right) <= 1e-5 * scale, (read.__name__, k)
    assert shape.velocity(0.0) == pytest.approx(shape.velocity(1.0), abs=1e-9)
    assert shape.acceleration(0.0) == pytest.approx(shape.acceleration(1.0), abs=1e-9)


def test_a_sampled_cosine_keeps_its_velocity_and_acceleration():
    """Sixteen samples of a cosine play back its speed within 0.5% and its acceleration within 2%: what the
    interpolant was chosen for."""
    shape = Curve(cosine())
    grid = [i / 1024 for i in range(1024)]
    assert max(abs(shape.velocity(u)) for u in grid) == pytest.approx(2 * math.pi, rel=5e-3)
    assert max(abs(shape.acceleration(u)) for u in grid) == pytest.approx((2 * math.pi) ** 2, rel=2e-2)
    for u in grid[::32]:
        assert shape.velocity(u) == pytest.approx(-2 * math.pi * math.sin(2 * math.pi * u), abs=0.05)


def test_the_whip_keeps_its_quick_strike():
    shape = Curve(whip())
    grid = [i / 2048 for i in range(2048)]
    speeds = [abs(shape.velocity(u)) for u in grid]
    fastest = grid[speeds.index(max(speeds))]
    assert 0.8 < fastest < 0.95  # in the strike back onto the hit, not in the slow lift
    assert max(speeds) == pytest.approx(math.pi / 0.25 * 1.0, rel=0.05)


@pytest.mark.parametrize(
    ("points", "why"),
    [
        (cosine(4), "dance.curve"),  # too few to hold a gesture
        (cosine(65), "dance.curve"),  # past the bound
        ((1.0, *([float("nan")] * 7)), "dance.curve"),
        ((1.0, *([float("inf")] * 7)), "dance.curve"),
        ((1.0, True, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0), "dance.curve"),
        ((1.0, "0", -1.0, 0.0, 0.0, 0.0, 0.0, 0.0), "dance.curve"),
        (tuple(0.9 * y for y in cosine()), "dance.curve"),  # the hit is not at +1
        (tuple(y if y > -0.99 else -0.9 for y in cosine()), "dance.curve"),  # the far extreme is not at -1
        (tuple(min(1.2, 1.2 * y) for y in cosine()), "dance.curve"),  # a sample past +1
        ((1.0, 0.5, 0.0, 0.8, 1.0, 0.0, -1.0, 0.0), "dance.curve"),  # a second hit inside the cycle
        ((*seam_twice(), 1.0), "dance.curve"),  # the seam written twice: the peak falls between them
        ((1.0, 1.0, 1.0, 1.0, -1.0, -1.0, -1.0, -1.0), "dance.curve"),  # rings past the bounds between samples
        ([1.0, 0.0, -1.0, 0.0, 1.0, 0.0, -1.0, 0.0], "dance.curve"),  # a list, not a tuple
    ],
)
def test_a_curve_outside_its_contract_is_refused(points, why):
    with pytest.raises(MoveError) as caught:
        Curve(points)
    assert caught.value.to_dict()["code"] == why


def test_a_curve_pattern_needs_its_samples_and_no_other_waveform_takes_them():
    with pytest.raises(MoveError):
        Pattern("chest.front_back", 0.2, waveform="curve")
    with pytest.raises(MoveError):
        Pattern("chest.front_back", 0.2, waveform="sine", curve=cosine())
    with pytest.raises(MoveError):
        wave("curve", 0.5, 0.1)
    p = Pattern("chest.front_back", 0.2, waveform="curve", curve=whip())
    assert p.shape is not None and p.shape.points == whip()
    assert p.timing() != Pattern("chest.front_back", 0.2, waveform="curve", curve=cosine()).timing()


def test_a_curve_move_samples_the_curve_on_the_beat_and_mirrors_with_it():
    groove = Groove(120)
    move = Move("whip", "either", (Pattern("left_upper_arm.down_up", 0.3, waveform="curve", curve=whip()),))
    for k in range(48):
        t = k * groove.beat / 48
        expected = 0.3 * Curve(whip()).value(k / 48)
        assert sample(move, groove, t).value("left_upper_arm.down_up") == pytest.approx(expected, abs=1e-12)
    flipped = move.mirror()
    assert flipped.patterns[0].target == "right_upper_arm.down_up" and flipped.patterns[0].curve == whip()
    assert flipped.mirror() == move


# --- the moves schema, 1.1.0 ----------------------------------------------------------------------------------------


def curve_document(schema=None, **pattern):
    return {
        "schema": schema or dance.MOVES_SCHEMA,
        "moves": [
            {
                "name": "probe",
                "support": "either",
                "patterns": [
                    {
                        "target": "chest.front_back",
                        "amplitude": 0.2,
                        "cycles": 1,
                        "per": "beat",
                        "phase": 0,
                        "waveform": "curve",
                        "curve": list(whip()),
                    }
                    | pattern
                ],
            }
        ],
    }


def test_the_moves_schema_reads_a_curve():
    assert dance.MOVES_SCHEMA == "srstudio.dance-moves/1.2.0"
    move = parse_moves(json.dumps(curve_document()))["probe"]
    assert move.patterns[0].waveform == "curve" and move.patterns[0].curve == whip()


def test_a_1_0_document_still_reads_and_cannot_hold_a_curve():
    old = curve_document("srstudio.dance-moves/1.0.0")
    with pytest.raises(DanceDataError):
        parse_moves(json.dumps(old))
    plain = copy.deepcopy(old)
    plain["moves"][0]["patterns"][0] |= {"waveform": "sine", "snap": 0.5}
    del plain["moves"][0]["patterns"][0]["curve"]
    assert parse_moves(json.dumps(plain))["probe"].patterns[0].waveform == "sine"


@pytest.mark.parametrize(
    "pattern",
    [
        {"snap": 0.5},  # a curve's shape is its samples
        {"curve": "1,0,-1"},
        {"curve": [1.0] + ["0"] * 15},
        {"curve": [1.0, 0.0, -1.0] * 30},
        {"curve": None},
        {"waveform": "sine", "snap": 0.5},  # samples on a stock waveform
    ],
)
def test_a_malformed_curve_is_refused(pattern):
    with pytest.raises(DanceDataError):
        parse_moves(json.dumps(curve_document(**pattern)))


def test_a_curve_without_samples_is_refused():
    data = curve_document()
    del data["moves"][0]["patterns"][0]["curve"]
    with pytest.raises(DanceDataError):
        parse_moves(json.dumps(data))


def test_a_curve_that_breaks_the_model_is_refused_at_its_path():
    with pytest.raises(MoveError) as caught:
        parse_moves(json.dumps(curve_document(curve=[0.5, 0.0, -1.0, 0.0] * 4)))
    assert caught.value.to_dict()["path"].startswith("$.moves[0].patterns[0]")


def test_the_shipped_presets_are_a_1_2_document():
    from importlib.resources import files

    data = json.loads(files("srstudio").joinpath("assets/dance/moves.json").read_text())
    assert data["schema"] == "srstudio.dance-moves/1.2.0"

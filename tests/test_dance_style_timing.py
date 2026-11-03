"""A style holds a gesture's timing (ADR 0204): ``srstudio.dance-style/1.1.0`` adds, per channel, ranges for the
place of the fastest moment, the attack and release in beats and the peak acceleration, and the mean velocity profile
with how far a dance's may lie from it, each only where enough windows read more than a sine. A 1.0 record still
reads, with no timing."""

import dataclasses
import json
import math

import pytest

from srstudio import dance, dance_style
from srstudio import dance_study as ds
from srstudio.music import Groove

GROOVE = Groove(120)
FPS = 30
BY = {"tool": "tests/test_dance_style_timing.py", "model": "Claude Opus 5.5 (claude-opus-5-5) in Claude Code"}
REFERENCE = dance_style.Reference(
    description="a synthetic reference: a whip of both arms on the realistic skeleton",
    source_sha256="0" * 64,
    estimator="srstudio-skeleton",
    estimator_version="1.0.0",
    model_sha256="0" * 64,
    seconds=8.0,
    frames=240,
    used=240,
    rejected={"lost": 0, "low_confidence": 0, "implausible": 0, "jump": 0, "arm": 0, "repeat": 0},
    bpm=120.0,
    beats_per_bar=4,
    offset_s=0.0,
)


def whip(n: int = 24, strike: float = 0.25) -> tuple[float, ...]:
    away = 1 - strike
    return tuple(
        math.cos(math.pi * (k / n) / away) if k / n < away else -math.cos(math.pi * (k / n - away) / strike)
        for k in range(n)
    )


def arms(curve: tuple[float, ...]) -> list:
    move = dance.Move(
        "probe",
        "either",
        tuple(
            dance.Pattern(f"{side}_upper_arm.down_up", 0.4, waveform="curve", curve=curve) for side in ("left", "right")
        ),
    )
    return list(dance.frames(move, GROOVE, 0.0, 16 * GROOVE.beat, FPS))


WHIP = arms(whip())
BACK = arms((whip()[0], *reversed(whip()[1:])))  # the same gesture played backwards: slow onto the hit, quick off it
READING = ds.measure_style(ds.dance_body(WHIP, FPS), GROOVE)
STYLE = dance_style.derive(READING, name="whip", description="a whip", reference=REFERENCE, generated_by=BY)


def target(style: dance_style.DanceStyle, name: str = "arms.height") -> dance_style.ChannelTarget:
    return next(c for c in style.channels if c.name == name)


def test_a_style_holds_the_timing_its_reference_was_read_with():
    arms_target, read = target(STYLE), READING.channels["arms.height"]
    assert read.timed >= ds.MIN_WINDOWS
    for name in dance_style.TIMING:
        assert getattr(arms_target, name) is not None
    assert arms_target.peak_speed_phase[0] <= read.peak_speed_phase.p50 <= arms_target.peak_speed_phase[1]
    assert arms_target.attack[0] <= read.attack.p50 <= arms_target.attack[1]
    assert len(arms_target.velocity) == dance.PROFILE_POINTS
    assert arms_target.profile_distance is not None and arms_target.profile_distance[0] == 0.0
    assert arms_target.evidence["timed"] == read.timed
    record = json.loads(dance_style.dump_style(STYLE))
    assert record["schema"] == dance_style.SCHEMA == "srstudio.dance-style/1.2.0"
    assert record["reference"]["rejected"]["repeat"] == 0
    assert dance_style.parse_style(dance_style.dump_style(STYLE)) == STYLE


def test_the_dance_it_was_read_from_meets_its_timing_and_its_time_reverse_misses_it():
    """Played backwards, the whip's quick stroke lands on the other extreme, and a reading counts its strokes from
    whichever extreme the quicker one lands on: the strokes match, and the profile and the fastest moment do not."""
    assert dance_style.check(STYLE, WHIP, GROOVE, FPS).misses == ()
    missed = dance_style.check(STYLE, BACK, GROOVE, FPS).misses
    timing = {m.measure for m in missed if m.channel == "arms.height"}
    assert {"profile_distance", "peak_speed_phase"} <= timing
    words = next(m.words for m in missed if m.measure == "profile_distance")
    assert "arms.height" in words and "profile" in words


def test_a_dance_read_as_a_sine_misses_the_timing_as_holding_none():
    sine = dance_style.check(STYLE, arms(tuple(math.cos(2 * math.pi * k / 16) for k in range(16))), GROOVE, FPS)
    found = [m for m in sine.misses if m.channel == "arms.height" and m.measure in dance_style.TIMING]
    assert found  # a sine's own timing, read as a sine is: no stroke of its own
    assert all(m.ours is not None or "no more than a sine" in m.words for m in found)


def test_windows_that_disagree_on_the_profile_give_no_profile_target():
    read = READING.channels["arms.height"]
    wide = dataclasses.replace(read, profile_spread=ds.Spread(0.2, 0.3, 0.35, 0.4, 0.5, read.timed))
    channels = dict(READING.channels) | {"arms.height": wide}
    style = dance_style.derive(
        dataclasses.replace(READING, channels=channels),
        name="whip",
        description="a whip",
        reference=REFERENCE,
        generated_by=BY,
    )
    assert target(style).velocity is None and target(style).profile_distance is None
    assert target(style).attack is not None  # the strokes still agree


def test_too_few_timed_windows_give_no_timing():
    read = READING.channels["arms.height"]
    few = dataclasses.replace(read, timed=ds.MIN_WINDOWS - 1)
    style = dance_style.derive(
        dataclasses.replace(READING, channels=dict(READING.channels) | {"arms.height": few}),
        name="whip",
        description="a whip",
        reference=REFERENCE,
        generated_by=BY,
    )
    assert all(getattr(target(style), name) is None for name in (*dance_style.TIMING, "velocity"))


def test_a_phase_is_met_either_side_of_the_seam():
    phase = dataclasses.replace(target(STYLE), peak_speed_phase=(0.95, 1.03))
    style = dataclasses.replace(STYLE, channels=(phase,), lags=())
    read = READING.channels["arms.height"]
    for ours, missed in ((0.01, False), (0.99, False), (0.5, True)):
        moved = dataclasses.replace(read, peak_speed_phase=ds.Spread(ours, ours, ours, ours, ours, 5))
        reading = dataclasses.replace(READING, channels=dict(READING.channels) | {"arms.height": moved})
        assert any(m.measure == "peak_speed_phase" for m in style.misses(reading)) is missed


def _record_1_0() -> dict:
    data = json.loads(dance_style.dump_style(STYLE))
    data["schema"] = "srstudio.dance-style/1.0.0"
    del data["reference"]["rejected"]["repeat"]
    for channel in data["channels"]:
        for name in (*dance_style.TIMING, "velocity", "profile_distance", "provenance", "confidence"):
            del channel[name]  # 1.0 held neither timing nor provenance (ADR 0202)
        del channel["evidence"]["timed"]
    return data


def test_a_1_0_record_reads_with_no_timing():
    style = dance_style.parse_style(json.dumps(_record_1_0()))
    assert style.reference.rejected["repeat"] == 0
    assert all(getattr(c, name) is None for c in style.channels for name in (*dance_style.TIMING, "velocity"))
    assert all(c.evidence["timed"] == 0 for c in style.channels)


def _edit(change) -> str:
    data = json.loads(dance_style.dump_style(STYLE))
    change(data)
    return json.dumps(data)


@pytest.mark.parametrize(
    ("text", "error", "words"),
    [
        (
            lambda: json.dumps(_record_1_0() | {"schema": "srstudio.dance-style/1.1.0"}),
            dance_style.StyleFormatError,
            "missing",
        ),
        (
            lambda: json.dumps(
                {**_record_1_0(), "channels": [c | {"attack": None} for c in _record_1_0()["channels"]]}
            ),
            dance_style.StyleFormatError,
            "unknown",
        ),
        (lambda: _edit(lambda d: d["reference"]["rejected"].pop("repeat")), dance_style.StyleFormatError, "missing"),
        (lambda: _edit(lambda d: d["channels"][8].update(velocity=[0.5] * 31)), dance_style.StyleFormatError, "32"),
        (lambda: _edit(lambda d: d["channels"][8].update(velocity=[1.5] * 32)), dance_style.StyleValueError, "lies in"),
        (lambda: _edit(lambda d: d["channels"][8].update(velocity=None)), dance_style.StyleValueError, "together"),
        (lambda: _edit(lambda d: d["channels"][8].update(attack=[0.1, 99.0])), dance_style.StyleValueError, "lies in"),
        (lambda: _edit(lambda d: d["channels"][8]["evidence"].update(timed=99)), dance_style.StyleValueError, "timed"),
        (lambda: _edit(lambda d: d["channels"][10].update(attack=[0.1, 0.2])), dance_style.StyleValueError, "level"),
    ],
)
def test_a_timing_record_outside_the_schema_is_refused(text, error, words):
    with pytest.raises(error, match=words):
        dance_style.parse_style(text())


def test_only_a_channel_read_in_the_pictures_plane_holds_timing():
    """A channel that needs the estimator's depth (trust below good) reads its timing with that depth's guess in it:
    its windows are counted, and it holds no timing target."""
    lean = READING.channels["torso.lean"]
    arms_read = READING.channels["arms.height"]
    fields = ("overtones", "timed", *dance_style.TIMING, "velocity", "shape", "profile_spread")
    counts = {"read": arms_read.read, "still": 0, "locked": arms_read.locked}
    timed = dataclasses.replace(lean, **counts, **{name: getattr(arms_read, name) for name in fields})
    style = dance_style.derive(
        dataclasses.replace(READING, channels=dict(READING.channels) | {"torso.lean": timed}),
        name="whip",
        description="a whip",
        reference=REFERENCE,
        generated_by=BY,
    )
    assert target(style, "torso.lean").evidence["timed"] == timed.timed >= ds.MIN_WINDOWS
    assert all(getattr(target(style, "torso.lean"), name) is None for name in (*dance_style.TIMING, "velocity"))
    assert target(style).attack is not None

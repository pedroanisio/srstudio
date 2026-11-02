"""The dance study's measures (ADR 0200): a reference's pose record and one of our dances become the same body track
and are measured by the same code. A record is untrusted: refused frames are counted by reason and never filled."""

import math
from types import MappingProxyType

import numpy as np
import pytest

from srstudio import dance
from srstudio import dance_study as ds
from srstudio import pose_track as pt
from srstudio.music import Groove
from support.pose_records import edited, record

GROOVE = Groove(120)  # two beats a second
FPS = 15


def frames(move: str, bars: int = 4, fps: int = FPS, groove: Groove = GROOVE):
    return list(dance.frames(dance.moves()[move], groove, 0.0, bars * groove.bar, fps))


@pytest.fixture(scope="module")
def bounce():
    return frames("bounce")


def test_a_dance_and_its_perfect_pose_record_measure_alike(bounce):
    ours = ds.measure_style(ds.dance_body(bounce, FPS), GROOVE)
    seen = ds.measure_style(ds.reference_body(pt.from_data(ds.pose_record(bounce, FPS))), GROOVE)
    assert seen.used == ours.used == len(bounce) and dict(seen.rejected) == dict.fromkeys(seen.rejected, 0)
    for name, mine in ours.channels.items():
        theirs = seen.channels[name]
        assert (mine.level is None) == (theirs.level is None)
        if mine.level is not None:
            assert theirs.level.p50 == pytest.approx(mine.level.p50, rel=1e-3, abs=2e-3), name
        if mine.peak_to_peak is not None:
            assert theirs.peak_to_peak.p50 == pytest.approx(mine.peak_to_peak.p50, abs=2e-3), name


def test_a_bounce_reads_twice_a_beat_on_the_beat_through_the_knees(bounce):
    reading = ds.measure_style(ds.dance_body(bounce, FPS), GROOVE)
    knees = reading.channels["knees.bend"]
    assert knees.read == knees.windows == 5 and knees.locked == 5
    assert knees.cycles_per_beat.p50 == pytest.approx(2.0, abs=0.01)
    assert abs(knees.hit_offset.p50) < 0.02
    assert reading.channels["torso.twist"].still == 5 and reading.channels["torso.twist"].peak_to_peak.p50 == 0.0
    assert reading.channels["stance.width"].level.p50 == pytest.approx(1.67, abs=0.05)


def test_the_unit_is_a_realistic_head_radius_by_the_torso():
    assert ds.torso_head_radii() == pytest.approx(4.8, abs=0.05)


def test_a_known_bob_reads_its_size_and_cycle():
    """The synthetic figure drops 0.06 m twice a second, feet still: at 120 BPM that is once a beat."""
    track = ds.reference_body(pt.from_data(record(300, bob=0.06, hz=2.0)))
    reading = ds.measure_style(track, GROOVE)
    hips = reading.channels["hips.bounce"]
    scale = ds.torso_head_radii() / 0.5  # the figure's torso is half a metre
    assert hips.cycles_per_beat.p50 == pytest.approx(1.0, abs=0.01)
    assert hips.peak_to_peak.p50 == pytest.approx(0.06 * scale, rel=0.02)
    assert hips.noise < 0.005  # a smooth motion is no noise
    head = reading.channels["head.bob"]
    assert head.still == head.windows  # the head rides the shoulders: nothing moves between them


def test_the_noise_reads_the_estimates_own_scatter():
    data = record(300, bob=0.06, hz=2.0)
    rng = np.random.default_rng(3)
    for frame in data["frames"]:
        frame["world"] = [[round(v + rng.normal(0, 0.004), 5) for v in row] for row in frame["world"]]
    reading = ds.measure_style(ds.reference_body(pt.from_data(data)), GROOVE)
    scale = ds.torso_head_radii() / 0.5
    assert reading.channels["head.bob"].noise == pytest.approx(0.004 * scale, rel=0.2)


def test_refused_frames_are_counted_by_reason_and_never_filled():
    data = record(300, lost=(5, 6))
    hip = pt.LANDMARKS.index("left_hip")
    shin = pt.LANDMARKS.index("left_ankle")
    head = (pt.LANDMARKS.index("left_ear"), pt.LANDMARKS.index("right_ear"))
    data["frames"][10]["image"][hip][3] = 0.1  # a hip barely seen
    data["frames"][20]["world"][shin] = [0.1, 2.5, 0.0]  # a shin three times its length
    data["frames"][30]["world"][head[0]] = [0.07, -2.6, 0.0]  # the head two metres up in a 30th of a second
    data["frames"][30]["world"][head[1]] = [-0.07, -2.6, 0.0]
    wrist = pt.LANDMARKS.index("right_wrist")
    data["frames"][40]["world"][wrist] = [-0.3, 0.6, -0.02]  # a forearm three times its length
    track = ds.reference_body(pt.from_data(data))
    assert dict(track.rejected) == {"lost": 2, "low_confidence": 1, "implausible": 1, "jump": 1, "arm": 1}
    assert track.used == 300 - 5
    right_arm = [ds.POINTS.index(p) for p in ("right_elbow", "right_wrist")]
    assert not track.seen[40, right_arm].any() and track.seen[40, ds.POINTS.index("left_wrist")]
    for f in (5, 6, 10, 20, 30):
        assert not track.seen[f].any() and np.isnan(track.points[f]).all()
    values, valid = ds.channel(track, "hips.bounce")
    assert not valid[[5, 6, 10, 20, 30]].any() and np.isnan(values[20])
    assert ds._runs(valid)[:3] == [(0, 5), (7, 10), (11, 20)]


def test_windows_read_through_short_gaps_and_skip_long_ones():
    whole = ds.measure_style(ds.reference_body(pt.from_data(record(300, bob=0.06, hz=2.0))), GROOVE)
    rng = np.random.default_rng(5)
    holes = tuple(int(i) for i in np.flatnonzero(rng.random(300) < 0.2))
    gappy = ds.measure_style(ds.reference_body(pt.from_data(record(300, lost=holes, bob=0.06, hz=2.0))), GROOVE)
    a, b = whole.channels["hips.bounce"], gappy.channels["hips.bounce"]
    assert b.windows == a.windows and b.read == a.read
    assert b.peak_to_peak.p50 == pytest.approx(a.peak_to_peak.p50, rel=0.02)
    assert b.cycles_per_beat.p50 == pytest.approx(1.0, abs=0.01)
    long_gap = ds.measure_style(
        ds.reference_body(pt.from_data(record(300, lost=tuple(range(140, 160)), bob=0.06))), GROOVE
    )
    assert long_gap.channels["hips.bounce"].windows < a.windows
    assert long_gap.lags["hips>chest"].windows < whole.lags["hips>chest"].windows


def test_a_point_seen_too_faintly_leaves_only_its_channels():
    data = record(120)
    wrist = pt.LANDMARKS.index("right_wrist")
    for frame in data["frames"]:
        frame["image"][wrist][3] = 0.2
    track = ds.reference_body(pt.from_data(data))
    assert track.used == 120
    assert not ds.channel(track, "arms.height")[1].any() and ds.channel(track, "knees.bend")[1].all()
    reading = ds.measure_style(track, GROOVE)
    assert reading.channels["arms.height"].level is None and reading.channels["hands.travel"].level is None


def test_a_track_with_no_dancer_or_off_the_clock_cannot_be_measured():
    lost = edited(record(20, lost=tuple(range(20))), "subject.first_frame", None)
    with pytest.raises(ds.DanceStudyError, match="nothing to measure"):
        ds.reference_body(pt.from_data(lost))
    faint = record(20)
    for frame in faint["frames"]:
        for row in frame["image"]:
            row[3] = 0.1
    with pytest.raises(ds.DanceStudyError, match="nothing to measure"):
        ds.reference_body(pt.from_data(faint))
    odd = record(20, fps=29.97)
    with pytest.raises(ds.DanceStudyError, match="resample"):
        ds.reference_body(pt.from_data(odd))
    with pytest.raises(ds.DanceStudyError):
        ds.reference_body(pt.from_data(record(20)), min_visibility=1.5)
    with pytest.raises(ds.DanceStudyError):
        ds.reference_body(record(20))


def test_our_frames_must_be_dance_frames_on_one_clock(bounce):
    with pytest.raises(ds.DanceStudyError, match="whole number"):
        ds.dance_body(bounce, 0)
    with pytest.raises(ds.DanceStudyError, match="DanceFrame"):
        ds.dance_body([], FPS)
    with pytest.raises(ds.DanceStudyError, match="apart"):
        ds.dance_body(bounce[::2], FPS)
    with pytest.raises(ds.DanceStudyError, match="BodyTrack"):
        ds.measure_style(bounce, GROOVE)
    track = ds.dance_body(bounce[:20], FPS)
    with pytest.raises(ds.DanceStudyError, match="Groove"):
        ds.measure_style(track, 120)
    with pytest.raises(ds.DanceStudyError, match="no channel"):
        ds.channel(track, "tail.wag")


def test_a_short_dance_reads_levels_but_no_windows(bounce):
    reading = ds.measure_style(ds.dance_body(bounce[:40], FPS), GROOVE)
    knees = reading.channels["knees.bend"]
    assert knees.windows == 0 and knees.level is not None and knees.cycles_per_beat is None


def _track(hips_up, chest_up, fps=30):
    """A body standing still but for its hips and chest heights, given per frame."""
    n = len(hips_up)
    rest = np.array(
        [[0.9 * s, 0, 0] for s in (-1, 1)]
        + [[0.9 * s, 4, 0] for s in (-1, 1)]
        + [[0.9 * s, 8, 0] for s in (-1, 1)]
        + [[2.0 * s, -4.8, 0] for s in (-1, 1)]
        + [[2.4 * s, -2.4, 0] for s in (-1, 1)]
        + [[2.6 * s, 0, 0] for s in (-1, 1)]
        + [[0, -7, 0]]
    )
    points = np.repeat(rest[None], n, axis=0)
    for p in (0, 1):
        points[:, p, 1] -= hips_up
    for p in (6, 7, 8, 9, 10, 11, 12):
        points[:, p, 1] -= chest_up
    return ds.BodyTrack(fps, 0.0, points, np.ones((n, 13), bool), MappingProxyType({}), "test")


def test_the_lag_from_hips_to_chest_is_read_in_beats():
    t = np.arange(600) / 30
    hips = 0.3 * np.sin(2 * math.pi * 2 * t)
    chest = 0.3 * np.sin(2 * math.pi * 2 * (t - 0.125))  # a quarter of a 0.5 s beat later
    reading = ds.measure_style(_track(hips, chest), GROOVE)
    lag = reading.lags["hips>chest"]
    assert lag.read == lag.windows > 4 and lag.beats.p50 == pytest.approx(0.25, abs=0.02)
    assert lag.correlation.p50 > 0.9
    assert reading.lags["chest>head"].beats.p50 == pytest.approx(0.0, abs=0.02)


def test_motions_that_do_not_correlate_read_no_lag():
    rng = np.random.default_rng(7)
    reading = ds.measure_style(_track(rng.normal(0, 0.2, 600), rng.normal(0, 0.2, 600)), GROOVE)
    lag = reading.lags["hips>chest"]
    assert lag.windows > 0 and lag.read < lag.windows


def test_a_body_track_checks_its_own_shape():
    good = np.zeros((4, 13, 3))
    seen = np.ones((4, 13), bool)
    with pytest.raises(ds.DanceStudyError, match="frames x 13 x 3"):
        ds.BodyTrack(30, 0.0, np.zeros((4, 12, 3)), seen, {}, "t")
    with pytest.raises(ds.DanceStudyError, match="bool"):
        ds.BodyTrack(30, 0.0, good, seen.astype(int), {}, "t")
    bad = good.copy()
    bad[0, 0, 0] = np.nan
    with pytest.raises(ds.DanceStudyError, match="finite"):
        ds.BodyTrack(30, 0.0, bad, seen, {}, "t")
    with pytest.raises(ds.DanceStudyError, match="start"):
        ds.BodyTrack(30, -1.0, good, seen, {}, "t")


def test_a_spread_of_nothing_is_none():
    assert ds.Spread.of([]) is None and ds.Spread.of([math.nan]) is None
    assert ds.Spread.of([1.0, 2.0, 3.0]).p50 == 2.0


def test_a_pose_record_of_ours_holds_no_real_person(bounce):
    data = ds.pose_record(bounce[:10], FPS)
    assert data["estimator"]["name"] == "srstudio-skeleton" and data["source"]["sha256"] == "0" * 64
    assert pt.from_data(data).found == 10

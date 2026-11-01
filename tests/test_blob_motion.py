"""A Soft figure shuts its mouth when a line stops, and walks a path at a stride a beat."""

import pytest

from srstudio import blob


def cue(time, pose="stand", spot=(100.0, 200.0), **kw):
    return blob.cue(time, pose, spot, scale=1.25, **kw)


def mouths(cues):
    return [(round(c.time, 3), c.mouth) for c in cues]


def test_quieted_talks_only_inside_a_line_of_a_long_hold():
    cues = blob.quieted([cue(0, mouth="flat")], [(2.0, 3.0)], 5.0, 15)
    assert mouths(cues) == [(0.0, "flat"), (2.0, "sing"), (3.0, "flat")]


def test_speaking_alone_talks_through_the_whole_hold():
    assert mouths(blob.speaking([cue(0, mouth="flat")], [(2.0, 3.0)], 5.0, 15)) == [(0.0, "sing")]


def test_quieted_splits_each_hold_at_each_line():
    cues = blob.quieted([cue(0, mouth="flat"), cue(4, mouth="grin")], [(1.0, 2.0), (4.5, 4.8)], 6.0, 15)
    assert mouths(cues) == [(0.0, "flat"), (1.0, "sing"), (2.0, "flat"), (4.0, "grin"), (4.5, "sing"), (4.8, "grin")]


def test_quieted_adds_no_cue_where_one_already_stands():
    cues = blob.quieted([cue(0, mouth="flat"), cue(1, "clasp", mouth="grin")], [(1.0, 2.0)], 3.0, 15)
    assert [c.pose for c in cues] == ["stand", "clasp", "clasp"]


def test_quieted_holds_the_figure_still_at_the_split():
    cues = blob.quieted([cue(0, ease=0.0, lift=0.2, mouth="flat"), cue(4, "clasp", ease=0.5)], [(1.0, 2.0)], 6.0, 15)
    split = [c for c in cues if c.time in (1.0, 2.0)]
    assert all(c.pose == "stand" and c.ease == 0.0 and c.lift == 0.0 for c in split)


@pytest.mark.parametrize("cues", [[], [cue(1.5)]])
def test_quieted_refuses_a_line_before_any_cue(cues):
    with pytest.raises(blob.BlobError, match="no cue"):
        blob.quieted(cues, [(1.0, 2.0)], 3.0, 15)


def test_quieted_refuses_a_line_that_ends_before_it_starts():
    with pytest.raises(blob.BlobError, match="ends before"):
        blob.quieted([cue(0)], [(2.0, 1.0)], 3.0, 15)


def test_walking_lands_on_the_last_point_at_stop():
    steps = blob.walking(((0.0, 1500.0), (500.0, 1500.0)), 1.0, 2.0, scale=1.25, eyes="happy")
    assert steps[-1].time == pytest.approx(2.0)
    assert (steps[-1].x * 1.25, steps[-1].y * 1.25) == pytest.approx((500.0, 1500.0))
    assert {c.eyes for c in steps} == {"happy"}


def test_walking_alternates_its_stride_a_beat_apart():
    steps = blob.walking(((0.0, 0.0), (100.0, 0.0)), 0.0, 1.0, step=0.25, scale=1.0)
    assert [c.pose for c in steps] == ["walk-a", "walk-b", "walk-a", "walk-b"]
    assert [c.time for c in steps] == pytest.approx([0.25, 0.5, 0.75, 1.0])
    assert all(c.ease == 0.25 for c in steps)


def test_walking_follows_every_leg_of_a_path():
    steps = blob.walking(((0.0, 0.0), (100.0, 0.0), (100.0, 100.0)), 0.0, 1.0, step=0.25, scale=1.0)
    assert [(round(c.x, 6), round(c.y, 6)) for c in steps] == [(50, 0), (100, 0), (100, 50), (100, 100)]


def test_walking_passes_flip_to_each_stride():
    assert all(c.flip for c in blob.walking(((0.0, 0.0), (9.0, 0.0)), 0.0, 1.0, flip=True))


@pytest.mark.parametrize(
    ("points", "start", "stop", "step", "why"),
    [
        (((0.0, 0.0),), 0.0, 1.0, 0.22, "two points"),
        (((0.0, 0.0), (1.0, 0.0)), 1.0, 1.0, 0.22, "after it starts"),
        (((0.0, 0.0), (1.0, 0.0)), 0.0, 1.0, 0.0, "positive"),
    ],
)
def test_walking_refuses_what_cannot_be_walked(points, start, stop, step, why):
    with pytest.raises(blob.BlobError, match=why):
        blob.walking(points, start, stop, step=step)

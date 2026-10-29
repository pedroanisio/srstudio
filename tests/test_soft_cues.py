"""Building a Soft performance: cues placed in output pixels, eases settled so no move starts before the previous
pose has landed (episodes 07, 08 and 10 each carried a copy of these before the library did)."""

import pytest

from srstudio import blob
from srstudio.blob import BlobError, Cue


def test_a_cue_at_a_spot_in_pixels_is_placed_in_rig_units():
    c = blob.cue(1.0, "sit", (300.0, 900.0), scale=1.5, ease=0.25, eyes="look")
    assert (c.x, c.y, c.ease, c.eyes) == (200.0, 600.0, 0.25, "look")


def test_a_cue_at_zero_never_eases_and_a_cue_without_a_spot_stays_put():
    assert blob.cue(0, "sit", (300.0, 900.0), scale=1.5, ease=0.25).ease == 0.0
    still = blob.cue(2.0, "nod", scale=1.5, ease=0.25)
    assert (still.x, still.y, still.ease) == (0.0, 0.0, 0.25)


@pytest.mark.parametrize("scale", [0, -1.0, float("nan")])
def test_a_cue_refuses_a_scale_that_cannot_map_pixels(scale):
    with pytest.raises(BlobError, match="scale"):
        blob.cue(1.0, "sit", (1.0, 1.0), scale=scale)


def test_settle_caps_each_ease_to_the_time_since_the_previous_pose_landed():
    fps = 10
    cues = blob.settle(
        [
            Cue(0, "sit"),
            Cue(1.0, "stand", ease=0.4, overshoot=0.08),  # lands at 1.0, settles one drawing later
            Cue(1.2, "cheer", ease=0.5),  # wants 0.5 s, has 1.2 - (1.0 + 1/fps) = 0.1 (less a hair)
            Cue(3.0, "sit", ease=0.5),  # room enough: unchanged
        ],
        fps,
    )
    assert [c.ease for c in cues[:2]] == [0.0, 0.4]
    assert 0.0 < cues[2].ease < 0.1 and cues[2].time - cues[2].ease > 1.0 + 1 / fps
    assert cues[3].ease == 0.5


def test_settle_orders_the_cues_and_the_result_performs():
    cues = blob.settle([Cue(2.0, "nod", ease=5.0), Cue(0, "sit"), Cue(1.0, "stand", ease=3.0)], 15)
    assert [c.time for c in cues] == [0, 1.0, 2.0] and [c.ease for c in cues] == [0.0, 1.0, 1.0]
    blob._check(cues, end=3.0)  # the rig accepts what settle returns


def test_settle_refuses_what_no_ease_can_fix():
    with pytest.raises(BlobError, match="increasing"):
        blob.settle([Cue(0, "sit"), Cue(1.0, "nod"), Cue(1.0, "sit")], 15)
    with pytest.raises(BlobError, match="fps"):
        blob.settle([Cue(0, "sit")], 0)

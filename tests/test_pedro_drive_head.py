"""His head through a shot: every frame's pose is a plate his sculpt has, the runs cover the shot with no gap, and the
turn to the lens, the blinks and the nods happen when the script says."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import pedro_drive_head as head  # noqa: E402

from srstudio.pedro import NODS, TURNS  # noqa: E402
from srstudio.pedro_host import VIEWS  # noqa: E402

SPAN = (3.0, 10.0)


def moving(_t: float) -> float:
    return 1.0


SCRIPT = head.Script(
    moods=((0.0, "neutral"), (4.4, "raised-brow")),
    blinks=(1.4,),
    holds=((4.4, 5.0, -3.0),),
    lens=(5.5, 5.9, -35.0),
    phase=0.5,
)


def runs(script=SCRIPT, speed=moving, span=SPAN):
    return head.track(span, script, dress="blazer", glasses=False, speed=speed)


def test_the_runs_cover_the_shot_with_no_gap_and_no_two_neighbours_on_one_plate():
    found = runs()
    assert found[0][1] == SPAN[0] and found[-1][2] == SPAN[1]
    assert all(a[2] == b[1] for a, b in zip(found, found[1:], strict=False))
    assert all(a[0] != b[0] for a, b in zip(found, found[1:], strict=False))
    assert all(start < end for _, start, end in found)


def test_every_plate_is_a_pose_his_sculpt_has_and_the_shot_needs_few_of_them():
    plates = {plate for plate, _, _ in runs()}
    for face, degrees, dress, glasses in plates:
        assert degrees in VIEWS and face.turn in TURNS and face.nod in NODS
        assert dress == "blazer" and glasses is False
    assert len(plates) <= 60


def test_his_body_turns_from_the_profile_to_the_lens_by_the_script_and_not_before():
    found = runs()
    before = [plate[1] for plate, start, _ in found if start - SPAN[0] < SCRIPT.lens[0]]
    after = [plate[1] for plate, start, _ in found if start - SPAN[0] >= SCRIPT.lens[1] + 0.2]
    assert max(before) <= head.PROFILE + 6.0 + 1e-9  # the sway stays near the profile
    assert after and all(-36.0 <= d <= -30.0 for d in after)  # and rests round the lens, swaying a little


def test_his_body_never_jumps_more_than_one_easing_step_between_frames():
    per_frame = [
        head.pose_at(SCRIPT, i / head.FPS, moving, "blazer", False)[1]
        for i in range(round(SPAN[1] - SPAN[0]) * head.FPS)
    ]
    assert max(abs(a - b) for a, b in zip(per_frame, per_frame[1:], strict=False)) <= 9.0


def test_he_blinks_when_the_script_says_for_a_moment_and_not_otherwise():
    shut = [(start, end) for (face, *_), start, end in runs() if face.lid == "shut"]
    assert shut and all(abs(start - (SPAN[0] + 1.4)) < 0.2 for start, _ in shut)
    assert sum(end - start for start, end in shut) == pytest.approx(head.BLINK, abs=1 / head.FPS)


def test_the_mood_changes_at_its_time_and_a_held_nod_holds():
    found = runs()
    assert all(plate[0].mood == "neutral" for plate, start, _ in found if start < SPAN[0] + 4.4)
    assert all(plate[0].mood == "raised-brow" for plate, start, _ in found if start >= SPAN[0] + 4.4)
    assert all(plate[0].nod == -3.0 for plate, start, end in found if SPAN[0] + 4.4 <= start and end <= SPAN[0] + 5.0)


def test_he_nods_on_the_road_and_not_when_the_traffic_has_stopped():
    stopped = runs(speed=lambda _t: 0.0)
    assert all(plate[0].nod == 0.0 for plate, start, _ in stopped if start < SPAN[0] + 4.4)
    assert any(plate[0].nod != 0.0 for plate, start, _ in runs() if start < SPAN[0] + 4.4)


def test_the_same_script_gives_the_same_track_and_another_phase_another():
    assert runs() == runs()
    other = head.Script(SCRIPT.moods, SCRIPT.blinks, SCRIPT.holds, SCRIPT.lens, phase=2.0)
    assert runs(other) != runs()


@pytest.mark.parametrize(
    "make",
    [
        lambda: head.Script(moods=()),
        lambda: head.Script(moods=((1.0, "neutral"),)),
        lambda: head.Script(moods=((0.0, "smile"), (-1.0, "neutral"))),
        lambda: head.Script(lens=(2.0, 2.0, -35.0)),
        lambda: head.Script(holds=((3.0, 1.0, -3.0),)),
    ],
)
def test_a_script_out_of_order_is_refused_with_a_typed_error(make):
    with pytest.raises(head.HeadError):
        make()


def test_a_shot_that_runs_backwards_and_a_mood_his_sculpt_does_not_have_are_refused():
    with pytest.raises(head.HeadError, match="later one"):
        head.track((5.0, 5.0), SCRIPT, dress="blazer", glasses=False, speed=moving)
    with pytest.raises(Exception, match="mood"):
        head.track((0.0, 1.0), head.Script(moods=((0.0, "furious"),)), dress="blazer", glasses=False, speed=moving)

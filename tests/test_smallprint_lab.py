"""Small Print's lab bench (ADR 0240): a goldfish with real detail that swims by bending, a lab tank whose lever, timer
and pellets move on the clock, and a calendar whose torn page never rises over the pad. Bad poses are refused."""

from __future__ import annotations

import math

import numpy as np
import pytest

from srstudio import smallprint_lab as lab
from srstudio.clay import Model


def _meshes(build) -> dict[str, np.ndarray]:
    m = Model()
    build(m)
    out: dict[str, list[np.ndarray]] = {}
    for mesh in m.meshes():
        out.setdefault(mesh.material, []).append(mesh.vertices)
    return {name: np.concatenate(parts) for name, parts in out.items()}


def _fish(**pose) -> dict[str, np.ndarray]:
    return _meshes(lambda m: lab.goldfish(m, lab.FishPose((0.0, 0.0, 0.0), **pose)))


def test_the_goldfish_has_a_body_belly_eyes_with_pupils_a_mouth_gills_fins_and_rayed_fins():
    assert {"goldfish", "goldbelly", "fisheye", "fishpupil", "fishlip", "fishgill", "goldfin", "finray"} <= set(_fish())


def test_he_bends_as_he_swims_and_his_tail_lags_the_stroke():
    a, b = _fish(phase=0.0, beat=1.0), _fish(phase=0.25, beat=1.0)
    assert not np.allclose(a["goldfish"], b["goldfish"])
    assert not np.allclose(a["goldfin"], b["goldfin"])
    still = _fish(phase=0.25, beat=0.0)
    assert np.ptp(b["goldfish"][:, 2]) > np.ptp(still["goldfish"][:, 2])


def test_his_mouth_opens_as_the_pose_asks():
    shut, wide = _fish(mouth=0.0)["fishlip"], _fish(mouth=1.0)["fishlip"]
    assert np.ptp(wide[:, 1]) > np.ptp(shut[:, 1])


@pytest.mark.parametrize(
    ("pose", "match"),
    [
        ({"at": (0.0, 0.0)}, "three numbers"),
        ({"at": (0.0, math.nan, 0.0)}, "three numbers"),
        ({"pitch": 70.0}, "60 degrees"),
        ({"mouth": 1.5}, "mouth"),
        ({"beat": -0.1}, "beat"),
        ({"heading": "left"}, "heading"),
    ],
)
def test_a_fish_pose_out_of_bounds_is_refused(pose, match):
    with pytest.raises(lab.LabError, match=match):
        lab.FishPose(**{"at": (0.0, 0.0, 0.0), **pose})


@pytest.mark.parametrize(
    ("rig", "match"),
    [
        ({"lever": 31.0}, "lever"),
        ({"lever": -1.0}, "lever"),
        ({"hour": 25.0}, "timer"),
        ({"bubbles": math.inf}, "bubbles"),
        ({"pellets": ((0.0, 1.0),)}, "pellet"),
    ],
)
def test_a_rig_out_of_bounds_is_refused(rig, match):
    with pytest.raises(lab.LabError, match=match):
        lab.Rig(**rig)


def test_his_nose_is_where_nose_to_middle_puts_it():
    for heading, pitch in ((0.0, 0.0), (-135.0, 22.0), (-450.0, 0.0)):
        nose = (10.0, -270.0, -205.0)
        middle = lab.nose_to_middle(nose, heading, pitch)
        verts = _meshes(lambda m, h=heading, p=pitch, at=middle: lab.goldfish(m, lab.FishPose(at, h, p, beat=0.0)))
        body = np.concatenate([v for k, v in verts.items() if k in ("goldfish", "fishlip")])
        assert np.linalg.norm(body - np.array(nose), axis=1).min() < 1.5, (heading, pitch)


def test_a_swim_eases_through_its_marks_and_beats_harder_on_the_way_than_at_rest():
    marks = (lab.Mark(0.0, (0.0, -270.0, -205.0)), lab.Mark(1.0, (20.0, -270.0, -205.0)),
             lab.Mark(3.0, (20.0, -270.0, -205.0), mouth=0.9))  # fmt: skip
    assert lab.swim(marks, 0.0).at == pytest.approx(marks[0].where)
    assert lab.swim(marks, 0.5).at[0] == pytest.approx(10.0)
    assert lab.swim(marks, 0.25).at[0] < 5.0  # eased: slow out of the mark
    assert lab.swim(marks, 0.5).beat > lab.swim(marks, 2.0).beat
    assert lab.swim(marks, 9.0).at == pytest.approx(marks[-1].where)
    assert lab.swim(marks, 3.0).mouth == pytest.approx(0.9)


def test_a_swim_whose_marks_go_back_in_time_is_refused():
    with pytest.raises(lab.LabError, match="forward in time"):
        lab.swim((lab.Mark(1.0, (0.0, 0.0, 0.0)), lab.Mark(0.5, (1.0, 0.0, 0.0))), 0.7)
    with pytest.raises(lab.LabError, match="forward in time"):
        lab.swim((), 0.0)


def test_the_lever_swings_out_to_its_peak_on_the_press_then_falls_back_slower():
    assert lab.lever(1.0 - lab.PUSH - 0.01, (1.0,)) == 0.0
    assert 0.0 < lab.lever(1.0 - lab.PUSH / 2, (1.0,)) < lab.PRESS
    assert lab.lever(1.0, (1.0,)) == pytest.approx(lab.PRESS)
    assert 0.0 < lab.lever(1.0 + lab.BACK / 2, (1.0,)) < lab.PRESS
    assert lab.lever(1.0 + lab.BACK + 0.01, (1.0,)) == 0.0
    assert lab.BACK > lab.PUSH


def test_a_pressed_lever_moves_its_paddle_toward_the_right_wall():
    rest, pressed = lab.lever_tip(0.0), lab.lever_tip(lab.PRESS)
    assert pressed[0] > rest[0] and pressed[2] == rest[2]
    assert lab.tank().x0 < rest[0] < pressed[0] < lab.tank().x1


def test_a_pellet_is_in_the_water_only_from_the_chute_until_it_is_eaten_and_sinks_meanwhile():
    drops = ((1.0, 2.0),)
    assert lab.pellets(0.9, drops) == () and lab.pellets(2.0, drops) == ()
    early, late = lab.pellets(1.1, drops)[0], lab.pellets(1.8, drops)[0]
    assert late[1] > early[1]  # y is down
    assert lab.tank().surface < early[1] < lab.tank().floor
    assert lab.pellet_at(1.0, 1.8) == pytest.approx(late)


def test_keyed_values_ease_between_keys_and_hold_outside_them():
    keys = ((1.0, 10.0), (3.0, 20.0))
    assert lab.keyed(0.0, keys) == 10.0 and lab.keyed(9.0, keys) == 20.0
    assert lab.keyed(2.0, keys) == pytest.approx(15.0)
    assert lab.keyed(1.5, keys) < 12.5


def test_the_timer_hand_points_at_the_fed_hour_at_the_top_and_goes_round_once_a_day():
    cx, cy, _ = lab.dial_centre()

    def hand(hour: float) -> np.ndarray:
        return _meshes(lambda m: lab.parts(m, lab.Rig(hour=hour), None))["dialhand"].mean(axis=0)

    top, six = hand(0.0), hand(6.0)
    assert top[1] < cy and abs(top[0] - cx) < abs(top[1] - cy)
    assert six[0] > cx and abs(six[1] - cy) < abs(six[0] - cx)


@pytest.mark.parametrize("hour", [h / 4 for h in range(96)])
def test_the_hand_never_covers_an_hour_printed_on_the_face(hour):
    """The hours are printed in a ring outside the hand's reach, so no hour is under it at any time of day."""
    cx, cy, _ = lab.dial_centre()
    hand = _meshes(lambda m: lab.parts(m, lab.Rig(hour=hour), None))["dialhand"]
    reach = float(np.max(np.hypot(hand[:, 0] - cx, hand[:, 1] - cy)))
    assert reach < lab.numbers_inside() * lab.DIAL_R


def test_the_hours_and_the_fed_wedge_sit_in_rings_of_their_own():
    mid = 256
    for line in lab.dial_print().lines:
        r = math.hypot(line.x - mid, line.y - mid) / mid
        assert r == pytest.approx(lab.NUMBER_AT)
        assert (r * mid - lab.GLYPH * line.size) / mid >= lab.numbers_inside() - 1e-9
    face = _meshes(lambda m: lab.bench(m, 1.0))
    cx, cy, _ = lab.dial_centre()
    wedge = face["fedhour"]
    outside = (lab.NUMBER_AT + lab.GLYPH * lab.NUMBER_SIZE / 256) * lab.DIAL_R  # the printed hours' outer reach
    assert np.min(np.hypot(wedge[:, 0] - cx, wedge[:, 1] - cy)) >= outside


def test_glass_is_only_thin_panes_facing_the_lens_and_the_water_only_its_top():
    """A transmissive surface with the plate's clear background behind it renders opaque: no glass box, no water
    volume, and the tank closed at the sides and back."""
    m = Model()
    lab.bench(m, 1.0)
    b = lab.tank()
    glass = np.concatenate([mesh.vertices for mesh in m.meshes() if mesh.material == "tankglass"])
    in_tank = glass[glass[:, 1] > b.top]  # y is down: under the lid, in the tank
    assert len(in_tank) and np.all(in_tank[:, 2] <= b.front + 1e-6) and np.ptp(in_tank[:, 2]) <= 1.3
    water = [mesh.vertices for mesh in m.meshes() if mesh.material == "tankwater"]
    assert water and all(np.ptp(v[:, 1]) <= 0.7 for v in water)
    assert {mesh.material for mesh in m.meshes()} >= {"tankback", "tankside", "tankframe"}
    assert lab.materials()["tankback"].transmission == 0.0


def test_the_hopper_shows_its_food_full_and_none_empty():
    assert "pellet" in _meshes(lambda m: lab.bench(m, 1.0))
    assert "pellet" not in _meshes(lambda m: lab.bench(m, 0.0))


@pytest.mark.parametrize("lift", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_a_torn_page_tips_forward_and_never_rises_over_the_pad(lift):
    stand = _meshes(lab.calendar_stand)["calendarback"]
    pages = _meshes(lambda m: lab.calendar_pages(m, ("WEEK", "1"), ("WEEK", "2"), lift))
    torn = pages[lab.page_name("WEEK", "1")]
    assert torn[:, 1].min() >= stand[:, 1].min() - 1e-6
    if lift > 0.0:
        assert torn[:, 2].min() < lab.CALENDAR[2] - 1.0  # toward the lens
        assert lab.page_name("WEEK", "2") in pages  # the page under shows as it goes


def test_a_page_lift_out_of_bounds_is_refused():
    with pytest.raises(lab.LabError, match="lifts 0 to 1"):
        lab.calendar_pages(Model(), ("WEEK", "1"), ("WEEK", "2"), 1.2)


def test_a_page_prints_its_word_over_its_number():
    word, number = lab.page_print("WEEK", "3").lines
    assert (word.text, number.text) == ("WEEK", "3") and word.y < number.y and number.size > word.size
    assert lab.page_material("WEEK", "3").print == lab.page_print("WEEK", "3")

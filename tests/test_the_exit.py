"""The Exit (Stick 09) as data: the script checks with two distinct voices (Dev keeps R3's), the hook is Noor's
first line, the shorthand escalates in alternating singles, both say "The tent." back to back into the dead air,
the callback turns "your sister's" around, and the phone buzzes and goes face down; every take poses both figures
from the windshield's seated poses, and the cameras keep the faces, the phone and the cactus in frame."""

import sys
from pathlib import Path

import pytest

from srstudio import stick
from srstudio import stick_windshield as ws

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
R3_DEV = "bIHbv24MWmeRgasZH58o"  # Will, Dev's voice in Repeat After Me


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import the_exit_audio

        return the_exit_audio
    finally:
        sys.path.pop(0)


def by_id(data):
    return {t.id: t for t in data.SCRIPT.takes}


def framed(camera, point):
    """Where ``point`` (frame pixels of the uncut two-shot) lands through ``camera`` = (focus, zoom, to)."""
    (fx, fy), zoom, (tx, ty) = camera
    return tx + (point[0] - fx) * zoom, ty + (point[1] - fy) * zoom


def inside(p, margin=0.0) -> bool:
    return margin <= p[0] <= 1080 - margin and margin <= p[1] <= 1920 - margin


def test_the_script_checks_with_two_voices_and_dev_keeps_his(data):
    data.SCRIPT.check()
    voices = data.SCRIPT.voices
    assert set(voices) == {"dev", "noor"} and voices["dev"].id == R3_DEV and voices["noor"].id != R3_DEV
    assert set(data.SCRIPT.shots) == {"two", "dev", "noor", "phone", "down"}


def test_it_opens_mid_argument_on_noor_s_line_in_the_two_shot(data):
    first = data.SCRIPT.takes[0]
    assert (first.actor, first.shot) == ("noor", "two")
    assert data.HOOK.lstrip("—").lower() == first.text.lower()  # the card is the line, cut in mid-sentence


def test_the_shorthand_alternates_singles_then_both_say_the_tent_into_dead_air(data):
    t = by_id(data)
    assert [(t[i].actor, t[i].shot) for i in ("02", "03")] == [("dev", "dev"), ("noor", "noor")]
    first, second = t["04"], t["05"]
    assert first.text == second.text == "The tent." and {first.actor, second.actor} == {"dev", "noor"}
    assert first.shot == second.shot == "two" and first.hold <= 0.05  # back to back, one breath
    assert second.hold >= data.DEAD_AIR >= 2.0  # then nobody speaks
    assert t["06"].text == t["07"].text == "Sorry." and t["06"].actor != t["07"].actor


def test_the_callback_turns_the_sister_around(data):
    t = by_id(data)
    assert "sister's" in t["02"].text  # cited as a grievance
    assert (t["08"].actor, t["09"].actor) == ("dev", "noor")
    assert "not going to your sister's" in t["08"].text and t["09"].text == "We are not going to my sister's."


def test_the_phone_buzzes_in_the_insert_and_goes_face_down_in_the_punch_in(data):
    *_, buzz, down = data.SCRIPT.takes
    assert (buzz.actor, buzz.shot, buzz.text) == ("sfx", "phone", "[BZZT]")
    assert (down.actor, down.shot) == ("sfx", "down") and down.text.startswith("[")
    assert 0 < data.DOWN < data.CUT < down.hold  # put down, then the cut back to the two-shot for the hold
    assert down.hold - data.CUT >= 1.2  # the ending is held


def test_every_take_poses_both_figures_from_the_front_seats(data):
    ids = [t.id for t in data.SCRIPT.takes]
    for take in data.SCRIPT.takes:
        if take.shot == "phone":
            continue
        for who in ("dev", "noor"):
            rows = data.part(who, ids, take.id)
            stick.check_keys([stick.RigKey(t, pose, face) for t, pose, face in rows], 10.0, ws.FRONT)
    reach = data.part("noor", ids, ids[-1])
    assert reach[0][1] == "reach" and reach[1][0] >= data.DOWN  # her hand is on the phone until it lies down


def test_settling_happens_inside_each_take_s_hold(data):
    t = by_id(data)
    for take_id, (delay, rows) in data.SETTLE.items():
        assert set(rows) == {"dev", "noor"} and all(pose in ws.FRONT for pose, _ in rows.values())
        assert delay + 0.2 <= t[take_id].hold, take_id


def test_the_two_shot_frames_the_glass_with_both_faces_and_the_cactus(data):
    cam = data.CAMERAS["two"]
    assert cam[1] == 1.25
    for at in (ws.PASSENGER_AT, ws.DRIVER_AT):
        head = ws.FRONT["sit"].head
        face = framed(cam, (head[0] + at[0], head[1] + at[1]))
        assert inside(face, 120) and face[1] + stick.HEAD_R < data.WORDS_Y  # faces clear of the edges and the words
    cactus = framed(cam, (196, ws.DASH_TOP + 8))  # the dashboard's cactus (ws.dashboard)
    assert inside(cactus, 40)
    hood = framed(cam, (540, 1462))
    assert hood[1] > data.WORDS_Y - stick.WORD_H  # the words sit on the hood, below the dashboard


def test_the_singles_and_the_punch_in_keep_their_subjects_in_frame(data):
    for who, at in (("dev", ws.DRIVER_AT), ("noor", ws.PASSENGER_AT)):
        cam = data.CAMERAS[who]
        assert cam[1] > data.CAMERAS["two"][1]
        head = ws.FRONT["cite" if who == "dev" else "crossed"].head
        assert inside(framed(cam, (head[0] + at[0], head[1])), 150), who
    cam = data.CAMERAS["down"]
    assert cam[1] == 1.5
    hand = ws.FRONT["reach"].hands[1]
    lx, ly, lw, lh = ws.LYING
    for p in ((hand[0] + ws.PASSENGER_AT[0], hand[1]), (lx, ly), (lx + lw, ly + lh)):
        q = framed(cam, p)
        assert inside(q, 60) and q[1] < data.WORDS_Y - stick.WORD_H, p  # the hand and the phone above the words
    assert inside(framed(cam, (196, ws.DASH_TOP + 8)), 40)


def test_the_release_declares_the_cover_the_builder_hides_its_text_for():
    sys.path.insert(0, str(EPISODES))
    try:
        from posts.the_exit import RELEASE
    finally:
        sys.path.pop(0)
    assert "ep.hide_on_cover(" in (EPISODES / "the_exit.py").read_text()
    assert RELEASE.cover and RELEASE.tags.recurring == ("dev", "noor")

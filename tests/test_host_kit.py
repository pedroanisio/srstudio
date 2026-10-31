"""The host kit: Lint's poses and mouths, a lit screen that pulls him, framings about his face, and the graphics that
keep to the safe area and refuse what the show cannot put on screen."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, head_motion, host_kit, native, sketch, toon
from srstudio.host_kit import Bubble, HostKitError, Pose
from srstudio.styles import TOON


def width(text: str, size: float) -> float:
    return 0.5 * size * len(text)


def canvas(end: float = 4.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=end, background=host_kit.INK)
    return Canvas(scene, host_kit.HOST.palette(), font_asset="fraunces")


def nodes(cv: Canvas) -> dict[str, ET.Element]:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return {node.get("id", ""): node for node in root.iter()}


def groups_with_keys(cv: Canvas, prop: str) -> list[ET.Element]:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [a for a in root.iter("animate") if a.get("property") == prop]


def beat(start: float, event: str = "", who: str = "lint") -> sketch.Beat:
    return sketch.Beat(start, who, "", "side", "flat", "desk", event=event)


# -- the voice and the look -------------------------------------------------------------------------------------------
def test_the_host_is_a_show_on_toons_road_with_its_own_letters_and_master():
    assert host_kit.HOST.fps == 30 and host_kit.HOST.mix.loudness == "-14"
    assert host_kit.HOST.font.family == "Fraunces" and host_kit.HOST.font.license == "OFL-1.1"
    assert host_kit.HOST.font.family != TOON.font.family
    assert host_kit.HOST.font.google is not None


def test_his_voice_is_none_the_other_shows_use():
    assert host_kit.LINT.voice.name == "Harry" and host_kit.LINT.character == "lint"
    assert host_kit.LINT.voice.name not in ("Bella", "Daniel", "Brian", "Matilda", "Charlie", "Alice", "George")


def test_only_the_framings_he_talks_in_are_cast_and_the_mouth_has_its_finer_poses():
    assert host_kit.HOST_CAST.lip_synced == ("lint",)
    assert set(host_kit.FRAMES) <= set(host_kit.HOST_CAST.characters)
    assert {"wide", "lip"} <= set(host_kit.HOST_CAST.visemes)


# -- poses ------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "kw",
    [
        dict(eyes="crossed"),
        dict(mouth="sneer"),
        dict(arm="wave"),
        dict(head=40.0),
        dict(pull=1.5),
        dict(pull=float("nan")),
    ],
)
def test_a_pose_the_rig_has_no_drawing_for_is_refused(kw):
    with pytest.raises(HostKitError):
        Pose(**kw)


def test_blinks_come_on_their_own_and_stay_off_a_stare():
    rows = host_kit.eye_track(((0.0, Pose()),), 8.0)
    assert ("shut" in [state for _, state in rows]) and rows[0] == (0.0, "level")
    assert all(state != "shut" for _, state in host_kit.eye_track(((0.0, Pose("wide")),), 8.0))


def test_a_talking_beat_takes_the_visemes_and_any_other_holds_its_expression():
    acts = ((0.0, Pose()), (1.0, Pose(mouth="chew")), (2.0, Pose()))
    track = [(0.1, "round"), (0.5, "wide"), (1.5, "open"), (2.4, "lip")]
    rows = host_kit.mouth_track(acts, track, 3.0)
    assert (0.5, "wide") in rows and (2.4, "lip") in rows
    assert (1.5, "open") not in rows and (1.0, "chew") in rows


def test_a_silent_master_still_opens_and_shuts_the_mouth():
    states = {state for _, state in host_kit.mouth_track(((0.0, Pose()),), (), 2.0)}
    assert states == {"open", "closed"}


def test_lint_is_drawn_from_his_poses_and_his_plan():
    cv = canvas()
    acts = ((0.0, Pose()), (1.0, Pose("down", "chew", "press", pull=1.0)), (2.0, Pose(arm="three")))
    plan = head_motion.plan(host_kit.MOTION, [], 4.0)
    host_kit.perform(cv, cv.comp, cv.comp, acts, 0.0, 4.0, plan=plan, buzzes=(1.0,), pull_spans=[(1.0, 2.0)])
    assert groups_with_keys(cv, "rotation")  # the head turns, the antennae react, the wings flutter


def test_lint_needs_a_pose_from_his_first_second():
    cv = canvas()
    with pytest.raises(HostKitError, match="pose"):
        host_kit.perform(cv, cv.comp, cv.comp, ((1.0, Pose()),), 0.0, 4.0)
    with pytest.raises(HostKitError, match="start"):
        host_kit.perform(cv, cv.comp, cv.comp, ((0.0, Pose()),), 3.0, 1.0)


# -- the phone's light ------------------------------------------------------------------------------------------------
def test_the_phone_is_lit_from_a_buzz_until_it_times_out_or_he_puts_it_out():
    beats = (beat(1.0, "buzz"), beat(2.0, "dark"), beat(3.0, "buzz"), beat(4.0, "buzz"), beat(5.0, "press"))
    assert host_kit.light_spans(beats, 9.0) == [(1.0, 2.0), (3.0, 5.0)]
    assert host_kit.light_spans((beat(1.0, "buzz"),), 9.0) == [(1.0, 9.0)]
    assert host_kit.light_spans((beat(1.0),), 9.0) == []


def test_the_light_fades_and_a_dark_phone_draws_nothing():
    cv = canvas()
    host_kit.dim_or_lit(cv, cv.comp, [], 4.0)
    assert not groups_with_keys(cv, "opacity")
    host_kit.dim_or_lit(cv, cv.comp, [(1.0, 2.0)], 4.0)
    keys = groups_with_keys(cv, "opacity")[0]
    assert keys.get("defaultInterpolation") == "linear"
    assert [float(k.get("value", "")) for k in keys.iter("key")] == [0.0, 0.0, 1.0, 1.0, 0.0]


# -- framings ---------------------------------------------------------------------------------------------------------
def test_a_punch_is_a_hold_on_the_cut_about_his_face():
    cv = canvas()
    shot = cv.group(cv.comp, "shot-001", start=2.0, end=3.0)
    host_kit.punch(cv, shot, "close", 2.0, "lint")
    assert (shot.anchorX, shot.anchorY) == (540.0, host_kit.PIVOT_Y) and (shot.x, shot.y) == (540.0, host_kit.PIVOT_Y)
    keys = groups_with_keys(cv, "scaleX")[0]
    assert keys.get("defaultInterpolation") == "hold"
    assert [float(k.get("value", "")) for k in keys.iter("key")] == [1.0, host_kit.FRAMES["close"]]


def test_the_same_framing_stays_put_and_the_first_shot_can_push():
    cv = canvas()
    still = cv.group(cv.comp, "shot-001")
    host_kit.punch(cv, still, "tight", 1.0, "tight")
    assert not groups_with_keys(cv, "scaleX") and still.scaleX == host_kit.FRAMES["tight"]
    moving = cv.group(cv.comp, "shot-002")
    host_kit.punch(cv, moving, "lint", 0.0, "lint", (0.8, 1.08))
    assert groups_with_keys(cv, "scaleX")[0].get("defaultInterpolation") == "linear"


def test_his_crown_clears_the_label_in_every_framing():
    crown = host_kit.FACE_Y - host_kit.HEAD_RY
    for scale in host_kit.FRAMES.values():
        assert host_kit.PIVOT_Y + scale * (crown - host_kit.PIVOT_Y) > host_kit.LABEL_Y + host_kit.LABEL_H


def test_a_framing_the_show_does_not_have_is_refused():
    cv = canvas()
    with pytest.raises(HostKitError, match="framings"):
        host_kit.punch(cv, cv.group(cv.comp, "shot-001"), "wide-shot", 0.0, "lint")


def test_framing_reads_the_framing_before_and_leaves_the_phone_to_the_overlay():
    cv = canvas()
    beats = (beat(0.0), beat(1.0, who=host_kit.CHAT), beat(2.0, who="close"))
    shot = SimpleNamespace(cv=cv, app=SimpleNamespace(who="close", start=2.0), beats=beats)
    host_kit.framing((0.8, 1.08), shot, cv.group(cv.comp, "shot-003"))
    keys = groups_with_keys(cv, "scaleX")[0]
    assert [float(k.get("value", "")) for k in keys.iter("key")] == [1.0, host_kit.FRAMES["close"]]
    chat = SimpleNamespace(cv=cv, app=SimpleNamespace(who=host_kit.CHAT, start=1.0), beats=beats)
    untouched = cv.group(cv.comp, "shot-002")
    host_kit.framing(None, chat, untouched)
    assert untouched.anchorX is None


# -- the graphics -----------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("bait", ["Send this to your group chat", "tag someone who does this", "Follow for more"])
def test_engagement_bait_is_refused_on_screen(bait):
    with pytest.raises(HostKitError, match="does not say"):
        host_kit.check_copy(bait)
    cv = canvas()
    with pytest.raises(HostKitError):
        host_kit.label(cv, cv.comp, bait, 0.0, 1.0, width)


def test_a_label_keeps_to_seven_words_and_the_safe_area():
    cv = canvas()
    with pytest.raises(HostKitError, match="seven"):
        host_kit.label(cv, cv.comp, "one two three four five six seven eight", 0.0, 1.0, width)
    with pytest.raises(HostKitError, match="does not fit"):
        host_kit.label(cv, cv.comp, "x" * 90, 0.0, 1.0, width)
    host_kit.label(cv, cv.comp, "RULE 1", 0.0, 1.0, width, id="a-label")
    assert "a-label" in nodes(cv)


def test_a_screen_shows_its_messages_and_refuses_what_cannot_be_read():
    cv = canvas()
    with pytest.raises(HostKitError, match="message to show"):
        host_kit.screen(cv, cv.comp, "Chat", (), 0.0, 1.0, width)
    with pytest.raises(HostKitError, match="after the screen"):
        host_kit.screen(cv, cv.comp, "Chat", (Bubble("late", at=2.0),), 0.0, 1.0, width)
    with pytest.raises(HostKitError, match="too wide"):
        host_kit.screen(cv, cv.comp, "Chat", (Bubble("x" * 60),), 0.0, 1.0, width)
    host_kit.screen(
        cv,
        cv.comp,
        "Chat",
        (Bubble("Has anyone seen it?", sender="You", status="Read by Lint", status_at=0.5),),
        0.0,
        1.5,
        width,
        id="a-screen",
    )
    assert "a-screen" in nodes(cv)


def test_the_sign_off_stays_to_the_last_frame():
    cv = canvas()
    card = host_kit.sign_off(cv, cv.comp, "You know what you did.", 2.0, 4.0, width)
    assert (card.start, card.end) == (2.0, 4.0)
    with pytest.raises(HostKitError):
        host_kit.sign_off(cv, cv.comp, "Tag a friend", 2.0, 4.0, width, id="other")


LINES = (
    toon.Line("1", "Nobody tells you", 0.0, 1.0, "lint"),
    toon.Line("2", "the group chat", 1.0, 2.0, "lint"),
    toon.Line("3", "You know", 2.0, 3.0, "lint"),
)
SAID = (
    (0.0, 0.3, "Nobody"),
    (0.3, 0.5, "tells"),
    (0.5, 0.7, "you"),
    (1.1, 1.2, "the"),
    (1.2, 1.5, "group"),
    (1.5, 1.8, "chat."),
    (2.1, 2.3, "You"),
    (2.3, 2.6, "know"),
)


def test_a_cue_carries_each_word_on_its_sound_and_holds_to_the_next():
    cues = host_kit.caption_cues(LINES, SAID, ("You know",))
    assert [c.text for c in cues] == ["Nobody tells you", "the group chat"]
    assert [w.start for w in cues[1].words] == [1.1, 1.2, 1.5] and cues[1].words[-1].end == 2.0


def test_a_silent_master_spreads_the_words_through_their_cue():
    assert [w.start for w in host_kit.caption_cues(LINES[:1])[0].words] == pytest.approx([0.0, 1 / 3, 2 / 3])


def test_a_caption_that_is_not_what_was_said_stops_the_build():
    wrong = ((0.0, 0.3, "Somebody"), *SAID[1:])
    with pytest.raises(HostKitError, match="not the next word"):
        host_kit.caption_cues(LINES, wrong)
    with pytest.raises(HostKitError, match="not the next word"):
        host_kit.caption_cues(LINES, SAID[:4])


def test_captions_sit_on_a_band_inside_the_safe_area_and_both_can_leave_the_cover():
    from srstudio.layout import VERTICAL

    seen: dict[str, object] = {}
    cv = canvas()
    region = VERTICAL.region(1080, 1920)

    class Stub:
        spec = SimpleNamespace(safe_area=VERTICAL, width=1080, height=1920)
        comp = cv.comp

        def __init__(self) -> None:
            self.cv = cv

        def native_captions(self, cues, *, look, id):
            seen.update(cues=cues, look=look, id=id)
            return "the track"

    bands, track = host_kit.captions(Stub(), LINES, width, SAID)
    assert track == "the track" and seen["look"] is host_kit.CAPTION_LOOK and bands.id == "host-caption-bands"
    drawn = nodes(cv)
    rects = [n for name, n in drawn.items() if name.startswith("rect") and n.get("fill") == host_kit.INK]
    assert len(rects) == 3 and all(float(n.get("y", "0")) >= region.y0 for n in rects)
    assert native.CAPTION_LOOK.preset == host_kit.CAPTION_LOOK.preset == "karaoke"


def test_the_stage_refuses_acts_that_do_not_match_the_beats():
    dress = host_kit.stage((Pose(),), lambda end: head_motion.plan(host_kit.MOTION, [], end))
    cv = canvas()
    shot = SimpleNamespace(cv=cv, app=SimpleNamespace(who="lint", start=0.0, end=1.0), beats=(beat(0.0), beat(0.5)))
    with pytest.raises(HostKitError, match="acts"):
        dress(shot)


def test_the_phones_full_frame_shot_draws_no_room():
    dress = host_kit.stage((Pose(),), lambda end: head_motion.plan(host_kit.MOTION, [], end))
    cv = canvas()
    before = len(nodes(cv))
    dress(SimpleNamespace(cv=cv, app=SimpleNamespace(who=host_kit.CHAT, start=0.0, end=1.0), beats=(beat(0.0),)))
    assert len(nodes(cv)) == before


def test_a_shot_draws_him_with_the_keys_of_the_beats_inside_it():
    dress = host_kit.stage((Pose(), Pose("down", pull=1.0)), lambda end: head_motion.plan(host_kit.MOTION, [], end))
    cv = canvas()
    back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
    shot = SimpleNamespace(
        cv=cv,
        app=SimpleNamespace(who="lint", start=0.0, end=4.0),
        beats=(beat(0.0), beat(1.0, "buzz")),
        back=back,
        front=front,
        end=4.0,
        mouths={},
    )
    dress(shot)
    assert any((n.get("id") or "").startswith("lint") for n in nodes(cv).values())


def test_a_click_is_a_sound_in_a_file(tmp_path: Path):
    path = host_kit.write_click(tmp_path / "click.wav", [0.5], 1.0)
    assert path.read_bytes()[:4] == b"RIFF"

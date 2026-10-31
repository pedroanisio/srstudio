"""The pilot's script is checked, the door's change is slow and clean, its claims are the sources', and it stays outside
the @tuxmeme publishing path."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, mind_kit, sketch, toon_sketch
from srstudio.sketch import Line
from srstudio.thumbnail import Thumbnail

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import change_blindness_data as pilot  # noqa: E402

AT = {name: sketch.events(pilot.BEATS, name)[0][0] for name in pilot.EVENTS}
FRAMES_PER_LEVEL = 1.0  # at most one 8-bit level of any channel per frame: nothing an eye can read as a step
CHANGE_WORDS = ("door", "colour", "color", "red", "teal", "paint")


def cover() -> Thumbnail:
    assert pilot.POST.thumbnail is not None
    return pilot.POST.thumbnail


def rgb(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def opacity_at(keys: list[tuple[float, float]], t: float) -> float:
    """The straight-line value of ``keys`` at ``t``, as the engine reads a linear animation."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:], strict=False):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


def ramp() -> list[tuple[float, float]]:
    """The door's keys on the scripted timing."""
    return pilot.door_keys(AT["reveal"], AT["first"])


def frames_of_the_change() -> list[float]:
    """The repainted door's opacity on every frame from the change's start to the reveal."""
    keys = ramp()
    start = AT["reveal"] - pilot.CHANGE
    count = round(pilot.CHANGE * pilot.FPS)
    return [opacity_at(keys, start + i / pilot.FPS) for i in range(count + 1)]


def with_line(index: int, text: str) -> sketch.Sketch:
    lines = list(pilot.LINES)
    lines[index] = replace(lines[index], text=text)
    return replace(pilot.SKETCH, lines=tuple(lines))


def on_screen() -> str:
    return " ".join(
        (
            *(q.text for q in pilot.LINES),
            *(b.caption for b in pilot.BEATS),
            *pilot.SLOW[0],
            pilot.SLOW[1],
            *pilot.SWAP[0],
            pilot.SWAP[1],
            pilot.POST.title,
            pilot.POST.description,
            cover().headline,
        )
    ).lower()


def scene_of() -> ET.Element:
    """The one shot as the pilot dresses it, the fox's own drawing left out."""
    sk = pilot.SKETCH
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=mind_kit.INK)
    cv = Canvas(scene, mind_kit.MIND.palette(), font_asset="fraunces")
    back, light, front = (cv.group(cv.comp, name) for name in ("back", "light", "front"))
    measure = lambda text, size: 0.5 * size * len(text)  # noqa: E731
    app = sketch.appearances(sk.beats, sk.end)[0]
    pilot.dress(toon_sketch.Shot(cv, app, back, front, sk.beats, sk.end, measure, light, pilot.VERSIONS))
    return ET.fromstring(scene.to_bytes(layout="pretty"))


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_reel_is_one_shot_so_nothing_cuts_away_from_the_door():
    assert len(sketch.appearances(pilot.SKETCH.beats, pilot.SKETCH.end)) == 1


# -- the change -------------------------------------------------------------------------------------------------------


def test_the_change_takes_the_twelve_seconds_the_sources_document():
    assert pilot.CHANGE == 12.0
    keys = ramp()
    start = next(t for (t, v), (_, after) in zip(keys, keys[1:], strict=False) if v == 0.0 and after > 0.0)
    done = next(t for t, v in keys if v == 1.0)
    assert done - start == pytest.approx(12.0)
    assert done == AT["reveal"]


def test_the_door_is_still_teal_on_the_first_frame_and_on_the_cover():
    keys = ramp()
    assert opacity_at(keys, 0.0) == 0.0
    assert opacity_at(keys, cover().at) == 0.0
    assert cover().at < AT["reveal"] - pilot.CHANGE


def test_the_change_only_ever_goes_one_way():
    frames = frames_of_the_change()
    assert frames[0] == pytest.approx(0.0) and frames[-1] == pytest.approx(1.0)
    assert all(b > a for a, b in zip(frames, frames[1:], strict=False))


@pytest.mark.parametrize(
    ("was", "becomes"), [(pilot.DOOR_LEAF, pilot.RED_LEAF), (pilot.DOOR_PANEL, pilot.RED_PANEL)], ids=["leaf", "panels"]
)
def test_no_step_of_the_change_is_big_enough_to_read_as_a_jump(was, becomes):
    frames = frames_of_the_change()
    for a, b in zip(rgb(was), rgb(becomes), strict=True):
        steps = [abs((b - a) * (later - earlier)) for earlier, later in zip(frames, frames[1:], strict=False)]
        assert max(steps) <= FRAMES_PER_LEVEL


def test_the_ramp_is_a_single_straight_line_so_it_cannot_flicker():
    frames = frames_of_the_change()
    steps = [b - a for a, b in zip(frames, frames[1:], strict=False)]
    assert max(steps) == pytest.approx(min(steps))
    assert max(steps) == pytest.approx(1 / (pilot.CHANGE * pilot.FPS))


def test_the_only_fast_moves_are_the_replay_after_the_reveal_and_the_cut_home():
    keys = ramp()
    fast = [t0 for (t0, v0), (t1, v1) in zip(keys, keys[1:], strict=False) if abs(v1 - v0) / (t1 - t0) > 0.5]
    assert all(t >= AT["reveal"] for t in fast)
    swings = [(v0, v1) for (_, v0), (_, v1) in zip(keys, keys[1:], strict=False) if v0 != v1]
    assert swings == [(0.0, 1.0), (1.0, 0.0), (0.0, 1.0), (1.0, 0.0)]  # the change, the rewind, the run, home


def test_the_repainted_door_is_opaque_shapes_over_the_same_shapes():
    """A fading object leaves see-through artefacts; two opaque doors in one place leave a plain mix of two colours."""
    root = scene_of()
    group = next(g for g in root.iter("group") if g.get("id") == "door-change")
    assert float(group.get("opacity")) == 0.0
    for shape in group:
        assert shape.get("opacity") is None


def test_the_change_is_a_large_area_not_a_detail():
    x0, y0, x1, y1 = pilot.DOOR_BOX
    share = (x1 - x0) * (y1 - y0) / (592.0 * 1058.0)
    assert share > 0.09


def test_the_change_keeps_its_brightness_so_only_the_hue_moves():
    def luma(colour: str) -> float:
        r, g, b = rgb(colour)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    assert abs(luma(pilot.DOOR_LEAF) - luma(pilot.RED_LEAF)) < 26
    assert abs(luma(pilot.DOOR_PANEL) - luma(pilot.RED_PANEL)) < 26


def test_a_long_shot_keeps_its_runs_of_carried_springs_short():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=30, background=mind_kit.INK)
    cv = Canvas(scene, mind_kit.MIND.palette(), font_asset="fraunces")
    group = cv.group(cv.comp, "head")
    spring = group.add_animate(property="y", defaultInterpolation="spring")
    for i in range(25):
        spring.add_key(time=i, value="0", stiffness="50", damping="10", mass="1", carry="true" if i else None)
    pilot.rest_springs(group, run=8)
    carried, longest = 0, 0
    for key in spring.iter("key"):
        carried = carried + 1 if key.carry else 0
        longest = max(longest, carried)
    assert 0 < longest < 8


def test_the_lens_only_pushes_slowly_while_the_door_changes_and_ends_on_the_first_framing():
    keys = pilot.lens_keys(AT["reveal"], AT["study"])
    assert keys[0] == (0.0, 1.0) and keys[-1][1] == 1.0
    assert keys[1][1] <= 1.06  # a slow push, never a cut, inside the change
    assert all(t >= AT["reveal"] - 0.001 for t, _ in keys[1:])


# -- the shape --------------------------------------------------------------------------------------------------------


def test_the_reel_keeps_to_the_length_and_opens_on_the_challenge():
    assert 20.0 <= pilot.END <= 30.0
    assert pilot.BEATS[0].line == 0 and pilot.BEATS[0].start == 0.0
    assert pilot.LINES[0].speaker == "narrator"


def test_the_reel_opens_on_its_line():
    beats = (replace(pilot.BEATS[0], line=None, word=None, caption=""), *pilot.BEATS[1:])
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_door_needs_its_time_before_the_reveal():
    early = tuple(replace(b, start=b.start - 3.0) if b.start >= AT["reveal"] else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=_ordered(early)))


def _ordered(beats: tuple[sketch.Beat, ...]) -> tuple[sketch.Beat, ...]:
    """The reveal moved earlier, dropping whatever beats the move would run into."""
    reveal = next(b.start for b in beats if b.event == "reveal")
    return tuple(b for b in beats if b.start >= reveal or b.start < reveal - 0.8)


@pytest.mark.parametrize("words", [pilot.LINES[0].text, pilot.LINES[1].text, pilot.POST.title])
def test_the_hook_and_the_first_line_of_the_caption_give_nothing_away(words):
    assert not set(words.lower().rstrip(".?").split()) & set(CHANGE_WORDS)


def test_the_fox_gives_nothing_away_before_the_reveal():
    before = [b for b in pilot.BEATS if b.start < AT["reveal"]]
    for beat in before:
        assert not set(beat.caption.lower().replace("?", " ").replace(".", " ").split()) & set(CHANGE_WORDS)


def test_the_pad_gives_nothing_away_before_the_reveal():
    for _, _, words, beat in pilot.NOTICED:
        if pilot.BEATS[beat].start < AT["reveal"]:
            assert not set(words.lower().replace(":", " ").replace(",", " ").split()) & set(CHANGE_WORDS)


def test_the_cover_gives_nothing_away():
    assert not set(cover().headline.lower().replace("\n", " ").rstrip(".").split()) & set(CHANGE_WORDS)


def test_the_last_frame_is_the_first():
    last = pilot.BEATS[-1]
    first = pilot.BEATS[0]
    assert (last.eyes, last.mouth, last.arms) == (first.eyes, first.mouth, first.arms)
    assert last.caption == first.caption
    assert opacity_at(ramp(), pilot.END - 0.01) == 0.0


def test_the_sloth_is_back_on_the_first_frames_return():
    assert pilot.swap_time(AT["carry"]) < AT["first"]


def test_the_door_hides_the_swap():
    """At the swap the carried door's width covers the whole listener."""
    swapped = pilot.swap_time(AT["carry"])
    x = opacity_at(pilot.carry_keys(AT["carry"]), swapped)
    middle = pilot.toon.fx(165) + x
    listener = pilot.toon.fx(165) + pilot.toon.fh(pilot.LISTENER[1])
    assert abs(middle - listener) + pilot.LISTENER_HALF < pilot.DOOR_W / 2


# -- the claims -------------------------------------------------------------------------------------------------------


def test_the_stamps_are_the_ones_in_the_sources():
    sources = (ROOT / "pilots/mind/change-blindness/sources.md").read_text(encoding="utf-8")
    assert f"{' '.join(pilot.SLOW[0])} {pilot.SLOW[1]}" in sources
    assert f"{' '.join(pilot.SWAP[0])} {pilot.SWAP[1]}" in sources


def test_the_link_to_the_study_is_the_safe_wording():
    assert any(q.text == "Researchers found the same with photographs." for q in pilot.LINES)


@pytest.mark.parametrize(
    "claim",
    [
        "most people",
        "most viewers",
        "you missed",
        "you're blind",
        "you are blind",
        "%",
        "7 of 15",
        "half of everyone",
        "a study changed a",
        "wall",
        "library",
        "flicker",
        "rensink",
        "scientists",
    ],
)
def test_the_reel_never_says_what_the_sources_rule_out(claim):
    assert claim not in on_screen()


@pytest.mark.parametrize("bad", ["Science proves it.", "This is your OCD talking.", "Tag someone who does this."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(with_line(2, bad))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "denial" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="bonus") if b.event == "denial" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swap = {"study": "carry", "carry": "study"}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


# -- the road ---------------------------------------------------------------------------------------------------------


def test_a_pilot_has_no_release_and_no_post():
    posts = (ROOT / "episodes" / "instagram_posts.py").read_text(encoding="utf-8")
    assert pilot.SLUG not in posts
    assert (
        not list((ROOT / "episodes" / "releases").rglob(f"*{pilot.SLUG}*"))
        if (ROOT / "episodes" / "releases").is_dir()
        else True
    )
    assert pilot.OUTPUT.startswith("renders/pilots/") and "/ig" not in pilot.OUTPUT


def test_no_hearing_was_written():
    assert all(isinstance(q, Line) and not q.heard for q in pilot.LINES)


def test_the_recording_script_carries_the_banner():
    text = (PILOTS / "change_blindness_audio.py").read_text(encoding="utf-8")
    assert "ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error." in text
    assert "Absence of output verification is a design defect, not a runtime bug." in text
    assert "All LLM output must be treated as untrusted and validated explicitly." in text

"""Small Print as a format: a script keeps the show's rules or is refused, the worktop's states tile the reel, the
question opens and closes it, every finding is stamped with its source inside the safe area (ADR 0195)."""

from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, host_kit, rafa_show, sketch, smallprint_lab, smallprint_scene, toon_sketch
from srstudio import smallprint as sp
from srstudio import smallprint_kit as kit
from srstudio.plates import Camera
from srstudio.sample import SYSTEM_FONTS
from srstudio.smallprint import Beat, ScriptError, Show, Stamp
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail, ThumbnailError

SMILE, BATTERY, MELTDOWN = "public-smile", "social-battery", "internal-meltdown"
TOWER = "smallprint-tower"
FOUND = Stamp("TOP SPEED 25 MPH", "Louis Bloomfield, Live Science, 2012")
BEATS = (
    Beat("hook", "Can a penny from up there kill you?", SMILE, TOWER, "top"),
    Beat("try", "Okay. One penny.", MELTDOWN, steps=((0.4, "fall-1"), (0.8, "fall-3"), (1.2, "landed")), hold=0.5),
    Beat("no", "Nope. It would sting.", BATTERY, framing="close"),
    Beat("why", "It is flat, so it tumbles. It tops out around 25 miles an hour.", BATTERY,
         panel="penny-fall", stamp=FOUND),
    Beat("busted", "MythBusters tried it in 2003. Busted.", BATTERY, panel="penny-fall",
         stamp=Stamp("BUSTED", "MythBusters, 2003")),
    Beat("check", "Please do not check.", BATTERY, TOWER, "landed", framing="tight", hold=0.6),
    Beat("bolt", "What does hit that building? Lightning. About 23 times a year.", SMILE, panel="lightning",
         stamp=Stamp("23 STRIKES A YEAR", "NASA Goddard, citing NOAA, 2017")),
    Beat("end", "So up there, the penny is the safe one.", SMILE, TOWER, "top"),
)  # fmt: skip
KEPT = (2.4, 1.4, 1.5, 4.6, 2.2, 1.2, 4.0, 2.2)
SHOW = Show(
    "penny", 1, "A penny", "Can a penny dropped from the Empire State Building kill you?", "Rafa and a penny.",
    "A clay man drops a penny off a model tower.", BEATS, KEPT, InstagramPost(title="Can a penny kill you?",
    description="d"),
)  # fmt: skip


def with_beat(i: int, **changes) -> Show:
    beats = list(BEATS)
    beats[i] = replace(beats[i], **changes)
    return replace(SHOW, beats=tuple(beats))


def test_a_script_that_keeps_the_format_is_valid_and_rafa_speaks_as_will():
    SHOW.validate_sketch()
    assert sp.SPEAKER == rafa_show.SPEAKER and sp.SPEAKER.voice.name == "Will"
    assert sp.SHORTEST <= SHOW.estimated_seconds() <= sp.LONGEST
    assert SHOW.sketch.end == pytest.approx(SHOW.starts()[-1] + KEPT[-1] + sp.TAIL)


def test_a_beat_with_no_prop_carries_the_worktop_on_in_the_state_its_steps_left():
    acts = SHOW.acts()
    assert acts[1][1:3] == (TOWER, "top")
    assert acts[2][1:3] == (TOWER, "landed")
    assert acts[-1] == acts[0]


@pytest.mark.parametrize(
    ("i", "changes", "match"),
    [
        (0, {"mood": "smug"}, "moods"),
        (0, {"framing": "wide"}, "framing"),
        (0, {"prop": "rafa-mug"}, "worktop props"),
        (0, {"state": "flying"}, "states"),
        (1, {"steps": ((0.8, "fall-1"), (0.4, "fall-2"))}, "forward"),
        (3, {"panel": "chart"}, "panels"),
        (2, {"stamp": FOUND}, "lands on a panel"),
        (3, {"stamp": Stamp("TOP SPEED", " ")}, "names its source"),
        (3, {"stamp": Stamp("A STAMP FAR TOO LONG TO READ AT A GLANCE", "x")}, "30 characters"),
        (7, {"state": "landed"}, "first one's picture"),
        (7, {"tears": True}, "first one's picture"),
        (0, {"prop": ""}, "first beat"),
        (0, {"line": "Send this to a friend who drops pennies."}, "does not say"),
        (2, {"hold": -1.0}, "not negative"),
        (2, {"line": "It tops out around twenty-five miles an hour."}, "caption band"),
    ],
)
def test_a_beat_the_show_cannot_stage_is_refused(i, changes, match):
    with pytest.raises((ScriptError, ValueError), match=match):
        with_beat(i, **changes).validate()


@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"question": "Can a penny kill you"}, "question"),
        ({"question": "Tell me if a penny from a very tall building in a very large city could kill you?"}, "fourteen"),
        ({"kept": KEPT[:-1]}, "measured takes"),
        ({"kept": tuple(k * 3 for k in KEPT)}, "takes come to"),
        ({"beats": tuple(replace(b, stamp=None) for b in BEATS)}, "stamped"),
    ],
)
def test_a_script_that_drops_a_show_rule_is_refused(changes, match):
    show = replace(SHOW, **changes)
    show.__dict__.pop("sketch", None)
    with pytest.raises(ScriptError, match=match):
        show.validate()


def test_the_estimate_is_what_the_takes_need_not_the_words_alone():
    long = replace(SHOW, beats=tuple(replace(b, hold=3.0) for b in BEATS))
    with pytest.raises(ScriptError, match="runs"):
        long.validate()


@pytest.mark.parametrize(("i", "hold"), [(0, 1.2), (1, 1.5)])
def test_a_hold_over_a_second_in_the_first_five_seconds_is_refused(i, hold):
    """The opening is where a scroll decides: the brief allows no quiet over 1 s in the first 5 s."""
    assert SHOW.starts()[i] + KEPT[i] < sp.OPENING
    with pytest.raises(ScriptError, match=f"{BEATS[i].id}: a {hold} s hold at .* the first {sp.OPENING:.0f} s"):
        with_beat(i, hold=hold).validate()


def test_a_long_hold_after_the_opening_breathes():
    i = 5
    assert SHOW.starts()[i] + KEPT[i] > sp.OPENING
    with_beat(i, hold=1.5).validate()


@pytest.mark.parametrize("source", ["US National Weather Service", "Guinness World Records", "NOAA, 23"])
def test_a_stamp_whose_source_names_no_year_is_refused(source):
    """Every fact on screen names its source and the year: a count of strikes from an undated page cannot be
    checked against what changed since."""
    with pytest.raises(ScriptError, match="names the year"):
        with_beat(6, stamp=Stamp("23 STRIKES A YEAR", source)).validate()


@pytest.mark.parametrize("source", ["Imai et al., Nature, 2002", "MythBusters, 1998", f"{sp.WORKED} 2 x 2 x 2 = 8"])
def test_a_dated_source_or_a_sum_worked_on_screen_passes(source):
    with_beat(6, stamp=Stamp("23 STRIKES A YEAR", source)).validate()


def test_a_panel_on_the_first_or_last_beat_is_refused():
    with pytest.raises(ScriptError, match="opens and closes on him"):
        with_beat(7, panel="lightning").validate()


def test_the_worktop_states_tile_the_reel_and_each_step_lands_on_its_frame():
    beats, end = SHOW.sketch.beats, SHOW.sketch.end
    spans = sp.states(SHOW, beats, end)
    flat = sorted(span for rows in spans.values() for span in rows)
    assert flat[0][0] == 0.0 and flat[-1][1] == end
    assert all(a[1] == pytest.approx(b[0]) for a, b in zip(flat, flat[1:], strict=False))
    start = sp.cut(beats[1].start)
    assert spans[(TOWER, "fall-1")] == [(sp.cut(beats[1].start + 0.4), sp.cut(beats[1].start + 0.8))]
    assert spans[(TOWER, "landed")][0] == (sp.cut(beats[1].start + 1.2), pytest.approx(spans[(TOWER, "landed")][0][1]))
    assert (TOWER, "top") in spans and start > 0.0


def test_a_step_past_its_beat_is_refused_and_a_recording_that_moves_it_past_never_lands():
    with pytest.raises(ScriptError, match="after its beat"):
        with_beat(1, steps=((40.0, "fall-1"),)).validate()
    beats = list(SHOW.sketch.beats)
    beats[2] = replace(beats[2], start=beats[1].start + 0.3)  # a take shorter than the script's: the step is late
    assert (TOWER, "fall-1") not in sp.states(SHOW, beats, SHOW.sketch.end)


def test_he_cries_only_on_the_beats_that_say_so():
    teary = with_beat(2, tears=True)
    beats, end = teary.sketch.beats, teary.sketch.end
    assert sp.tear_spans(teary, beats, end) == [teary.spans(beats, end)[2]]
    assert sp.tear_spans(SHOW, SHOW.sketch.beats, SHOW.sketch.end) == []


def test_beats_that_share_a_panel_share_one_page_and_each_keeps_its_stamp():
    runs = SHOW.panel_runs(SHOW.sketch.beats, SHOW.sketch.end)
    assert [(name, len(held)) for name, _, _, held in runs] == [("penny-fall", 2), ("lightning", 1)]
    spans = SHOW.spans(SHOW.sketch.beats, SHOW.sketch.end)
    assert runs[0][1:3] == (spans[3][0], spans[4][1])


def drawn(show: Show = SHOW) -> ET.Element:
    sk = show.sketch
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=sp.PAPER)
    cv = Canvas(scene, font_asset="fraunces")
    show.overlay(cv, cv.comp, sk.beats, sk.end, lambda text, size: 0.52 * size * len(text))
    return ET.fromstring(scene.to_bytes(layout="pretty"))


def test_every_word_on_screen_stands_inside_the_safe_area_above_the_captions():
    root = drawn()
    texts = {t.get("id"): t for t in root.iter() if t.tag.endswith("text") and t.get("width")}
    layers = [layer for layer in root.iter() if layer.tag.endswith("layer") and layer.get("asset") in texts]
    assert layers
    for layer in layers:
        text = texts[layer.get("asset")]
        x, y = float(layer.get("x")), float(layer.get("y"))
        assert sp.LEFT - 1 <= x and x + float(text.get("width")) <= sp.RIGHT + 1, text.get("text")
        assert kit.CARD_Y - 1 <= y and y + float(text.get("height")) <= sp.BOTTOM + 1, text.get("text")


def test_the_question_is_up_from_the_first_frame_and_again_on_the_last_beat():
    root = drawn()
    cards = {g.get("id"): g for g in root.iter() if g.get("id") in ("smallprint-card", "smallprint-card-again")}
    assert float(cards["smallprint-card"].get("start")) == 0.0
    assert float(cards["smallprint-card-again"].get("end")) == pytest.approx(SHOW.sketch.end)
    assert float(cards["smallprint-card"].get("end")) <= sp.QUESTION_BY + SHOW.sketch.beats[1].start


def test_every_finding_is_stamped_with_its_source_on_screen():
    words = " ".join(t.get("text") or "" for t in drawn().iter() if t.tag.endswith("text"))
    for beat in BEATS:
        if beat.stamp:
            assert beat.stamp.text in words
            assert all(part in words for part in beat.stamp.source.split())


@pytest.mark.parametrize("panel", sorted(sp.PANELS))
def test_every_panel_moves_while_it_is_up(panel):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=6.0)
    cv = Canvas(scene, font_asset="fraunces")
    g = cv.group(cv.comp, "panel", start=1.0, end=5.0)
    sp.PANELS[panel](cv, g, 1.0, 5.0, lambda text, size: 0.52 * size * len(text))
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    moving = [a for a in root.iter() if a.tag.endswith("animate") and a.get("property") != "opacity"]
    assert moving, f"{panel} holds still"
    keyed = sorted(float(k.get("time")) for a in moving for k in a)
    assert keyed[0] <= 1.6 and keyed[-1] >= 3.0, f"{panel} moves only for a moment"


def test_a_card_or_a_stamp_that_cannot_fit_is_refused():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=6.0)
    cv = Canvas(scene, font_asset="fraunces")
    wide = lambda text, size: 3.0 * size * len(text)  # noqa: E731
    with pytest.raises(ScriptError, match="wider|two lines"):
        sp.card(cv, cv.comp, "Why do onions make you cry every single time you cut one?", 0.0, 2.0, wide)
    with pytest.raises(ScriptError, match="fit a stamp"):
        sp.stamp(cv, cv.comp, Stamp("TOP SPEED 25 MPH", "x"), 0.0, 2.0, wide)
    with pytest.raises(ScriptError, match="time on screen"):
        sp.card(cv, cv.comp, "Why?", 2.0, 2.0, lambda text, size: size)


def test_the_shared_sounds_are_the_room_the_bed_a_page_and_a_stamp(tmp_path):
    sk = SHOW.sketch
    rows = sp.shared_sounds(SHOW, sk.beats, sk.end, tmp_path, 7)
    assert [row["id"] for row in rows] == ["room", "bed", "page", "stamp"]
    assert next(row for row in rows if row["id"] == "bed")["role"] == "music"
    assert all((tmp_path / row["audio"]).exists() for row in rows)


def test_the_sketch_matches_the_script():
    sketch.check(SHOW.sketch)
    with pytest.raises((ScriptError, sketch.SketchError), match="beats for|every line"):
        SHOW.validate_sketch(replace(SHOW.sketch, beats=SHOW.sketch.beats[:-1]))


def _panels_and_overlay() -> list[ET.Element]:
    roots = [drawn()]
    for panel in sp.PANELS:
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1920, fps="30", duration=6.0)
        cv = Canvas(scene, font_asset="fraunces")
        sp.PANELS[panel](cv, cv.group(cv.comp, "panel", start=1.0, end=5.0), 1.0, 5.0, lambda t, s: 0.52 * s * len(t))
        roots.append(ET.fromstring(scene.to_bytes(layout="pretty")))
    return roots


def test_a_group_that_scales_or_turns_about_a_point_stays_where_it_is_drawn():
    """The engine puts a group's anchor at its x, y: an anchor with no matching x, y moves the group off its place."""
    anchored = [g for root in _panels_and_overlay() for g in root.iter() if g.get("anchorX") is not None]
    assert anchored
    for g in anchored:
        keyed = {a.get("property") for a in g if a.tag.endswith("animate")}
        for axis in ("x", "y"):
            if axis not in keyed:
                assert float(g.get(axis, 0.0)) == float(g.get(f"anchor{axis.upper()}")), g.get("id")


def test_a_stamp_stays_inside_the_safe_width_at_its_largest_as_it_lands():
    measure = lambda text, size: 0.52 * size * len(text)  # noqa: E731
    for finding in (Stamp("IT'S A GAS", "x"), Stamp("SHARP KNIFE, FEWER DROPLETS", "x"), Stamp("BUSTED", "x")):
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1920, fps="30", duration=4.0)
        cv = Canvas(scene, font_asset="fraunces")
        g = sp.stamp(cv, cv.comp, finding, 1.0, 3.0, measure)
        root = ET.fromstring(scene.to_bytes(layout="pretty"))
        group = next(e for e in root.iter() if e.get("id") == g.id)
        biggest = max(float(k.get("value")) for a in group if a.get("property") == "scaleX" for k in a)
        text = next(e for e in root.iter() if e.tag.endswith("text") and e.get("text") == finding.text)
        size = float(text.get("size"))
        half = biggest * kit.spread(finding.text, size, measure) / 2
        middle = float(group.get("x"))
        assert kit.LEFT - 1e-6 <= middle - half and middle + half <= kit.RIGHT + 1e-6, finding.text


def test_a_group_that_pops_in_scales_about_a_point_of_its_own():
    """A group scaled about the frame's corner grows towards the right edge: every popped group has a pivot."""
    for root in _panels_and_overlay():
        for g in root.iter():
            scaled = {a.get("property") for a in g if a.tag.endswith("animate")} & {"scaleX", "scaleY"}
            if scaled and g.get("id") != "panel":
                assert g.get("anchorX") is not None, g.get("id")


def _luminance(colour: str) -> float:
    rgb = [int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def _shown(element: ET.Element, parents: dict[ET.Element, ET.Element], end: float) -> tuple[float, float]:
    """When a layer is drawn: inside every enclosing group's start and end, and after any fade from nothing."""
    first, last = 1.0, end
    node: ET.Element | None = element
    while node is not None:
        first = max(first, float(node.get("start", first)))
        last = min(last, float(node.get("end", last)))
        if node.get("opacity") == "0.0" or node.get("opacity") == "0":
            fades = [a for a in node if a.tag.endswith("animate") and a.get("property") == "opacity"]
            seen = [float(k.get("time")) for a in fades for k in a if float(k.get("value")) > 0.0]
            first = max(first, min(seen, default=last))
        node = parents.get(node)
    return first, last


@pytest.mark.parametrize(("panel", "end"), [(panel, end) for panel in sorted(sp.PANELS) for end in (5.0, 9.0)])
def test_every_word_on_a_panel_stays_long_enough_to_read_reads_on_paper_and_stays_in_the_safe_width(panel, end):
    """LEG-SHORT and LEG-CONTRAST on a master: a word drawn under 0.8333 s, or under 4.5:1 on paper, is a finding."""
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=end + 1.0)
    cv = Canvas(scene, font_asset="fraunces")
    sp.PANELS[panel](cv, cv.group(cv.comp, "panel", start=1.0, end=end), 1.0, end, lambda t, s: 0.52 * s * len(t))
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    texts = {t.get("id"): t for t in root.iter() if t.tag.endswith("text") and t.get("width")}
    parents = {child: parent for parent in root.iter() for child in parent}
    paper = _luminance(kit.PAPER)
    layers = [layer for layer in root.iter() if layer.tag.endswith("layer") and layer.get("asset") in texts]
    for layer in layers:
        text = texts[layer.get("asset")]
        first, last = _shown(layer, parents, end)
        assert last - first >= 0.8334, f"{text.get('text')!r} is up for {last - first:.3f} s"
        ink = _luminance(text.get("color")[:7])
        assert (max(ink, paper) + 0.05) / (min(ink, paper) + 0.05) >= 4.5, f"{text.get('text')!r} is faint on paper"
        left, right = float(layer.get("x")), float(layer.get("x")) + float(text.get("width"))
        top, bottom = float(layer.get("y")), float(layer.get("y")) + float(text.get("height"))
        node = parents.get(layer)
        while node is not None:  # each popping group scales the box about its own pivot
            if node.get("anchorX") is not None:
                keyed = {a.get("property"): a for a in node if a.tag.endswith("animate")}
                sx = max((float(k.get("value")) for k in keyed.get("scaleX", ())), default=1.0)
                sy = max((float(k.get("value")) for k in keyed.get("scaleY", ())), default=1.0)
                px, py = float(node.get("anchorX")), float(node.get("anchorY"))
                if sx > 1.0:
                    left, right = px + (left - px) * sx, px + (right - px) * sx
                if sy > 1.0:
                    top, bottom = py + (top - py) * sy, py + (bottom - py) * sy
            node = parents.get(node)
        assert kit.LEFT - 1 <= left and right <= kit.RIGHT + 1, f"{text.get('text')!r} leaves the safe width"
        assert kit.CARD_Y - 1 <= top and bottom <= sp.BOTTOM + 1, f"{text.get('text')!r} leaves the safe height"


def test_the_blunt_knife_sprays_more_droplets_than_the_sharp_one_for_as_long_as_the_page_is_up():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=9.0)
    cv = Canvas(scene, font_asset="fraunces")
    sp.onion_fix(cv, cv.group(cv.comp, "panel", start=1.0, end=8.0), 1.0, 8.0, lambda t, s: 0.52 * s * len(t))
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    drops = [g for g in root.iter() if (g.get("id") or "").startswith("sp-droplet")]
    rows = sorted({round(float(e.get("y"))) for g in drops for e in g if e.get("shape") == "ellipse"})
    assert len(rows) == 2, "one row of droplets under each knife"
    per_row = [
        sum(1 for g in drops for e in g if e.get("shape") == "ellipse" and round(float(e.get("y"))) == y) for y in rows
    ]
    assert per_row[0] > per_row[1], "the blunt knife, drawn first, sprays more"
    last_seen = max(float(k.get("time")) for g in drops for a in g if a.get("property") == "opacity" for k in a)
    assert last_seen >= 7.0, "the knives keep cutting while the page is up"


def test_a_long_fold_page_turns_from_the_count_to_sheets_four_times_the_last():
    """The sheets are all down well before the page ends, so the whole picture is seen before the cut."""
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=9.0)
    cv = Canvas(scene, font_asset="fraunces")
    sp.fold_layers(cv, cv.group(cv.comp, "panel", start=1.0, end=8.0), 1.0, 8.0, lambda t, s: 0.52 * s * len(t))
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    sheets = [g for g in root.iter() if (g.get("id") or "").startswith("sp-sheet")]
    sides = sorted(float(s.get("width")) for g in sheets for s in g if s.get("shape") == "rect")
    assert len(sides) == 5 and all(b == 2 * a for a, b in zip(sides, sides[1:], strict=False))
    counts = [g for g in root.iter() if (g.get("id") or "").startswith("sp-count")]
    turn = min(float(g.get("start")) for g in sheets)
    assert all(float(g.get("end")) == turn for g in counts), "the count gives the page to the sheets"
    assert max(float(g.get("start")) for g in sheets) <= turn + 0.6 * (8.0 - turn)


@pytest.mark.parametrize("held_frames", [False, True])
def test_the_show_hands_its_held_frames_to_the_staging(monkeypatch, tmp_path, held_frames):
    """A delivered episode keeps its six-decimal keys; a new one asks for held_frames (ADR 0216)."""
    seen = []
    monkeypatch.setattr(sp, "build", lambda root, staging, flags: seen.append(staging))
    engine = tmp_path / "scene-render"
    engine.write_text("#!/bin/sh\n")  # the engine must exist (layout.find_engine); --init renders nothing with it
    env = {"SRSTUDIO_ENGINE": str(engine), "SRSTUDIO_RENDERS": str(tmp_path), "SRSTUDIO_FONTS": str(tmp_path)}
    sp.run(replace(SHOW, held_frames=held_frames), ["show", str(tmp_path), "--init"], env)
    assert seen[0].held_frames is held_frames


def panel_root(name: str, first: float = 1.0, last: float = 8.0) -> ET.Element:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=last + 1.0)
    cv = Canvas(scene, font_asset="fraunces")
    sp.PANELS[name](cv, cv.group(cv.comp, "panel", start=first, end=last), first, last, lambda t, s: 0.52 * s * len(t))
    return ET.fromstring(scene.to_bytes(layout="pretty"))


def groups(root: ET.Element, prefix: str) -> list[ET.Element]:
    return [g for g in root.iter() if (g.get("id") or "").startswith(prefix)]


def keyed(group: ET.Element, prop: str) -> list[tuple[float, float]]:
    return [(float(k.get("time")), float(k.get("value"))) for a in group if a.get("property") == prop for k in a]


def laps(group: ET.Element) -> list[float]:
    """The seconds between a travelling group's returns to its start: one per lap it runs."""
    rows = keyed(group, "x")
    starts = [t for (t, v), (_, before) in zip(rows[1:], rows, strict=False) if v < before]
    return [b - a for a, b in zip(starts, starts[1:], strict=False)]


def test_through_the_skull_the_voice_travels_in_bigger_slower_pulses_than_through_the_air():
    root = panel_root("voice-routes")
    air, bone = groups(root, "sp-air"), groups(root, "sp-bone")
    assert air and bone
    width = lambda g: float(next(e for e in g if e.get("shape") == "ellipse").get("width"))  # noqa: E731
    assert min(map(width, bone)) > 1.5 * max(map(width, air)), "the low end is the big dot"
    for dots in (air, bone):
        assert max(t for g in dots for t, _ in keyed(g, "x")) >= 7.0, "they keep coming while the page is up"
    lap = lambda g: keyed(g, "x")[8][0] - keyed(g, "x")[0][0]  # noqa: E731
    assert lap(bone[0]) > lap(air[0])


def test_what_you_hear_swells_deeper_than_what_a_phone_hears():
    root = panel_root("voice-air")
    waves = groups(root, "sp-wave")
    assert len(waves) == 2

    def swing(g):
        d = next(e for e in g if e.get("shape") == "path").get("path")
        ys = [float(part.split()[1]) for part in d[1:].split(" L")]
        return max(ys) - min(ys)

    yours, phone = map(swing, waves)
    assert yours > 2.0 * phone, "the skull's deep swell is under your own voice and not under the phone's"
    words = " ".join(t.get("text") or "" for t in root.iter() if t.tag.endswith("text"))
    assert "what you hear" in words and "what a phone hears" in words


def test_the_vessels_narrow_and_only_then_the_skin_folds_over_a_tip_that_shrinks():
    root = panel_root("finger-nerves")
    vessels = groups(root, "sp-vessel")
    assert len(vessels) == 2
    narrowed = [keyed(v, "scaleX") for v in vessels]
    assert all(rows[-1][1] < 0.5 and rows[0][1] == 1.0 for rows in narrowed)
    begins = min(t for rows in narrowed for (t, v), (_, w) in zip(rows, rows[1:], strict=False) if w < v)
    (ridges,) = groups(root, "sp-ridges")
    shows = min(t for t, v in keyed(ridges, "opacity") if v > 0.0)
    assert shows > begins, "the ridges follow the squeeze"
    (tip,) = groups(root, "sp-tip")
    assert ridges in list(tip), "the ridges lie on the tip and shrink with it"
    assert keyed(tip, "scaleX")[-1][1] < 1.0


def test_in_2013_wrinkled_fingers_finish_first_and_in_2014_they_keep_level():
    marbles = groups(panel_root("wet-grip", 1.0, 12.0), "sp-marble")
    assert len(marbles) == 4
    wrinkled13, smooth13, wrinkled14, smooth14 = (laps(g)[0] for g in marbles)
    assert wrinkled13 == pytest.approx(smooth13 * (1 - sp.GRIP_GAP), abs=0.02), "12 per cent less time (2013)"
    assert wrinkled14 == pytest.approx(smooth14), "no difference (2014)"


@pytest.mark.parametrize("name", ["wall-orbit", "wall-colour"])
def test_the_wall_is_drawn_in_nearly_the_land_s_own_colour(name):
    root = panel_root(name)
    strokes = {e.get("stroke") for e in root.iter() if e.get("shape") == "path"}
    fills = {e.get("fill") for e in root.iter()}
    assert sp.WALLSTONE in strokes and sp.LAND in fills
    assert _contrast(sp.WALLSTONE, sp.LAND) < 1.3


def test_the_wall_and_the_dirt_are_nearly_alike_and_never_drawn_as_one():
    """NASA (2005) says the wall's materials are similar in colour and texture to the dirt: the page says nearly, with
    an approximately-equal sign drawn as two waves, and keeps two earths a reader can tell apart."""
    root = panel_root("wall-colour")
    words = [t.get("text") or "" for t in root.iter() if t.tag.endswith("text")]
    assert "=" not in "".join(words), "an equals sign says the wall is the dirt"
    (nearly,) = groups(root, "sp-nearly")
    waves = [e for e in nearly.iter() if e.get("shape") == "path"]
    assert len(waves) == 2 and all(w.get("stroke") == sp.STAMP for w in waves)
    assert all(" C" in w.get("path") or " Q" in w.get("path") or " S" in w.get("path") for w in waves), "waves"
    assert 1.05 < _contrast(sp.WALLSTONE, sp.LAND) < 1.3, "two earths, close but not one colour"


def test_the_station_goes_round_while_the_page_is_up():
    (station,) = groups(panel_root("wall-orbit"), "sp-station")
    assert len(laps(station)) >= 1 and max(t for t, _ in keyed(station, "x")) >= 7.0


def _contrast(a: str, b: str) -> float:
    hi, lo = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def caption_scene(held_frames: bool, starts: tuple[float, ...]) -> bytes:
    """The caption bands of one line per start, a second each, on a reel that does or does not hold its frames."""
    from types import SimpleNamespace

    from srstudio import toon
    from srstudio.layout import VERTICAL

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=10.0)
    cv = Canvas(scene, font_asset="fraunces", held_frames=held_frames)
    spec = SimpleNamespace(safe_area=VERTICAL, width=1080, height=1920)
    ep = SimpleNamespace(spec=spec, cv=cv, comp=cv.comp, native_captions=lambda cues, look, id: None)
    lines = [toon.Line(f"{k}", "Not a chance.", at, at + 1.0) for k, at in enumerate(starts)]
    sp.captions(ep, lines, lambda t, s: 0.52 * s * len(t))
    return scene.to_bytes(layout="pretty")


def test_a_caption_band_on_a_held_reel_shows_on_the_frame_its_line_starts():
    from srstudio.held_gate import late_changes

    starts = (2.0, 4.108, 6.367)  # 6.367 s is a hair after frame 191 (6.3667 s): written there, the engine shows 192
    assert late_changes(caption_scene(True, starts)) == []


def test_a_caption_band_on_a_reel_built_before_held_frames_keeps_its_times():
    root = ET.fromstring(caption_scene(False, (6.367,)))
    (band,) = [g for g in root.iter() if g.get("start") is not None]
    assert (band.get("start"), band.get("end")) == ("6.367", "7.367")


def words_on(root: ET.Element) -> str:
    return " ".join(t.get("text") or "" for t in root.iter() if t.tag.endswith("text"))


def test_the_goldfish_swims_to_his_lever_again_and_again_and_food_comes_one_hour_in_twenty_four():
    root = panel_root("fish-lever")
    (fish,) = groups(root, "sp-fish")
    xs = keyed(fish, "x")
    arrivals = [t for t, v in xs if v == max(v for _, v in xs)]
    assert len(arrivals) >= 2 and arrivals[-1] >= 5.0, "he keeps going to the lever while the page is up"
    (hour,) = groups(root, "sp-hour")
    d = next(e for e in hour if e.get("shape") == "path").get("path")
    (cx, cy), *arc = [tuple(map(float, part.strip(" MLZ").split())) for part in d.split("L")]
    turn = [math.degrees(math.atan2(y - cy, x - cx)) for x, y in (arc[0], arc[-1])]
    assert turn[1] - turn[0] == pytest.approx(360.0 / 24.0, abs=0.01), "one hour of the dial's day"
    (hand,) = groups(root, "sp-clock-hand")
    assert keyed(hand, "rotation")[-1][1] > keyed(hand, "rotation")[0][1], "the clock goes round"
    assert "lever" in words_on(root) and "1 hour a day" in words_on(root)


def test_when_the_food_stops_the_goldfish_keeps_pressing_and_no_pellet_comes():
    root = panel_root("fish-stopped")
    assert groups(root, "sp-pellet") == [], "no food comes"
    (fish,) = groups(root, "sp-fish")
    xs = keyed(fish, "x")
    assert len([t for t, v in xs if v == max(v for _, v in xs)]) >= 2, "he keeps going to the lever"
    (lever,) = groups(root, "sp-lever")
    assert max(v for _, v in keyed(lever, "rotation")) > 0.0, "and pressing it"
    assert "no food" in words_on(root) and "1 hour a day" not in words_on(root)
    assert groups(panel_root("fish-lever"), "sp-pellet"), "while it was fed, the pellets came"


def test_the_days_are_crossed_off_week_after_week_and_the_fish_waits_at_his_corner():
    root = panel_root("fish-weeks", 1.0, 9.0)
    days = groups(root, "sp-day")
    assert len(days) == 28, "four weeks of days"
    shown = [min(t for t, v in keyed(day, "opacity") if v > 0.0) for day in days]
    assert shown == sorted(shown) and shown[-1] <= 9.0 - 1.0, "crossed off in order, the last a second before the cut"
    (fish,) = groups(root, "sp-fish")
    assert len(keyed(fish, "y")) >= 4, "he bobs where his food comes"
    assert "weeks" in words_on(root) and "food here" in words_on(root)
    food = groups(root, "sp-food")
    assert len(food) >= 3, "pellets on the water mark where the food comes"
    hollow = [e for e in root.iter() if e.get("shape") == "ellipse" and (e.get("fill") or "").endswith("00000000")]
    assert hollow == [], "no ring over the fish: a ring over his head reads as a halo"


def test_the_cut_face_browns_only_once_its_cells_have_broken_and_the_oxygen_has_come_in():
    root = panel_root("apple-cells")
    cells = groups(root, "sp-cell")
    broken = min(t for cell in cells for t, v in keyed(cell, "scaleX") if v < 0.5)
    (brown,) = groups(root, "sp-browning")
    rises = [(t, v) for t, v in keyed(brown, "opacity")]
    assert rises[0][1] == 0.0 and rises[-1][1] > 0.6
    assert min(t for t, v in rises if v > 0.0) > broken
    assert groups(root, "sp-oxygen") and groups(root, "sp-enzyme")
    assert "enzyme" in words_on(root) and "oxygen" in words_on(root) and "cells" in words_on(root)


def test_the_bare_half_browns_and_the_lemon_half_stays_pale_under_its_drops():
    root = panel_root("apple-lemon")
    browning = groups(root, "sp-browning")
    assert len(browning) == 1, "only the bare half has a brown layer"
    assert max(v for _, v in keyed(browning[0], "opacity")) > 0.6
    drops = groups(root, "sp-juice")
    assert drops and all(len(keyed(d, "y")) >= 4 for d in drops), "the juice keeps dripping on the other half"
    bare_x = float(next(e for e in browning[0] if e.get("shape") == "ellipse").get("x"))
    drop_x = float(next(e for e in drops[0] if e.get("shape") == "path").get("path").split()[0][1:])
    assert drop_x > bare_x + 300.0, "the drops fall on the other half"
    assert "bare" in words_on(root) and "lemon juice" in words_on(root)


def test_tapped_and_untapped_cans_lose_the_same_foam():
    root = panel_root("can-test")
    bars = groups(root, "sp-foam-bar")
    assert len(bars) == 2
    lengths = [keyed(bar, "scaleX")[-1][1] for bar in bars]
    assert lengths[0] == pytest.approx(lengths[1]), "no significant difference (Sopina et al., 2019)"
    (finger,) = groups(root, "sp-finger")
    assert len(keyed(finger, "rotation")) >= 6, "the finger taps, and keeps tapping"
    words = words_on(root)
    assert "tapped" in words and "not tapped" in words and "1,000 cans" in words
    assert "beer lost" in words and "foam" not in words, "the trial weighed the beer lost, not the foam"


def test_the_bubbles_on_the_can_s_wall_shrink_away_while_the_clock_runs():
    root = panel_root("can-bubbles")
    bubbles = groups(root, "sp-bubble")
    assert len(bubbles) >= 6
    for bubble in bubbles:
        rows = keyed(bubble, "scaleX")
        assert rows[0][1] == 1.0 and min(v for _, v in rows) < 0.2, "each one dissolves"
    (hand,) = groups(root, "sp-clock-hand")
    assert keyed(hand, "rotation")[-1][1] > keyed(hand, "rotation")[0][1]
    assert "wait" in words_on(root)
    last = max(bubbles, key=lambda b: max(t for t, _ in keyed(b, "scaleX")))
    assert float(last.get("x")) < 500.0, "the last bubble to go is on the wall by its label"


FIXTURE_FONT = next((f for f in SYSTEM_FONTS if f.is_file()), None)  # DejaVu Sans Bold, the fixture font
NEEDS_FONT = pytest.mark.skipif(FIXTURE_FONT is None, reason="no DejaVu Sans Bold to measure with")


def project_with_font(root: Path) -> Path:
    """A project folder holding the fixture font where the show's style installs its own."""
    assert FIXTURE_FONT is not None and host_kit.HOST.font is not None
    font = root / host_kit.HOST.font.src
    font.parent.mkdir(parents=True)
    font.write_bytes(FIXTURE_FONT.read_bytes())
    return root


def with_cover(headline: str) -> Show:
    """SHOW with a cover, its last line short enough for the fixture font's wider letters."""
    post = InstagramPost(title="Goldfish", description="d", thumbnail=Thumbnail(headline, 1.0, "Small Print #7"))
    return replace(with_beat(7, line="So the penny is the safe one up there."), post=post)


@NEEDS_FONT
def test_the_recording_refuses_a_cover_headline_too_wide_before_any_take(monkeypatch, tmp_path):
    """goldfish-memory's first headline only failed when its cover was drawn from the master, every take paid for."""
    taken = []
    monkeypatch.setattr(toon_sketch, "record_episode", lambda *a, **k: taken.append(a) or {})
    project = project_with_font(tmp_path)
    with pytest.raises(ThumbnailError, match="THREE-SECOND MEMORY"):
        sp.audio_main(with_cover("Goldfish\nthree-second memory?"), None, lambda *a, **k: [])([str(project)], {})
    assert taken == []
    sp.audio_main(with_cover("Goldfish\n3 seconds?"), None, lambda *a, **k: [])([str(project)], {})
    assert len(taken) == 1


def test_the_recording_refuses_a_cover_whose_font_is_not_installed(monkeypatch, tmp_path):
    monkeypatch.setattr(toon_sketch, "record_episode", lambda *a, **k: pytest.fail("a take was recorded"))
    with pytest.raises(ThumbnailError, match="is not in"):
        sp.audio_main(with_cover("Goldfish\n3 seconds?"), None, lambda *a, **k: [])([str(tmp_path)], {})


def display(text: str, size: float) -> float:
    """A display face's widths: m and w twice as wide as every other character."""
    return size * sum(1.0 if ch in "mwMW" else 0.5 for ch in text)


def test_a_caption_row_that_fits_by_characters_but_not_by_pixels_is_refused():
    """ "Hi, buddy. Remember me?" kept validate's 23 characters; in Fraunces it was 871 px of the 840 allowed."""
    SHOW.check_fit(display)
    buddy = with_beat(1, line="Hi, buddy. Remember me?")
    buddy.validate()
    with pytest.raises(ScriptError, match=r"try: 'Hi, buddy. Remember me\?' is 844 px"):
        buddy.check_fit(display)


@NEEDS_FONT
def test_the_recording_refuses_a_caption_too_wide_before_any_take(monkeypatch, tmp_path):
    taken = []
    monkeypatch.setattr(toon_sketch, "record_episode", lambda *a, **k: taken.append(a) or {})
    project = project_with_font(tmp_path)
    fits = with_cover("Goldfish\n3 seconds?")
    buddy = replace(fits, beats=tuple(replace(b, line="Hi, buddy. Remember me?") if b.id == "try" else b
                                     for b in fits.beats))  # fmt: skip
    with pytest.raises(ScriptError, match="Hi, buddy"):
        sp.audio_main(buddy, None, lambda *a, **k: [])([str(project)], {})
    assert taken == []
    sp.audio_main(fits, None, lambda *a, **k: [])([str(project)], {})
    assert len(taken) == 1


def narration(show: Show, kept: tuple[float, ...] | None = None) -> dict:
    """The recorder's narration.json for ``show``, its takes measured as ``kept`` (the show's own when None) and laid
    where the show's data said when it was recorded."""
    takes = show.kept if kept is None else kept
    recorded = replace(show, kept=takes)
    return {
        "items": [
            {"id": f"{i:02d}", "phase": "line", "start": at, "speech_duration": take}
            for i, (at, take) in enumerate(zip(recorded.starts(), takes, strict=True), 1)
        ]
    }


def test_takes_laid_where_the_data_says_are_in_step():
    SHOW.check_recorded(narration(SHOW))


def test_a_kept_changed_after_recording_is_refused_line_by_line():
    """The total can agree while the lines do not: two estimates off in opposite directions cancel out."""
    swapped = (KEPT[1], KEPT[0], *KEPT[2:])
    with pytest.raises(
        ScriptError,
        match=r"hook: take 1\.400 s, kept 2\.4 s; try: take 2\.400 s, kept 1\.4 s; "
        r"try: laid at 1\.600 s, starts at 2\.6 s$",
    ) as refused:
        SHOW.check_recorded(narration(SHOW, swapped))
    assert "no: laid at" not in str(refused.value), "from the third line on the two agree again"


def test_a_recording_with_a_line_missing_is_refused():
    short = narration(SHOW)
    short["items"].pop()
    with pytest.raises(ScriptError, match="7 recorded lines for 8 beats"):
        SHOW.check_recorded(short)


def run_env(tmp_path: Path) -> dict[str, str]:
    engine = tmp_path / "scene-render"
    engine.write_text("#!/bin/sh\n")  # the engine must exist (layout.find_engine)
    return {"SRSTUDIO_ENGINE": str(engine), "SRSTUDIO_RENDERS": str(tmp_path), "SRSTUDIO_FONTS": str(tmp_path)}


def test_the_voiced_build_refuses_takes_out_of_step_before_it_draws(monkeypatch, tmp_path):
    monkeypatch.setattr(sp, "build", lambda *a: pytest.fail("the build drew a reel whose voice is out of step"))
    env = run_env(tmp_path)
    (tmp_path / "narration.json").write_text(json.dumps(narration(SHOW, (KEPT[1], KEPT[0], *KEPT[2:]))))
    with pytest.raises(ScriptError, match="out of step"):
        sp.run(SHOW, ["show", str(tmp_path), "--voice"], env)
    (tmp_path / "narration.json").unlink()
    with pytest.raises(ScriptError, match="no narration.json"):
        sp.run(SHOW, ["show", str(tmp_path), "--voice"], env)


def test_the_voiced_build_draws_takes_in_step(monkeypatch, tmp_path):
    built = []
    monkeypatch.setattr(sp, "build", lambda root, staging, flags: built.append(flags))
    (tmp_path / "narration.json").write_text(json.dumps(narration(SHOW)))
    sp.run(SHOW, ["show", str(tmp_path), "--voice"], run_env(tmp_path))
    assert built == [{"--voice"}]


@pytest.mark.parametrize(
    "recorded",
    [[], {"items": "lines"}, {"items": [{"id": "01", "phase": "line", "start": 0.0}] * len(BEATS)},
     {"items": [{"phase": "line", "start": "soon", "speech_duration": 1.0}] * len(BEATS)}],
)  # fmt: skip
def test_a_recording_that_is_not_one_is_refused(recorded):
    with pytest.raises(ScriptError):
        SHOW.check_recorded(recorded)


# -- explainer shots in 3D on his worktop (ADR 0240) ------------------------------------------------------------------
LENS = Camera((0.0, -300.0, -362.0), (0.0, -290.0, -205.0), 33.0, 4.0)


def _tank(m) -> None:
    m.box("feeder", (0.0, -290.0, -205.0), (70.0, 120.0, 10.0))


def _pellet(m, pose: float) -> None:
    m.ell("pellet", (pose, -290.0, -215.0), (3.0, 3.0, 3.0))


def _shot(name: str = "test-tank", stamp_at: float | None = None) -> smallprint_scene.Shot:
    return smallprint_scene.Shot(name, LENS, "A TEST", _tank, lambda t: round(math.sin(t * 3.0) * 12.0, 1), _pellet,
                                 smallprint_lab.materials, smallprint_lab.finished, stamp_at=stamp_at)  # fmt: skip


def _with_shot(stamp_at: float | None = None, **changes) -> Show:
    return replace(with_beat(3, panel="test-tank"), scenes=(_shot(stamp_at=stamp_at),), **changes)


def test_an_explainer_shot_takes_a_panel_s_place_and_its_stamp_lands_on_its_word():
    sk = SHOW.sketch
    plain = _with_shot()
    plain.validate()
    (name, first, last, held), *_ = plain.panel_runs(sk.beats, sk.end)
    assert name == "test-tank" and [beat.id for beat, _ in held] == ["why"]
    on_word = _with_shot(stamp_at=first + 0.5)
    times = on_word.stamp_times(sk.beats, sk.end)
    assert times[0] == pytest.approx(first + 0.5)
    assert plain.stamp_times(sk.beats, sk.end)[0] == pytest.approx(max(first, sp.cut(held[0][1]) + 0.35))
    assert times[1:] == SHOW.stamp_times(sk.beats, sk.end)[1:]  # the paper panels keep theirs


@pytest.mark.parametrize(
    ("panel", "scenes", "match"),
    [
        ("test-tank", (_shot(), _shot()), "a panel name of its own"),
        ("penny-fall", (_shot("penny-fall"),), "a panel name of its own"),
        ("test-tank", (_shot(), _shot("unused-tank")), "no beat shows"),
    ],
)
def test_explainer_shots_that_clash_or_go_unused_are_refused(panel, scenes, match):
    with pytest.raises(ScriptError, match=match):
        replace(with_beat(3, panel=panel), scenes=scenes).validate()


def test_a_beat_on_a_shot_the_show_does_not_have_is_refused():
    with pytest.raises(ScriptError, match="the panels are"):
        with_beat(3, panel="test-tank").validate()


def test_an_explainer_shot_with_no_renders_to_draw_its_plates_is_refused():
    with pytest.raises(ScriptError, match="plates' renders"):
        drawn(_with_shot())


def test_an_explainer_shot_is_drawn_from_plates_with_its_stamp_and_its_chip(tmp_path):
    asked = []

    class Renders:
        def plate(self, plate) -> Path:
            asked.append(plate)
            path = tmp_path / f"plate-{len(asked)}.png"
            path.write_bytes(b"png")
            return path

    show = _with_shot()
    sk = show.sketch
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=sp.PAPER)
    cv = Canvas(scene, font_asset="fraunces")
    show.overlay(cv, cv.comp, sk.beats, sk.end, lambda text, size: 0.52 * size * len(text), Renders(), tmp_path / "p")
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    ids = {e.get("id") for e in root.iter()}
    assert {"test-tank-room-angle", "test-tank-bench-angle"} <= ids and len(asked) > 2
    words = {e.get("text") for e in root.iter() if e.tag.endswith("text")}
    assert {"A TEST", FOUND.text, *[f"{b.stamp.text}" for b in BEATS if b.stamp and b.panel != "penny-fall"]} <= words
    assert any(e.get("fill") == "#F4F0E6EB" for e in root.iter())  # the source on its chip, over a picture


def test_a_stamp_lands_where_its_layout_says_and_the_paper_page_keeps_its_place():
    measure = lambda text, size: 0.52 * size * len(text)  # noqa: E731
    for top, chip in ((kit.STAMP_Y, False), (236.0, True)):
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1920, fps="30", duration=4.0)
        cv = Canvas(scene, font_asset="fraunces")
        kit.stamp(cv, cv.comp, FOUND, 1.0, 3.0, measure, top=top, chip=chip)
        root = ET.fromstring(scene.to_bytes(layout="pretty"))
        _, box, sources, rows = kit.stamp_layout(FOUND, measure, top)
        rects = [e for e in root.iter() if e.get("shape") == "rect"]
        assert any(float(r.get("y")) == top for r in rects)
        assert box[1] < top + 10.0 and sources[0][1] > top
        chips = [r for r in rects if r.get("fill") == "#F4F0E6EB"]
        assert len(chips) == chip
        if chip:
            x0, y0, x1, y1 = kit.source_chip(sources)
            assert float(chips[0].get("x")) == pytest.approx(x0) and float(chips[0].get("y")) == pytest.approx(y0)
            assert x0 < sources[0][0] and y1 > sources[-1][3]
    with pytest.raises(ScriptError, match="needs a source row"):
        kit.source_chip([])

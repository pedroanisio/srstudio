"""Small Print as a format: a script keeps the show's rules or is refused, the worktop's states tile the reel, the
question opens and closes it, every finding is stamped with its source inside the safe area (ADR 0195)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, rafa_show, sketch
from srstudio import smallprint as sp
from srstudio import smallprint_kit as kit
from srstudio.smallprint import Beat, ScriptError, Show, Stamp
from srstudio.social import InstagramPost

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
         stamp=Stamp("23 STRIKES A YEAR", "US National Weather Service")),
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

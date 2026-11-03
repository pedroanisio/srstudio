"""Toon sets, second round: the office kitchen, the home office at night, the coffee machine, the desk lamp, the
plant and the tear-off calendar."""

import hashlib
import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, TOON, Canvas, flat_counter, fonts, registry, toon, toon_sets
from srstudio.canvas import Signature
from srstudio.toon import ToonDataError

D = 8.0


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=PEACH.background)
    return Canvas(
        scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"), signature=Signature() if signed else None
    )


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def animations(cv: Canvas, prop: str | None = None):
    return [a for a in tree(cv).iter("animate") if prop is None or a.get("property") == prop]


def keys_of(a):
    return [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]


def group_ids(cv: Canvas):
    return [g.get("id") for g in tree(cv).iter("group")]


def texts(cv: Canvas):
    return [t.get("text") for t in tree(cv).iter("text")]


# -- registration ---------------------------------------------------------------------------------------------------
def test_the_sets_and_props_are_registered_for_the_toon_style():
    assert "toon_sets" in TOON.parts
    entries = {e.name: e for e in registry.entries()}
    for kind, name in (
        ("location", "toon-kitchen"),
        ("location", "toon-home"),
        ("prop", "toon-coffee-machine"),
        ("prop", "toon-desk-lamp"),
        ("prop", "toon-plant"),
        ("prop", "toon-calendar"),
    ):
        assert entries[name].kind == kind
        assert entries[name].style == "toon"


# -- cycle_keys -----------------------------------------------------------------------------------------------------
def test_cycle_keys_repeat_the_pattern_and_key_both_ends():
    keys = toon_sets.cycle_keys([(0.0, 1.0), (0.5, 0.0)], 1.0, 0.0, 2.2)
    assert keys == [(0.0, 1.0), (0.5, 0.0), (1.0, 1.0), (1.5, 0.0), (2.0, 1.0), (2.2, 1.0)]


def test_cycle_keys_shift_by_the_phase_and_start_late():
    keys = toon_sets.cycle_keys([(0.0, 1.0), (0.5, 0.0)], 1.0, 3.0, 4.0, phase=0.25)
    assert keys == [(3.0, 0.0), (3.25, 1.0), (3.75, 0.0), (4.0, 0.0)]


def test_cycle_keys_hold_the_last_value_before_the_first_offset():
    keys = toon_sets.cycle_keys([(0.25, 1.0), (0.75, 0.0)], 1.0, 0.0, 1.0)
    assert keys == [(0.0, 0.0), (0.25, 1.0), (0.75, 0.0), (1.0, 0.0)]


@pytest.mark.parametrize(
    "pattern, period, start, end, message",
    [
        ([(0.0, 1.0)], 0.0, 0.0, 1.0, "period"),
        ([(0.0, 1.0)], float("nan"), 0.0, 1.0, "period"),
        ([], 1.0, 0.0, 1.0, "offsets"),
        ([(1.0, 1.0)], 1.0, 0.0, 1.0, "offsets"),
        ([(-0.1, 1.0)], 1.0, 0.0, 1.0, "offsets"),
        ([(0.0, 1.0)], 1.0, 2.0, 1.0, "later end"),
        ([(0.0, 1.0)], 1.0, -1.0, 1.0, "later end"),
    ],
)
def test_cycle_keys_refuse_a_bad_cycle(pattern, period, start, end, message):
    with pytest.raises(ToonDataError, match=message):
        toon_sets.cycle_keys(pattern, period, start, end)


@pytest.mark.parametrize("phase", [float("nan"), float("inf"), float("-inf"), True, "0.5"])
def test_cycle_keys_refuse_a_phase_that_is_not_a_finite_number_of_seconds(phase):
    with pytest.raises(ToonDataError, match="phase"):
        toon_sets.cycle_keys([(0.0, 1.0)], 1.0, 0.0, 2.0, phase=phase)


def test_cycle_keys_take_a_negative_phase_as_the_same_cycle_shifted_back():
    keys = toon_sets.cycle_keys([(0.0, 1.0), (0.5, 0.0)], 1.0, 0.0, 1.0, phase=-0.25)
    assert keys == [(0.0, 1.0), (0.25, 0.0), (0.75, 1.0), (1.0, 1.0)]
    assert keys == toon_sets.cycle_keys([(0.0, 1.0), (0.5, 0.0)], 1.0, 0.0, 1.0, phase=0.75)


# -- the kitchen ----------------------------------------------------------------------------------------------------
def test_the_kitchen_is_still_and_leaves_the_signature_to_the_desk():
    cv = canvas()
    toon_sets.kitchen(cv, cv.comp)
    assert animations(cv) == []
    assert not any((i or "").startswith("sig-") for i in group_ids(cv))  # toon.desk carries both marks
    assert texts(cv) == []  # no note on the fridge


def test_the_fridge_carries_a_note():
    cv = canvas()
    toon_sets.kitchen(cv, cv.comp, note="WHOSE MILK?")
    assert "WHOSE MILK?" in texts(cv)


@pytest.mark.parametrize("note", ["   ", "LABEL YOUR MILK!"])
def test_the_fridge_refuses_a_blank_or_long_note(note):
    cv = canvas()
    with pytest.raises(ToonDataError, match="1 to 14"):
        toon_sets.kitchen(cv, cv.comp, note=note)


def test_the_longest_note_the_fridge_takes_is_published_for_scripts_to_check():
    cv = canvas()
    toon_sets.kitchen(cv, cv.comp, note="X" * toon_sets.NOTE_MAX)
    with pytest.raises(ToonDataError, match="1 to 14"):
        toon_sets.kitchen(cv, cv.comp, note="X" * (toon_sets.NOTE_MAX + 1))


# -- the home office ------------------------------------------------------------------------------------------------
def test_the_home_office_is_still_without_an_end():
    cv = canvas()
    toon_sets.home(cv, cv.comp)
    assert animations(cv) == []
    assert not any((i or "").startswith("sig-") for i in group_ids(cv))


def test_the_home_office_twinkles_until_the_end():
    cv = canvas()
    toon_sets.home(cv, cv.comp, end=D)
    fades = animations(cv, "opacity")
    # every star, both groups of string lights and every fourth lit window
    assert len(fades) == len(toon_sets.STARS) + 2 + 3
    for a in fades:
        keys = keys_of(a)
        assert keys[0][0] == 0 and keys[-1][0] == D
        assert all(0 <= v <= 1 for _, v in keys)


@pytest.mark.parametrize("end", [-1, float("inf"), True, "8"])
def test_the_home_office_refuses_a_bad_end(end):
    cv = canvas()
    with pytest.raises(ToonDataError, match="end"):
        toon_sets.home(cv, cv.comp, end=end)


# -- the coffee machine ---------------------------------------------------------------------------------------------
def test_the_coffee_machine_is_dark_and_still_until_it_brews():
    cv = canvas()
    toon_sets.coffee_machine(cv, cv.comp)
    assert animations(cv) == []


def test_the_coffee_machine_blinks_drips_and_steams_while_it_brews():
    cv = canvas()
    toon_sets.coffee_machine(cv, cv.comp, brewing=[(1.0, 3.0), (5.0, 6.0)])
    blink, drop, steam_gate = animations(cv, "opacity")
    assert keys_of(blink)[0] == (0, 0) and keys_of(blink)[-1] == (6.0, 0)
    assert (1.0, 1) in keys_of(blink) and (1.5, 0) in keys_of(blink)
    assert all(t < 1.0 or 1.0 <= t <= 3.0 or 5.0 <= t <= 6.0 for t, v in keys_of(drop) if v == 1)
    (fall,) = animations(cv, "y")
    assert max(v for _, v in keys_of(fall)) == pytest.approx(toon.fh(52))
    assert keys_of(steam_gate) == [(0, 0), (1.0, 1), (3.0, 0), (5.0, 1), (6.0, 0)]
    (sway,) = animations(cv, "rotation")
    assert {v for _, v in keys_of(sway)} == {-4.0, 4.0}


@pytest.mark.parametrize(
    "spans, message",
    [
        ([(2.0, 1.0)], "start < end"),
        ([(-1.0, 1.0)], "start < end"),
        ([(0.0, float("nan"))], "start < end"),
        ([(True, 2.0)], "start < end"),
        ([(0.0, 2.0), (1.0, 3.0)], "overlap"),
        ([(1.0,)], "pairs"),
        (["ab"], "pairs"),
    ],
)
def test_the_coffee_machine_refuses_bad_spans(spans, message):
    cv = canvas()
    with pytest.raises(ToonDataError, match=message):
        toon_sets.coffee_machine(cv, cv.comp, brewing=spans)


# -- the desk lamp --------------------------------------------------------------------------------------------------
def test_the_desk_lamp_is_on_throughout_by_default():
    cv = canvas()
    toon_sets.desk_lamp(cv, cv.comp)
    assert animations(cv) == []


def test_the_desk_lamp_shows_its_light_only_in_its_spans():
    cv = canvas()
    toon_sets.desk_lamp(cv, cv.comp, lit=[(0.0, 4.0)])
    (gate,) = animations(cv, "opacity")
    assert keys_of(gate) == [(0, 1), (4.0, 0)]
    off = canvas()
    toon_sets.desk_lamp(off, off.comp, lit=())
    (dark,) = animations(off, "opacity")
    assert keys_of(dark) == [(0, 0)]


def test_the_lamp_and_the_plant_stand_clear_of_the_signature_cactus_on_the_desk():
    cv = canvas()
    toon.desk(cv, cv.comp)
    (cactus,) = [g for g in tree(cv).iter("group") if (g.get("id") or "").startswith("sig-cactus")]
    half = 44 * float(cactus.get("scaleX"))  # the cactus's widest arm, frame pixels at its scale
    left, right = float(cactus.get("x")) - half, float(cactus.get("x")) + half
    lamp_x = toon_sets.desk_lamp.__defaults__[1][0]
    assert toon.fx(lamp_x - 44) >= right  # the lamp's base
    plant_x, plant_scale = toon_sets.plant.__defaults__[0][0], toon_sets.plant.__defaults__[1]
    assert toon.fx(plant_x + 34 * plant_scale) <= left  # the plant's pot rim


# -- the plant ------------------------------------------------------------------------------------------------------
def test_the_plant_sways_until_the_end_and_is_still_without_one():
    cv = canvas()
    toon_sets.plant(cv, cv.comp, end=D)
    (sway,) = animations(cv, "rotation")
    keys = keys_of(sway)
    assert keys[0][0] == 0 and keys[-1][0] == D
    assert {v for _, v in keys} <= {-toon_sets.SWAY_DEGREES, toon_sets.SWAY_DEGREES}
    still = canvas()
    toon_sets.plant(still, still.comp, scale=0.6)
    assert animations(still) == []


@pytest.mark.parametrize("scale", [0.1, 4, float("nan"), "1"])
def test_the_plant_refuses_a_bad_scale(scale):
    cv = canvas()
    with pytest.raises(ToonDataError, match="scale"):
        toon_sets.plant(cv, cv.comp, scale=scale)


# -- the calendar ---------------------------------------------------------------------------------------------------
def test_the_calendar_tears_each_page_off_at_the_next_date():
    cv = canvas()
    toon_sets.calendar(cv, cv.comp, [(0, "OCT 27"), (2.0, "OCT 28"), (5.0, "NOV 1")])
    assert texts(cv) == ["NOV", "1", "OCT", "28", "OCT", "27"]  # the last page at the bottom
    fades = animations(cv, "opacity")
    assert [keys_of(a) for a in fades] == [
        [(0, 1), (5.0, 1), (5.0 + toon_sets.FLIP, 0)],
        [(0, 1), (2.0, 1), (2.0 + toon_sets.FLIP, 0)],
    ]
    for a in animations(cv, "rotation"):
        assert keys_of(a)[-1][1] == 38


def test_a_single_page_calendar_never_moves():
    cv = canvas()
    toon_sets.calendar(cv, cv.comp, [(0, "MON 9")])
    assert animations(cv) == []


@pytest.mark.parametrize(
    "pages, message",
    [
        ([], "from 0 s"),
        ([(1.0, "OCT 27")], "from 0 s"),
        ([(0, "Oct 27")], "reads like"),
        ([(0, "OCT 32")], "reads like"),
        ([(0, "OCT 0")], "reads like"),
        ([(0, 27)], "reads like"),
        ([(0, "OCT 1"), (0, "OCT 2")], "rising"),
        ([(-1, "OCT 1")], "second"),
        ([(True, "OCT 1")], "second"),
        ([("0", "OCT 1")], "second"),
        ([(0, "OCT 1", "x")], "is \\(second"),
    ],
)
def test_the_calendar_refuses_bad_pages(pages, message):
    with pytest.raises(ToonDataError, match=message):
        toon_sets.parse_pages(pages)


# -- the note insert -----------------------------------------------------------------------------------------------
def test_the_note_insert_fills_the_frame_with_the_note_for_its_span():
    cv = canvas()
    toon_sets.note_insert(cv, cv.comp, "IT MOVED.", 2.0, 3.5)
    t = tree(cv)
    g = next(g for g in t.iter("group") if g.get("start") == "2" or g.get("start") == "2.0")
    assert float(g.get("end")) == 3.5
    shapes = list(g.iter("shape"))
    assert shapes[0].get("width") == "1080" and shapes[0].get("height") == "1920"  # the fridge door, the whole frame
    assert texts(cv) == ["IT MOVED."]
    size = next(int(a.get("size")) for a in t.iter("text"))
    assert size >= 100  # legible on a phone, unlike the note on the fridge in the wide shot
    pushes = animations(cv, "scaleX")
    assert len(pushes) == 1 and keys_of(pushes[0])[0][0] == 2.0 and keys_of(pushes[0])[-1][0] == 3.5


@pytest.mark.parametrize(
    ("text", "start", "end", "match"),
    [
        ("", 1.0, 2.0, "1 to 14"),
        ("X" * 15, 1.0, 2.0, "1 to 14"),
        ("OK", 2.0, 2.0, "starts before it ends"),
        ("OK", -1.0, 2.0, "starts before it ends"),
    ],
)
def test_the_note_insert_refuses_a_note_or_span_it_cannot_show(text, start, end, match):
    cv = canvas()
    with pytest.raises(ToonDataError, match=match):
        toon_sets.note_insert(cv, cv.comp, text, start, end)


def test_the_note_insert_is_a_registered_toon_prop():
    part = registry.get("prop", "toon-note-insert")
    assert part.kind == "prop" and part.style == "toon"


# -- the call centre --------------------------------------------------------------------------------------------------
def test_the_call_centre_is_a_registered_toon_location():
    entry = {e.name: e for e in registry.entries()}["toon-call-centre"]
    assert entry.kind == "location" and entry.style == "toon"


def test_the_call_centre_counts_the_calls_waiting_and_shows_one_count_at_a_time():
    cv = canvas()
    toon_sets.call_centre(cv, cv.comp, [(0.0, 41), (2.5, 128), (5.0, 999)])
    shown = texts(cv)
    assert "CALLS WAITING" in shown and "41" in shown and "128" in shown and "999" in shown
    assert any("YOUR CALL" in t for t in shown if t)
    gates = [keys_of(a) for a in animations(cv, "opacity")]
    assert len(gates) == 3  # one gate per count, nothing else moves without an end
    assert gates[1][0] == (0.0, 0.0) and (2.5, 1.0) in gates[1] and (5.0, 0.0) in gates[1]


def test_the_call_centre_lamp_blinks_until_the_end_only():
    still = canvas()
    toon_sets.call_centre(still, still.comp, [(0.0, 7)])
    moving = canvas()
    toon_sets.call_centre(moving, moving.comp, [(0.0, 7)], end=6.0)
    assert len(animations(moving, "opacity")) == len(animations(still, "opacity")) + 1


@pytest.mark.parametrize(
    ("waiting", "message"),
    [
        ([], "at least one"),
        ([(1.0, 4)], "from 0"),
        ([(0.0, 4), (2.0, 5), (2.0, 6)], "in order"),
        ([(0.0, -1)], "0 to 9999"),
        ([(0.0, 10000)], "0 to 9999"),
        ([(0.0, 2.5)], "0 to 9999"),
        ([(0.0, True)], "0 to 9999"),
        ([(0.0, 3), (float("nan"), 4)], "in order"),
    ],
)
def test_the_call_centre_refuses_counts_it_cannot_show(waiting, message):
    cv = canvas()
    with pytest.raises(ToonDataError, match=message):
        toon_sets.call_centre(cv, cv.comp, waiting)


def test_a_bright_count_is_lettered_lighter_and_leaves_the_label_alone():
    plain, bright = canvas(), canvas()
    toon_sets.call_centre(plain, plain.comp, ((0.0, 99),))
    toon_sets.call_centre(bright, bright.comp, ((0.0, 99),), bright_count=True)

    def colours(cv):
        return {t.get("text"): t.get("color") for t in tree(cv).iter("text")}

    assert colours(plain)["99"] == toon_sets.LED and colours(bright)["99"] == toon_sets.LED_LABEL
    assert colours(plain)["CALLS WAITING"] == colours(bright)["CALLS WAITING"]


def test_a_legible_call_centre_letters_its_label_lighter_and_leaves_the_rest_as_it_was():
    plain, legible = canvas(), canvas()
    toon_sets.call_centre(plain, plain.comp, [(0.0, 12)])
    toon_sets.call_centre(legible, legible.comp, [(0.0, 12)], legible=True)
    label = {t.get("text"): t.get("color") for t in tree(legible).iter("text")}
    assert label["CALLS WAITING"] == toon_sets.LED_LABEL != toon_sets.LED and label["12"] == toon_sets.LED
    unchanged = canvas()
    toon_sets.call_centre(unchanged, unchanged.comp, [(0.0, 12)], legible=False)
    assert unchanged.scene.to_bytes() == plain.scene.to_bytes()  # off by default: published sets are unchanged


@pytest.fixture(scope="module")
def comic_neue() -> Path:
    """The pinned Comic Neue of a generated Toon project (``SRSTUDIO_EPISODES``), and the engine, or skip: contrast
    is measured on the glyphs as drawn, so the check needs the real font and a render."""
    env, found = os.environ.get("SRSTUDIO_EPISODES"), os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not env or not found:
        pytest.skip("set SRSTUDIO_EPISODES and SRSTUDIO_ENGINE to measure the label's contrast")
    font = Path(env) / "in-network" / "assets" / "fonts" / "comic-neue-700-italic.ttf"
    if not font.is_file():
        pytest.skip(f"no pinned Comic Neue at {font}")
    return font


def contrast_findings(folder: Path, font: Path, **kw) -> tuple[int, list[dict]]:
    """Encode the call centre strictly under the style's accessibility checks; the exit code and the findings."""
    folder.mkdir()
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=1.0, background=PEACH.background)
    scene.add_metadata(title="call centre").add_accessibility(**TOON.accessibility)
    cv = Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"), signature=Signature())
    shutil.copy(font, folder / font.name)
    cv.assets.add_font(id="comic-neue", src=font.name, family=fonts.inspect_ttf(font.read_bytes()).family,
                       sha256=hashlib.sha256(font.read_bytes()).hexdigest())  # fmt: skip
    toon_sets.call_centre(cv, cv.comp, [(0.0, 12)], **kw)
    (folder / "set.scene.xml").write_bytes(scene.to_bytes(layout="pretty"))
    engine = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    run = subprocess.run(
        [engine, "encode", "set.scene.xml", "-o", "set.mp4", "--strict", "--report", "report.json"],
        cwd=folder, capture_output=True, text=True,
    )  # fmt: skip
    return run.returncode, json.loads((folder / "report.json").read_text()).get("findings", [])


def test_the_call_centre_label_fails_the_strict_contrast_check_unless_legible(tmp_path, comic_neue):
    code, findings = contrast_findings(tmp_path / "plain", comic_neue)
    assert code != 0 and [f["code"] for f in findings] == ["LEG-CONTRAST"] and findings[0]["measured"] < 4.5
    assert contrast_findings(tmp_path / "legible", comic_neue, legible=True) == (0, [])


def test_a_kitchen_can_leave_the_chair_out_and_the_default_keeps_it():
    def drawn(**options) -> bytes:
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background=PEACH.background)
        cv = Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))
        toon_sets.kitchen(cv, cv.comp, **options)
        return scene.to_bytes(layout="pretty")

    assert toon_sets.KITCHEN_CHAIR.encode().lower() in drawn().lower()
    assert toon_sets.KITCHEN_CHAIR.encode().lower() not in drawn(chair=False).lower()
    assert drawn() == drawn(chair=True)

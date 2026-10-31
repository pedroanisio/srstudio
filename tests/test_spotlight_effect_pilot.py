"""The pilot's script is checked, its figures are the sources', and it stays outside the @tuxmeme publishing path."""

from __future__ import annotations

import math
import sys
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, mind_kit, sketch, toon, toon_rigs, toon_sketch
from srstudio.sketch import Line

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import spotlight_effect_data as pilot  # noqa: E402

SHIRT_HALF, BOARD_HALF = 78.0, 80.0  # the shirt's and the clipboard's drawn half-widths, in their own units


def with_lines(*changes: tuple[int, str]) -> sketch.Sketch:
    lines = list(pilot.LINES)
    for index, text in changes:
        lines[index] = replace(lines[index], text=text)
    return replace(pilot.SKETCH, lines=tuple(lines))


def test_the_pilot_as_written_is_valid():
    pilot.validate()


def test_the_figures_are_the_ones_the_paper_printed():
    assert pilot.GUESSED[1:] == (0.46, "46%")
    assert pilot.COULD[1:] == (0.23, "23%")
    assert pilot.GUESSED[1] == pytest.approx(2 * pilot.COULD[1])  # "exactly twice as high", which the card says
    assert "double" in pilot.STUDY.result


def test_the_figures_in_the_post_are_the_ones_on_the_card():
    for figure in (pilot.GUESSED[2], pilot.COULD[2]):
        assert figure in pilot.POST.description
    assert "Gilovich, Medvec & Savitsky (2000)" in pilot.POST.description


@pytest.mark.parametrize(
    "claim", ["Nobody noticed", "Nobody is looking", "far less", "a whole day", "stain", "haircut"]
)
def test_a_reel_never_says_what_the_sources_contradict(claim):
    words = " ".join((*(q.text for q in pilot.LINES), pilot.POST.title, pilot.POST.description)).lower()
    assert claim.lower() not in words


@pytest.mark.parametrize("bad", ["Science proves it.", "This is your OCD talking.", "Tag someone who does this."])
def test_a_line_the_channel_keeps_off_screen_stops_the_build(bad):
    with pytest.raises(mind_kit.MindKitError):
        pilot.validate(with_lines((15, bad)))


def test_a_lost_event_stops_the_build():
    beats = tuple(replace(b, event="") if b.event == "real" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_an_unknown_event_stops_the_build():
    beats = tuple(replace(b, event="bonus") if b.event == "split" else b for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_events_out_of_order_stop_the_build():
    swap = {"guess": "real", "real": "guess"}
    beats = tuple(replace(b, event=swap.get(b.event, b.event)) for b in pilot.BEATS)
    with pytest.raises(sketch.SketchError, match="the events run"):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_reel_opens_on_the_behaviour_with_its_line():
    beats = (replace(pilot.BEATS[0], line=None, word=None, caption=""), *pilot.BEATS[1:])
    with pytest.raises(sketch.SketchError):
        pilot.validate(replace(pilot.SKETCH, beats=beats))


def test_the_end_cuts_back_to_the_first_words():
    assert pilot.LINES[0].text == pilot.LINES[-1].text == "One embarrassing shirt."


def test_the_name_is_spoken_once_and_the_card_holds_it():
    assert sum(pilot.NAME.lower() in q.text.lower() for q in pilot.LINES) == 1


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


def scene_of(app: sketch.Appearance) -> ET.Element:
    """The shot as the pilot dresses it, the character's own drawing left out."""
    sk = pilot.SKETCH
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=sk.end, background=mind_kit.INK)
    cv = Canvas(scene, mind_kit.MIND.palette(), font_asset="fraunces")
    back, light, front = (cv.group(cv.comp, name) for name in ("back", "light", "front"))
    measure = lambda text, size: 0.5 * size * len(text)  # noqa: E731
    pilot.dress(toon_sketch.Shot(cv, app, back, front, sk.beats, sk.end, measure, light, pilot.VERSIONS))
    return ET.fromstring(scene.to_bytes(layout="pretty"))


def transforms(root: ET.Element, wanted: str) -> list[tuple[float, float, float]]:
    """Each group whose id starts with ``wanted``: where its origin lands on screen, and at what scale."""
    found = []

    def walk(node, x, y, scale):
        for child in node:
            if child.tag != "group":
                continue
            anchor_x, anchor_y = float(child.get("anchorX", 0)), float(child.get("anchorY", 0))
            local = float(child.get("scaleX", 1))
            there = (
                x + scale * (float(child.get("x", 0)) - local * anchor_x),
                y + scale * (float(child.get("y", 0)) - local * anchor_y),
                scale * local,
            )
            if child.get("id", "").startswith(wanted):
                found.append(there)
            walk(child, *there)

    walk(root.find("composition"), 0.0, 0.0, 1.0)
    return found


def figure_framing(app: sketch.Appearance, who: str) -> tuple[float, float, float]:
    """How the shot draws ``who``: the screen x and y of reference pixel (0, 0), and the scale."""
    if app.who == mind_kit.STAGE:
        return pilot.ROW[who] - pilot.ROW_SCALE * toon.fx(165), pilot.ROW_Y, pilot.ROW_SCALE
    scale, dx = pilot.FIGURES[who]
    seat_x, seat_y = toon.fx(toon_sketch.SEAT[0]), toon.fy(toon_sketch.SEAT[1])
    return seat_x + toon.fh(dx) - scale * seat_x, seat_y - scale * seat_y, scale


def rest_of_head(who: str) -> tuple[float, float]:
    """The reference x of the neck and the lowest the head sits at rest, where the muzzle and chin are."""
    rig = toon_rigs.rig_of(sketch.part_of(who), pilot.VERSIONS)
    a = math.radians(rig.tilt)
    return rig.neck[0], max(
        rig.neck[1] + (x - rig.neck[0]) * math.sin(a) + (y - rig.neck[1]) * math.cos(a) for x, y in rig.head
    )


def wearers(app: sketch.Appearance) -> list[str]:
    return [who for who in ("hamster", "goat") if app.who == who or (app.who == mind_kit.STAGE and who in pilot.ROW)]


def shirts() -> list[tuple[str, sketch.Appearance, tuple[float, float, float]]]:
    """Every shirt in the reel: who wears it, the shot, and where the scene really puts it."""
    worn = []
    for app in sketch.appearances(pilot.SKETCH.beats, pilot.SKETCH.end):
        root = scene_of(app)
        for at in transforms(root, "tee"):
            necks = {
                who: figure_framing(app, who)[0] + figure_framing(app, who)[2] * toon.fx(rest_of_head(who)[0])
                for who in wearers(app)
            }
            worn.append((min(necks, key=lambda who: abs(necks[who] - at[0])), app, at))
    return worn


SHIRTS = shirts()


def test_the_shirt_is_in_the_shots_the_reel_shows_it():
    assert {who for who, _, _ in SHIRTS} == {"hamster", "goat"}
    assert {app.who for _, app, _ in SHIRTS} == {"hamster", "goat", mind_kit.STAGE}


@pytest.mark.parametrize("worn", SHIRTS, ids=lambda w: f"{w[0]}-in-{w[1].who}-at-{w[1].start:.1f}")
def test_the_collar_is_below_the_muzzle_in_every_shot(worn):
    who, app, (_, collar, _) = worn
    _, y, scale = figure_framing(app, who)
    assert collar > y + scale * toon.fy(rest_of_head(who)[1])


@pytest.mark.parametrize("worn", SHIRTS, ids=lambda w: f"{w[0]}-in-{w[1].who}-at-{w[1].start:.1f}")
def test_the_shirt_is_centred_on_the_figure_in_every_shot(worn):
    who, app, (middle, _, _) = worn
    x, _, scale = figure_framing(app, who)
    assert middle == pytest.approx(x + scale * toon.fx(rest_of_head(who)[0]), abs=1.0)


@pytest.mark.parametrize("who", ["hamster", "goat"])
def test_a_shirt_is_one_size_on_its_figure_whatever_the_shot(who):
    sizes = {round(scale / figure_framing(app, wearer)[2], 3) for wearer, app, (_, _, scale) in SHIRTS if wearer == who}
    assert len(sizes) == 1


def test_the_board_hides_the_shirt_entirely_until_it_drops():
    checked = 0
    for app in sketch.appearances(pilot.SKETCH.beats, pilot.SKETCH.end):
        root = scene_of(app)
        boards = transforms(root, "board")
        if boards:
            shirt = [at for _, shot, at in SHIRTS if shot == app and min(abs(at[0] - b[0]) for b in boards) < 150.0]
            for x, _, scale in shirt:
                board_x, _, board_scale = min(boards, key=lambda b: abs(b[0] - x))
                half = SHIRT_HALF * scale * toon.fh(1)
                cover = BOARD_HALF * board_scale * toon.fh(1)
                assert board_x - cover <= x - half and x + half <= board_x + cover
                checked += 1
    assert checked >= 4


def test_the_ledge_stands_in_front_of_every_shirt():
    seen = 0
    for app in sketch.appearances(pilot.SKETCH.beats, pilot.SKETCH.end):
        nodes = list(scene_of(app).iter())  # in drawing order
        ledges = [k for k, n in enumerate(nodes) if n.get("width") == str(toon.fh(612))]
        if ledges:
            worn = [k for k, n in enumerate(nodes) if n.tag == "group" and n.get("id", "").startswith("tee")]
            assert worn and max(worn) < ledges[-1], app
            seen += 1
    assert seen >= 4


def test_the_rows_board_keeps_its_lettering_large_enough_to_hold_contrast():
    assert pilot.ROW_SCALE * pilot.ROW_BOARD["scale"] * 24 >= 16.0  # a clipboard's labels, in screen pixels

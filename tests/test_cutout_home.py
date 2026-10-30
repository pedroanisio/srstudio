"""Cutout at home and in the shops: the study, the till, and the printer's ransom demand."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_home, registry
from support.tip_tablet import canvas


def texts(cv) -> list[str]:
    root = ET.fromstring(cv.scene.to_bytes())
    return [t.get("text") for t in root.iter() if t.tag.rsplit("}", 1)[-1] == "text"]


def ids(cv) -> set[str]:
    return {e.get("id") for e in ET.fromstring(cv.scene.to_bytes()).iter() if e.get("id")}


def errors(cv) -> list:
    return [f for f in cv.scene.check() if f.severity == "error" and "fontAsset" not in f.message]


@pytest.mark.parametrize(
    ("kind", "name"),
    [
        ("prop", "desk-printer"),
        ("prop", "ransom-note"),
        ("prop", "hostage-photo"),
        ("prop", "paper-bag"),
        ("location", "home-study"),
        ("location", "shop-till"),
    ],
)
def test_each_is_a_registered_cutout_part(kind, name):
    entry = registry.get(kind, name)
    assert entry.style == "cutout" and entry.summary


def test_the_printer_holds_each_reading_until_the_next():
    cv = canvas()
    cutout_home.desk_printer(cv, cv.comp, lcd=((0.0, "LOW ON CYAN"), (2.0, "THANK YOU")), whirs=((0.5, 1.0),))
    assert {"LOW ON CYAN", "THANK YOU"} <= set(texts(cv))
    assert {"desk-printer-reading-1", "desk-printer-reading-2"} <= ids(cv)
    assert errors(cv) == []


def test_each_sheet_gets_its_own_group_in_the_tray():
    cv = canvas()
    cutout_home.desk_printer(cv, cv.comp, sheets=((1.0, 0.5, "#111111"), (2.0, 0.5, "#14B4DA")))
    assert {"desk-printer-sheet-1", "desk-printer-sheet-2"} <= ids(cv)
    assert errors(cv) == []


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(lcd=()), "lcd"),
        (dict(lcd=((1.0, "LATE"),)), "lcd"),
        (dict(lcd=((0.0, "A"), (0.0, "B"))), "lcd"),
        (dict(lcd=((0.0, ""),)), "reading"),
        (dict(lcd=((0.0, "X" * (cutout_home.LCD_CHARS + 1)),)), "reading"),
        (dict(whirs=((2.0, 1.0),)), "whir"),
        (dict(sheets=((2.0, 0.5, "#111111"), (1.0, 0.5, "#111111"))), "sheets"),
        (dict(scale=0), "scale"),
        (dict(scale=True), "scale"),
    ],
)
def test_it_refuses_a_printer_it_cannot_draw(kw, match):
    with pytest.raises(cutout_home.CutoutHomeError, match=match):
        cutout_home.desk_printer(canvas(), None, **kw)


def test_the_printer_needs_a_font():
    with pytest.raises(cutout_home.CutoutHomeError, match="font"):
        cutout_home.desk_printer(canvas(None), None)


def test_a_ransom_note_cuts_every_letter_out_on_its_own_scrap():
    cv = canvas()
    cutout_home.ransom_note(cv, cv.comp, lines=("PAY", "UP NOW"))
    assert sorted(t for t in texts(cv) if t) == sorted("PAYUPNOW")
    assert errors(cv) == []


def test_a_ransom_note_is_the_same_note_for_the_same_seed():
    first, again, other = canvas(), canvas(), canvas()
    for cv, seed in ((first, 7), (again, 7), (other, 8)):
        cutout_home.ransom_note(cv, cv.comp, seed=seed)
    assert first.scene.to_bytes() == again.scene.to_bytes() != other.scene.to_bytes()


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(lines=()), "lines"),
        (dict(lines=("   ",)), "lines"),
        (dict(lines=("X" * (cutout_home.NOTE_LINE + 1),)), "lines"),
        (dict(height=0), "height"),
        (dict(size=-1), "size"),
        (dict(lines=("A",) * 12), "do not fit"),
    ],
)
def test_it_refuses_a_note_it_cannot_cut_out(kw, match):
    with pytest.raises(cutout_home.CutoutHomeError, match=match):
        cutout_home.ransom_note(canvas(), None, **kw)


def test_a_ransom_note_needs_a_font():
    with pytest.raises(cutout_home.CutoutHomeError, match="font"):
        cutout_home.ransom_note(canvas(None), None)


@pytest.mark.parametrize("draw", [cutout_home.hostage_photo, cutout_home.paper_bag])
def test_the_small_props_draw_and_refuse_a_bad_scale(draw):
    cv = canvas(None)
    draw(cv, cv.comp, 300, 900, scale=1.2)
    assert errors(cv) == []
    with pytest.raises(cutout_home.CutoutHomeError, match="scale"):
        draw(canvas(None), None, scale=0)


def test_the_study_draws_its_slots_in_order_and_gates_its_shots():
    cv = canvas()
    order: list[str] = []
    cutout_home.home_study(
        cv,
        cv.comp,
        behind_desk=lambda g: order.append("behind"),
        on_desk=lambda g: order.append("on"),
        cactus=lambda g: order.append("cactus"),
        shots=[(0.0, 1.0)],
    )
    assert order == ["behind", "cactus", "on"]
    assert "location-home-study" in ids(cv)
    assert errors(cv) == []


def test_the_till_draws_its_counter_slot():
    cv = canvas()
    order: list[str] = []
    cutout_home.shop_till(cv, cv.comp, on_counter=lambda g: order.append("counter"), shots=[(0.0, 1.0)])
    assert order == ["counter"] and "location-shop-till" in ids(cv)
    assert errors(cv) == []


def test_the_desk_seen_from_above_fills_the_frame():
    cv = canvas(None)
    assert cutout_home.desk_top(cv, cv.comp).id == "study-desk-top"
    assert errors(cv) == []

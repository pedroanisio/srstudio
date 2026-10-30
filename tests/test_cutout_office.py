"""Cutout at the office, off the clock: the break room, the leaving party, and the props of a long career."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_office, registry
from support.tip_tablet import canvas

CHECKED = cutout_office.CutoutOfficeError


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
        ("prop", "drip-machine"),
        ("prop", "office-mug"),
        ("prop", "days-board"),
        ("prop", "wall-planner"),
        ("prop", "gold-watch"),
        ("prop", "stage-mic"),
        ("prop", "party-crowd"),
        ("location", "break-room"),
        ("location", "office-party"),
    ],
)
def test_each_is_a_registered_cutout_part(kind, name):
    entry = registry.get(kind, name)
    assert entry.style == "cutout" and entry.summary


def test_the_machine_pours_only_when_asked():
    plain, pouring = canvas(None), canvas(None)
    cutout_office.drip_machine(plain, plain.comp)
    cutout_office.drip_machine(pouring, pouring.comp, pours=((0.0, 2.0),))
    assert "drip-machine-stream" not in ids(plain) and "drip-machine-stream" in ids(pouring)
    assert errors(pouring) == []


def test_a_mug_letters_its_label_and_can_go_plain():
    cv = canvas()
    cutout_office.office_mug(cv, cv.comp, label="6 YEARS")
    assert texts(cv) == ["6 YEARS"]
    plain = canvas(None)
    cutout_office.office_mug(plain, plain.comp)
    assert texts(plain) == []


@pytest.mark.parametrize("label", ["", "  ", "X" * (cutout_office.MUG_LABEL + 1)])
def test_it_refuses_a_label_it_cannot_letter(label):
    with pytest.raises(CHECKED, match="label"):
        cutout_office.office_mug(canvas(), None, label=label)


def test_a_mug_label_needs_a_font():
    with pytest.raises(CHECKED, match="font"):
        cutout_office.office_mug(canvas(None), None, label="MUG")


def test_the_board_holds_each_count_until_the_next():
    cv = canvas()
    cutout_office.days_board(cv, cv.comp, heading="DAYS", counts=((0.0, "0"), (2.0, "2,190")))
    assert {"DAYS", "0", "2,190"} <= set(texts(cv))
    assert {"days-board-count-1", "days-board-count-2"} <= ids(cv)
    assert errors(cv) == []


@pytest.mark.parametrize(
    ("kw", "match"),
    [
        (dict(counts=()), "counts"),
        (dict(counts=((1.0, "0"),)), "counts"),
        (dict(counts=((0.0, "1"), (0.0, "2"))), "counts"),
        (dict(counts=((0.0, " "),)), "counts"),
        (dict(counts=((0.0, "X" * (cutout_office.BOARD_CHARS + 1)),)), "counts"),
        (dict(heading=" "), "heading"),
        (dict(scale=0), "scale"),
    ],
)
def test_it_refuses_a_board_it_cannot_draw(kw, match):
    with pytest.raises(CHECKED, match=match):
        cutout_office.days_board(canvas(), None, **kw)


def test_every_page_of_the_planner_circles_every_friday():
    cv = canvas()
    cutout_office.wall_planner(cv, cv.comp, months=((0.0, "MARCH"), (1.0, "JUNE")), note="QUIT")
    assert texts(cv).count("QUIT") == 2 * cutout_office.PLANNER_WEEKS
    assert {"MARCH", "JUNE"} <= set(texts(cv))
    assert errors(cv) == []


@pytest.mark.parametrize(
    ("kw", "match"), [(dict(months=()), "months"), (dict(months=((2.0, "MAY"),)), "months"), (dict(note=" "), "note")]
)
def test_it_refuses_a_planner_it_cannot_print(kw, match):
    with pytest.raises(CHECKED, match=match):
        cutout_office.wall_planner(canvas(), None, **kw)


def test_the_watch_gleams_only_when_asked():
    plain, shining = canvas(None), canvas(None)
    cutout_office.gold_watch(plain, plain.comp)
    cutout_office.gold_watch(shining, shining.comp, gleam=1.0)
    assert "gold-watch-gleam" not in ids(plain) and "gold-watch-gleam" in ids(shining)


def test_the_mic_needs_a_height():
    cv = canvas(None)
    cutout_office.stage_mic(cv, cv.comp)
    assert errors(cv) == []
    with pytest.raises(CHECKED, match="height"):
        cutout_office.stage_mic(canvas(None), None, height=0)


def test_the_crowd_claps_only_in_its_spans():
    still, clapping = canvas(None), canvas(None)
    cutout_office.party_crowd(still, still.comp)
    cutout_office.party_crowd(clapping, clapping.comp, claps=((0.0, 1.0),))
    assert not any("hands" in i for i in ids(still)) and any("hands" in i for i in ids(clapping))
    with pytest.raises(CHECKED, match="clap"):
        cutout_office.party_crowd(canvas(None), None, claps=((2.0, 1.0),))


@pytest.mark.parametrize(
    ("draw", "kw", "match"),
    [
        (cutout_office.drip_machine, dict(scale=0), "scale"),
        (cutout_office.drip_machine, dict(pours=((2.0, 1.0),)), "pour"),
        (cutout_office.gold_watch, dict(scale=True), "scale"),
    ],
)
def test_the_props_refuse_bad_arguments(draw, kw, match):
    with pytest.raises(CHECKED, match=match):
        draw(canvas(None), None, **kw)


def test_the_break_room_draws_its_slots_in_depth_order():
    cv = canvas()
    order: list[str] = []
    cutout_office.break_room(
        cv,
        cv.comp,
        behind_counter=lambda g: order.append("behind"),
        on_counter=lambda g: order.append("on"),
        on_wall=lambda g: order.append("wall"),
        shots=[(0.0, 1.0)],
    )
    assert order == ["wall", "behind", "on"]
    assert errors(cv) == []


def test_the_party_hangs_its_banner_and_draws_its_slots():
    cv = canvas()
    order: list[str] = []
    cutout_office.office_party(
        cv, cv.comp, stage=lambda g: order.append("stage"), front=lambda g: order.append("front"), banner="40 YEARS"
    )
    assert order == ["stage", "front"] and "40 YEARS" in texts(cv)
    assert errors(cv) == []


@pytest.mark.parametrize("banner", [" ", "X" * (cutout_office.PARTY_BANNER_CHARS + 1)])
def test_it_refuses_a_banner_it_cannot_letter(banner):
    with pytest.raises(CHECKED, match="banner"):
        cutout_office.office_party(canvas(), None, banner=banner)


def test_the_party_needs_a_font():
    with pytest.raises(CHECKED, match="font"):
        cutout_office.office_party(canvas(None), None)

"""The Ink parking meter: a talking pay station whose coin slot is taped over, whose display changes over the take
and whose lights chase only while it speaks; the kerb it stands on, with the doodle, a parked car and the tow truck
that takes it; and the parking app on a held phone, each row arriving and ticking in turn, a progress bar that
fills and five stars that light; plus the refusals."""

import xml.etree.ElementTree as ET

import pytest

from srstudio import Canvas, ink_meter, registry
from srstudio.ink_meter import AppRow, MeterError
from support.ink_meter import canvas, take


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas):
    return [t.get("text") for t in tree(cv).iter("text")]


def animated(cv: Canvas, prop: str):
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == prop
    ]


def test_the_parts_are_registered_in_the_ink_style():
    entries = {e.name: e for e in registry.entries()}
    for kind, name in (("character", "talking-meter"), ("location", "ink-kerb"), ("graphic", "ink-app-screen")):
        assert entries[name].kind == kind and entries[name].style == "ink"


def test_the_meter_chases_its_lights_and_shows_voice_marks_only_when_it_speaks():
    talking, silent = canvas(), canvas()
    ink_meter.meter(talking, talking.comp, take(), 500, 300)
    ink_meter.meter(silent, silent.comp, take("human"), 500, 300)
    assert animated(silent, "opacity") == []
    fades = animated(talking, "opacity")
    assert len(fades) == ink_meter.LIGHTS + 1  # each light over the display, and the voice marks
    assert all(k[0] == (0.0, 1.0) and k[-1][0] < 2.0 for k in fades[: ink_meter.LIGHTS])


def test_the_slot_is_taped_over_and_the_display_changes_on_cue():
    cv = canvas()
    ink_meter.meter(cv, cv.comp, take("human"), 500, 300, display=((0.0, "SCAN TO PAY"), (1.2, "THANK YOU")))
    assert {"SCAN TO PAY", "THANK YOU", ink_meter.TAPE_TEXT} <= set(texts(cv))
    assert [(0.0, 0.0), (1.2, 1.0)] in animated(cv, "opacity")  # the second reading shows from 1.2 s


def test_lettering_too_small_to_read_is_scrawled_not_set():
    near, far = canvas(), canvas()
    ink_meter.kerb(near, near.comp, take("human", 3.0))
    ink_meter.kerb(far, far.comp, take("human", 3.0), tow=0.8)  # pulled back to TOW_WIDE
    assert {"SCAN TO PAY", ink_meter.TAPE_TEXT} <= set(texts(near))
    assert texts(far) == []  # the display and the tape drawn as pen scrawl at 0.6, under LEGIBLE_PX
    small = canvas()
    ink_meter.meter(small, small.comp, take(), 500, 300, 0.5)
    assert texts(small) == []


def text_spans(cv: Canvas) -> list[tuple[str, float, float]]:
    """Each text layer's text and the x span it is drawn over in the frame, through its groups' x, anchor and scale."""
    root = tree(cv)
    assets = {t.get("id"): t for t in root.iter("text")}
    spans = []

    def walk(node, at: float, scale: float):
        for child in node:
            if child.tag == "group":
                s = float(child.get("scaleX") or 1)
                x, ax = float(child.get("x") or 0), float(child.get("anchorX") or 0)
                walk(child, at + (x - ax * s) * scale, scale * s)
            elif child.tag == "layer" and child.get("asset") in assets:
                asset = assets[child.get("asset")]
                left = at + float(child.get("x") or 0) * scale
                spans.append((asset.get("text"), left, left + float(asset.get("width")) * scale))
            elif child.tag != "assets":
                walk(child, at, scale)  # the project and the composition hold the groups

    walk(root, 0.0, 1.0)
    return spans


@pytest.mark.parametrize("view", [ink_meter.KERB_VIEW, ink_meter.TOW_WIDE, ink_meter.TOW_TIGHT])
def test_no_lettering_is_cut_by_the_frame_edge_in_any_kerb_view(view):
    cv = canvas()
    ink_meter.kerb(cv, cv.comp, take("human", 3.0), tow=0.8, view=view, display=((0.0, "SESSION ON"),))
    spans = text_spans(cv)
    assert all(0 <= left and right <= 1080 for _, left, right in spans), spans
    if view == ink_meter.TOW_TIGHT:
        assert spans == []  # the meter sits on the left edge: its display is a scrawl, not "ESSION ON"
    if view == ink_meter.KERB_VIEW:
        assert {text for text, _, _ in spans} == {"SESSION ON", ink_meter.TAPE_TEXT}


def test_the_kerb_puts_the_doodle_the_meter_and_the_car_in_frame_and_a_tow_takes_the_car():
    still, towed = canvas(), canvas()
    ink_meter.kerb(still, still.comp, take("human", 3.0))
    ink_meter.kerb(towed, towed.comp, take("human", 3.0), tow=0.8)
    assert animated(still, "x") == [] and animated(still, "rotation") == []
    (rise,) = animated(towed, "rotation")  # the hook lifts the car's front
    assert rise[0] == (0.0, 0.0) and rise[1][0] == pytest.approx(0.8) and rise[-1][1] < 0
    (away,) = animated(towed, "x")  # then truck and car leave to the right
    assert away[0][0] == pytest.approx(0.8) and away[-1][1] > away[0][1] + 1080


def test_a_tow_begun_before_the_take_carries_on_across_the_cut():
    lifting, leaving, gone = canvas(), canvas(), canvas()
    ink_meter.kerb(lifting, lifting.comp, take("human", 3.0), tow=-0.25)  # cut in mid-lift
    ink_meter.kerb(leaving, leaving.comp, take("human", 3.0), tow=-1.0)  # cut in as it pulls away
    ink_meter.kerb(gone, gone.comp, take("human", 3.0), tow=-9.0)  # long gone
    (rise,) = animated(lifting, "rotation")
    assert rise[0] == (0.0, pytest.approx(ink_meter.LIFT_DEGREES / 2)) and rise[-1] == (0.25, ink_meter.LIFT_DEGREES)
    (away,) = animated(leaving, "x")
    assert away[0] == (0.0, pytest.approx(0.5 * ink_meter.TOW_SPEED))  # half a second under way at the cut
    (rise,) = animated(gone, "rotation")
    (away,) = animated(gone, "x")
    assert rise == [(0.0, ink_meter.LIFT_DEGREES)] and len(away) == 1 and away[0][1] > 1080 / ink_meter.TOW_WIDE[0]


def views(cv: Canvas) -> list[tuple[float, float, float]]:
    """The kerb's framings: (scale, where the pavement's left end lands in x and y)."""
    return [
        (float(g.get("scaleX") or 1), float(g.get("x")), float(g.get("y")))
        for g in tree(cv).iter("group")
        if g.get("anchorX") == "0" and g.get("anchorY") == str(ink_meter.PAVEMENT)
    ]


def test_the_kerb_frames_the_doodle_clear_of_the_left_edge_and_a_tow_wide_or_on_car_and_truck():
    plain, wide, tight = canvas(), canvas(), canvas()
    ink_meter.kerb(plain, plain.comp, take("human", 3.0))
    ink_meter.kerb(wide, wide.comp, take("human", 3.0), tow=0.8)
    ink_meter.kerb(tight, tight.comp, take("human", 3.0), tow=0.8, view=ink_meter.TOW_TIGHT)
    assert views(plain) == [ink_meter.KERB_VIEW] and views(wide) == [ink_meter.TOW_WIDE]
    assert views(tight) == [ink_meter.TOW_TIGHT]
    assert ink_meter.KERB_VIEW[1] >= 60 and ink_meter.TOW_WIDE[1] >= 60 * ink_meter.TOW_WIDE[0] + 40  # head clear
    zoom, x, _ = ink_meter.TOW_TIGHT
    assert zoom == pytest.approx(1.4 * ink_meter.TOW_WIDE[0])
    car_rear, truck_end = ink_meter.CAR_X, ink_meter.CAR_X + 480 + 40 + 430
    assert 60 <= x + car_rear * zoom and x + truck_end * zoom <= 1080 - 60  # car and truck both in frame
    (rise,) = animated(tight, "rotation")
    assert rise[-1][1] == ink_meter.LIFT_DEGREES == pytest.approx(-15.0)  # the nose well up


@pytest.mark.parametrize("view", [(0.0, 0.0, 880.0), (float("nan"), 0.0, 880.0), (1.0, float("inf"), 880.0)])
def test_a_kerb_view_has_a_positive_scale_and_a_place(view):
    cv = canvas()
    with pytest.raises(MeterError, match="view"):
        ink_meter.kerb(cv, cv.comp, take(), view=view)


def test_the_close_kerb_frames_the_meter_alone(monkeypatch):
    drawn = []
    monkeypatch.setattr(ink_meter, "human", lambda *a, **kw: drawn.append(a))
    wide, close = canvas(), canvas()
    ink_meter.kerb(wide, wide.comp, take())
    assert len(drawn) == 1  # the wide kerb has the doodle on the pavement
    ink_meter.kerb(close, close.comp, take(), close=True, display=((0.0, "2 HR MIN"),))
    assert "2 HR MIN" in texts(close) and len(drawn) == 1  # the close one is the meter alone


def test_the_app_screen_lays_out_its_rows_ticks_them_and_fills_its_bar_and_stars():
    cv = canvas()
    rows = (AppRow("A capital", at=0.2, tick=0.6), AppRow("A symbol", at=0.4, tick=0.9), AppRow("A memory", at=0.6))
    ink_meter.app_screen(cv, cv.comp, take("meter", 3.0), title="ParkPal", rows=rows, progress=(0.0, 1.5), stars=2.0)
    assert {"ParkPal", "A capital", "A symbol", "A memory"} <= set(texts(cv))
    fades = animated(cv, "opacity")
    assert [(0.0, 0.0), (0.2, 1.0)] in fades and [(0.0, 0.0), (0.6, 1.0)] in fades  # rows arrive in turn
    assert sum(1 for k in fades if k == [(0.0, 0.0), (0.9, 1.0)]) == 1  # the second tick, once
    (bar,) = animated(cv, "scaleX")
    assert bar[0] == (0.0, 0.0) and bar[-1] == (1.5, 1.0)
    lit = [k for k in fades if k[-1][0] >= 2.0 and k[0] == (0.0, 0.0)]
    assert len(lit) == ink_meter.STARS  # five stars light, one after another, from 2.0 s
    assert [k[-1][0] for k in lit] == sorted(k[-1][0] for k in lit)


def test_a_taken_row_flips_to_ink_with_a_cross_and_the_word_taken():
    cv = canvas()
    rows = (AppRow("A capital", tick=0.3), AppRow("A childhood memory", at=0.2, taken=1.1))
    ink_meter.app_screen(cv, cv.comp, take("meter", 3.0), title="ParkPal", rows=rows)
    assert {"A childhood memory", ink_meter.TAKEN_TEXT} <= set(texts(cv))
    assert [(0.0, 0.0), (1.1, 1.0)] in animated(cv, "opacity")  # the flip shows from 1.1 s
    root = tree(cv)
    (word,) = [t.get("id") for t in root.iter("text") if t.get("text") == ink_meter.TAKEN_TEXT]
    (flip,) = [g for g in root.iter("group") if any(x.get("asset") == word for x in g.findall("layer"))]
    assert [(float(k.get("time")), float(k.get("value"))) for k in flip.iter("key")] == [(0.0, 0.0), (1.1, 1.0)]
    assert len(flip.findall("shape")) == 3  # the ink box and the cross's two strokes, flipped with the word


@pytest.mark.parametrize(
    "call, match",
    [
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=()), "display"),
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((0.5, "LATE"),)), "from 0"),
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((0.0, "A"), (0.0, "B"))), "rising"),
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((0.0, "X" * 20),)), "characters"),
        (lambda cv: ink_meter.meter(cv, cv.comp, take(), 0, 0, display=((0.0, "OK"), (9.0, "NO"))), "within"),
        (lambda cv: ink_meter.kerb(cv, cv.comp, take(), tow=float("nan")), "tow"),
        (lambda cv: ink_meter.kerb(cv, cv.comp, take(), tow=5.0), "tow"),
        (lambda cv: ink_meter.kerb(cv, cv.comp, take(), close=True, tow=1.0), "close"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="", rows=()), "title"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x"),) * 9), "rows"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow(""),)), "row"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x", at=3.0),)), "within"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x", 0.5, 0.2),)), "tick"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x", 0.5, taken=0.2),)), "taken"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x", taken=5.0),)), "within"),
        (
            lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(AppRow("x", tick=0.2, taken=0.4),)),
            "both",
        ),  # fmt: skip
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(), progress=(1.0, 0.5)), "progress"),
        (lambda cv: ink_meter.app_screen(cv, cv.comp, take(), title="P", rows=(), stars=7.0), "stars"),
    ],
)
def test_the_meter_the_kerb_and_the_app_refuse_what_they_cannot_show(call, match):
    with pytest.raises(MeterError, match=match):
        call(canvas())


@pytest.mark.parametrize('local', [False, True])
@pytest.mark.parametrize(
    'count,extras', [(6, {}), (5, {'progress': (0, 1)}), (5, {'stars': 1}), (4, {'progress': (0, 1), 'stars': 1})]
)
def test_app_refuses_content_that_overflows_the_phone_before_drawing(count, extras, local):
    cv = canvas()
    cv.local_time = local
    before = cv.scene.to_bytes()
    with pytest.raises(MeterError, match='fit.*screen'):
        ink_meter.app_screen(
            cv, cv.comp, take(duration=3), title='Park', rows=tuple(AppRow(f'Row {i}') for i in range(count)), **extras
        )
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize(
    'count,extras', [(5, {}), (4, {'progress': (0, 1)}), (4, {'stars': 1}), (3, {'progress': (0, 1), 'stars': 1})]
)
def test_app_keeps_largest_fitting_forms_inside_the_glass(count, extras):
    cv = canvas()
    ink_meter.app_screen(
        cv, cv.comp, take(duration=3), title='Park', rows=tuple(AppRow(f'Row {i}') for i in range(count)), **extras
    )
    root = ET.fromstring(cv.scene.to_bytes())
    assets = {t.get('id'): t for t in root.iter('text')}
    rows = [
        layer
        for layer in root.iter('layer')
        if layer.get('asset') in assets and assets[layer.get('asset')].get('text', '').startswith('Row ')
    ]
    assert len(rows) == count
    for row in rows:
        assert float(row.get('y')) >= 368
        assert float(row.get('y')) + float(assets[row.get('asset')].get('height')) <= 980

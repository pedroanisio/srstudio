"""The study props: each draws what it says, keeps its marks in the frame, and refuses what it cannot draw."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_study
from srstudio.toon import ToonDataError, fh, fx, fy
from srstudio.toon_study import BOOK_ROWS, HIGHLIGHT, PINK, SHEET_ROWS


def measure(text: str, size: float) -> float:
    return 0.5 * size * len(text)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="fraunces", namer=flat_counter("k"))


def stage(cv: Canvas):
    return cv.comp


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def fills(cv: Canvas) -> list[str]:
    return [node.get("fill", "") for node in tree(cv).iter() if node.get("fill")]


def texts(cv: Canvas) -> list[str]:
    return [node.get("text", "") or (node.text or "") for node in tree(cv).iter() if node.tag.endswith("text")]


@pytest.mark.parametrize(
    ("name", "builder"),
    [
        ("toon-open-book", toon_study.open_book),
        ("toon-shut-book", toon_study.shut_book),
        ("toon-highlighter", toon_study.highlighter),
        ("toon-study-page", toon_study.study_page),
        ("toon-quiz-sheet", toon_study.quiz_sheet),
    ],
)
def test_the_props_are_registered(name, builder):
    assert registry.get("prop", name).builder is builder


def test_an_open_book_highlights_the_rows_it_is_told_to():
    plain, marked = canvas(), canvas()
    toon_study.open_book(plain, stage(plain))
    toon_study.open_book(marked, stage(marked), {0: HIGHLIGHT, 3: PINK})
    assert HIGHLIGHT not in fills(plain)
    assert fills(marked).count(HIGHLIGHT) == 1
    assert fills(marked).count(PINK) == 1


def test_a_sweep_starts_on_its_cue_and_fills_from_its_left_end():
    cv = canvas()
    toon_study.open_book(cv, stage(cv), sweep=(BOOK_ROWS - 1, HIGHLIGHT, 2.0), id="book")
    root = tree(cv)
    swept = next(node for node in root.iter() if node.get("id") == "book-sweep")
    assert swept.get("start") in ("2", "2.0")
    assert ET.tostring(swept).count(b"scaleX") >= 1


def test_every_row_of_a_book_stays_on_the_frame():
    for row in range(BOOK_ROWS):
        left, right, y = toon_study.row_span(row)
        assert 0 < left < right < 1080
        assert fy(801) - fh(toon_study.BOOK_H) <= y < fy(801) + 10


def test_a_note_is_written_on_the_right_page_and_swept_on_cue():
    cv = canvas()
    note = ("Plants make", "food from light.")
    toon_study.open_book(cv, stage(cv), note=note, note_sweep=(HIGHLIGHT, 1.0), measure=measure, id="book")
    assert any(node.get("id") == "book-sweep-1" for node in tree(cv).iter())
    left, right, _ = toon_study.note_span(note, measure)
    assert fx(300) < left < right


@pytest.mark.parametrize('note', [False, True])
def test_book_sweeps_interpolate_across_the_row_instead_of_holding_until_the_end(note):
    cv = canvas()
    options = (
        dict(note=('Hello',), note_sweep=(HIGHLIGHT, 1.0), measure=measure) if note else dict(sweep=(0, HIGHLIGHT, 1.0))
    )
    toon_study.open_book(cv, cv.comp, **options)
    animations = list(cv.scene.iter('animate'))
    assert len(animations) == 1
    assert animations[0].defaultInterpolation == 'linear'
    assert animations[0].timeBase is None


def test_marker_path_interpolates_between_authored_frame_positions():
    cv = canvas()
    toon_study.highlighter(cv, cv.comp, (100, 900), '#c49a6c', ((1, 100), (2, 500)))
    assert next(cv.scene.iter('animate')).defaultInterpolation == 'linear'


def test_engine_samples_a_sweep_and_marker_between_their_keys(tmp_path, scene_render):
    from support.acting import canvas as unlettered_canvas
    from support.acting import evaluate

    cv = unlettered_canvas()
    toon_study.open_book(cv, cv.comp, sweep=(0, HIGHLIGHT, 1.0), id='book')
    toon_study.highlighter(cv, cv.comp, (100, 900), '#c49a6c', ((1, 100), (1 + toon_study.SWEEP, 500)), id='marker')
    path = tmp_path / 'sweep.scene.xml'
    path.write_bytes(cv.scene.to_bytes())
    for fraction in (0.25, 0.5, 0.75):
        nodes = {n['id']: n for n in evaluate(scene_render, path, 1 + toon_study.SWEEP * fraction)}
        assert nodes['book-sweep']['local'][0] == pytest.approx(0.02 + 0.98 * fraction)
        assert nodes['marker']['local'][4] == pytest.approx(100 + 400 * fraction)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"marks": {BOOK_ROWS: HIGHLIGHT}},
        {"marks": {0: "yellow"}},
        {"scale": 0},
        {"at": "here"},
        {"sweep": (BOOK_ROWS, HIGHLIGHT, 1.0)},
        {"sweep": (0, HIGHLIGHT, -1.0)},
        {"note": ()},
        {"note": ("one", "two", "three")},
        {"note": ("one",)},  # no measure to fit it with
        {"note": ("W" * 60,), "measure": measure},
        {"note": ("one",), "measure": measure, "marks": {BOOK_ROWS - 1: HIGHLIGHT}},
        {"note_sweep": (HIGHLIGHT, 1.0)},
        {"note": ("one",), "measure": measure, "note_sweep": ("yellow", 1.0)},
    ],
)
def test_a_book_refuses_what_it_cannot_draw(kwargs):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_study.open_book(cv, stage(cv), **kwargs)


def test_a_shut_book_stays_inside_its_scale():
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_study.shut_book(cv, stage(cv), scale=-1)
    with pytest.raises(ToonDataError):
        toon_study.shut_book(cv, stage(cv), at=(1,))


def test_a_marker_moves_along_its_path():
    cv = canvas()
    toon_study.highlighter(cv, stage(cv), (100.0, 900.0), "#c49a6c", ((1.0, 100.0), (2.0, 500.0)), id="marker")
    assert b"marker" in cv.scene.to_bytes(layout="pretty")


@pytest.mark.parametrize(
    ("at", "paw", "path", "scale"),
    [
        ((1,), "#c49a6c", (), 1.0),
        ((1.0, 2.0), "brown", (), 1.0),
        ((1.0, 2.0), "#c49a6c", ((2.0, 1.0), (1.0, 2.0)), 1.0),
        ((1.0, 2.0), "#c49a6c", (), 0),
    ],
)
def test_a_marker_refuses_a_bad_place_paw_or_path(at, paw, path, scale):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_study.highlighter(cv, stage(cv), at, paw, path, scale)


KEY = ((HIGHLIGHT, "important"), (PINK, "very important"))


def test_a_page_marks_each_row_it_is_told_to_and_carries_its_key():
    cv = canvas()
    marks = {row: HIGHLIGHT for row in range(SHEET_ROWS)}
    toon_study.study_page(cv, stage(cv), "Chapter 4: Plants", marks, KEY, measure=measure)
    assert fills(cv).count(HIGHLIGHT) == SHEET_ROWS + 1  # the rows and the key's own swatch
    assert fills(cv).count(PINK) == 1


@pytest.mark.parametrize(
    ("heading", "marks", "key"),
    [
        ("", {}, KEY),
        ("W" * 60, {}, KEY),
        ("Heading", {SHEET_ROWS: HIGHLIGHT}, KEY),
        ("Heading", {}, ()),
        ("Heading", {}, KEY * 2),
        ("Heading", {}, (("yellow", "important"),)),
        ("Heading", {}, ((HIGHLIGHT, "W" * 60),)),
    ],
)
def test_a_page_refuses_what_it_cannot_draw(heading, marks, key):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_study.study_page(cv, stage(cv), heading, marks, key, measure=measure)


def test_a_quiz_sheet_can_land_on_cue():
    cv = canvas()
    toon_study.quiz_sheet(cv, stage(cv), ("Quiz",), "Mostly A's:", "VISUAL", measure=measure, start=3.0, id="sheet")
    sheet = next(node for node in tree(cv).iter() if node.get("id") == "sheet")
    assert sheet.get("start") in ("3", "3.0")


@pytest.mark.parametrize(
    ("title", "rule", "result", "kwargs"),
    [
        ((), "Rule", "Result", {}),
        (("a", "b", "c"), "Rule", "Result", {}),
        (("Title",), "", "Result", {}),
        (("Title",), "Rule", "W" * 60, {}),
        (("Title",), "Rule", "Result", {"scale": 0}),
        (("Title",), "Rule", "Result", {"at": (1,)}),
        (("Title",), "Rule", "Result", {"tilt": "a little"}),
    ],
)
def test_a_quiz_sheet_refuses_what_it_cannot_draw(title, rule, result, kwargs):
    cv = canvas()
    with pytest.raises(ToonDataError):
        toon_study.quiz_sheet(cv, stage(cv), title, rule, result, measure=measure, **kwargs)


def sheet(**options) -> Canvas:
    cv = canvas()
    toon_study.quiz_sheet(
        cv, stage(cv), ("What kind of learner", "are you?"), "Mostly A's:", "VISUAL", measure=measure, **options
    )
    return cv


def test_a_sheet_is_on_only_while_it_is_told_to_be():
    root = next(node for node in tree(sheet(start=1.0, end=3.0)).iter() if node.get("id") == "quiz-sheet")
    assert (float(root.get("start")), float(root.get("end"))) == (1.0, 3.0)


def test_a_sheet_without_times_is_on_throughout():
    root = next(node for node in tree(sheet()).iter() if node.get("id") == "quiz-sheet")
    assert root.get("start") is None and root.get("end") is None


def test_a_small_sheet_can_leave_the_answer_letters_out_and_keeps_its_words():
    lettered, plain = texts(sheet()), texts(sheet(answers_lettered=False))
    assert set(lettered) - set(plain) == set("ABCD")
    assert {"Mostly A's:", "VISUAL"} <= set(plain)


def test_a_small_sheet_keeps_its_ticked_answers():
    ticked = fills(sheet(answers_lettered=False)).count(toon_study.CIRCLE)
    assert ticked == fills(sheet()).count(toon_study.CIRCLE) == 4

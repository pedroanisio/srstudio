"""What My Dad Does (Stick 07) as data: the script checks, the voices, a page for every essay take that the page
can letter, the page never ahead of the reading, the hold before the punchline and the grade on the button."""

import sys
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, Canvas, flat_counter, stick, stick_school

EPISODES = Path(__file__).resolve().parent.parent / "episodes"


@pytest.fixture(scope="module")
def data():
    sys.path.insert(0, str(EPISODES))
    try:
        import what_my_dad_does_audio

        return what_my_dad_does_audio
    finally:
        sys.path.pop(0)


def test_the_script_checks_with_two_distinct_voices_and_a_bed(data):
    script = data.SCRIPT
    script.check()
    assert "?" in script.takes[0].text and len({v.id for v in script.voices.values()}) == 2
    assert script.bed is not None and script.bed.bpm == 120
    assert set(t.shot for t in script.takes) == set(data.SHOTS)


def test_every_essay_take_has_a_page_the_page_can_letter(data):
    essay = {t.id for t in data.SCRIPT.takes if t.shot == "essay"}
    assert essay == data.PAGES.keys()
    for take_id, (shown, mark, word) in data.PAGES.items():
        text = next(t.text for t in data.SCRIPT.takes if t.id == take_id)
        scene = Scene(version="auto")
        scene.add_project(width=1080, height=1920, fps="24", duration=3.0, background="#d9d2c4")
        cv = Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))
        stick_school.essay(cv, cv.comp, data.LINES, title=data.TITLE, by=data.BY, shown=shown, mark=mark)
        if mark is not None:
            assert word in text.split()  # the highlighter starts on a word she says


def test_the_page_never_runs_ahead_of_what_she_has_read(data):
    shown = [data.PAGES[k][0] for k in sorted(data.PAGES)]
    assert shown == sorted(shown) and shown[-1] == len(data.LINES)
    takes = {t.id: t for t in data.SCRIPT.takes}
    for take_id, (_, mark, _) in data.PAGES.items():
        if mark is not None:  # the marked line is what she reads, give or take the child's spelling
            spoken = takes[take_id].text.lower().replace("'", "")
            first = data.LINES[mark].lower().split()[0]
            assert first in spoken


def test_the_punchline_holds_and_the_grade_is_the_button(data):
    takes = data.SCRIPT.takes
    setup = next(t for t in takes if t.text == "Dad says he works from home.")
    assert setup.hold >= 1.2 and takes[takes.index(setup) + 1].text == "Mom says he's just home."
    assert takes[-1].id == data.GRADED and data.NOTE_WORD in takes[-1].text.lower() and takes[-1].hold >= 1.2
    sting = takes[takes.index(setup) + 2]
    assert sting.is_effect and takes[-2].actor == "dev"
    for look in (data.DEV, data.TEACHER):
        stick.check_look(look)

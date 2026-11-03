"""The news kit: its copy check, its typed refusals, the anchors' tracks, the graphics' timing and the show's sting."""

from __future__ import annotations

import subprocess
import wave
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image
from sr_core.scene import Scene

from srstudio import Canvas, flat_counter, news_kit, registry, toon
from srstudio.news_kit import Act, Bubble, NewsKitError, Pose, Source
from support.social import engine

SIDE = ("level", "flat", "rest")


def measure(text: str, size: float) -> float:
    return 0.42 * size * len(text)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12.0, background=news_kit.PLUM_DEEP)
    return Canvas(scene, news_kit.NEWS.palette(), font_asset="barlow-condensed", namer=flat_counter("k"))


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def group(cv: Canvas, name: str) -> ET.Element:
    found = [node for node in tree(cv).iter() if node.get("id") == name]
    assert len(found) == 1, name
    return found[0]


def card() -> Source:
    return Source("The Daily Example", "Oct 30, 2026", "A plain headline, word for word")


@pytest.mark.parametrize(
    "kind, name, part",
    [
        ("location", "news-set", news_kit.studio),
        ("prop", "news-desk", news_kit.desk),
        ("character", "news-vera", news_kit.vera),
        ("character", "news-gus", news_kit.gus),
        ("graphic", "news-bug", news_kit.bug),
        ("graphic", "news-parody-tag", news_kit.parody_tag),
        ("graphic", "news-source-card", news_kit.source_card),
        ("graphic", "news-lower-third", news_kit.lower_third),
        ("graphic", "news-banner", news_kit.banner),
        ("graphic", "news-ticker", news_kit.ticker),
        ("graphic", "news-captions", news_kit.captions),
        ("graphic", "news-phone", news_kit.phone_insert),
    ],
)
def test_every_part_of_the_kit_is_in_the_catalog(kind, name, part):
    assert registry.get(kind, name).builder is part


def test_the_show_letters_in_a_google_font_and_never_in_dejavu():
    font = news_kit.NEWS.font
    assert font is not None and font.family == "Barlow Condensed" and font.google is not None


def test_the_two_voices_are_two_voices():
    assert news_kit.VERA.voice.id != news_kit.GUS.voice.id
    assert news_kit.VERA.settings.stability > news_kit.GUS.settings.stability  # she reads, he cannot help himself


@pytest.mark.parametrize(
    "copy",
    [
        "Send this to your brother",
        "SEND IT TO someone late",
        "tag a friend who is late",
        "Follow for more",
        "comment below",
        "link in bio",
        "share this",
        "Double tap if you agree",
        "smash that button",
    ],
)
def test_bait_is_refused_in_any_case(copy):
    with pytest.raises(NewsKitError, match="does not say"):
        news_kit.check_copy(copy)


@pytest.mark.parametrize("copy", ["Local man says five minutes", "He first said it at seven fifteen.", "tagliatelle"])
def test_ordinary_copy_passes_unchanged(copy):
    assert news_kit.check_copy(copy) == copy


@pytest.mark.parametrize(
    "args, needle",
    [
        (("", "Oct 30, 2026", "h"), "outlet"),
        (("o", " ", "h"), "outlet"),
        (("o", "Oct 30, 2026", ""), "outlet"),
        (("o", "2026-10-30", "h"), "reads like"),
        (("o", "yesterday", "h"), "reads like"),
        ((None, "Oct 30, 2026", "h"), "outlet"),
    ],
)
def test_a_source_is_complete_and_dated(args, needle):
    with pytest.raises(NewsKitError, match=needle):
        Source(*args)


@pytest.mark.parametrize(
    "kw, needle",
    [
        ({"eyes": "crossed"}, "eyes"),
        ({"mouth": "shout"}, "mouth"),
        ({"arms": "wave"}, "arms"),
        ({"head": 16.0}, "tilts"),
        ({"head": -16.0}, "tilts"),
        ({"head": float("nan")}, "tilts"),
        ({"head": "up"}, "tilts"),
    ],
)
def test_a_pose_the_rig_cannot_draw_is_refused(kw, needle):
    with pytest.raises(NewsKitError, match=needle):
        Pose(**kw)


@pytest.mark.parametrize(
    "call, needle",
    [
        (lambda cv: news_kit.lower_third(cv, cv.comp, "K", "WORD " * 60, 0.0, 2.0, measure), "does not fit"),
        (lambda cv: news_kit.lower_third(cv, cv.comp, "K", "follow us", 0.0, 2.0, measure), "does not say"),
        (lambda cv: news_kit.lower_third(cv, cv.comp, "K", "fine", 2.0, 2.0, measure), "start < end"),
        (lambda cv: news_kit.banner(cv, cv.comp, 3.0, 1.0, measure), "start < end"),
        (lambda cv: news_kit.ticker(cv, cv.comp, (), 0.0, 2.0, measure), "at least one"),
        (lambda cv: news_kit.ticker(cv, cv.comp, ("  ",), 0.0, 2.0, measure), "at least one"),
        (lambda cv: news_kit.ticker(cv, cv.comp, ("tag a friend",), 0.0, 2.0, measure), "does not say"),
        (lambda cv: news_kit.phone_insert(cv, cv.comp, "Chat", (), 0.0, 2.0, measure), "a message"),
        (
            lambda cv: news_kit.phone_insert(cv, cv.comp, "Chat", (Bubble("8:00", "late", at=2.0),), 0.0, 2.0, measure),
            "after the phone",
        ),
        (
            lambda cv: news_kit.phone_insert(cv, cv.comp, "Chat", (Bubble("8:00", "x" * 90),), 0.0, 2.0, measure),
            "too wide",
        ),
        (lambda cv: news_kit.source_card(cv, cv.comp, card(), 2.0, 2.0, 5.0, measure), "start < end"),
        (lambda cv: news_kit.source_card(cv, cv.comp, card(), 0.0, 5.0, 5.0, measure), "corner"),
        (lambda cv: news_kit.perform(cv, cv.comp, "bob", 300.0, [(0.0, Pose())], 0.0, 2.0), "seats vera and gus"),
        (lambda cv: news_kit.perform(cv, cv.comp, "vera", 300.0, [], 0.0, 2.0), "needs a pose"),
        (lambda cv: news_kit.perform(cv, cv.comp, "gus", 300.0, [(1.0, Pose())], 0.0, 2.0), "needs a pose"),
    ],
)
def test_what_cannot_go_on_screen_is_refused_by_name(call, needle):
    with pytest.raises(NewsKitError, match=needle):
        call(canvas())


def test_a_caption_of_three_lines_stops_the_build():
    long = toon.Line("a", "A caption that goes on " * 12, 0.0, 2.0, "vera")
    cv = canvas()
    cv.require_font = lambda *_: None  # the words are what this test measures
    with pytest.raises(NewsKitError, match="two lines at most"):
        news_kit.captions(cv, cv.comp, [long], measure)


def test_a_stage_needs_one_act_for_each_beat():
    dress = news_kit.stage((Act(),))
    with pytest.raises(NewsKitError, match="1 acts for 2 beats"):
        dress(SimpleNamespace(beats=(1, 2)))


def test_a_blink_never_lands_on_a_stare():
    wide = news_kit.eye_track([(0.0, Pose(eyes="wide"))], 10.0, 2.0, 0.5)
    assert [state for _, state in wide] == ["wide"]


def test_a_level_gaze_blinks_on_its_period_and_comes_back():
    track = news_kit.eye_track([(0.0, Pose())], 5.0, 2.0, 0.5)
    assert [state for _, state in track] == ["level", "shut", "level", "shut", "level", "shut", "level"]
    assert [at for at, state in track if state == "shut"] == [0.5, 2.5, 4.5]


def test_a_held_expression_ignores_the_words_under_it():
    acts = [(0.0, Pose(mouth="talk")), (2.0, Pose(mouth="frown"))]
    visemes = [(0.5, "open"), (1.0, "closed"), (2.5, "open")]
    assert news_kit.mouth_track(acts, visemes, 4.0) == [(0.0, "closed"), (0.5, "open"), (1.0, "closed"), (2.0, "frown")]


def test_a_silent_master_still_moves_a_talking_mouth():
    states = [state for _, state in news_kit.mouth_track([(0.0, Pose(mouth="talk"))], (), 1.0)]
    assert {"open", "closed"} == set(states)


def test_a_talking_beat_with_no_words_in_it_shuts_the_mouth():
    rows = news_kit.mouth_track([(0.0, Pose(mouth="talk")), (1.0, Pose(mouth="talk"))], [(1.5, "open")], 2.0)
    assert rows == [(0.0, "closed"), (1.0, "closed"), (1.5, "open")]


def test_a_talking_beat_opens_on_the_sound_already_due_when_it_starts():
    """The beat lands on the heard word; the take's first viseme leads it by a sample. Shut until the next viseme, the
    mouth missed the first sound of the line at every cut to its speaker."""
    acts = [(0.0, Pose(mouth="flat")), (1.0, Pose(mouth="talk"))]
    rows = news_kit.mouth_track(acts, [(0.95, "open"), (1.2, "teeth"), (1.5, "closed")], 2.0)
    assert rows == [(0.0, "flat"), (1.0, "open"), (1.2, "teeth"), (1.5, "closed")]


def test_a_talking_beat_after_a_closed_take_still_starts_shut():
    acts = [(0.0, Pose(mouth="talk")), (1.0, Pose(mouth="talk"))]
    rows = news_kit.mouth_track(acts, [(0.2, "open"), (0.6, "closed"), (1.3, "open")], 2.0)
    assert rows == [(0.0, "closed"), (0.2, "open"), (0.6, "closed"), (1.0, "closed"), (1.3, "open")]


def test_the_ticker_never_runs_out_of_words():
    cv = canvas()
    news_kit.ticker(cv, cv.comp, ("ONE",), 0.0, 25.0, measure)
    words = max((node.text or node.get("text") or "" for node in tree(cv).iter()), key=len)
    assert "ONE" in words
    assert measure(words, 42.0) >= cv.width + news_kit.TICKER_SPEED * 25.0


def test_the_banner_moves_inside_the_first_second():
    assert news_kit.SLIDE < 1.0
    cv = canvas()
    news_kit.banner(cv, cv.comp, 0.0, 4.0, measure)
    assert group(cv, "news-banner").get("start") in (None, "0", "0.0")


def test_the_card_goes_small_and_stays_to_the_end():
    cv = canvas()
    news_kit.source_card(cv, cv.comp, card(), 0.0, 4.0, 20.0, measure)
    assert float(group(cv, "news-source-card").get("end", "0")) == 4.0
    corner = group(cv, "news-source-card-small")
    assert (float(corner.get("start", "0")), float(corner.get("end", "0"))) == (4.0, 20.0)


def test_the_tag_says_parody(tmp_path):
    cv = canvas()
    news_kit.parody_tag(cv, cv.comp, 0.0, 20.0, measure)
    text = ET.tostring(tree(cv), encoding="unicode")
    assert "PARODY" in text


def test_the_sting_is_short_and_written_where_it_is_asked(tmp_path: Path):
    path = news_kit.write_sting(tmp_path / "sting.wav", [0.0], 3.0)
    with wave.open(str(path)) as w:
        assert w.getnframes() / w.getframerate() == pytest.approx(3.0, abs=0.01)
    assert sum(glide[2] for glide in news_kit.STING) < 1.0  # a sting, never a bed


# -- the wall above the screens is wall ---------------------------------------------------------------------------
def wall_frame(tmp_path: Path, n: int) -> np.ndarray:
    cv = canvas()
    news_kit.studio(cv, cv.comp, 12.0)
    doc = tmp_path / "studio.scene.xml"
    doc.write_bytes(cv.scene.to_bytes())
    png = tmp_path / f"{n}.png"
    subprocess.run([engine(), "render", str(doc), "-f", str(n), "-o", str(png)], check=True, capture_output=True)
    return np.asarray(Image.open(png).convert("RGB"), dtype=float)


def test_nothing_crosses_the_bare_wall_above_the_screens(tmp_path):
    """The lit sweep belongs to the screens. Drawn as a free band it read as a grey bar growing from the frame's top."""
    first = wall_frame(tmp_path, 0)
    for n in (12, 24, 36, 48, 60):
        assert np.abs(wall_frame(tmp_path, n)[:120] - first[:120]).max() <= 2.0, n


def test_the_sweep_still_lights_the_screens(tmp_path):
    first, lit = wall_frame(tmp_path, 0), wall_frame(tmp_path, 75)  # 2.5 s, as the first row is at its brightest
    assert (lit[200:380] - first[200:380]).mean() > 3.0


def test_no_part_of_the_set_moves_position():
    """A sweep can only leave the screens by moving: the set animates brightness alone."""
    cv = canvas()
    news_kit.studio(cv, cv.comp, 12.0)
    assert {a.get("property") for a in tree(cv).iter() if a.tag.endswith("animate")} == {"opacity"}


# -- captions do not leave a widow ------------------------------------------------------------------------------------
def test_a_last_line_of_one_word_takes_a_word_from_the_line_above():
    wrapped = news_kit._wrap(measure, "A live update. He now says he's just parking.", 80.0, 1400.0, 2)
    assert wrapped == ["A live update. He now says he's", "just parking."]


def test_a_wrap_with_no_widow_is_left_as_the_greedy_fill_laid_it():
    assert news_kit._wrap(measure, "one two three four five six", 80.0, 500.0, 2) == ["one two three", "four five six"]


def test_one_line_is_no_widow():
    assert news_kit._wrap(measure, "just parking.", 80.0, 800.0, 2) == ["just parking."]


def test_a_widow_that_cannot_borrow_stays_within_the_width():
    """The word pulled down must fit beside the widow: a long last word keeps its own line."""
    wrapped = news_kit._wrap(measure, "tiny words here extraordinarily-long", 80.0, 700.0, 2)
    assert wrapped == ["tiny words here", "extraordinarily-long"]

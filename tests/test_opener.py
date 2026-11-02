"""The send-v2 opening line: the viewer's own words from the first frame until the first spoken line ends."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, opener, send_gate, show
from srstudio.opener import OpenerError


def measure(text: str, size: float) -> float:
    return 0.5 * size * len(text)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


@pytest.mark.parametrize(
    "text",
    [
        "my mom texting about me in giant font",
        "my partner on november 1st",
        "my best friend who's always on 2%",
        "my mom when I say I'm fine",
        "the group chat when someone says 'quick question'",
    ],
)
def test_the_viewers_own_words_pass(text):
    assert opener.check(text, 3.0) == text


@pytest.mark.parametrize(
    ("text", "end", "names", "match"),
    [
        ("", 3.0, (), "1 to 50 characters"),
        ("  my mom", 3.0, (), "1 to 50 characters"),
        ("x" * 51, 9.0, (), "1 to 50 characters"),
        ("My mom texting", 3.0, (), "lower case"),
        ("my mom and Brent", 3.0, (), "lower case"),
        ("my mom on okayville", 3.0, (), "the show's name"),
        ("send this to your mom", 3.0, (), "bait"),
        ("tag a friend who does this", 3.0, (), "bait"),
        ("rosa when i say i'm fine", 3.0, ("rosa", "gary"), "a character's name"),
        ("my mom #relatable", 3.0, (), "hashtag or handle"),
        ("my mom @okay", 3.0, (), "hashtag or handle"),
        ("my mom", 0.5, (), "at least"),
        ("my best friend who's always on 2%", 1.5, (), "at least"),
        ("my mom", float("nan"), (), "at least"),
    ],
)
def test_words_that_are_not_the_viewers_or_a_window_too_short_are_refused(text, end, names, match):
    with pytest.raises(OpenerError, match=match):
        opener.check(text, end, names=names)


def test_the_reading_window_follows_the_length_of_the_line():
    line = "my best friend who's always on 2%"
    assert opener.seconds(line) == pytest.approx(len(line) / opener.READ_CPS)
    assert opener.seconds("my mom") == opener.MINIMUM


def test_the_line_is_on_from_the_first_frame_to_its_end_and_shows_its_words():
    cv = canvas()
    g = opener.draw(cv, cv.comp, "my dad finding out my rent", 2.6, measure=measure, top=420.0)
    root = tree(cv)
    assert "my dad finding out my rent" in [t.get("text") for t in root.iter("text")]
    node = next(n for n in root.iter("group") if n.get("id") == g.id)
    assert float(node.get("start", "0")) == 0.0
    assert float(node.get("end")) == 2.6


def test_the_pill_stays_inside_the_safe_area_and_clear_of_the_bug():
    left, top, right, bottom = opener.box(600.0, 420.0)
    assert (left + right) / 2 == pytest.approx(opener.CENTER)
    assert opener.SAFE.x0 <= left and right <= opener.SAFE.x1
    assert bottom == top + opener.HEIGHT
    assert opener.SAFE.x1 < show.BUG_BOX[0]  # inside the safe area, the pill can never reach the bug
    with pytest.raises(OpenerError, match="safe area"):
        cv = canvas()
        opener.draw(cv, cv.comp, "my mom", 2.0, measure=measure, top=100.0)
    with pytest.raises(OpenerError, match="safe area"):
        cv = canvas()
        opener.draw(cv, cv.comp, "my mom", 2.0, measure=measure, top=1400.0)
    with pytest.raises(OpenerError, match="safe area"):
        cv = canvas()
        opener.draw(
            cv, cv.comp, "my mom when i say i am fine", 9.0, measure=lambda text, size: 40.0 * len(text), top=420.0
        )


def test_the_pill_keeps_the_clearance_off_the_bug():
    cv = canvas()
    wide = lambda line, size: 772.0  # noqa: E731  # a pill 836 px wide: inside the safe area, 6 px from the bug
    left, top, right, bottom = opener.box(772.0 + opener.PAD, 260.0)
    assert opener.SAFE.x0 <= left and right <= opener.SAFE.x1 and not show.clear_of_bug((left, top, right, bottom))
    with pytest.raises(OpenerError, match="show bug"):
        opener.draw(cv, cv.comp, "my mom texting about me", 3.0, measure=wide, top=260.0)
    opener.draw(cv, cv.comp, "my mom texting about me", 3.0, measure=wide, top=show.BUG_BOX[3] + show.CLEAR)


def test_the_pill_is_read_first_above_the_caption_it_shares_the_screen_with():
    cv = canvas()
    with pytest.raises(OpenerError, match="above the first caption"):
        opener.draw(cv, cv.comp, "my mom", 2.0, measure=measure, top=460.0, caption_top=334.0)
    g = opener.draw(cv, cv.comp, "my mom", 2.0, measure=measure, top=224.0, caption_top=334.0)
    pill = next(n for n in tree(cv).iter("group") if n.get("id") == g.id).find(".//shape")
    assert float(pill.get("y")) + float(pill.get("height")) <= 334.0


def test_a_line_too_wide_for_one_row_is_broken_by_hand_onto_two():
    text = "my best friend who's\nalways on 2%"
    cv = canvas()
    wide = lambda line, size: 30.0 * len(line)  # noqa: E731
    with pytest.raises(OpenerError, match="safe area"):
        opener.draw(canvas(), cv.comp, text.replace("\n", " "), 3.0, measure=wide, top=440.0)
    g = opener.draw(cv, cv.comp, text, 3.0, measure=wide, top=440.0)
    root = tree(cv)
    assert text in [t.get("text") for t in root.iter("text")]
    node = next(n for n in root.iter("group") if n.get("id") == g.id)
    pill = next(n for n in node.iter("shape"))
    assert float(pill.get("width")) == 30.0 * len("my best friend who's") + opener.PAD
    assert float(pill.get("height")) == opener.HEIGHT + opener.ROW
    assert opener.box(600.0, 440.0, rows=2)[3] == 440.0 + opener.HEIGHT + opener.ROW
    assert opener.seconds(text) == opener.seconds(text.replace("\n", " "))


@pytest.mark.parametrize("text", ["my\nbest\nfriend", "my mom\n", "\nmy mom", "my\n\nmom", "my \nmom", "my\n mom"])
def test_a_line_breaks_once_between_two_words(text):
    with pytest.raises(OpenerError):
        opener.check(text, 9.0)


def test_a_send_v2_claim_is_on_the_send_test_like_a_send_v1_one():
    from srstudio.releases import Release
    from srstudio.social import InstagramPost

    release = Release("a-b", InstagramPost(title="A title", description="A description."))
    assert send_gate.on_test(release, "send-v2")
    assert send_gate.on_test(release, "send-v1")
    assert not send_gate.on_test(release, "")
    assert "send-v2" in send_gate.BRIEFS

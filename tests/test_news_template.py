"""Version 2 of the News frame (ADR 0238): one band, medium close-ups, heads keyed from the speech, a source card off
the hands, the PARODY tag only on fiction, and inserts that never hold still."""

from __future__ import annotations

import math
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from srstudio import head_motion, news_head, news_inked, news_kit, news_template, toon
from srstudio.head_motion import Speech, Word
from srstudio.layout import VERTICAL
from srstudio.news_kit import Act, NewsKitError, Pose, Source
from srstudio.news_template import FRAME_H, FRAME_W, Lower
from support.news_contracts import canvas, measure

SAFE = VERTICAL.region(FRAME_W, FRAME_H)
SOURCE = Source("The Verge", "Nov 4, 2026", "Uber only fulfilled 4 rides from AI agents last quarter")
TICKER = ("UBER EATS: AROUND 500 ORDERS FROM AI AGENTS", "VERY, VERY EARLY AND VERY LIMITED TRACTION")
LOWERS = (Lower(3.0, 6.0, "VERA STILLMAN, ANCHOR", "AI AGENTS: FOUR RIDES"), Lower(6.0, 9.0, "DEVELOPING", "ALL GUS"))
LINES = (toon.Line("a", "Uber says AI agents booked just four rides.", 0.2, 2.8, "vera"),)
READ = Pose(mouth="talk")
PHONE = Pose("down", "talk", "phone")


# -- helpers ----------------------------------------------------------------------------------------------------------
def _shapes(cv, prefix: str):
    """Every rect and text box ``(id, x0, y0, x1, y1)`` in frame pixels under the groups whose id starts with
    ``prefix``, with the groups' offsets added; a path counts by its points."""
    root = ET.fromstring(cv.scene.to_bytes())
    sizes = {t.get("id"): (float(t.get("width", 0)), float(t.get("height", 0))) for t in root.iter("text")}

    def walk(node, dx, dy, inside):
        for child in node:
            x, y = dx + float(child.get("x", 0)), dy + float(child.get("y", 0))
            mine = inside or str(child.get("id", "")).startswith(prefix)
            if child.tag == "group":
                yield from walk(child, x, y, mine)
            elif not mine:
                continue
            elif child.tag == "layer" and child.get("asset") in sizes:
                w, h = sizes[child.get("asset")]
                yield child.get("id"), x, y, x + w, y + h
            elif child.tag == "shape" and child.get("shape") == "rect":
                yield child.get("id"), x, y, x + float(child.get("width")), y + float(child.get("height"))
            elif child.tag == "shape" and child.get("shape") == "path":
                nums = [float(v) for v in child.get("path").replace(",", " ").split() if _number(v)]
                xs, ys = nums[0::2], nums[1::2]
                yield child.get("id"), dx + min(xs), dy + min(ys), dx + max(xs), dy + max(ys)

    return [box for comp in root.iter("composition") for box in walk(comp, 0.0, 0.0, False)]


def _number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def _texts(cv, prefix: str) -> list[str]:
    root = ET.fromstring(cv.scene.to_bytes())
    assets = {t.get("id"): t.get("text", "") for t in root.iter("text")}
    out = []
    for group in root.iter("group"):
        if str(group.get("id", "")).startswith(prefix):
            out += [assets[layer.get("asset")] for layer in group.iter("layer") if layer.get("asset") in assets]
    return out


def _overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def _speech(at: float, text: str, step: float = 0.32, loud: tuple[int, ...] = (1, 4, 6)) -> Speech:
    """A take of ``text`` from ``at``: a word every ``step`` seconds, its letters evenly over 0.26 s, with the words
    at ``loud`` 8 dB over the rest."""
    words = []
    for k, raw in enumerate(text.split()):
        letters = "".join(c for c in raw if c.isalnum())
        start = at + k * step
        chars = tuple(
            (start + i * 0.26 / len(letters), start + (i + 1) * 0.26 / len(letters)) for i in range(len(letters))
        )
        words.append(Word(letters, start, start + 0.26, chars, raw.endswith((".", "?", "!"))))
    seconds = len(words) * step + 0.4
    levels = []
    for i in range(int(seconds * head_motion.LOUD_RATE)):
        k = int(i / head_motion.LOUD_RATE / step)
        levels.append(-20.0 if k in loud else -28.0)
    return Speech(at, tuple(words), tuple(levels))


# -- the band ---------------------------------------------------------------------------------------------------------
def test_the_band_is_one_strip_of_at_most_a_fifth_inside_the_safe_foot():
    assert news_template.BAND_FOOT - news_template.BAND_TOP <= 0.2 * FRAME_H
    assert news_template.BAND_FOOT <= SAFE.y1
    cv = canvas()
    card = news_template.CardPlan(large=(0.0, 2.5), credit=0.0)
    news_template.band(cv, cv.comp, ticker=TICKER, lowers=LOWERS, end=9.0, measure=measure, source=SOURCE, card=card)
    boxes = _shapes(cv, "news-band")
    assert len(boxes) > 10
    top, foot = min(b[2] for b in boxes), max(b[4] for b in boxes)
    assert top >= news_template.BAND_TOP - 0.5 and foot <= news_template.BAND_FOOT + 0.5, (top, foot)


def test_the_band_holds_the_label_the_kicker_the_line_and_the_ticker():
    cv = canvas()
    card = news_template.CardPlan(large=(0.0, 2.5), credit=0.0)
    news_template.band(cv, cv.comp, ticker=TICKER, lowers=LOWERS, end=9.0, measure=measure, source=SOURCE, card=card)
    words = " ".join(" ".join(_texts(cv, "news-band")).split())  # a wrapped line reads as one
    for text in ("VERA STILLMAN, ANCHOR", "AI AGENTS: FOUR RIDES", "The Verge", SOURCE.headline, TICKER[0], "NEWS"):
        assert text in words, text


def test_the_bands_words_keep_inside_the_safe_column_except_the_crawl():
    cv = canvas()
    card = news_template.CardPlan(large=(0.0, 2.5), credit=0.0)
    news_template.band(cv, cv.comp, ticker=TICKER, lowers=LOWERS, end=9.0, measure=measure, source=SOURCE, card=card)
    root = ET.fromstring(cv.scene.to_bytes())
    crawl = {
        layer.get("id") for g in root.iter("group") if g.get("id", "").endswith("-crawl") for layer in g.iter("layer")
    }
    texts = {t.get("id") for t in root.iter("text")}
    words = [b for b in _shapes(cv, "news-band") if b[0].removesuffix("-layer") in texts and b[0] not in crawl]
    assert words
    assert all(b[1] >= SAFE.x0 - 0.5 and b[3] <= SAFE.x1 + 0.5 for b in words), words


def test_no_parody_tag_on_a_real_story():
    cv = canvas()
    with pytest.raises(NewsKitError, match="PARODY"):
        news_template.band(
            cv, cv.comp, ticker=TICKER, lowers=LOWERS, end=9.0, measure=measure, source=SOURCE, parody=True
        )
    fiction = canvas()
    news_template.band(fiction, fiction.comp, ticker=TICKER, lowers=LOWERS, end=9.0, measure=measure, parody=True)
    words = _texts(fiction, "news-band")
    assert "PARODY" in words and "BREAKING" in words


def test_the_band_stands_down_under_an_insert():
    cv = canvas()
    news_template.band(cv, cv.comp, ticker=TICKER, lowers=LOWERS, end=9.0, measure=measure, inserts=((4.0, 5.0),))
    root = ET.fromstring(cv.scene.to_bytes())
    windows = [
        (float(g.get("start")), float(g.get("end")))
        for g in root.iter("group")
        if g.get("id", "").startswith("news-band") and g.get("start") is not None
    ]
    assert windows
    assert not any(a < 5.0 and b > 4.0 for a, b in windows), windows


# -- the framing ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("shot", ["vera", "gus"])
def test_a_close_shot_is_a_medium_close_up_of_at_least_two_fifths(shot):
    assert news_template.fill(news_template.SHOTS[shot]) >= 0.40


def test_the_two_shot_covers_a_third():
    assert news_template.fill(news_template.SHOTS["desk"]) >= 1 / 3


def test_the_old_close_shot_falls_short_of_the_bar():
    old = news_template.Framing(scale=news_inked.FRAMING["vera"][1], desk_y=news_inked.DESK_Y, seats=(("vera", 540.0),))
    assert news_template.fill(old) < 0.2


@pytest.mark.parametrize("shot", ["vera", "gus", "desk"])
def test_every_face_stays_clear_of_the_words_and_the_edges(shot):
    framing = news_template.SHOTS[shot]
    for who, x in framing.seats:
        reach = news_template.face_reach(who, framing, x)
        assert reach.low <= news_template.BAND_TOP, (who, reach)  # the face's lowest point over the band
        assert reach.crown >= news_template.CAPTION_FOOT, (who, reach)  # the hair under two lines of caption
        assert 0.0 <= reach.left and reach.right <= FRAME_W, (who, reach)  # no face cut by the edge


def test_the_desk_under_a_close_shot_is_no_band_over_a_fifth():
    for framing in news_template.SHOTS.values():
        assert FRAME_H - news_template.hands_line(framing) <= 0.2 * FRAME_H


# -- the source card --------------------------------------------------------------------------------------------------
def _beats(*rows):
    return tuple(SimpleNamespace(start=at, who=who, event=event) for at, who, event in rows)


def test_the_card_goes_before_a_phone_comes_up_under_it():
    beats = _beats((0.0, "vera", "card"), (2.9, "gus", ""), (5.6, "vera", ""))
    acts = (Act(READ, Pose()), Act(Pose(), PHONE), Act(READ, PHONE))
    seen = news_template.seen(beats, acts, 8.0)
    plan = news_template.card_plan(seen, 0.0, 5.6)
    assert plan.large is not None and plan.large[0] == 0.0
    assert plan.large[1] <= 2.9 - news_template.EASE + 1e-9
    for box in news_template.obstacles(seen):
        if box.start < plan.large[1] and box.end > plan.large[0]:
            assert not _overlap(news_template.CARD_BOX, box.box), box


def test_a_phone_under_the_card_from_frame_zero_leaves_only_the_credit():
    beats = _beats((0.0, "gus", "card"), (3.0, "vera", ""))
    acts = (Act(Pose(), PHONE), Act(READ, PHONE))
    plan = news_template.card_plan(news_template.seen(beats, acts, 6.0), 0.0, 3.0)
    assert plan.large is None and plan.credit == 0.0


def test_a_clear_desk_keeps_the_card_until_it_goes_small():
    beats = _beats((0.0, "vera", "card"), (2.9, "gus", ""), (5.6, "vera", ""))
    acts = (Act(READ, Pose()), Act(Pose(), Pose(mouth="talk")), Act(READ, Pose()))
    plan = news_template.card_plan(news_template.seen(beats, acts, 8.0), 0.0, 5.6)
    assert plan.large == (0.0, 5.6)


def test_hands_and_the_phone_are_obstacles_where_they_are_drawn():
    beats = _beats((0.0, "gus", "card"))
    found = news_template.obstacles(news_template.seen(beats, (Act(Pose(), PHONE),), 3.0))
    kinds = {box.what for box in found}
    assert {"gus hand", "gus phone"} <= kinds
    phone = next(box for box in found if box.what == "gus phone")
    assert _overlap(news_template.CARD_BOX, phone.box)  # the very case the card must yield to


# -- the heads --------------------------------------------------------------------------------------------------------
TAKE = "Uber says AI agents booked just four rides, out of about three hundred million."


def test_a_talking_hold_of_three_seconds_moves_the_head_not_only_the_mouth():
    said = ((None, _speech(0.5, "Fine.")), ("vera", _speech(1.0, TAKE)))
    rig = news_template.rig("vera")
    plan = news_template.plan_of("vera", rig, said, (), 6.0)
    scale = news_template.SHOTS["vera"].scale
    travel = news_template.crown_travel(plan, "vera", scale, 1.0, 4.0)
    assert travel >= news_template.HEAD_TRAVEL_LEAST, travel


def test_the_old_rig_holds_the_head_nearly_still_over_the_same_take():
    said = (("vera", _speech(1.0, TAKE)),)
    old = news_inked.RIGS["news-vera@6"]
    plan = news_head.plan_of("vera", old, said, (), 6.0)
    travel = news_template.crown_travel(plan, "vera", news_inked.FRAMING["vera"][1], 1.0, 4.0)
    assert travel < news_template.HEAD_TRAVEL_LEAST


def test_a_reply_turns_toward_the_other_anchor_on_its_onset():
    said = (("vera", _speech(0.2, "Uber says four rides.")), ("gus", _speech(2.6, "Four? Amateurs. Watch this.")))
    rig = news_template.rig("gus")
    spans = news_template.onsets("gus", rig, said, (), 6.0)
    onset = said[1][1].words[0].start
    assert any(on <= onset <= on + 0.3 and side == rig.toward for on, _, side in spans), spans


def test_a_line_that_follows_its_own_turns_the_other_way():
    said = (("vera", _speech(0.2, "Uber says four rides.")), ("vera", _speech(2.6, "Out of millions of rides.")))
    rig = news_template.rig("vera")
    spans = news_template.onsets("vera", rig, said, (), 6.0)
    second = said[1][1].words[0].start
    assert any(on <= second <= on + 0.3 and side == -rig.toward for on, _, side in spans), spans


def test_the_head_motion_is_the_same_on_every_build():
    said = (("vera", _speech(1.0, TAKE)),)
    rig = news_template.rig("vera")
    assert news_template.plan_of("vera", rig, said, (), 6.0) == news_template.plan_of("vera", rig, said, (), 6.0)


def test_a_pose_tilted_past_the_templates_reach_is_refused():
    beats = _beats((0.0, "vera", "card"))
    with pytest.raises(NewsKitError, match="tilt"):
        news_template.seen(beats, (Act(Pose(head=12.0), Pose()),), 3.0)


# -- inserts and the stage --------------------------------------------------------------------------------------------
def test_an_insert_keeps_moving_for_its_whole_span():
    cv = canvas()
    g = news_template.phone_insert(
        cv, cv.comp, "My AI", (news_kit.Bubble("6:01", "Book me a ride home"),), 2.0, 6.4, measure
    )
    root = ET.fromstring(cv.scene.to_bytes())
    node = next(n for n in root.iter("group") if n.get("id") == g.id)
    keys = {
        a.get("property"): [(float(k.get("time")), float(k.get("value"))) for k in a.findall("key")]
        for a in node.findall("animate")
    }
    scale = keys["scaleX"]
    assert scale[0][0] <= 2.0 and scale[-1][0] >= 6.4
    assert all(b[1] != a[1] for a, b in zip(scale, scale[1:], strict=False))  # every stretch moves
    assert max(b[0] - a[0] for a, b in zip(scale, scale[1:], strict=False)) <= news_template.STILL_MOST


def test_the_insert_keeps_its_words_inside_the_safe_area_at_its_largest():
    lo, hi = news_template.insert_reach()
    assert lo[0] >= SAFE.x0 - 0.5 and hi[0] <= SAFE.x1 + 0.5
    assert lo[1] >= news_template.CAPTION_FOOT and hi[1] <= SAFE.y1


def test_the_stage_draws_a_close_shot_as_framed():
    cv = canvas()
    beats = _beats((0.0, "vera", "card"), (2.0, "vera", ""))
    acts = (Act(READ, Pose()), Act(Pose(), Pose()))
    app = SimpleNamespace(who="vera", start=0.0, end=4.0)
    back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
    shot = SimpleNamespace(cv=cv, app=app, back=back, front=front, beats=beats, end=4.0, mouths={}, said=tuple)
    news_template.stage(acts, version=6)(shot)
    root = ET.fromstring(cv.scene.to_bytes())
    camera = next(g for g in root.iter("group") if g.get("id", "").startswith("tpl-camera-vera"))
    assert float(camera.get("scaleX")) == pytest.approx(news_template.SHOTS["vera"].scale)
    assert float(camera.get("y")) == pytest.approx(news_template.SHOTS["vera"].desk_y)


def test_the_stage_refuses_acts_that_do_not_match_the_beats():
    cv = canvas()
    shot = SimpleNamespace(cv=cv, app=SimpleNamespace(who="vera", start=0.0, end=1.0), beats=_beats((0.0, "vera", "")))
    with pytest.raises(NewsKitError):
        news_template.stage((Act(), Act()), version=6)(shot)


def test_captions_sit_on_the_templates_line():
    cv = canvas()
    news_template.captions(cv, cv.comp, LINES, measure, safe=VERTICAL)
    boxes = _shapes(cv, "news-captions")
    assert min(b[2] for b in boxes) == pytest.approx(news_template.CAPTION_TOP, abs=0.5)
    assert max(b[4] for b in boxes) <= news_template.CAPTION_FOOT + 0.5
    assert math.isclose(news_template.TEMPLATE, 2)

"""Version 2 of the News frame (ADR 0238): one band, medium close-ups, heads keyed from the speech, a source card off
the hands, the PARODY tag only on fiction, and inserts that never hold still."""

from __future__ import annotations

import math
from types import SimpleNamespace
from xml.etree import ElementTree as ET

import pytest

from srstudio import craft, head_motion, news_arms, news_head, news_inked, news_kit, news_template, toon
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
            x = dx + float(child.get("x", 0)) - float(child.get("anchorX", 0))  # a group's anchor goes to its x
            y = dy + float(child.get("y", 0)) - float(child.get("anchorY", 0))
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


@pytest.mark.parametrize("wide", [0.42, 0.5], ids=["narrow", "wide"])
def test_every_band_word_fits_its_box_at_the_measure_given(wide):
    def sized(text: str, size: float) -> float:
        return wide * size * len(text)

    cv = canvas()
    card = news_template.CardPlan(large=(0.0, 2.5), credit=2.5)
    news_template.band(cv, cv.comp, ticker=TICKER, lowers=LOWERS, end=9.0, measure=sized, source=SOURCE, card=card)
    fiction = canvas()
    news_template.band(fiction, fiction.comp, ticker=TICKER, lowers=LOWERS, end=9.0, measure=sized, parody=True)
    for drawn in (cv, fiction):
        root = ET.fromstring(drawn.scene.to_bytes())
        for t in root.iter("text"):
            rows = t.get("text", "").split("\n")
            assert max(sized(row, float(t.get("size", "0"))) for row in rows) <= float(t.get("width", "0")), rows


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


@pytest.mark.parametrize(
    "lowers, line",
    [
        ((Lower(2.0, 6.0, "GUS BELLOWS, CO-HOST", "BOOKING A RIDE, LIVE"),), None),  # 5.6-6.0 after the phone
        ((Lower(2.0, 5.0, "GUS BELLOWS, CO-HOST", "BOOKING A RIDE, LIVE"),), "AI AGENTS: FOUR RIDES"),  # 5.6-6.0
    ],
)
def test_the_band_refuses_words_a_cut_back_leaves_too_short_to_read(lowers, line):
    with pytest.raises(NewsKitError, match="too short to read"):
        news_template.band(
            cv := canvas(),
            cv.comp,
            ticker=TICKER,
            lowers=lowers if line is None else (*lowers, Lower(6.0, 9.0, "FOUR AI RIDES", "ALL OF THEM: GUS")),
            end=9.0,
            measure=measure,
            line=line,
            inserts=((3.0, 5.6),),
        )


def test_the_storys_line_fills_the_line_row_whenever_no_lower_is_up():
    cv = canvas()
    card = news_template.CardPlan(large=(0.0, 2.0), credit=2.0)
    lowers = (Lower(4.0, 6.0, "VERA STILLMAN, ANCHOR", "AI AGENTS: FOUR RIDES"),)
    news_template.band(
        cv,
        cv.comp,
        ticker=TICKER,
        lowers=lowers,
        end=9.0,
        measure=measure,
        source=SOURCE,
        card=card,
        line="FOUR AI RIDES",
        inserts=((7.0, 8.0),),
    )
    root = ET.fromstring(cv.scene.to_bytes())
    rows = sorted(
        (float(g.get("start", "0")), float(g.get("end", "0")))
        for g in root.iter("group")
        if g.get("id", "").startswith(("news-band-lower", "news-band-line"))
    )
    assert rows == [(2.0, 4.0), (4.0, 6.0), (6.0, 7.0), (8.0, 9.0)]
    assert "FOUR AI RIDES" in _texts(cv, "news-band-line")


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
    assert not _overlap(news_template.CARD_BOX, phone.box)  # raised over the band
    fists = [box for box in found if box.what == "gus hand"]
    assert any(_overlap(news_template.CARD_BOX, box.box) for box in fists)  # the very case the card must yield to


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


def test_the_reels_first_line_is_said_to_the_camera():
    said = (("vera", _speech(0.2, "Uber says four rides.")), ("gus", _speech(2.6, "Four? Amateurs. Watch this.")))
    spans = news_template.onsets("vera", news_template.rig("vera"), said, (), 6.0)
    assert not [span for span in spans if span[0] < 1.0], spans


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
    cv, g = _cutaway()
    root = ET.fromstring(cv.scene.to_bytes())
    node = next(n for n in root.iter("group") if n.get("id") == g.id)
    keys = {
        a.get("property"): [(float(k.get("time")), float(k.get("value"))) for k in a.findall("key")]
        for a in node.findall("animate")
    }
    scale = keys["scaleX"]
    assert scale[0][0] <= 2.0 and scale[-1][0] >= 7.6
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


# -- the phone cutaway (arc4d3, 4 Nov) --------------------------------------------------------------------------------
CHAT = (
    news_kit.Bubble("6:01", "Book me a ride home"),
    news_kit.Bubble("6:01", "Sure! Which home?", out=False, at=2.6),
    news_kit.Bubble("6:02", "Booked! Pickup: Tuesday", out=False, at=4.4),
    news_kit.Bubble("6:02", "Also booked 3 backups!", out=False, at=6.8),
)


def _cutaway(bubbles=CHAT, start: float = 2.0, end: float = 7.8):
    cv = canvas()
    g = news_template.phone_insert(cv, cv.comp, "My AI", bubbles, start, end, measure)
    return cv, g


def _fill_of(cv, ident: str) -> str:
    root = ET.fromstring(cv.scene.to_bytes())
    node = next(n for n in root.iter("shape") if n.get("id") == ident)
    return str(node.get("fill", ""))


def test_the_phone_is_a_cutaway_whose_screen_fills_the_frame_width():
    cv, _ = _cutaway()
    boxes = _shapes(cv, "news-phone")
    screen = [b for b in boxes if b[1] <= 0.0 and b[3] >= FRAME_W and b[2] < news_template.CHAT_TOP]
    assert screen, "no screen edge to edge"
    back = [b for b in boxes if b[1] <= 0 and b[2] <= 0 and b[3] >= FRAME_W and b[4] >= FRAME_H]
    assert back and all(len(_fill_of(cv, b[0])) == 7 for b in back)  # opaque: nothing of the shot shows through


def test_the_chat_fills_the_screen_down_to_its_foot():
    cv, _ = _cutaway()
    root = ET.fromstring(cv.scene.to_bytes())
    rows = []
    for k in range(len(CHAT)):
        node = next(n for n in root.iter("group") if n.get("id") == f"news-phone-{k}")
        rects = [r for r in node.iter("shape") if r.get("shape") == "rect"]
        y0 = min(float(r.get("y")) for r in rects)
        rows.append((y0, max(float(r.get("y")) + float(r.get("height")) for r in rects)))
    assert rows == sorted(rows)
    assert rows[0][0] <= news_template.CHAT_TOP + 40.0
    assert rows[-1][1] >= news_template.CHAT_FOOT - 40.0  # the last message lands near the bottom
    covered = sum(b - a for a, b in rows)
    assert covered >= 0.6 * (news_template.CHAT_FOOT - news_template.CHAT_TOP)  # no blank half


def test_something_lands_on_the_screen_at_least_every_one_and_a_half_seconds():
    cv, _ = _cutaway()
    root = ET.fromstring(cv.scene.to_bytes())
    lands = sorted(
        float(g.get("start"))
        for g in root.iter("group")
        if g.get("id", "").startswith("news-phone-") and g.get("start") is not None
    )
    times = [2.0, *lands, 7.8]
    assert max(b - a for a, b in zip(times, times[1:], strict=False)) <= news_template.STILL_MOST + 1e-9
    assert [t for t in lands if t not in (2.0, 2.6, 4.4, 6.8)], "a gap of 1.8 s needs the typing dots"


def test_the_cutaway_cuts_back_within_one_and_a_half_seconds_of_its_last_message():
    with pytest.raises(NewsKitError, match="cut back"):
        _cutaway(CHAT[:2], 2.0, 4.4)


def test_a_wait_the_typing_dots_cannot_bridge_is_refused():
    late = (CHAT[0], news_kit.Bubble("6:09", "Booked!", out=False, at=5.4))
    with pytest.raises(NewsKitError, match="typing"):
        _cutaway(late, 2.0, 6.4)


def test_the_cutaways_words_stay_inside_the_safe_area_at_its_largest():
    cv, _ = _cutaway()
    ax, ay = news_template.CUT_AT
    big = news_template.CUT_TO
    for ident, x0, y0, x1, y1 in _shapes(cv, "news-phone"):
        if not str(ident).startswith("news-text"):
            continue
        assert ax + (x0 - ax) * big >= SAFE.x0 - 0.5 and ax + (x1 - ax) * big <= SAFE.x1 + 0.5, ident
        assert ay + (y0 - ay) * big >= news_template.CAPTION_FOOT and ay + (y1 - ay) * big <= SAFE.y1 + 0.5, ident


def test_the_cutaway_cuts_back_to_gus():
    beats = _beats((0.0, "vera", "card"), (2.0, "phone", ""), (7.6, "gus", ""), (9.0, "vera", ""))
    acts = (Act(READ, Pose()), Act(Pose(), PHONE), Act(Pose(), PHONE), Act(READ, PHONE))
    shots = news_template.seen(beats, acts, 11.0)
    news_template.reaction(shots, 7.6)
    with pytest.raises(NewsKitError, match="reaction"):
        news_template.reaction(shots, 9.0)


# -- Gus's raised hold (arc4d3, 4 Nov) --------------------------------------------------------------------------------
@pytest.mark.parametrize("shot", ["gus", "desk"])
def test_gus_holds_his_phone_up_clear_of_the_band(shot):
    framing = news_template.SHOTS[shot]
    x = dict(framing.seats)["gus"]
    box = news_template.held_phone(framing, x)
    assert box[3] <= news_template.BAND_TOP  # every pixel of it over the band
    assert 0.0 <= box[0] and box[2] <= FRAME_W


def test_the_raised_phone_stays_under_his_mouth():
    framing = news_template.SHOTS["gus"]
    assert news_template.held_phone(framing, 540.0)[1] >= news_template.mouth_low("gus", framing)


def _elbow(who: str, side: float, reach) -> float:
    """The inside angle of the elbow ``reach`` solves to, in degrees."""
    build = news_arms.BUILDS[who]
    shoulder = (build.shoulder[0] * side, build.shoulder[1])
    elbow = news_arms.elbow_of(build, side, reach)
    a = (shoulder[0] - elbow[0], shoulder[1] - elbow[1])
    b = (reach.wrist[0] - elbow[0], reach.wrist[1] - elbow[1])
    return math.degrees(math.acos((a[0] * b[0] + a[1] * b[1]) / (math.hypot(*a) * math.hypot(*b))))


def test_the_raised_hold_is_a_mirrored_pair_on_his_own_bones():
    left, right = news_template.GRIP.reaches["phone"]
    assert left.wrist == (-right.wrist[0], right.wrist[1]) and left.hand == right.hand and left.turn == -right.turn
    for side, reach in ((-1.0, left), (1.0, right)):
        news_arms.Hand(reach.hand, side).on(side)
        assert _elbow("gus", side, reach) >= news_arms.ELBOW_LEAST


def test_the_fists_hold_the_phone_from_under_it_clear_of_the_mouth():
    framing = news_template.SHOTS["gus"]
    for reach in news_template.GRIP.reaches["phone"]:
        _, y = framing.frame((540.0 + reach.wrist[0], news_inked.DESK_Y + reach.wrist[1]))
        assert y > news_template.BAND_TOP  # the wrists behind the band, the fists come up to the phone
        assert y - news_template.HAND_REACH * framing.scale > news_template.mouth_low("gus", framing)
        _, top, _, foot = news_template.held_phone(framing, 540.0)
        assert y - news_template.HAND_REACH * framing.scale > (top + foot) / 2  # the phone shows over the fists


def test_the_raised_phone_is_the_obstacle_the_card_plans_around():
    beats = _beats((0.0, "gus", "card"))
    found = news_template.obstacles(news_template.seen(beats, (Act(Pose(), PHONE),), 3.0))
    phone = next(box for box in found if box.what == "gus phone")
    assert phone.box == pytest.approx(news_template.held_phone(news_template.SHOTS["gus"], 540.0))


def test_version_1_keeps_its_phone_hold():
    assert news_arms.REACHES["gus"]["phone"][0].wrist == (-68.0, -2.0)
    assert news_inked.PHONE_HELD == -66.0


# -- the body on each line (arc4d3, 4 Nov: C5) ------------------------------------------------------------------------
SAID = (
    ("vera", _speech(0.2, "Uber says four rides.")),
    ("gus", _speech(2.6, "Four? Amateurs. Watch this.")),
    ("vera", _speech(5.0, "Out of millions of rides.")),
    ("vera", _speech(7.0, "So how are you getting home?")),
    ("gus", _speech(9.4, "I will just open the app.")),
)


@pytest.mark.parametrize("who", ["vera", "gus"])
def test_every_line_moves_the_body_not_only_the_head(who):
    keys = news_template.body(who, SAID, 12.0)
    for by, speech in SAID:
        if by != who:
            continue
        first = speech.words[0].start
        before = news_template.body_at(keys, max(0.0, first - news_template.ONSET_LEAD - 0.01))
        during = news_template.body_at(keys, first + news_template.BODY_RISE)
        assert before != during, (by, first, before, during)


def test_the_body_moves_change_kind_from_line_to_line():
    keys = news_template.body("vera", SAID, 12.0)
    states = [news_template.body_at(keys, s.words[0].start + news_template.BODY_RISE) for by, s in SAID if by == "vera"]
    assert len(set(states)) == len(states)
    assert any(up for _, up in states) and any(lean != 0 for lean, _ in states)  # hands up and a lean
    assert all(abs(lean) <= news_template.LEAN_MOST for lean, _ in states)


def test_hands_busy_with_the_phone_lean_instead_of_coming_up():
    second = SAID[2][1].words[0].start  # Vera's second line: her hands' turn
    assert news_template.body_at(news_template.body("vera", SAID, 12.0), second + news_template.BODY_RISE)[1]
    keys = news_template.body("vera", SAID, 12.0, busy=((second - 1.0, second + 2.0),))
    lean, up = news_template.body_at(keys, second + news_template.BODY_RISE)
    assert not up and lean != 0


def test_the_body_moves_are_the_same_on_every_build():
    assert news_template.body("gus", SAID, 12.0) == news_template.body("gus", SAID, 12.0)


@pytest.mark.parametrize("who", ["vera", "gus"])
def test_hands_up_is_a_mirrored_pair_beside_the_face_inside_the_close_shot(who):
    left, right = news_template.GRIPS[who].reaches["up"]
    assert left.wrist == (-right.wrist[0], right.wrist[1]) and left.hand == right.hand == "open"
    for side, reach in ((-1.0, left), (1.0, right)):
        news_arms.Hand(reach.hand, side).on(side)
        assert _elbow(who, side, reach) >= news_arms.ELBOW_LEAST
    framing = news_template.SHOTS[who]
    face = news_template.face_reach(who, framing, 540.0)
    x, y = framing.frame((540.0 + right.wrist[0], news_inked.DESK_Y + right.wrist[1]))
    assert y < news_template.BAND_TOP  # over the band, in the picture
    assert x - news_template.HAND_REACH * framing.scale * 0.5 > face.right - 120.0  # beside the face, not over it
    assert x <= FRAME_W


def test_the_stage_leans_the_anchor_and_brings_the_hands_up():
    cv = canvas()
    beats = _beats((0.0, "vera", "card"), (2.6, "gus", ""), (5.0, "vera", ""))
    acts = (Act(READ, Pose()), Act(Pose(), Pose(mouth="talk")), Act(READ, Pose()))
    app = SimpleNamespace(who="vera", start=0.0, end=12.0)
    back, front = cv.group(cv.comp, "back"), cv.group(cv.comp, "front")
    shot = SimpleNamespace(cv=cv, app=app, back=back, front=front, beats=beats, end=12.0, mouths={}, said=lambda: SAID)
    news_template.stage(acts, heads=False, version=6)(shot)
    root = ET.fromstring(cv.scene.to_bytes())
    groups = {g.get("id", ""): g for g in root.iter("group")}
    lean = [g for name, g in groups.items() if name.startswith("tpl-lean-vera")]
    assert len(lean) == 2  # the body behind the desk and the arms in front of it lean together
    assert all(any(a.get("property") == "skewX" for a in g.findall("animate")) for g in lean)
    gestured = news_template.gestured(((0.0, READ),), news_template.body("vera", SAID, 12.0), 0.0, 12.0)
    assert [pose.arms for _, pose in gestured].count("up") == 1  # Vera's second line, hands up and down again


def test_the_last_message_stays_up_long_enough_to_be_read():
    with pytest.raises(NewsKitError, match="read"):
        _cutaway(CHAT, 2.0, 6.8 + craft.MIN_DISPLAY - 0.1)
    _cutaway(CHAT, 2.0, 6.8 + craft.MIN_DISPLAY + 0.01)


@pytest.mark.parametrize("shot", ["vera", "gus", "desk"])
def test_hands_up_stay_over_the_band_in_every_shot(shot):
    framing = news_template.SHOTS[shot]
    for who, x in framing.seats:
        for reach in news_template.GRIPS[who].reaches["up"]:
            wx, wy = reach.wrist
            _, low = framing.frame((framing.camera_x(x) + wx, news_inked.DESK_Y + wy + news_template.HAND_REACH))
            assert low < news_template.BAND_TOP, (who, reach)


def test_the_hands_that_come_up_on_a_line_are_the_cards_obstacles():
    beats = _beats((0.0, "vera", "card"), (2.6, "gus", ""), (5.0, "vera", ""))
    acts = (Act(READ, Pose()), Act(Pose(), Pose(mouth="talk")), Act(READ, Pose()))
    shots = news_template.seen(beats, acts, 12.0)
    second = SAID[2][1].words[0].start  # Vera's second line: her hands come up, in her own shot from 5.0
    quiet = [o for o in news_template.obstacles(shots) if o.what == "vera hand" and o.start >= 5.0]
    moving = [o for o in news_template.obstacles(shots, said=SAID) if o.what == "vera hand" and o.start >= 5.0]
    assert all(o.box[1] > news_template.BAND_TOP for o in quiet)  # without the takes, the hands stay down
    up = [o for o in moving if o.box[1] < news_template.BAND_TOP]
    assert up and min(o.start for o in up) <= second

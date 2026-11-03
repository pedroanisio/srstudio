"""The News overlays keep their words inside a declared safe area (ADR 0222)."""

from xml.etree import ElementTree as ET

import pytest

from srstudio import news_inked, news_kit, toon
from srstudio.layout import VERTICAL, SafeArea
from srstudio.news_kit import NewsKitError
from support.news_contracts import canvas, measure

SAFE = VERTICAL.region(1080, 1920)  # x 80-920, y 220-1420
SOURCE = news_kit.Source(
    "The Irish Times", "Nov 3, 2026", "‘Mogging’ is Collins’ Word of the Year for 2026. What does it mean?"
)
LINES = (
    toon.Line("a", "Also listed: ghost jobs.", 1, 3, "vera"),
    toon.Line("b", "I've been ghosted by way more jobs than you.", 3, 5, "gus"),
)


def _boxes(cv, start=False):
    """Every text layer's box (id, x0, y0, x1, y1) in frame pixels with its groups' offsets added; with ``start``, a
    group whose ``y`` is keyed sits at its first key, where its arrival begins."""
    root = ET.fromstring(cv.scene.to_bytes())
    sizes = {t.get("id"): (float(t.get("width")), float(t.get("height"))) for t in root.iter("text")}

    def y(group):
        keys = [k for a in group.findall("animate") if a.get("property") == "y" for k in a.findall("key")]
        return float(keys[0].get("value")) if keys and start else float(group.get("y", 0))

    def walk(node, dx, dy):
        for child in node:
            if child.tag == "layer" and child.get("asset") in sizes:
                w, h = sizes[child.get("asset")]
                x0, y0 = dx + float(child.get("x", 0)), dy + float(child.get("y", 0))
                yield child.get("id"), x0, y0, x0 + w, y0 + h
            elif child.tag == "group":
                yield from walk(child, dx + float(child.get("x", 0)), dy + y(child))

    return [box for comp in root.iter("composition") for box in walk(comp, 0.0, 0.0)]


def _outside(boxes):
    return [b for b in boxes if b[1] < SAFE.x0 - 0.5 or b[3] > SAFE.x1 or b[2] < SAFE.y0 or b[4] > SAFE.y1]


def _draw(safe):
    cv = canvas()
    parent = cv.comp
    news_inked.lower_third(cv, parent, "DEVELOPING", "CARSPREADING: LONGER, WIDER, HEAVIER", 1, 7, measure, safe=safe)
    news_inked.source_card(cv, parent, SOURCE, 1, 3, 7, measure, safe=safe)
    short = news_kit.Source("AP", "Nov 3, 2026", SOURCE.headline)
    news_inked.source_card(cv, parent, short, 1, 3, 7, measure, id="beside", beside_tag=True, safe=safe)
    news_inked.parody_tag(cv, parent, 1, 7, measure, safe=safe)
    news_inked.captions(cv, parent, LINES, measure, safe=safe)
    return cv


def test_every_word_keeps_inside_the_vertical_safe_area():
    boxes = _boxes(_draw(VERTICAL))
    assert len(boxes) >= 9
    assert _outside(boxes) == []


def test_the_source_card_starts_its_rise_inside_the_area():
    cv = canvas()
    news_inked.source_card(cv, cv.comp, SOURCE, 1, 3, 7, measure, safe=VERTICAL)
    assert _outside(_boxes(cv, start=True)) == []
    old = canvas()
    news_inked.source_card(old, old.comp, SOURCE, 1, 3, 7, measure)
    assert _outside(_boxes(old, start=True))  # the rise the delivered reels drew starts under the area's foot


def test_no_area_still_draws_what_went_out():
    """A scene with no area, a reel delivered before ADR 0218: the lower-third's words still run to 1000."""
    boxes = _boxes(_draw(None))
    assert max(b[3] for b in boxes) == pytest.approx(news_kit.TEXT_RIGHT, abs=0.5)


def test_captions_centre_on_the_safe_column_and_keep_inside_it():
    cv = canvas()
    long = toon.Line("c", "Mine does not even fit in the garage, I said, the garage!", 1, 3, "gus")
    news_inked.captions(cv, cv.comp, (LINES[1], long), measure, safe=VERTICAL)
    boxes = _boxes(cv)
    assert _outside(boxes) == []
    assert (boxes[0][1] + boxes[0][3]) / 2 == pytest.approx((SAFE.x0 + SAFE.x1) / 2, abs=1.0)  # a pixel in


def test_the_ticker_crawl_is_marked_forced_only_under_a_declared_area():
    def forced(safe):
        cv = canvas()
        news_inked.ticker(cv, cv.comp, ("A plain headline",), 1, 7, measure, safe=safe)
        root = ET.fromstring(cv.scene.to_bytes())
        return [g.get("safeAreaForce") for g in root.iter("group") if g.get("id") == "news-ticker"]

    assert forced(VERTICAL) == ["true"]
    assert forced(None) == [None]


@pytest.mark.parametrize(
    "area",
    [
        SafeArea("narrow", top=0.1146, right=0.4, bottom=0.2604, left=0.0741),  # right edge 648
        SafeArea("indented", top=0.1146, right=0.1481, bottom=0.2604, left=0.1),  # left edge 108
    ],
)
def test_a_column_the_kit_cannot_keep_to_is_refused(area):
    cv = canvas()
    with pytest.raises(NewsKitError, match="safe area"):
        news_inked.lower_third(cv, cv.comp, "DEVELOPING", "A plain headline", 1, 7, measure, safe=area)


def test_a_foot_over_the_card_is_refused():
    short = SafeArea("short", top=0.1146, right=0.1481, bottom=0.36, left=0.0741)  # foot 1228, over the headline
    cv = canvas()
    with pytest.raises(NewsKitError, match="safe area short"):
        news_inked.source_card(cv, cv.comp, SOURCE, 1, 3, 7, measure, safe=short)


@pytest.mark.parametrize("safe", ["vertical-safe", 920.0, True])
def test_safe_must_be_an_area(safe):
    cv = canvas()
    with pytest.raises(NewsKitError, match="SafeArea"):
        news_inked.captions(cv, cv.comp, LINES, measure, safe=safe)

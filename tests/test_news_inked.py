"""Version 2 of the news parts: a set with planes and light, a real desk, anchors inked like the approved cast, and one
system of graphics. Version 1 stays drawable, and the look is tested like any other contract (ADR 0060)."""

from __future__ import annotations

import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, look, news_inked, news_kit, parts, registry, signature
from srstudio.canvas import Signature
from srstudio.news_kit import Act, Pose

ROOT = Path(__file__).resolve().parents[1]
PILOTS = ROOT / "episodes" / "pilots"
if str(PILOTS) not in sys.path:
    sys.path.insert(0, str(PILOTS))

import everyday_breaking_data as breaking  # noqa: E402
import real_roast_data as roast  # noqa: E402

DRAWINGS = (
    ("location", "news-set"),
    ("prop", "news-desk"),
    ("character", "news-vera"),
    ("character", "news-gus"),
    ("graphic", "news-bug"),
    ("graphic", "news-parody-tag"),
    ("graphic", "news-source-card"),
    ("graphic", "news-lower-third"),
    ("graphic", "news-banner"),
    ("graphic", "news-ticker"),
    ("graphic", "news-captions"),
    ("graphic", "news-phone"),
)


def canvas(signed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12.0, background=news_kit.PLUM_DEEP)
    return Canvas(scene, news_kit.NEWS.palette(), signature=Signature() if signed else None)


def measure(text: str, size: float) -> float:
    return 0.42 * size * len(text)


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def blurred(root: ET.Element) -> list[ET.Element]:
    declared = {e.get("id") for e in root.iter() if e.tag.endswith("effect") and e.get("type") == "blur"}
    return [n for n in root.iter() if declared & set((n.get("effects") or "").split())]


def words(root: ET.Element) -> list[str]:
    return [node.text or node.get("text") or "" for node in root.iter() if node.tag == "text"]


def children(root: ET.Element, id: str) -> list[ET.Element]:
    return [*next(n for n in root.iter() if n.get("id") == id)]


def shot(cv: Canvas, who: str) -> SimpleNamespace:
    beats = (SimpleNamespace(start=0.0),)
    app = SimpleNamespace(who=who, start=0.0, end=4.0)
    return SimpleNamespace(
        cv=cv,
        app=app,
        beats=beats,
        back=cv.group(cv.comp, "back"),
        front=cv.group(cv.comp, "front"),
        mouths={},
        end=4.0,
        said=tuple,
    )


@pytest.mark.parametrize(("kind", "name"), DRAWINGS)
def test_every_part_has_an_approved_second_version_and_keeps_its_first(kind, name):
    part = parts.get(name)
    assert [v.number for v in part.versions] == ([1, 2, 3, 4, 5, 6] if name in ("news-vera", "news-gus") else [1, 2])
    newest = part.version(2)
    assert newest.status == "approved"
    assert "1793475342.947029" in newest.approval.words
    assert part.version(1).status == "approved"
    assert newest.proof == "generated/character-proofs/news-v2/index.html"
    assert registry.get(kind, name).builder is not registry.get(kind, f"{name}@2").builder


def test_only_the_named_kit_may_take_a_second_version_beside_the_routed_kinds():
    assert parts.routed("news-desk", "prop", "toon")
    assert not parts.routed("toon-desk", "location", "toon")


def test_the_published_pilots_stay_on_the_first_version():
    for name in ("real_roast", "everyday_breaking"):
        source = (PILOTS / f"{name}.py").read_text(encoding="utf-8")
        assert "news_kit.stage(ACTS)" in source
        assert "news_kit.desk" in source
        assert "news_kit.captions" in source
        assert "news_inked" not in source
    assert "news_inked" not in roast.overlay.__globals__
    assert "news_inked" not in breaking.overlay.__globals__


# -- the look ---------------------------------------------------------------------------------------------------------
def test_the_far_plane_is_out_of_focus_and_the_anchors_are_not():
    cv = canvas()
    news_inked.stage((Act(),))(shot(cv, "desk"))
    root = tree(cv)
    far = blurred(root)
    assert far, "the monitor wall has to sit behind a blur"
    assert all("anchor" not in (n.get("id") or "") for far_node in far for n in far_node.iter())
    assert sum("anchor" in (n.get("id") or "") for n in root.iter("group")) == 2  # both are drawn, outside it


def test_the_far_blur_goes_through_the_look_module_with_the_kit_s_number(monkeypatch):
    seen = []
    real = look.depth

    def spy(cv, parent, name, radius):
        seen.append((name, radius))
        return real(cv, parent, name, radius)

    monkeypatch.setattr(news_inked.look, "depth", spy)
    cv = canvas()
    news_inked.studio(cv, cv.comp, 12.0)
    assert ("news-far", news_inked.FAR_BLUR) in seen


def test_every_figure_and_prop_on_the_desk_has_a_contact_shadow():
    cv = canvas()
    news_inked.stage((Act(Pose(), Pose(arms="rest")),))(shot(cv, "desk"))
    ids = [n.get("id") or "" for n in tree(cv).iter()]
    assert sum(i.startswith("news-contact-vera") for i in ids) == 1
    assert sum(i.startswith("news-contact-gus") for i in ids) == 1
    cv = canvas()
    news_inked.desk(cv, cv.comp)
    assert any((n.get("id") or "").startswith("news-contact-floor") for n in tree(cv).iter())


def test_the_finish_grades_a_shot_and_blurs_nothing():
    cv = canvas()
    g = cv.group(cv.comp, "shot")
    news_kit.finish(cv, g)
    root = tree(cv)
    assert not blurred(root)
    assert set(news_kit.GRADE) == {"bloom", "vignette", "film-grain"}
    assert all(f"news-{kind}" in g.effects for kind in news_kit.GRADE)


def test_no_signature_mark_sits_under_a_blur():
    cv = canvas(signed=True)
    news_inked.stage((Act(),))(shot(cv, "desk"))
    news_inked.desk(cv, cv.group(cv.comp, "shot"))
    news_inked.sign(cv, cv.comp)
    root = tree(cv)
    assert {m for m in signature.MARKS if any(n.get("id") == m for n in root.iter())} == set(signature.MARKS)
    assert len(blurred(root)) == 2  # the far plane and the foreground
    for far in blurred(root):
        assert not any((n.get("id") or "").startswith(signature.MARKS) for n in far.iter())


Box = tuple[float, float, float, float]  # left, top, right, foot, in frame pixels
PAIR = re.compile(r"-?\d+(?:\.\d+)?")


def placed(node: ET.Element, x: float, y: float, sx: float, sy: float, turn: float) -> tuple:
    """The transform a group's children draw in: its own on top of what it sits in."""
    gx, gy = float(node.get("x") or 0.0), float(node.get("y") or 0.0)
    ax, ay = float(node.get("anchorX") or 0.0), float(node.get("anchorY") or 0.0)
    scale_x, scale_y = float(node.get("scaleX") or 1.0), float(node.get("scaleY") or 1.0)
    own = math.radians(float(node.get("rotation") or 0.0))
    cos, sin = math.cos(math.radians(turn)), math.sin(math.radians(turn))
    return (
        x + (gx * cos - gy * sin) * sx,
        y + (gx * sin + gy * cos) * sy,
        sx * scale_x,
        sy * scale_y,
        turn + math.degrees(own),
        ax,
        ay,
    )


def outline(shape: ET.Element) -> list[tuple[float, float]]:
    """The points of a shape, a curve's control points with them, so a box over them can only be too generous."""
    if shape.get("shape") == "path":
        numbers = [float(n) for n in PAIR.findall(shape.get("path") or "")]
        return list(zip(numbers[::2], numbers[1::2], strict=False))
    x, y = float(shape.get("x") or 0.0), float(shape.get("y") or 0.0)
    w, h = float(shape.get("width") or 0.0), float(shape.get("height") or 0.0)
    return [(x, y), (x + w, y), (x, y + h), (x + w, y + h)]


def solids(node: ET.Element, at: tuple = (0.0, 0.0, 1.0, 1.0, 0.0)) -> list[Box]:
    """A box in frame pixels round every solid drawn under ``node``. A gradient pool is a shadow or a sheen, and a
    shadow may fall where it likes."""
    boxes: list[Box] = []
    for child in node:
        if child.tag == "group":
            x, y, sx, sy, turn, ax, ay = placed(child, *at)
            boxes += solids(child, (x - ax * sx, y - ay * sy, sx, sy, turn))
        elif child.tag == "shape" and not (child.get("fill") or "").startswith("url("):
            x, y, sx, sy, turn = at
            cos, sin = math.cos(math.radians(turn)), math.sin(math.radians(turn))
            spots = [(x + (px * cos - py * sin) * sx, y + (px * sin + py * cos) * sy) for px, py in outline(child)]
            xs, ys = [p[0] for p in spots], [p[1] for p in spots]
            boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def desk_shot(who: str, arms: str) -> tuple[Box, list[Box]]:
    """The box round the mug on the desk, and every solid an anchor draws in shot ``who`` with Gus's arms ``arms``."""
    cv = canvas()
    desk = cv.group(cv.comp, "desk-plane")
    news_inked.desk(cv, desk)
    news_inked.stage((Act(Pose(), Pose(arms=arms)),))(shot(cv, who))
    root = tree(cv)
    mug = next(n for n in root.iter() if (n.get("id") or "").startswith("news-mug"))
    drawn = solids(mug, placed(mug, 0.0, 0.0, 1.0, 1.0, 0.0)[:5])
    box = min(b[0] for b in drawn), min(b[1] for b in drawn), max(b[2] for b in drawn), max(b[3] for b in drawn)
    anchors = [n for n in root.iter() if (n.get("id") or "").startswith(("anchor", "hands"))]
    return box, [b for node in anchors for b in solids(node, placed(node, 0.0, 0.0, 1.0, 1.0, 0.0)[:5])]


@pytest.mark.parametrize("who", ["desk", "vera", "gus"])
@pytest.mark.parametrize("arms", news_kit.ARMS)
def test_no_anchor_touches_the_mug_in_any_shot_or_pose(who, arms):
    mug, solid = desk_shot(who, arms)
    touching = [b for b in solid if b[0] < mug[2] and mug[0] < b[2] and b[1] < mug[3] and mug[1] < b[3]]
    assert not touching, f"{who} with Gus's arms {arms}: {mug} under {touching[:3]}"


def test_the_mug_stays_on_the_desk_and_in_the_picture():
    (left, top, right, foot), _ = desk_shot("desk", "rest")
    assert news_inked.DESK_Y - 60.0 < top < news_inked.LIP_Y
    assert foot <= news_inked.LIP_Y + 6.0  # standing on the top, not hanging off its lip
    assert left < 1020.0  # a mug, not a sliver at the frame's edge
    assert (1080.0 - left) / (right - left) > 0.5


def test_the_desk_carries_no_word_a_viewer_could_need():
    cv = canvas()
    news_inked.desk(cv, cv.comp)
    assert ET.tostring(tree(cv), encoding="unicode").count("<layer") == 0  # text reaches a frame only through a layer


# -- the anchors ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("who", ["vera", "gus"])
@pytest.mark.parametrize("arms", news_kit.ARMS)
@pytest.mark.parametrize("mouth", [*news_kit.EXPRESSIONS, "talk"])
def test_every_mouth_and_arm_of_the_first_version_still_draws(who, arms, mouth):
    cv = canvas()
    news_inked.perform(cv, cv.comp, who, 540.0, ((0.0, Pose("level", mouth, arms)),), 0.0, 2.0, ((0.0, "open"),))


@pytest.mark.parametrize("who", ["vera", "gus"])
@pytest.mark.parametrize("eyes", news_kit.EYES)
def test_every_eye_of_the_first_version_still_draws(who, eyes):
    cv = canvas()
    news_inked.perform(cv, cv.comp, who, 540.0, ((0.0, Pose(eyes)),), 0.0, 2.0)


def head_extent(who: str) -> tuple[float, float]:
    """The highest and lowest point the head's brush contours reach, in the head's own coordinates."""
    cv = canvas()
    news_inked.perform(cv, cv.comp, who, 540.0, ((0.0, Pose()),), 0.0, 2.0)
    root = tree(cv)
    head = next(n for n in root.iter() if n.tag == "group" and n.get("anchorY"))
    ys = []
    for node in head.iter("shape"):
        numbers = [float(v) for v in re.findall(r"-?\d+\.?\d*", node.get("path") or "")]
        ys += numbers[1::2]
    return min(ys), max(ys)


@pytest.mark.parametrize("who", ["vera", "gus"])
def test_a_neck_shows_between_the_chin_and_the_collar(who):
    assert news_inked.NECK_Y < news_kit.NECK_Y
    _, chin = head_extent(who)
    assert chin <= news_inked.CHIN_TIP
    on_the_bust = chin + news_inked.NECK_Y - news_kit.CHIN_Y
    assert on_the_bust <= news_inked.COLLAR_Y - 12.0  # a stretch of neck, whatever the hair and the mouth are doing


@pytest.mark.parametrize("who", ["vera", "gus"])
def test_a_close_up_keeps_the_head_clear_of_a_two_line_cue(who):
    top, _ = head_extent(who)
    _, scale = news_inked.FRAMING[who]
    drawn = news_inked.DESK_Y + scale * (top + news_inked.NECK_Y - news_kit.CHIN_Y)
    cue = news_kit.CAPTION_TOP + 2 * news_kit.CAPTION_SIZE * news_kit.CAPTION_LEADING + news_kit.CAPTION_PAD
    assert drawn >= cue


def test_the_arms_can_go_over_the_desk():
    cv = canvas()
    back, over = cv.group(cv.comp, "b"), cv.group(cv.comp, "o")
    news_inked.perform(cv, back, "gus", 540.0, ((0.0, Pose(arms="rest")),), 0.0, 2.0, over=over)
    root = tree(cv)
    hands = children(root, "o")
    assert len(hands) == 1, "the arms have one plane, over the desk"
    assert [*hands[0].iter("shape")], "and they are drawn there"
    assert hands[0].get("x") == children(root, "b")[0].get("x")


def test_gus_points_along_the_desk_and_never_raises_one_finger():
    *_, turn = news_inked.GUS_ARMS["point"][0]
    assert abs(turn) >= 60.0


def test_a_refused_anchor_is_refused_by_name():
    cv = canvas()
    with pytest.raises(news_kit.NewsKitError, match="the desk seats vera and gus"):
        news_inked.perform(cv, cv.comp, "bo", 540.0, ((0.0, Pose()),), 0.0, 2.0)


# -- one system of graphics -------------------------------------------------------------------------------------------
def test_the_stack_is_flush_and_stays_over_the_safe_zone():
    assert news_inked.BANNER_Y + news_inked.BANNER_H == news_inked.LOWER_Y
    assert news_inked.LOWER_Y + news_inked.LOWER_H == news_inked.TICKER_Y
    assert news_inked.TICKER_Y + news_inked.TICKER_H <= 1420.0


def test_every_chip_in_the_top_row_is_one_height_on_one_line():
    cv = canvas()
    source = news_kit.Source("The Outlet", "Oct 30, 2026", "A headline, word for word")
    news_inked.bug(cv, cv.comp, 0.0, 4.0, measure)
    news_inked.parody_tag(cv, cv.comp, 0.0, 4.0, measure)
    news_inked.source_card(cv, cv.comp, source, 0.0, 2.0, 4.0, measure)
    root = {n.get("id"): n for n in tree(cv).iter()}
    rows = {
        (float(n.get("y")), float(n.get("height")))
        for chip in ("news-bug", "news-parody-tag", "news-source-card-small")
        for n in root[chip]
        if n.get("shape") == "rect" and n.get("fill") != news_inked.SHADOW
    }
    assert rows == {(news_kit.BUG_Y, news_kit.BUG_H)}


def test_the_card_still_goes_small_and_stays_to_the_end():
    cv = canvas()
    source = news_kit.Source("The Outlet", "Oct 30, 2026", "A headline, word for word")
    news_inked.source_card(cv, cv.comp, source, 0.0, 2.0, 9.0, measure)
    root = {n.get("id"): n for n in tree(cv).iter()}
    assert root["news-source-card"].get("end") in ("2", "2.0")
    assert root["news-source-card-small"].get("end") in ("9", "9.0")


@pytest.mark.parametrize(
    ("call", "needle"),
    [
        (lambda cv: news_inked.ticker(cv, cv.comp, (), 0.0, 2.0, measure), "ticker"),
        (lambda cv: news_inked.lower_third(cv, cv.comp, "DM ME", "link in bio", 0.0, 2.0, measure), "link in bio"),
        (lambda cv: news_inked.phone_insert(cv, cv.comp, "Chat", (), 0.0, 2.0, measure), "message"),
        (lambda cv: news_inked.banner(cv, cv.comp, 2.0, 1.0, measure), "banner"),
    ],
)
def test_what_cannot_go_on_screen_is_still_refused(call, needle):
    with pytest.raises(news_kit.NewsKitError, match=needle):
        call(canvas())


def test_the_missing_card_shows_its_picture_and_its_name_for_its_window():
    cv = canvas()
    news_inked.missing_card(cv, cv.comp, "ONE LID", 2.0, 5.0, measure)
    root = tree(cv)
    card = next(node for node in root.iter() if node.get("id") == "news-missing-card")
    assert (card.get("start"), card.get("end")) == ("2", "5")
    drawn = ET.tostring(root, encoding="unicode")
    assert "MISSING" in drawn and "ONE LID" in drawn
    assert next(node for node in root.iter() if node.get("id") == "news-missing-card-lid") is not None


@pytest.mark.parametrize(
    ("label", "needle"), [("", "fit"), ("   ", "fit"), ("ONE LID, LAST SEEN AT A VERY LONG POTLUCK", "fit")]
)
def test_a_missing_card_that_cannot_be_read_is_refused(label, needle):
    cv = canvas()
    with pytest.raises(news_kit.NewsKitError, match=needle):
        news_inked.missing_card(cv, cv.comp, label, 0.0, 1.0, measure)


def test_a_missing_card_with_no_time_on_screen_is_refused():
    cv = canvas()
    with pytest.raises(news_kit.NewsKitError):
        news_inked.missing_card(cv, cv.comp, "ONE LID", 2.0, 2.0, measure)


def test_the_live_door_stands_ajar_with_its_name_for_its_window():
    cv = canvas()
    news_inked.live_door(cv, cv.comp, "KITCHEN", 2.0, 5.0, measure)
    root = tree(cv)
    door = next(node for node in root.iter() if node.get("id") == "news-live-door")
    assert (door.get("start"), door.get("end")) == ("2", "5")
    drawn = ET.tostring(root, encoding="unicode")
    assert "LIVE" in drawn and "KITCHEN" in drawn
    ids = {node.get("id") for node in root.iter()}
    assert "news-live-door-ajar" in ids and "news-live-door-shut" not in ids


def test_the_live_door_shuts_at_the_instant_it_is_told_and_stays_shut():
    cv = canvas()
    news_inked.live_door(cv, cv.comp, "KITCHEN", 2.0, 5.0, measure, shut=3.5)
    nodes = {node.get("id"): node for node in tree(cv).iter()}
    ajar, closed = nodes["news-live-door-ajar"], nodes["news-live-door-shut"]
    assert (ajar.get("start"), ajar.get("end")) == ("2", "3.5")
    assert (closed.get("start"), closed.get("end")) == ("3.5", "5")


@pytest.mark.parametrize("label", ["", "   ", "THE KITCHEN AT THE VERY END OF THE LONG HALLWAY"])
def test_a_live_door_that_cannot_be_read_is_refused(label):
    cv = canvas()
    with pytest.raises(news_kit.NewsKitError, match="fit"):
        news_inked.live_door(cv, cv.comp, label, 0.0, 1.0, measure)


@pytest.mark.parametrize(
    ("start", "end", "shut"), [(2.0, 2.0, None), (2.0, 5.0, 2.0), (2.0, 5.0, 5.0), (2.0, 5.0, 9.0)]
)
def test_a_live_door_outside_its_window_is_refused(start, end, shut):
    cv = canvas()
    with pytest.raises(news_kit.NewsKitError):
        news_inked.live_door(cv, cv.comp, "KITCHEN", start, end, measure, shut=shut)


def test_the_ticker_never_runs_out_of_words():
    cv = canvas()
    news_inked.ticker(cv, cv.comp, ("ONE",), 0.0, 30.0, measure)
    assert measure(max(words(tree(cv)), key=len), 40.0) >= 1080 + news_kit.TICKER_SPEED * 30.0

"""Shipped graphics drawn on their own: ids, gating, text and motion."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Canvas, graphics


def fresh():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=6)
    return Canvas(scene, OFFICE)


def render(cv):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def node(root, node_id):
    return next(el for el in root.iter() if el.get("id") == node_id)


def keys(root, node_id, prop):
    anim = next(a for a in node(root, node_id).findall("animate") if a.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in anim.findall("key")]


def texts(root):
    return {t.get("id"): t.get("text") for t in root.find("assets").iter("text")}


def test_quiz_card_without_verdict_draws_no_wrong_label():
    cv = fresh()
    graphics.quiz_card(cv, cv.comp, "QUICK MATH", "17 × 19 = ?", show=(1.0, 3.0))
    root = render(cv)
    assert texts(root) == {"quiz-label": "QUICK MATH", "quiz-question": "17 × 19 = ?"}
    assert keys(root, "quiz-card", "opacity") == [(0, 0), (1.0, 1), (3.0, 0)]


def test_quiz_verdict_defaults_to_the_card_span():
    cv = fresh()
    graphics.quiz_card(cv, cv.comp, "Q", "?", show=(1.0, 3.0), verdict="NOPE.")
    root = render(cv)
    assert texts(root)["wrong-label"] == "NOPE."
    assert keys(root, "wrong-label-layer", "opacity") == [(0, 0), (1.0, 1), (3.0, 0)]


def test_answer_bubble_is_tilted_streaked_and_pops_in():
    cv = fresh()
    graphics.answer_bubble(cv, cv.comp, "42", show=(2.0, 4.0))
    root = render(cv)
    bubble = node(root, "instant-answer")
    assert (bubble.get("x"), bubble.get("y"), bubble.get("rotation")) == ("876", "660", "9")
    assert texts(root) == {"wrong-answer-number": "42"}
    assert keys(root, "instant-answer", "opacity") == [(0, 0), (2.0, 1), (4.0, 0)]
    assert keys(root, "instant-answer", "scaleX")[1] == (2.0, 0.45)
    streaks = [s for s in bubble.iter("shape") if s.get("shape") == "path" and s.get("stroke") == graphics.GOLD]
    assert [s.get("strokeWidth") for s in streaks] == ["6", "6", "6"]


def test_dashboard_lists_every_row_and_slides_up():
    cv = fresh()
    rows = [("EMAIL", "OPEN"), ("CALL", "MUTED"), ("WORK", "0 %")]
    graphics.dashboard(cv, cv.comp, "MULTITASKING: ACTIVE", rows, show=(1.0, 5.0))
    root = render(cv)
    got = texts(root)
    assert got["dashboard-heading"] == "MULTITASKING: ACTIVE"
    assert [(got[f"dashboard-label-{i}"], got[f"dashboard-value-{i}"]) for i in range(3)] == rows
    assert [node(root, f"dashboard-label-{i}-layer").get("y") for i in range(3)] == ["91", "170", "249"]
    assert keys(root, "multitasking-dashboard", "y") == [(0, 1515), (1.0, 1515), (1.19, 1457), (1.32, 1465)]


def test_notification_rises_into_place_at_its_start():
    cv = fresh()
    graphics.notification(cv, cv.comp, 2, "BOSS", "Typing…", show=(1.5, 3.0), x=700, y=400)
    root = render(cv)
    assert texts(root) == {"notification-person-2": "BOSS", "notification-status-2": "Typing…"}
    assert keys(root, "notification-2", "y") == [(0, 422), (1.5, 422), (1.63, 396), (1.74, 400)]
    assert keys(root, "notification-2", "opacity") == [(0, 0), (1.5, 1), (3.0, 0)]


def test_connected_card_shows_heading_and_value_with_a_status_dot():
    cv = fresh()
    graphics.connected_card(cv, cv.comp, "CONNECTED", "hunter2", show=(0.5, 2.0), prefix="ok")
    root = render(cv)
    card = node(root, "park-connected-card")
    assert texts(root) == {"ok-heading": "CONNECTED", "ok-password": "hunter2"}
    assert keys(root, "park-connected-card", "opacity") == [(0, 0), (0.5, 1), (2.0, 0)]
    assert [s.get("fill") for s in card.iter("shape") if s.get("shape") == "ellipse"] == ["#62976F"]


@pytest.mark.parametrize(
    "builder,args,options",
    [
        (graphics.episode_slate, ("01", "TITLE"), {}),
        (graphics.quiz_card, ("QUESTION", "1 + 1?", (1, 3)), {"verdict": "YES"}),
        (graphics.answer_bubble, ("2", (1, 3)), {}),
        (graphics.scorecard, ("SCORE", [("POINTS", "2", "#FFFFFF")], (1, 3)), {}),
        (graphics.dashboard, ("STATUS", [("WORK", "DONE")], (1, 3)), {}),
        (graphics.password_card, ("PASSWORD", "secret", "NO SPACES", (1, 3)), {}),
        (graphics.location_slate, ("LATER", (1, 3)), {}),
        (graphics.connected_card, ("CONNECTED", "secret", (1, 3)), {}),
    ],
)
def test_graphic_instances_have_distinct_assets_and_resolve_their_own_text(builder, args, options):
    cv = fresh()
    builder(cv, cv.comp, *args, **options)
    first = builder(cv, cv.comp, *args, id="first", **options)
    second = builder(cv, cv.comp, *args, id="second", **options)
    root = render(cv)
    ids = [el.get("id") for el in root.iter() if el.get("id")]
    assert len(ids) == len(set(ids)), "reusing a graphic must not duplicate scene IDs"
    first_assets = {n.asset for n in first.iter() if n.xml_name == "layer"}
    second_assets = {n.asset for n in second.iter() if n.xml_name == "layer"}
    assert first_assets and second_assets and first_assets.isdisjoint(second_assets)
    declared = texts(root)
    assert all(asset in declared for asset in first_assets | second_assets)

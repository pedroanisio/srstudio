"""A reel of Rafa stages one long appearance: what a beat changes lands on one frame, ahead of the word."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, plates, rafa, rafa_host, rafa_reel
from srstudio.rafa_reel import Act, RafaReelError
from srstudio.styles import TOON


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=10, background="#000000")
    return Canvas(scene, TOON.palette)


def nodes(cv: Canvas) -> dict[str, ET.Element]:
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return {node.get("id", ""): node for node in root.iter()}


def scale_keys(node: ET.Element) -> list[tuple[float, float]]:
    track = next(a for a in node.iter() if a.tag.endswith("animate") and a.get("property") == "scaleX")
    return [(float(k.get("time", "")), float(k.get("value", ""))) for k in track]


def beats(*starts: float):
    return [SimpleNamespace(start=at) for at in starts]


MUG = Act("medium", "rafa-mug", "public-smile")
CLOSE = Act("close", "rafa-mug", "public-smile")
TOTE = Act("tight", "rafa-tote", "internal-meltdown")


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [("framing", "wide", "framings"), ("prop", "rafa-toaster", "props"), ("mood", "calm", "moods")],
)
def test_an_act_his_plates_cannot_show_is_refused(field, value, match):
    act = {"framing": "medium", "prop": "rafa-mug", "mood": "public-smile", field: value}
    with pytest.raises(RafaReelError, match=match):
        Act(**act)


def test_a_cut_lands_on_a_frame_ahead_of_its_word_and_never_before_the_first():
    assert rafa_reel.cut(0.0) == 0.0
    assert rafa_reel.cut(0.02) == 0.0
    at = rafa_reel.cut(5.004)
    assert at < 5.004
    assert at * rafa_host.FPS == pytest.approx(round(at * rafa_host.FPS))


def test_the_acts_must_be_parallel_to_the_beats():
    with pytest.raises(RafaReelError, match="2 acts for 3 beats"):
        rafa_reel.moods(beats(0.0, 1.0, 2.0), (MUG, TOTE))


def test_his_mood_changes_only_where_the_act_does():
    rows = rafa_reel.moods(beats(0.0, 2.0, 4.0), (MUG, CLOSE, TOTE))
    assert rows == ((0.0, "public-smile"), (rafa_reel.cut(4.0), "internal-meltdown"))


def test_a_prop_under_his_hand_leaves_no_frame_empty_and_can_come_back():
    spans = rafa_reel.prop_spans(beats(0.0, 2.0, 4.0), (MUG, TOTE, MUG), 6.0)
    assert spans == {
        "rafa-mug": [(0.0, rafa_reel.cut(2.0)), (rafa_reel.cut(4.0), 6.0)],
        "rafa-tote": [(rafa_reel.cut(2.0), rafa_reel.cut(4.0))],
    }


def test_the_framing_holds_from_cut_to_cut_about_his_face():
    cv = canvas()
    group = cv.group(cv.comp, "shot")
    rafa_reel.framing((MUG, CLOSE, TOTE))(SimpleNamespace(cv=cv, beats=beats(0.0, 2.0, 4.0)), group)
    assert rafa_reel.FRAMES["close"] < rafa_reel.FRAMES["tight"]
    assert scale_keys(nodes(cv)["shot"]) == [
        (0.0, 1.0),
        (pytest.approx(rafa_reel.cut(2.0)), rafa_reel.FRAMES["close"]),
        (pytest.approx(rafa_reel.cut(4.0)), rafa_reel.FRAMES["tight"]),
    ]


def test_only_a_prop_with_a_lens_has_an_insert():
    with pytest.raises(RafaReelError, match="insert"):
        rafa_reel.insert_plate("rafa-phone")


def test_the_insert_is_the_approved_prop_on_its_own_at_his_plate_size():
    plate = rafa_reel.insert_plate("rafa-tote")
    assert (plate.width, plate.height) == (rafa_host.WIDTH, rafa_host.HEIGHT)
    assert plate.background == rafa_reel.INSERT_WALL
    model = rafa.clay.Model()
    rafa.PROPS["rafa-tote"](model)
    assert len(plate.placed[0].meshes) == len(model.meshes())
    assert plates.digest(plate) == plates.digest(rafa_reel.insert_plate("rafa-tote"))


def test_the_insert_runs_from_cut_to_cut(monkeypatch, tmp_path: Path):
    cv = canvas()
    drawn = []
    monkeypatch.setattr(rafa_host, "front", lambda cv, g, picture, root: drawn.append((g, picture)))
    renders = SimpleNamespace(plate=lambda plate: tmp_path / "plate.png")
    g = rafa_reel.insert(cv, cv.comp, "rafa-tote", 2.0, 4.0, renders, tmp_path)
    assert drawn == [(g, tmp_path / "plate.png")]
    node = nodes(cv)["rafa-tote-insert"]
    assert (float(node.get("start", "")), float(node.get("end", ""))) == pytest.approx(
        (rafa_reel.cut(2.0), rafa_reel.cut(4.0))
    )


def test_the_stage_draws_him_once_gates_each_prop_and_cuts_the_push_back_on_the_first_change(monkeypatch, tmp_path):
    cv = canvas()
    calls = []
    monkeypatch.setattr(rafa_host, "faces", lambda end, **kw: calls.append(("faces", kw["moods"])) or ())
    monkeypatch.setattr(rafa_host, "sheet", lambda rows, **kw: "sheet")
    monkeypatch.setattr(rafa_host, "room", lambda name: name)
    monkeypatch.setattr(rafa_host, "foreground", lambda prop, room: prop)
    monkeypatch.setattr(rafa_host, "backdrop", lambda *a: calls.append(("backdrop", a[2])))
    monkeypatch.setattr(rafa_host, "perform", lambda *a, **kw: calls.append(("perform",)))
    monkeypatch.setattr(rafa_host, "worktop", lambda picture, cache: picture)
    monkeypatch.setattr(rafa_host, "front", lambda cv, g, picture, root: calls.append(("front", picture)))
    renders = SimpleNamespace(plate=lambda plate: plate, engine="engine", cache="cache", fonts="fonts")
    shot = SimpleNamespace(cv=cv, back=cv.comp, end=6.0, beats=beats(0.0, 3.0), mouths={})
    rafa_reel.stage((MUG, TOTE), lambda end: "plan", renders, tmp_path)(shot)
    assert [c[0] for c in calls].count("perform") == 1
    assert [c[1] for c in calls if c[0] == "front"] == ["rafa-mug", "rafa-tote"]
    rows = scale_keys(nodes(cv)["rafa-world"])
    assert rows[0] == (0.0, 1.0) and rows[1] == (2.4, 1.05)
    assert rows[-1] == (pytest.approx(rafa_reel.cut(3.0)), 1.0)

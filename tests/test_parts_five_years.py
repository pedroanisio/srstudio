"""Parts added for episode 06: office-desk, chair-back, squeak-mark and the camera spin."""

import math
import xml.etree.ElementTree as ET

import pytest

from srstudio import Episode, EpisodeSpec, camera, cast, graphics, locations, props, registry


def episode(project, slug):
    return Episode(EpisodeSpec(slug=slug, title="t", description="t", root=project, seed=6, background="#D5DFDF"))


def shapes(group):
    return [c for c in group.iter() if c.tag == "shape"]


def keys(root, node_id, prop):
    node = next(el for el in root.iter() if el.get("id") == node_id)
    anim = next(a for a in node.findall("animate") if a.get("property") == prop)
    return [(float(k.get("time")), float(k.get("value"))) for k in anim.findall("key")]


def test_new_parts_are_registered():
    names = {(e.kind, e.name) for e in registry.entries()}
    assert {("location", "office-desk"), ("prop", "chair-back"), ("graphic", "squeak-mark")} <= names


def test_office_desk_draws_the_room_without_the_foreground_candidate(project, tmp_path):
    ep = episode(project, "t-desk")
    seen = []
    desk = ep.setup(locations.office_desk, [(0, 1)], behind_desk=lambda g: seen.append(g))
    bare = ep.setup(locations.office_desk, [(1, 2)], chair=False, id="bare-desk")
    wide = ep.setup(locations.office_wide, [(2, ep.t.duration)])
    ep.audio_mix()
    root = ET.parse(ep.finish(tmp_path / "t-desk.scene.xml")).getroot()
    groups = {el.get("id"): el for el in root.iter("group")}
    assert seen == [desk]
    n_desk, n_bare, n_wide = (len(shapes(groups[i])) for i in ("desk-office-angle", "bare-desk", "wide-office-angle"))
    assert n_desk - n_bare == 5  # the black chair is five paths
    assert n_wide - n_desk == 5  # the foreground candidate's back is five paths
    assert bare is not None and wide is not None


def test_spin_follows_the_cosine_of_the_turn_and_reports_facing(project, tmp_path):
    ep = episode(project, "t-spin")
    g = ep.cv.group(ep.comp, "spinner")
    facing = camera.spin(ep.cv, g, start=1.0, turns=2, period=0.9, fps=30)
    ep.audio_mix()
    root = ET.parse(ep.finish(tmp_path / "t-spin.scene.xml")).getroot()
    k = keys(root, "spinner", "scaleX")
    assert k[0] == (0, 1) and k[1] == (1.0, 1)
    assert k[-1][0] == pytest.approx(1.0 + 1.8) and k[-1][1] == pytest.approx(1)
    for t, v in k[1:]:
        expected = max(abs(math.cos(2 * math.pi * (t - 1.0) / 0.9)), camera.EDGE_ON)
        assert v == pytest.approx(expected, abs=1e-5)
    # Facing flips at every quarter of a turn past the edge: back, front, back, front.
    assert [f for _, f in facing] == ["back", "front", "back", "front"]
    assert [t for t, _ in facing] == pytest.approx([1.225, 1.675, 2.125, 2.575])


@pytest.mark.parametrize("turns,period", [(0, 0.9), (2, 0), (2, -1)])
def test_spin_refuses_an_impossible_turn(project, turns, period):
    ep = episode(project, "t-bad-spin")
    with pytest.raises(ValueError):
        camera.spin(ep.cv, ep.cv.group(ep.comp, "s"), start=0, turns=turns, period=period)


def test_squeak_mark_is_visible_only_in_its_span_and_shakes(project, tmp_path):
    ep = episode(project, "t-squeak")
    graphics.squeak_mark(ep.cv, ep.comp, "SQUEAK!", show=(1.0, 1.5), x=600, y=1200)
    ep.audio_mix()
    root = ET.parse(ep.finish(tmp_path / "t-squeak.scene.xml")).getroot()
    assert keys(root, "squeak-mark", "opacity") == [(0, 0), (1.0, 1), (1.5, 0)]
    rotation = [v for t, v in keys(root, "squeak-mark", "rotation") if 1.0 < t < 1.5]
    assert len(rotation) >= 4 and all(
        a != b for a, b in zip(rotation, rotation[1:], strict=False)
    )  # it wobbles while shown
    assert keys(root, "squeak-mark", "rotation")[-1] == (1.5, -8)  # and settles
    texts = {el.get("id"): el for el in root.iter("text")}
    assert texts["squeak-mark-text"].get("text") == "SQUEAK!"


def test_chair_back_hides_the_occupant_below_the_headrest(project, tmp_path):
    ep = episode(project, "t-chair-back")
    g = ep.cv.group(ep.comp, "back-view")
    props.chair_back(ep.cv, g, head=(560, 724, 145))
    ep.audio_mix()
    root = ET.parse(ep.finish(tmp_path / "t-chair-back.scene.xml")).getroot()
    drawn = shapes(next(el for el in root.iter("group") if el.get("id") == "back-view"))
    # Head first (behind), backrest after it (in front): the backrest's fill is the leather gradient.
    assert drawn[0].get("shape") == "ellipse"
    assert any(s.get("fill") == "url(#leather-black)" for s in drawn[1:])


def test_a_spinning_occupant_builds_with_the_office_cast(project, tmp_path):
    """Integration: the end-card setup of episode 06 on the synthetic project passes every check."""
    ep = episode(project, "t-end")
    t = ep.t

    def behind(g):
        spinner = ep.cv.group(g, "spin")
        camera.anchor(spinner, 560, 900, place=True)
        front, back = ep.cv.group(spinner, "spin-front"), ep.cv.group(spinner, "spin-back")
        props.chair(ep.cv, front)
        ep.perform(cast.Candidate(ep.cv, tag="spinner-character"), front, 560, 724, 1.45, smile=[(0, t.duration)])
        props.chair_back(ep.cv, back, head=(560, 724, 145))
        facing = camera.spin(ep.cv, spinner, start=0.5, turns=1, period=1.0)
        camera.show_facing(ep.cv, front, back, facing)

    ep.setup(locations.office_desk, [(0, t.duration)], chair=False, behind_desk=behind)
    ep.audio_mix()
    path = ep.finish(tmp_path / "t-end.scene.xml")
    assert ep.check() == []
    root = ET.parse(path).getroot()
    assert keys(root, "spin-front", "opacity") == [(0, 1), (pytest.approx(0.75), 0), (pytest.approx(1.25), 1)]
    assert keys(root, "spin-back", "opacity") == [(0, 0), (pytest.approx(0.75), 1), (pytest.approx(1.25), 0)]

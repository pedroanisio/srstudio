"""A wheel on a proxy (ADR 0088): a tyre model that stays still and a drawn rim that turns on its disc."""

from __future__ import annotations

from xml.etree import ElementTree

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, clay, proxy, vehicle


@pytest.fixture
def cv() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10, seed=1)
    return Canvas(scene, font_asset=None)


def test_a_tyre_scales_with_its_radius_and_its_parts_are_named():
    small, large = clay.Model(), clay.Model()
    vehicle.tyre(small, 0.0, 0.0, 25.0, side=-1)
    vehicle.tyre(large, 0.0, 0.0, 50.0, side=-1)
    assert {m.material for m in small.meshes()} == set(vehicle.TYRE)
    tall = {m.material: m for m in large.meshes()}["tire"].vertices[:, 1]
    assert tall.max() - tall.min() == pytest.approx(100.0, abs=1.0)


def test_a_tyre_with_no_radius_is_refused():
    with pytest.raises(vehicle.VehicleError):
        vehicle.tyre(clay.Model(), 0.0, 0.0, 0.0, side=-1)
    with pytest.raises(vehicle.VehicleError):
        vehicle.tyre(clay.Model(), 0.0, 0.0, 25.0, side=0)


def test_a_rim_turns_at_a_steady_rate_on_its_disc_through_the_span(cv):
    view = proxy.View((0.0, -25.0, -600.0), (0.0, -25.0, 0.0), 20.0)
    disc = view.disc((0.0, -25.0, -70.0), 17.0, facing=-1)
    vehicle.turning_rim(cv, cv.comp, disc, 17.0, 2.0, 4.0, 432.0, "rim-a")
    tree = ElementTree.fromstring(cv.scene.to_bytes(layout="pretty"))
    group = next(e for e in tree.iter() if e.attrib.get("id") == "rim-a")
    animate = next(c for c in group if c.tag.endswith("animate") and c.attrib["property"] == "rotation")
    (t0, a0), (t1, a1) = [(float(k.attrib["time"]), float(k.attrib["value"])) for k in animate]
    assert (t0, t1) == (2.0, 4.0)
    assert (a1 - a0) / (t1 - t0) == pytest.approx(432.0)
    assert cv.scene.check() == []


def test_a_rim_with_five_windows_by_default_and_any_count_on_request(cv):
    vehicle.rim_face(cv, cv.group(cv.comp, "plain"), 17.0)
    vehicle.rim_face(cv, cv.group(cv.comp, "count"), 17.0, vehicle.RimLook(windows=3))
    paths = [e for e in ElementTree.fromstring(cv.scene.to_bytes()).iter() if e.attrib.get("shape") == "path"]
    assert len(paths) == 8
    with pytest.raises(vehicle.VehicleError):
        vehicle.RimLook(windows=1)


def test_a_rim_with_no_disc_or_no_radius_is_refused_and_draws_nothing(cv):
    disc = proxy.Disc(100.0, 100.0, 0.0, 1.0, 0.8, 0.0)
    before = cv.scene.to_bytes(layout="pretty")
    for bad_disc, radius in ((None, 40.0), (disc, 0.0)):
        with pytest.raises(vehicle.VehicleError):
            vehicle.turning_rim(cv, cv.comp, bad_disc, radius, 0.0, 1.0, 90.0, "rim")
    assert cv.scene.to_bytes(layout="pretty") == before

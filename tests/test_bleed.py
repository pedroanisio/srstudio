"""A blurred far plane reaches the frame's edge: the opt-in bleed (no episode drawn so far uses it).

scene-render draws a group's blur in a frame-sized offscreen, so transparency comes in at the frame's edge however far
the drawing overscans, and the page shows through in a pale rim. A ``threeD`` group gets a sheet the size of what it
draws. These tests measure the page itself: the same frame on a black and on a white page differs only where the page
shows.
"""

from __future__ import annotations

import shutil
import subprocess
import xml.etree.ElementTree as ET
from types import SimpleNamespace

import numpy as np
import pytest
from sr_core.scene import Scene

from srstudio import Episode, EpisodeSpec, camera, get, look, mind_kit, stick_door, stick_reel, toon_sketch
from srstudio.canvas import MONO, Canvas, flat_counter
from srstudio.look import LookError

WIDTH, HEIGHT = 1080, 1920


def _canvas(page: str = "#000000", bleed: bool = False) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=WIDTH, height=HEIGHT, fps="24", duration=4.0, background=page)
    return Canvas(scene, MONO, font_asset=None, namer=flat_counter("n"), bleed=bleed)


def _luma(engine, draw, page: str, bleed: bool, folder, at: float) -> np.ndarray:
    cv = _canvas(page, bleed)
    draw(cv)
    document = folder / f"{page[1:]}.scene.xml"
    document.write_bytes(cv.scene.to_bytes())
    picture = folder / f"{page[1:]}.png"
    subprocess.run([engine, "render", document, "-t", str(at), "-o", picture], check=True, capture_output=True)
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", picture, "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        check=True,
        capture_output=True,
    ).stdout
    return np.frombuffer(raw, np.uint8).reshape(HEIGHT, WIDTH).astype(float)


def _leak(engine, draw, bleed: bool, folder, at: float = 1.0) -> dict[str, float]:
    """The share of white page, 0 to 255, in the pixels along each edge of the frame."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg decodes the frames")
    shown = _luma(engine, draw, "#ffffff", bleed, folder, at) - _luma(engine, draw, "#000000", bleed, folder, at)
    return {
        "left": shown[:, 0].mean(),
        "right": shown[:, -1].mean(),
        "top": shown[0].mean(),
        "bottom": shown[-1].mean(),
    }


def _location(name: str, **options):
    def draw(cv: Canvas) -> None:
        get("location", name)(cv, cv.comp, **options)

    return draw


# each set paints its far plane to the frame's edge in another way, and each leaks today
FAR_PLANES = {
    "collage-boardroom": _location("collage-boardroom"),  # scaled, as its backdrop always was
    "collage-bedroom": _location("collage-bedroom"),
    "office-wide": _location("office-wide", depth=5.0),  # painted exactly to the frame
    "office-reverse": _location("office-reverse", depth=5.0),
    "home-study": _location("home-study"),  # painted past the frame
    "saga-desert": _location("saga-desert", end=4.0),  # painted exactly to the frame, on a near-black page
    "saga-cantina": _location("saga-cantina", end=4.0),
}


@pytest.mark.parametrize("name", FAR_PLANES)
def test_the_page_shows_along_the_frame_edge_as_published(scene_render, tmp_path, name):
    assert max(_leak(scene_render, FAR_PLANES[name], False, tmp_path).values()) > 40


@pytest.mark.parametrize("name", FAR_PLANES)
def test_with_bleed_no_page_reaches_the_frame_edge(scene_render, tmp_path, name):
    leak = _leak(scene_render, FAR_PLANES[name], True, tmp_path)
    assert max(leak.values()) < 1, leak


def test_a_crash_zoom_keeps_the_edge_covered(scene_render, tmp_path):
    def zoomed(cv: Canvas) -> None:
        g = cv.group(cv.comp, "shot")
        get("location", "collage-cafe")(cv, g)
        camera.anchor(g, 540.0, 700.0, place=True)
        camera.crash_zoom(cv, g, 0.5, 1.55, duration=0.15)

    leak = _leak(scene_render, zoomed, True, tmp_path, at=1.0)
    assert max(leak.values()) < 1, leak


def test_a_stick_far_plane_keeps_its_blur_on_a_sheet():
    cv = _canvas(bleed=True)
    stick_door.street(cv, cv.comp, end=4.0)
    assert 'threeD="true"' in cv.scene.to_bytes().decode()


def test_nothing_is_drawn_differently_without_bleed():
    """The guard for every delivered reel: without bleed, not one attribute of the scene changes."""
    cv = _canvas()
    for name in ("collage-boardroom", "saga-desert"):
        kwargs = {"end": 4.0} if name.startswith("saga") else {}
        get("location", name)(cv, cv.comp, **kwargs)
    look.depth(cv, cv.comp, "far", 3.0)
    document = cv.scene.to_bytes().decode()
    assert "threeD" not in document
    assert 'scaleX="1.04"' in document  # the backdrop's own overscan, as published


def test_bleed_is_off_unless_a_reel_asks():
    assert _canvas().bleed is False


def test_a_far_plane_that_stops_at_the_frame_grows_by_the_reach_of_its_blur():
    cv = _canvas(bleed=True)
    far = look.depth(cv, cv.comp, "far", 3.0, overscan=True)
    assert far.threeD is True
    assert far.anchorX == WIDTH / 2 and far.anchorY == HEIGHT / 2
    assert far.scaleX == far.scaleY
    assert (far.scaleX - 1) * WIDTH / 2 == pytest.approx(look.REACH * 3.0)


def test_overscan_is_part_of_bleed():
    cv = _canvas()
    far = look.depth(cv, cv.comp, "far", 3.0, overscan=True)
    assert far.scaleX is None and far.threeD is None


def test_a_far_plane_that_needs_no_overscan_stays_in_place():
    cv = _canvas(bleed=True)
    far = look.depth(cv, cv.comp, "far", 3.0)
    assert far.threeD is True and far.scaleX is None


def test_a_bad_radius_is_still_refused():
    with pytest.raises(LookError):
        look.depth(_canvas(bleed=True), None, "far", 0)


def test_a_stick_reel_can_ask_for_bleed():
    assert stick_reel.spec("/tmp/x", "a-reel", "R1", "A Reel", "A reel.", 1, bleed=True).bleed is True
    assert stick_reel.spec("/tmp/x", "a-reel", "R1", "A Reel", "A reel.", 1).bleed is False


def test_an_episode_hands_its_bleed_to_the_canvas(project):
    def made(**options):
        return Episode(EpisodeSpec(slug="x", title="x", description="x", root=project, seed=1, **options)).cv

    assert made(bleed=True).bleed is True
    assert made().bleed is False


def _far(cv: Canvas) -> ET.Element:
    mind_kit.far(cv, cv.comp)
    return next(n for n in ET.fromstring(cv.scene.to_bytes(layout="pretty")).iter() if n.get("threeD"))


def test_a_mind_far_plane_is_on_a_sheet_past_the_frame_on_a_reel_with_bleed():
    assert float(_far(_canvas(bleed=True)).get("scaleX")) > 1.0


def test_a_mind_far_plane_is_unchanged_on_a_reel_without_bleed():
    cv = _canvas()
    mind_kit.far(cv, cv.comp)
    assert b"threeD" not in cv.scene.to_bytes(layout="pretty")


def test_a_sketch_asks_for_bleed_through_its_staging(monkeypatch, tmp_path):
    class Stop(Exception):
        pass

    def stop(spec):
        assert spec.bleed is True
        raise Stop

    monkeypatch.setattr(toon_sketch, "Episode", stop)
    monkeypatch.setattr(toon_sketch, "check_heads", lambda *a: None)
    monkeypatch.setattr(toon_sketch, "head_plans", lambda *a: {})
    monkeypatch.setattr(toon_sketch.sketch, "check", lambda sk: None)
    data = SimpleNamespace(slug="s", title="t", beats=(), end=1.0)
    staging = SimpleNamespace(
        sketch=data, heads=(), versions={}, bleed=True, description="d", narration="n", accessibility="a", seed=1,
        style=mind_kit.MIND, output="o.mp4", safe_area=None, crf="21", held_frames=False,
    )  # fmt: skip
    with pytest.raises(Stop):
        toon_sketch.build(tmp_path, staging, ())


def test_a_far_plane_that_moves_stays_off_the_sheet():
    cv = _canvas(bleed=True)
    mind_kit.far(cv, cv.comp, moving=True)
    assert b"threeD" not in cv.scene.to_bytes(layout="pretty")


def test_a_far_plane_that_moves_is_still_out_of_focus():
    cv = _canvas(bleed=True)
    mind_kit.far(cv, cv.comp, moving=True)
    assert b"mind-depth" in cv.scene.to_bytes(layout="pretty")

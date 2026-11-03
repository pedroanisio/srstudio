"""A reel shows its signature (ADR 0001): :func:`srstudio.signature.missing` reads the document, so a mark drawn behind
the cast, the props or outside the shot passes it. Rendered with and without each mark, these reels show both in at
least half of the frames sampled across their length. The check itself is proved on a built scene, with a mark in view
and one buried, so it cannot pass by being unable to fail."""

import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from PIL import Image, ImageChops

from srstudio import Episode, EpisodeSpec, locations, signature

REELS = tuple(
    "the-last-guy mosquito fitted-sheet one-more-taste you-have-it eye-chart sensor first-sip best-day the-scale "
    "one-symptom slept-wrong wave-back did-you-pack seat-belt-sign bin-day some-assembly how-is-everything headphones "
    "shortest-line sinking-chair the-tongs warranty quiet-please".split()
)
SAMPLES = 6
ENOUGH = {"sig-cactus": 40, "sig-code": 12}  # changed pixels that are more than a stray edge, at 1080 by 1920


def _render(engine: Path, project: Path, document: bytes, at: float, tag: str) -> Image.Image:
    scene, png = project / f".seen-{tag}.scene.xml", project / f".seen-{tag}.png"
    scene.write_bytes(document)
    try:
        subprocess.run(
            [str(engine), "render", scene.name, "-t", f"{at:g}", "-o", png.name],
            cwd=project,
            check=True,
            capture_output=True,
        )
        return Image.open(png).convert("RGB").copy()
    finally:
        scene.unlink(missing_ok=True)
        png.unlink(missing_ok=True)


def shown(engine: Path, project: Path, document: bytes, at: float, mark: str) -> int:
    """Pixels of the frame at second ``at`` that the mark changes."""
    frame = _render(engine, project, document, at, "with")
    other = _render(engine, project, signature.without(document, mark), at, "without")
    grey = ImageChops.difference(frame, other).convert("L")
    return sum(grey.point(lambda v: 255 if v > 8 else 0).histogram()[255:])


def length(document: bytes) -> float:
    return float(ET.fromstring(document).find("project").get("duration"))


def test_without_takes_out_the_mark_and_only_that_mark():
    doc = b'<s><group id="sig-code"/><group id="a"><group id="sig-code-2"/><group id="sig-cactus"/></group></s>'
    left = ET.fromstring(signature.without(doc, "sig-code"))
    assert [g.get("id") for g in left.iter("group")] == ["a", "sig-cactus"]
    assert signature.missing(signature.without(doc, "sig-code")) == ["sig-code"]


def test_without_refuses_an_unknown_mark():
    with pytest.raises(signature.SignatureError, match="one of"):
        signature.without(b"<s/>", "sig-flower")


@pytest.mark.parametrize("mark", signature.MARKS)
def test_a_render_tells_a_mark_in_view_from_a_buried_one(mark, project, scene_render):
    spec = EpisodeSpec(slug="t", title="t", description="t", root=project, seed=1, background="#D5DFDF")
    ep = Episode(spec)
    locations.office_wide(ep.cv, ep.comp)
    in_view = ep.scene.to_bytes()
    ep.cv.rect(ep.comp, 0, 0, 1080, 1920, "#336699")
    buried = ep.scene.to_bytes()
    assert not signature.missing(buried)  # the gate alone cannot see the difference
    assert shown(scene_render, project, in_view, 0.5, mark) > ENOUGH[mark]
    assert shown(scene_render, project, buried, 0.5, mark) == 0


@pytest.mark.parametrize("slug", REELS)
def test_a_reel_shows_both_marks_for_most_of_its_length(slug, scene_render):
    root = os.environ.get("SRSTUDIO_EPISODES")
    if not root or not (Path(root) / slug / f"{slug}.scene.xml").is_file():
        pytest.skip("renders the built reels: set SRSTUDIO_EPISODES to the projects")
    project = Path(root) / slug
    document = (project / f"{slug}.scene.xml").read_bytes()
    end = length(document)
    times = [round(end * (2 * k + 1) / (2 * SAMPLES), 2) for k in range(SAMPLES)]
    for mark, enough in ENOUGH.items():
        seen = [at for at in times if shown(scene_render, project, document, at, mark) > enough]
        assert len(seen) >= SAMPLES / 2, f"{slug}: {mark} shows only at {seen} of {times}"

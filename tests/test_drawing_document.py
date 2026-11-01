"""Executable examples and evidence links in the repository drawing decision.

Run from the repository with its Python dependencies installed:
    python -m unittest discover -s tests -p 'test_drawing_document.py' -v

These checks validate documented APIs and scene structure, not rendered aesthetics.
"""

from __future__ import annotations

import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from srstudio.limbs.errors import LimbError

ROOT = Path(__file__).resolve().parents[1]
DOCUMENT = ROOT / "DRAWING.md"


def example() -> dict[str, Any]:
    text = DOCUMENT.read_text()
    blocks = re.findall(r"^```python\n(.*?)^```", text, re.MULTILINE | re.DOTALL)
    if len(blocks) != 1:
        raise AssertionError("DRAWING.md must contain one self-contained, runnable Python example")
    namespace: dict[str, Any] = {}
    exec(compile(blocks[0], str(DOCUMENT), "exec"), namespace)
    return namespace


class DrawingDocumentTests(unittest.TestCase):
    def test_example_builds_a_schema_valid_scene(self) -> None:
        ns = example()
        self.assertEqual(ns["scene"].check(), [])

    def test_projection_cancels_the_drawing_parent_transform(self) -> None:
        ns = example()
        camera, parent, contact = ns["camera"], ns["parent"], ns["contact"]
        screen = camera.project(contact).xy
        local = camera.project(contact, parent=parent).xy
        self.assertNotEqual(local, screen, "the example must exercise a transformed drawing parent")
        for actual, expected in zip(parent.point(local), screen, strict=True):
            self.assertAlmostEqual(actual, expected)
        root = ET.fromstring(ns["scene"].to_bytes())
        world = root.find(".//group[@id='world']")
        assert world is not None
        self.assertEqual(
            tuple(float(world.attrib[name]) for name in ("scaleX", "scaleY", "x", "y")),
            (parent.a, parent.d, parent.e, parent.f),
        )

    def test_near_plane_failure_is_typed_and_leaves_the_scene_unchanged(self) -> None:
        ns = example()
        before = ns["scene"].to_bytes()
        with self.assertRaisesRegex(LimbError, "near plane") as caught:
            ns["camera"].project(ns["Vec3"](0, 0, ns["camera"].distance))
        self.assertEqual(caught.exception.code, "projection")
        self.assertEqual(ns["scene"].to_bytes(), before)

    def test_unsupported_projection_is_refused(self) -> None:
        ns = example()
        with self.assertRaisesRegex(LimbError, "orthographic or perspective"):
            ns["Camera"](projection="panoramic")

    def test_information_is_outside_the_world_finish(self) -> None:
        root = ET.fromstring(example()["scene"].to_bytes())
        composition = root.find("composition")
        assert composition is not None
        world = composition.find("group[@id='world']")
        information = composition.find("group[@id='information']")
        assert world is not None
        assert information is not None
        self.assertTrue(world.get("effects"))
        self.assertIsNone(composition.get("effects"))
        self.assertTrue(all(not node.get("effects") for node in information.iter()))
        self.assertLess(list(composition).index(world), list(composition).index(information))

    def test_lighting_includes_key_fill_and_rim(self) -> None:
        lights = {light.id: light for light in example()["lighting"]}
        self.assertTrue({"key", "fill", "rim"} <= lights.keys())
        self.assertTrue(all(light.intensity > 0 for light in lights.values()))

    def test_rebuilding_the_example_is_deterministic(self) -> None:
        first, second = example(), example()
        self.assertEqual(first["scene"].to_bytes(), second["scene"].to_bytes())
        self.assertEqual(first["lighting"], second["lighting"])

    def test_evidence_links_are_local_or_pin_renderer_sources(self) -> None:
        links = re.findall(r"\[[^\]\n]+\]\(([^)]+)\)", DOCUMENT.read_text())
        self.assertTrue(links, "the decision must link its implementation evidence")
        for target in links:
            with self.subTest(target=target):
                if "://" in target:
                    self.assertRegex(
                        target, r"\Ahttps://github\.com/pedroanisio/scene-render/blob/[0-9a-f]{40}/[\w./-]+\Z"
                    )
                    self.assertNotIn("..", target.split("/"))
                    continue
                path = (ROOT / target.split("#", 1)[0]).resolve()
                self.assertTrue(path.is_relative_to(ROOT.resolve()), target)
                self.assertTrue(path.is_file(), target)


if __name__ == "__main__":
    unittest.main()

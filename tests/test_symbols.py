"""Symbols and instances: static scenery drawn once and placed per camera angle."""

import json
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, locations


def engine() -> Path:
    found = os.environ.get("SRSTUDIO_ENGINE") or shutil.which("scene-render")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    return Path(found)


def canvas() -> tuple[Scene, Canvas]:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="10", duration=1, background="#FFFFFF")
    return scene, Canvas(scene)


def test_a_symbol_is_drawn_once_and_reused():
    scene, cv = canvas()
    calls = []

    def draw(symbol):
        calls.append(symbol)
        cv.rect(symbol, 0, 0, 10, 10, "#000000")

    assert cv.symbol("tile", draw) == "tile"
    assert cv.symbol("tile", draw) == "tile"
    cv.instance(cv.comp, "a", "tile")
    cv.instance(cv.comp, "b", "tile", x=20)
    root = ET.fromstring(scene.to_bytes())
    assert len(calls) == 1 and len(root.findall("symbols/symbol")) == 1
    assert [(i.get("id"), i.get("symbol"), i.get("x")) for i in root.iter("instance")] == [
        ("a", "tile", None),
        ("b", "tile", "20"),
    ]


def test_an_instance_needs_a_defined_symbol():
    _, cv = canvas()
    with pytest.raises(ValueError, match="no symbol"):
        cv.instance(cv.comp, "a", "missing")


def office(instanced: bool) -> tuple[Scene, Canvas]:
    scene, cv = canvas()
    locations.office_wide(cv, cv.comp, instanced=instanced)
    locations.office_desk(cv, cv.comp, instanced=instanced)
    return scene, cv


def test_instanced_office_angles_share_the_room_and_the_desk():
    scene, _ = office(instanced=True)
    root = ET.fromstring(scene.to_bytes())
    assert sorted(s.get("id") for s in root.iterfind("symbols/symbol")) == ["office-desk-front", "office-room"]
    assert sum(1 for g in root.iter("group") if g.get("id", "").endswith("plant")) == 1
    placed = {i.get("id"): i.get("symbol") for i in root.iter("instance")}
    assert placed == {
        "wide-office-angle-room": "office-room",
        "wide-office-angle-desk-front": "office-desk-front",
        "desk-office-angle-room": "office-room",
        "desk-office-angle-desk-front": "office-desk-front",
    }


def test_inline_office_angles_declare_no_symbols():
    scene, _ = office(instanced=False)
    root = ET.fromstring(scene.to_bytes())
    assert root.find("symbols") is None and not list(root.iter("instance"))


def evaluate(path: Path) -> dict[str, list[float]]:
    run = subprocess.run(
        [str(engine()), "eval", "--json", "-t", "0", str(path)], capture_output=True, text=True, check=True
    )
    return {n["id"]: n["world"] for n in json.loads(run.stdout)["result"]["nodes"] if n["kind"] == "shape"}


def test_instanced_office_draws_what_the_inline_office_draws(tmp_path):
    """Every shape lands where the inline drawing puts it: same world transform, same order."""
    inline_scene, _ = office(instanced=False)
    inline = tmp_path / "inline.scene.xml"
    inline.write_bytes(inline_scene.to_bytes())
    shared_scene, _ = office(instanced=True)
    shared = tmp_path / "shared.scene.xml"
    shared.write_bytes(shared_scene.to_bytes())
    check = subprocess.run([str(engine()), "validate", "--deny-warnings", str(shared)], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    a, b = list(evaluate(inline).values()), list(evaluate(shared).values())
    assert len(a) > 100 and len(a) == len(b) and a == b

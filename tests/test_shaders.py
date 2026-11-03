"""Every fragment shader a paint-over uses is compiled by the real engine, and the vendored ones match their pin.

A scene hands a shader to the engine as a path, and without ``--strict`` the engine passes a shader that fails to
compile straight through, draws the frame without it and exits 0."""

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import srstudio

ROOT = Path(__file__).resolve().parent.parent
HERE = Path(srstudio.__file__).parent / "assets" / "shaders"
PIN = json.loads((HERE / "vendored.json").read_text())
SHADERS = [*(HERE / name for name in sorted(PIN["sha256"])), ROOT / "episodes" / "pilots" / "paint.glsl"]
SCENE = """<?xml version="1.0" encoding="UTF-8"?>
<scene version="1.1">
  <project width="64" height="64" fps="30" duration="1" seed="1" background="#202020" antialias3d="4"/>
  <materials><material id="clay" baseColor="#c08040" roughness="0.7"/></materials>
  <composition>
    <group id="world" effects="fx">
      <object3D id="aim" primitive="sphere" material="clay" radius="0.1" visible="false"/>
      <object3D id="box" primitive="box" material="clay" width="40" height="40" depth="40"/>
    </group>
    <camera id="lens" start="0" end="1" x="0" y="0" z="-120" projection="perspective" fov="40" near="5" far="1000"
      target="aim"/>
  </composition>
  <lights><light id="sun" type="directional" intensity="2" yaw="70" pitch="-24"/></lights>
  <effects><effect id="fx" type="shader" src="shader.fs"/></effects>
</scene>
"""


def render(engine: Path, folder: Path, source: str) -> subprocess.CompletedProcess:
    (folder / "shader.fs").write_text(source)
    scene = folder / "scene.xml"
    scene.write_text(SCENE)
    command = [engine, "render", scene, "--strict", "--frames", "0..=0", "-o", folder / "f%04d.png"]
    return subprocess.run(command, capture_output=True, text=True, timeout=120)


def test_the_vendored_files_are_the_ones_pinned():
    assert sorted(PIN["sha256"]) == sorted(p.name for p in HERE.glob("*.fs"))
    for name, digest in PIN["sha256"].items():
        assert hashlib.sha256((HERE / name).read_bytes()).hexdigest() == digest, name


@pytest.mark.parametrize("path", SHADERS, ids=lambda p: p.name)
def test_a_shader_compiles_and_runs(path, scene_render, tmp_path):
    done = render(scene_render, tmp_path, path.read_text())
    assert done.returncode == 0, done.stdout + done.stderr


def test_a_broken_shader_is_caught(scene_render, tmp_path):
    done = render(scene_render, tmp_path, "vec4 effect(vec2 uv) { return nonsense(uv); }\n")
    assert done.returncode != 0
    assert "nonsense" in done.stdout + done.stderr  # the shader is what failed, not the document

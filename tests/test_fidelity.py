"""The shipped episodes rebuilt from their packages must match the shipped scene XML.

Needs ``SRSTUDIO_PACKAGES=<folder>`` holding ``<package>/project`` for each extracted ``.vpkg.zip``.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
EPISODES = HERE.parent / "episodes"
TOOLS = HERE.parent / "tools"
INTERVIEW_INPUTS = ("dialogue.json", "assets")
# module, package folder, scene file, inputs copied into the work folder, extra outputs compared byte for byte
CASES = [
    ("fast_at_math", "fast-at-math-1.1.0", "fast-at-math.scene.xml", INTERVIEW_INPUTS, ()),
    ("multitasking", "multitasking-1.0.0", "multitasking.scene.xml", INTERVIEW_INPUTS, ()),
    ("pressure_interview", "pressure-interview-1.1.0", "pressure-interview.scene.xml", INTERVIEW_INPUTS, ()),
    ("honesty_interview", "honesty-interview-1.1.0", "honesty-interview.scene.xml", INTERVIEW_INPUTS, ()),
    ("wifi_password", "wifi-password-1.0.0", "wifi-password.scene.xml", INTERVIEW_INPUTS, ()),
    (
        "printer_recreation",
        "printer-recreation-1.0.0",
        "scene.xml",
        ("timeline.json", "assets", "audio"),
        ("Printer_Captions.srt",),
    ),
    (
        "mushroom_training",
        "mushroom-training-2.0.0",
        "scene.xml",
        ("script.json", "assets"),
        ("Mushroom_Training_Captions.srt",),
    ),
]


@pytest.mark.parametrize("module,package,scene,inputs,extra_outputs", CASES)
def test_rebuild_matches_shipped_scene(packages, tmp_path, module, package, scene, inputs, extra_outputs):
    source = packages / package / "project"
    if not source.is_dir():
        pytest.skip(f"{source} missing")
    work = tmp_path / package
    work.mkdir()
    for name in inputs:
        src = source / name
        shutil.copytree(src, work / name) if src.is_dir() else shutil.copy(src, work)
    subprocess.run([sys.executable, str(EPISODES / f"{module}.py"), str(work)], check=True, cwd=EPISODES)
    sys.path.insert(0, str(TOOLS))
    try:
        from compare_scene import diff
    finally:
        sys.path.pop(0)
    assert diff(str(source / scene), str(work / scene)) == []
    for name in extra_outputs:
        assert (work / name).read_bytes() == (source / name).read_bytes()

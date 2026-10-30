"""Consumer typing, actionable build errors, and refused performance typos."""

import os
import subprocess
import sys

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Canvas, Performance, SrstudioError, cast

PROP_SOURCE = '''from srstudio import register
@register("prop", "p")
def p(size: float) -> float:
    return size
'''
PERFORM_SOURCE = '''from srstudio import Episode, Actor
from sr_core.scene import Group
def build(ep: Episode, actor: Actor) -> None:
'''


@pytest.mark.parametrize(
    "source,expected",
    [
        (PROP_SOURCE + 'p("bad")', "arg-type"),
        (PROP_SOURCE + 'x: str = p(1)', "assignment"),
        (PERFORM_SOURCE + '    ep.perform(actor, ep.comp, "left", "top", "large")', "arg-type"),
        (PERFORM_SOURCE + '    result: int = ep.perform(actor, ep.comp, 0, 0, 1)', "assignment"),
        (PERFORM_SOURCE + '    ep.perform(actor, ep.comp, 0, 0, 1, blinks="bad")', "arg-type"),
        (PROP_SOURCE + 'x: float = p(1)', None),
        (PERFORM_SOURCE + '    result: Group = ep.perform(actor, ep.comp, 0, 0, 1, blinks=[(0.2, 0.3)])', None),
    ],
)
def test_external_consumer_types(tmp_path, source, expected):
    env = {key: value for key, value in os.environ.items() if key not in {"MYPYPATH", "PYTHONPATH"}}
    result = subprocess.run(
        [sys.executable, "-m", "mypy", "--follow-imports=silent", "--no-incremental", "-c", source],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if expected:
        assert result.returncode == 1 and f"[{expected}]" in result.stdout, result.stdout + result.stderr
    else:
        assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "rig,options,match",
    [
        (cast.Manager, {"arm": "articulated"}, "arm"),
        (cast.Manager, {"arms": "articulatd"}, "arms"),
        (cast.Candidate, {"arms": None}, "arms"),
        (cast.Candidate, {"facepalm": (0, 1)}, "facepalm"),
        (cast.Barista, {"held_cup": [(0, 1)]}, "held_cup"),
        (cast.Customer, {"naem": "Milo"}, "naem"),
        (cast.Manager, {"pupils": "bad"}, "pupils"),
        (cast.Candidate, {"arms": "articulated", "forearm": [(0, "bad")]}, "forearm"),
        (cast.Manager, {"brows": [()]}, "brows"),
        (cast.Manager, {"brows": (["bad"], [])}, "brows"),
        (cast.Manager, {"facepalm": (1, 0)}, "facepalm"),
        (cast.Manager, {"hide_right_arm_at": float("nan")}, "hide_right_arm_at"),
        (cast.Candidate, {"pointing": [(-1, 1)]}, "pointing"),
        (cast.Customer, {"held_cup": [(1, 0)]}, "held_cup"),
        (cast.Customer, {"skin": 3}, "skin"),
        (cast.Barista, {"name": 3}, "name"),
    ],
)
def test_bad_actor_options_are_refused_before_drawing(rig, options, match):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=1)
    cv = Canvas(scene, OFFICE)
    before = scene.to_bytes()
    with pytest.raises(SrstudioError, match=match):
        rig(cv).build(cv.comp, 0, 0, perf=Performance(extras=options))
    assert scene.to_bytes() == before


@pytest.mark.parametrize(
    "rig,options",
    [
        (
            cast.Manager,
            {
                "arms": "articulated",
                "legs": "standing",
                "pupils": [(0, -20)],
                "brows": ([(0, -2)], [(0, 2)]),
                "hide_right_arm_at": 0.5,
                "facepalm": (0.5, 1),
            },
        ),
        (cast.Candidate, {"arms": "articulated", "forearm": [(0, -90)], "pointing": [(0, 1)]}),
        (cast.Barista, {"skin": "#C28A65", "name": None}),
        (cast.Customer, {"held_cup": [(0, 1)]}),
        (cast.Manager, {"brows": None, "pupils": None, "facepalm": None, "hide_right_arm_at": None}),
        (cast.Candidate, {"forearm": None, "pointing": None}),
    ],
)
def test_existing_actor_options_remain_usable(rig, options):
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=1)
    cv = Canvas(scene, OFFICE, font_asset=None)
    rig(cv).build(cv.comp, 0, 0, perf=Performance(extras=options))
    assert scene.check() == []


def test_custom_actor_options_can_extend_the_contract():
    class BadgeManager(cast.Manager):
        extra_options = cast.Manager.extra_options | {"badge"}

    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=1)
    cv = Canvas(scene, OFFICE)
    assert BadgeManager(cv).build(cv.comp, 0, 0, perf=Performance(extras={"badge": True})) is not None


@pytest.mark.parametrize("module", [False, True])
def test_build_reports_expected_library_errors_without_tracebacks(tmp_path, module):
    script = tmp_path / "bad_timeline.py"
    script.write_text("from srstudio import Timeline\nTimeline.from_dict({'duration': 1})\n")
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    result = subprocess.run(
        [sys.executable, "-m", "srstudio", "build", "bad_timeline" if module else str(script)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1
    assert "timeline.phrases" in result.stderr
    assert "Traceback" not in result.stderr

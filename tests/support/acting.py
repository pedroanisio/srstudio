"""What test_acting.py shares with other test modules."""

from __future__ import annotations

import json
import subprocess

from sr_core.scene import Scene

from srstudio import Canvas


def canvas():
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='30', duration=12)
    return Canvas(scene, font_asset=None)


def evaluate(engine, path, time):
    result = subprocess.run(
        [str(engine), 'eval', str(path), '--time', str(time), '--json'], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)['result']['nodes']


def contact_track():
    from srstudio.limbs import HUMAN, ArmProfile, Camera, Frame, Vec3
    from srstudio.limbs.compile import BakeOptions
    from srstudio.limbs.integration import LimbTrack
    from srstudio.limbs.motion import Action, Contact, Motion, TransformKey, TransformTrack

    target = TransformTrack((TransformKey(0, Frame(origin=Vec3(0.4, 0.2, 0))),))
    motion = Motion(
        ArmProfile(), HUMAN, (Action('press', duration=4),), contacts=(Contact('button', 0.5, 3.5, target),)
    )
    return LimbTrack(
        motion, style='gloss', camera=Camera(origin=(-92, -345), scale=200), options=BakeOptions(fps=4), backend='baked'
    )

"""Intent metadata drawn from the same vocabulary and envelopes as compilation."""

from __future__ import annotations

from dataclasses import fields
from typing import TYPE_CHECKING

from . import gloss
from .character_clips import toon_pose_vocabulary
from .head_motion import CHANNELS, GAZES, limit
from .toon_cast import VISEMES
from .toon_head import Glancing

if TYPE_CHECKING:
    from .acting import ActingRig


def controls(rig: ActingRig) -> dict:
    from .acting import HeadTarget

    channels = {}
    gaze: list[str]
    visemes: tuple[str, ...]
    if rig.family == 'toon' and rig.head_rig is not None:
        eyes, mouths, gestures = toon_pose_vocabulary(rig.head_rig)
        gaze = sorted(GAZES) if isinstance(rig.head_rig.look.drawing, Glancing) else []
        visemes = VISEMES
        targets = {f.name for f in fields(HeadTarget)}
        for name in CHANNELS:
            maximum = limit(rig.head_rig.style, name)
            channels[name] = {
                'minimum': 0 if name == 'breath' else -maximum,
                'maximum': maximum,
                'unit': 'normalized'
                if name == 'breath'
                else 'reference pixels'
                if name in ('nod', 'face_x', 'idle_y')
                else 'degrees',
                'input': 'beat.breath'
                if name == 'breath'
                else f'beat.head.{name}'
                if name in targets
                else f'overrides.head.{name}',
            }
    else:
        eyes = set(gloss.HOST_FACES if rig.gloss_character == 'sunny' else gloss.FACES)
        mouths, gaze = set(), []
        gestures = set() if rig.gloss_character == 'sunny' else set(gloss.POSES)
        visemes = gloss.VISEMES
    return {
        'vocabulary': {
            'eyes': sorted(eyes),
            'mouths': sorted(mouths),
            'gestures': sorted(gestures),
            'gaze': gaze,
            'visemes': sorted(visemes),
        },
        'channels': channels,
    }

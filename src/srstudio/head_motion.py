"""Organic head motion as data (ADR 0050): what a drawn head does while it listens, speaks and sits still, as sparse
keys for the engine's own curves, deterministic and bounded.

:func:`plan` turns a :class:`HeadStyle` and the :class:`Speech` of a shot into a :class:`HeadPlan`, one
:class:`Channel` per thing that moves and a track of where the eyes look:

* **Springs.** A nod, a glance and a lean are targets on spring keys with carried momentum, so the motion lags,
  overshoots and settles. Short channels use engine springs; long channels are sampled to bound evaluation cost.
  A :class:`Spring` is named by frequency and damping ratio.
* **Speech.** A nod falls on about four in five accents (:func:`accents`: content words whose stressed syllable, from
  the CMU Pronouncing Dictionary, stands above the phrase's loudness), spans two to four phones and leads its
  syllable; a phrase after a pause opens with a dip; a character repeats one movement type; an intensifier earns a
  bigger nod. The counts follow Graf, Cosatto, Strom and Huang, *Visual Prosody* (2002).
* **Idle.** Two octaves of hashed 1-D gradient noise, ducked while speaking, and a breath taken in the pauses and let
  out across the phrases, or an uneven slow cycle in silence.
* **Glances.** The eyes jump on hold keys; the head follows late through its spring and comes back.
* **Listening.** What another character says is ``heard``: the listener's eyes stay on them, its idle quiets, and it
  gives a small nod of its own signature at the end of their phrases (:func:`listening`).

No draw comes from a global generator or the clock: :func:`hash_unit` hashes the seed, a channel name and an ordinal,
so one channel never shifts another. The head-drawing side is :mod:`srstudio.toon_head`.

Implementation boundaries: _head_channels (sampling), _head_types (records and
limits), _head_speech (alignment and cues), _head_noise (seeded noise), and
_head_planner (composition). This module preserves the public import path.
"""

from __future__ import annotations

from types import FunctionType

from ._head_channels import _CURVES as _CURVES
from ._head_channels import SPRING_RUN as SPRING_RUN
from ._head_channels import Channel as Channel
from ._head_channels import HeadMotionError as HeadMotionError
from ._head_channels import Key as Key
from ._head_channels import Spring as Spring
from ._head_channels import _bake_spring as _bake_spring
from ._head_channels import _channel_bounds as _channel_bounds
from ._head_channels import _sample_spring as _sample_spring
from ._head_noise import fbm as fbm
from ._head_noise import hash_unit as hash_unit
from ._head_noise import noise as noise
from ._head_planner import plan as plan
from ._head_speech import Accent as Accent
from ._head_speech import Nod as Nod
from ._head_speech import Speech as Speech
from ._head_speech import Word as Word
from ._head_speech import accents as accents
from ._head_speech import dips as dips
from ._head_speech import listening as listening
from ._head_speech import nods as nods
from ._head_speech import speech_of as speech_of
from ._head_speech import stress as stress
from ._head_speech import stressed_at as stressed_at
from ._head_speech import words_of as words_of
from ._head_types import ANTICIPATE as ANTICIPATE
from ._head_types import AVERT as AVERT
from ._head_types import AVERT_BACK as AVERT_BACK
from ._head_types import CHANNELS as CHANNELS
from ._head_types import DUCK as DUCK
from ._head_types import FACE_DOWN as FACE_DOWN
from ._head_types import FACE_UP as FACE_UP
from ._head_types import GAZES as GAZES
from ._head_types import INTENSIFIER_GAIN as INTENSIFIER_GAIN
from ._head_types import LISTEN_LAG as LISTEN_LAG
from ._head_types import LISTEN_SHARE as LISTEN_SHARE
from ._head_types import LOOK_AWAY as LOOK_AWAY
from ._head_types import LOUD_RATE as LOUD_RATE
from ._head_types import NOD_SPAN as NOD_SPAN
from ._head_types import PAUSE as PAUSE
from ._head_types import PHONES as PHONES
from ._head_types import Facing as Facing
from ._head_types import HeadPlan as HeadPlan
from ._head_types import HeadStyle as HeadStyle
from ._head_types import limit as limit
from .voice import Alignment as Alignment

__all__ = [
    "AVERT_BACK",
    "CHANNELS",
    "DUCK",
    "FACE_DOWN",
    "FACE_UP",
    "GAZES",
    "INTENSIFIER_GAIN",
    "LISTEN_SHARE",
    "LOUD_RATE",
    "Accent",
    "Channel",
    "Facing",
    "HeadMotionError",
    "HeadPlan",
    "HeadStyle",
    "Nod",
    "Speech",
    "Spring",
    "Word",
    "accents",
    "dips",
    "fbm",
    "hash_unit",
    "limit",
    "listening",
    "nods",
    "noise",
    "plan",
    "speech_of",
    "stress",
    "stressed_at",
    "words_of",
]

# Keep existing pickles and introspection on the supported public path.
# Aliases share their implementation objects; no wrappers or duplicate samplers.
for _name in __all__:
    _value = globals()[_name]
    if isinstance(_value, (type, FunctionType)):
        _value.__module__ = __name__
del _name, _value

"""Closed data records for the versioned agent authoring interface."""

from dataclasses import dataclass

from .blob import Cue
from .stick import RigKey
from .toon import Pose


@dataclass(frozen=True)
class ActorInputs:
    mouth: tuple[tuple[float, str], ...] = ()
    blinks: tuple[tuple[float, float], ...] = ()
    nods: tuple[tuple[float, float], ...] = ()


@dataclass(frozen=True)
class SoftInputs:
    cues: tuple[Cue, ...]
    mouth_states: tuple[tuple[float, str], ...] = ()
    shadow: bool = False


@dataclass(frozen=True)
class StickInputs:
    keys: tuple[RigKey, ...]
    blinks: tuple[float, ...] = ()


@dataclass(frozen=True)
class ToonInputs:
    poses: tuple[Pose, ...]
    mouths: tuple[tuple[float, str], ...] = ()


@dataclass(frozen=True)
class GlossInputs:
    talk: tuple[tuple[float, str], ...] = ()
    face: tuple[tuple[float, str], ...] = ()
    pose: tuple[tuple[float, str], ...] = ()


@dataclass(frozen=True)
class SagaInputs:
    talk: tuple[tuple[float, str], ...] = ()
    flip: bool = False


@dataclass(frozen=True)
class InkInputs:
    text: str = ''
    mood: str = ''
    gesture: bool = False
    blink_after: float = 1.2


FAMILIES = {
    'actor': (ActorInputs, ('manager', 'candidate')),
    'soft': (SoftInputs, ('pip', 'bo', 'juno', 'juno@2', 'remy')),
    'stick': (StickInputs, ('stick-rig',)),
    'toon': (ToonInputs, ('toon-bento', 'toon-bento@2', 'toon-sloth', 'toon-goat', 'toon-hamster')),
    'gloss': (GlossInputs, ('gloss-nadia', 'gloss-gus', 'gloss-tamsin', 'gloss-sunny')),
    'saga': (SagaInputs, ('saga-gloom', 'saga-enforcer', 'saga-droid', 'saga-juno', 'saga-rook', 'saga-mabel')),
    'ink': (InkInputs, ('doodle',)),
}

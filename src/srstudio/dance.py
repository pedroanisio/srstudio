"""Dance moves timed on music, independent of any drawing style, so any character can dance to any song (ADR 0186).

A :class:`Move` is versioned data (``srstudio.dance-moves/1.0.0``, the presets in ``assets/dance/moves.json``): one
:class:`Pattern` per canonical ``"joint.dof"`` of srlocations' mannequin, or per root axis, each a waveform that hits
its amplitude on the beat. :func:`sample` reads a move or a :class:`Routine` (``srstudio.dance-routine/1.0.0``, bar
ranges of moves with transitions and held faces) on a :class:`music.Groove` into a :class:`DanceFrame`; :func:`frames`
samples it at a picture rate, bounded. :func:`song_map` measures a track's beat energy and its louder and quieter
phrases, and :func:`measure_dance` reads the groove back out of a sampled channel, so a move is tested against the
dance it was measured from.

Amplitudes are body-relative: head radii on the root, radians on joints. Turning deltas into a pose, and keeping
planted feet planted, is the skeleton's and the body's job.
"""

from __future__ import annotations

from ._dance_curve import CurveError
from ._dance_measure import (
    PROFILE_POINTS,
    SEAT_GROOVE_BOB,
    SEAT_GROOVE_SWAY,
    DanceMeasureError,
    DanceReading,
    DanceTarget,
    measure_dance,
    profile_distance,
)
from ._dance_model import (
    CHAINS,
    CURVE_POINTS,
    FEET,
    JOINTS,
    ROOT,
    SUPPORTS,
    TARGETS,
    WAVEFORMS,
    Contact,
    Curve,
    DanceError,
    Entry,
    Move,
    MoveError,
    Pattern,
    Routine,
    RoutineError,
    chain,
    mirrored,
    wave,
)
from ._dance_parse import (
    MOVES_SCHEMA,
    ROUTINE_SCHEMA,
    DanceDataError,
    DanceSchemaError,
    dump_routine,
    load_moves,
    load_routine,
    moves,
    parse_moves,
    parse_routine,
)
from ._dance_sample import MAX_FPS, MAX_FRAMES, DanceFrame, frames, sample
from ._dance_song import SongMap, SongMapError, SongPart, song_map

__all__ = [
    "CHAINS",
    "CURVE_POINTS",
    "FEET",
    "JOINTS",
    "MAX_FPS",
    "MAX_FRAMES",
    "MOVES_SCHEMA",
    "PROFILE_POINTS",
    "ROOT",
    "ROUTINE_SCHEMA",
    "SEAT_GROOVE_BOB",
    "SEAT_GROOVE_SWAY",
    "SUPPORTS",
    "TARGETS",
    "WAVEFORMS",
    "Contact",
    "Curve",
    "CurveError",
    "DanceDataError",
    "DanceError",
    "DanceFrame",
    "DanceMeasureError",
    "DanceReading",
    "DanceSchemaError",
    "DanceTarget",
    "Entry",
    "Move",
    "MoveError",
    "Pattern",
    "Routine",
    "RoutineError",
    "SongMap",
    "SongMapError",
    "SongPart",
    "chain",
    "dump_routine",
    "frames",
    "load_moves",
    "load_routine",
    "measure_dance",
    "mirrored",
    "moves",
    "parse_moves",
    "parse_routine",
    "profile_distance",
    "sample",
    "song_map",
    "wave",
]

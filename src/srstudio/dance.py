"""Dance moves timed on music, independent of any drawing style, so any character can dance to any song (ADR 0186).

A :class:`Move` is versioned data (``srstudio.dance-moves/1.1.0``, the presets in ``assets/dance/moves.json``): one
:class:`Pattern` per canonical ``"joint.dof"`` of srlocations' mannequin, or per root axis, each a waveform that hits
its amplitude on the beat. :func:`sample` reads a move or a :class:`Routine` (``srstudio.dance-routine/1.0.0``, bar
ranges of moves with transitions and held faces) on a :class:`music.Groove` into a :class:`DanceFrame`; :func:`frames`
samples it at a picture rate, bounded. :func:`song_map` measures a track's beat energy and its louder and quieter
phrases, and :func:`measure_dance` reads the groove back out of a sampled channel, so a move is tested against the
dance it was measured from.

A move's :class:`Follow` records carry its swing (ADR 0201): a joint follows another channel late, through a damped
:func:`spring` that overshoots and settles, so a head trails the body and a curve replaces a straight stroke.
:func:`measure_swing` reads that swing back off the head's path, its roll and the neck's lean, which
:func:`dance_pose.body_series` reads off any character, and :data:`SEAT_GROOVE_SWING` holds the seat-groove to the car
reel's curve.

Amplitudes are body-relative: head radii on the root, radians on joints. Turning deltas into a pose, and keeping
planted feet planted, is the skeleton's and the body's job.
"""

from __future__ import annotations

from ._dance_measure import (
    SEAT_GROOVE_BOB,
    SEAT_GROOVE_SWAY,
    SEAT_GROOVE_SWING,
    ChainLag,
    DanceMeasureError,
    DanceReading,
    DanceTarget,
    PathReading,
    PathTarget,
    SwingReading,
    SwingTarget,
    measure_dance,
    measure_lag,
    measure_path,
    measure_swing,
)
from ._dance_model import (
    CHAINS,
    FEET,
    JOINTS,
    ROOT,
    SUPPORTS,
    TARGETS,
    WAVEFORMS,
    Contact,
    DanceError,
    Entry,
    Follow,
    Move,
    MoveError,
    Pattern,
    Routine,
    RoutineError,
    chain,
    mirrored,
    spring,
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
    "FEET",
    "JOINTS",
    "MAX_FPS",
    "MAX_FRAMES",
    "MOVES_SCHEMA",
    "ROOT",
    "ROUTINE_SCHEMA",
    "SEAT_GROOVE_BOB",
    "SEAT_GROOVE_SWAY",
    "SEAT_GROOVE_SWING",
    "SUPPORTS",
    "TARGETS",
    "WAVEFORMS",
    "ChainLag",
    "Contact",
    "DanceDataError",
    "DanceError",
    "DanceFrame",
    "DanceMeasureError",
    "DanceReading",
    "DanceSchemaError",
    "DanceTarget",
    "Entry",
    "Follow",
    "Move",
    "MoveError",
    "PathReading",
    "PathTarget",
    "Pattern",
    "Routine",
    "RoutineError",
    "SongMap",
    "SongMapError",
    "SongPart",
    "SwingReading",
    "SwingTarget",
    "chain",
    "dump_routine",
    "frames",
    "load_moves",
    "load_routine",
    "measure_dance",
    "measure_lag",
    "measure_path",
    "measure_swing",
    "mirrored",
    "moves",
    "parse_moves",
    "parse_routine",
    "sample",
    "song_map",
    "spring",
    "wave",
]

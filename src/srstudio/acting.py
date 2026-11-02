"""Coordinated acting on one persistent performance clock.

Compile a score once, sample it in any order, and place windows of that same plan in
shots. Emotion mappings are explicit artistic choices of a rig profile. Discrete faces
and gestures switch on arrival; numeric head and breath targets ease during transitions.
Explicit track overrides own their channels. No audio synthesis or model calls occur.
"""

from __future__ import annotations

import re
from bisect import bisect_right
from dataclasses import dataclass, field, replace
from typing import Literal

from sr_core.scene import Composition, Group

from . import checks
from ._transaction import scene_transaction
from .canvas import Canvas
from .character_clips import GlossClip, Interval, Placement, ToonClip, place_character
from .errors import SrstudioError
from .gaze import GazePlan, GazeSample
from .head_motion import CHANNELS, HeadPlan, Spring
from .limbs.integration import LimbTrack
from .limbs.math3d import Frame
from .limbs.motion import Sample
from .toon_head import Glancing, HeadRig, gaze_capabilities
from .voice import Alignment

__all__ = [
    'BENTO',
    'ActingBeat',
    'ActingError',
    'ActingRig',
    'ActingScore',
    'ActingState',
    'ChannelTiming',
    'Emotion',
    'Expression',
    'HeadTarget',
    'HeadValues',
    'LimbState',
    'Overrides',
    'PerformancePlan',
    'PerformanceWindow',
    'SpokenLine',
    'TransitionPolicy',
    'compile_performance',
    'gloss_actor',
    'parse_score',
]


class ActingError(SrstudioError, ValueError):
    """A score is ambiguous, unsupported or cannot produce a bounded performance."""


def _error(path: str, actual: object, expected: object, code: str = 'acting.input') -> ActingError:
    return ActingError(
        f'{path}: expected {expected}',
        code=code,
        path=path,
        actual=actual,
        expected=expected,
        remedy='Use the rig profile vocabulary, local performance seconds and one explicit owner per channel.',
    )


@dataclass(frozen=True)
class Expression:
    eyes: str
    mouth: str | None = None


@dataclass(frozen=True)
class HeadTarget:
    """Persistent authored targets; omitted fields keep their previous owner/value."""

    lean: float | None = None
    turn: float | None = None
    nod: float | None = None
    roll: float | None = None
    face_x: float | None = None


@dataclass(frozen=True)
class Emotion:
    name: str
    expression: Expression
    gesture: str | None = None


@dataclass(frozen=True)
class ActingRig:
    """Versioned, explicit semantic mappings; no emotion is inferred from a rig's name."""

    name: str
    family: Literal['toon', 'gloss']
    emotions: tuple[Emotion, ...]
    head_rig: HeadRig | None = None
    gloss_character: Literal['nadia', 'gus', 'tamsin', 'sunny'] | None = None
    version: str = '1.0.0'

    def describe(self) -> dict:
        from ._acting_transitions import describe_continuity, describe_policy

        return {
            'schema': 'srstudio.acting-rig/1.0.0',
            'name': self.name,
            'version': self.version,
            'family': self.family,
            'clock': 'performance seconds',
            'capabilities': {
                'expression': True,
                'speech': True,
                'head': self.family == 'toon',
                'gaze': self.family == 'toon'
                and self.head_rig is not None
                and isinstance(self.head_rig.look.drawing, Glancing),
                'target_gaze': self.head_rig is not None and gaze_capabilities(self.head_rig)['continuous'],
                'breath': self.family == 'toon',
                'gesture': self.gloss_character != 'sunny',
                'limbs': self.family == 'gloss' and self.gloss_character != 'sunny',
            },
            'emotions': [
                {'name': e.name, 'eyes': e.expression.eyes, 'mouth': e.expression.mouth, 'gesture': e.gesture}
                for e in self.emotions
            ],
            'transitions': {
                'discrete': 'switch at arrival',
                'numeric': 'sampled sine-in-out',
                'continuity': describe_continuity(policy=False),
                'policy': describe_policy(self),
            },
        }


@dataclass(frozen=True)
class ChannelTiming:
    """A channel's delay from beat.at and optional replacement transition duration, in seconds."""

    channel: str
    delay: float = 0.0
    duration: float | None = None


@dataclass(frozen=True)
class TransitionPolicy:
    """Opt-in numeric phases and held drawing arrival times; validated during compilation.

    Anticipation precedes the delayed launch. Settling follows arrival. Amounts are
    fractions of the target delta; spring parameters use Hz and damping ratio.
    This policy does not morph faces or promise velocity/acceleration continuity.
    """

    version: str = '1.0.0'
    curve: str = 'sine-in-out'
    anticipation: float = 0.0
    anticipation_amount: float = 0.15
    settle: float = 0.0
    overshoot: float = 0.0
    spring: Spring | None = None
    timing: tuple[ChannelTiming, ...] = ()


@dataclass(frozen=True)
class ActingBeat:
    at: float
    emotion: str | None = None
    expression: Expression | None = None
    gaze: str | None = None
    gesture: str | None = None
    head: HeadTarget | None = None
    breath: float | None = None
    transition: float = 0.25
    reset: bool = False
    policy: TransitionPolicy | None = None


@dataclass(frozen=True)
class SpokenLine:
    """Alignment is relative to this line; loudness is measured dB at HeadPlan's 100 Hz."""

    at: float
    alignment: Alignment
    levels: tuple[float, ...]


@dataclass(frozen=True)
class Overrides:
    """None inherits the score; a supplied track replaces the whole channel.

    An explicit HeadPlan owns all numeric head channels and gaze. It cannot be combined
    with a second gaze override. Limb tracks own gestures and retain their own contacts
    and attachment lifetimes; a beat cannot silently release those constraints.
    """

    expression: tuple[tuple[float, Expression], ...] | None = None
    gesture: tuple[tuple[float, str], ...] | None = None
    gaze: tuple[tuple[float, str], ...] | None = None
    mouth: tuple[tuple[float, str], ...] | None = None
    head: HeadPlan | None = None
    limbs: tuple[LimbTrack, ...] = ()


@dataclass(frozen=True)
class ActingScore:
    duration: float
    beats: tuple[ActingBeat, ...] = ()
    speech: tuple[SpokenLine, ...] = ()
    heard: tuple[SpokenLine, ...] = ()
    overrides: Overrides = field(default_factory=Overrides)
    seed: int = 0
    sample_rate: int = 30
    idle: bool = True


@dataclass(frozen=True)
class HeadValues:
    lean: float
    turn: float
    nod: float
    roll: float
    face_x: float
    idle_roll: float
    idle_y: float
    breath: float


@dataclass(frozen=True)
class LimbState:
    side: str
    pose: Sample
    contacts: tuple[str, ...]
    props: tuple[tuple[str, Frame], ...]


@dataclass(frozen=True)
class ActingState:
    time: float
    emotion: str
    expression: Expression
    gesture: str | None
    gaze: str | GazeSample | None
    mouth: str
    head: HeadValues | None
    limbs: tuple[LimbState, ...]


def _held(track, time):
    return track[max(0, bisect_right([key[0] for key in track], time) - 1)][1]


@dataclass(frozen=True)
class PerformancePlan:
    rig: ActingRig
    duration: float
    clip: ToonClip | GlossClip
    emotions: tuple[tuple[float, str], ...]
    expressions: tuple[tuple[float, Expression], ...]
    gestures: tuple[tuple[float, str | None], ...]
    mouths: tuple[tuple[float, str], ...]
    head: HeadPlan | None
    limbs: tuple[LimbTrack, ...]
    owners: tuple[tuple[str, str], ...]

    def sample(self, time: float) -> ActingState:
        """Pure random-access planned state, including exact Motion contact/prop frames.

        Limb geometry may be drawn on held frames at its configured sampling rate; the
        returned spatial pose is the continuous source sample, not a rendered-pixel claim.
        """
        if not checks.number(time) or not 0 <= time <= self.duration:
            raise _error('time', time, f'a finite performance second in 0..{self.duration}')
        head = HeadValues(*(getattr(self.head, name).sample(time) for name in CHANNELS)) if self.head else None
        gaze = _held(((0, 'ahead'), *self.head.gaze), time) if self.head else None
        if isinstance(self.clip, ToonClip) and self.clip.target_gaze is not None:
            gaze = self.clip.target_gaze.sample(time)
        limbs = []
        for track in self.limbs:
            t = max(0, time - track.options.offset)
            motion = track.motion
            limbs.append(
                LimbState(
                    motion.arm.side,
                    motion.sample(t),
                    tuple(c.name for c in motion.contacts if c.start <= t < c.end),
                    tuple((a.name, motion.prop_frame(a.name, t)) for a in motion.attachments),
                )
            )
        return ActingState(
            time,
            _held(self.emotions, time),
            _held(self.expressions, time),
            _held(self.gestures, time),
            gaze,
            _held(self.mouths, time),
            head,
            tuple(limbs),
        )

    def with_target_gaze(self, target: GazePlan) -> PerformancePlan:
        """Bind target eyes and additive head follow without restarting the performance.

        Neutral named holds may be replaced; authored look-away states are refused.
        Use Overrides(gaze=()) at score compilation to suppress procedural glances
        while retaining idle and breath. Rebinding replaces the previous target.
        """
        from ._gaze_drawing import prepare
        from .gaze import _fail

        if not isinstance(self.clip, ToonClip) or self.rig.head_rig is None:
            raise _fail('rig', self.rig.name, 'a Toon rig declaring target gaze', 'gaze.unsupported')
        tracking = prepare(self.rig.head_rig, self.clip.poses, self.duration, self.clip.head, target)
        owners = dict(self.owners)
        owners.update(gaze='target', head='base plus target follow')
        return replace(
            self, clip=replace(self.clip, target_gaze=target), head=tracking.head, owners=tuple(owners.items())
        )

    def window(self, start: float, end: float) -> PerformanceWindow:
        if not (checks.number(start) and checks.number(end) and 0 <= start < end <= self.duration):
            raise _error('window', (start, end), f'0 <= start < end <= {self.duration}')
        return PerformanceWindow(self, start, end)


@dataclass(frozen=True)
class PerformanceWindow:
    """A view of an existing plan. Its returned drawing group uses the full performance clock."""

    plan: PerformancePlan
    start: float
    end: float

    def sample(self, time: float) -> ActingState:
        if not checks.number(time) or not 0 <= time <= self.end - self.start:
            raise _error('window.time', time, f'a local second in 0..{self.end - self.start}')
        return self.plan.sample(self.start + time)

    def place(
        self,
        cv: Canvas,
        parent: Composition | Group,
        *,
        at: float = 0,
        placement: Placement | None = None,
        id: str | None = None,
    ) -> Group:
        self.plan.window(self.start, self.end)  # validate direct construction too
        if not isinstance(parent, (Composition, Group)) or not any(n is parent for n in cv.scene.iter()):
            raise _error('parent', parent, 'a composition or group on this canvas')
        if not checks.number(at) or at < 0:
            raise _error('at', at, 'a nonnegative finite parent-timeline second')
        if cv._frozen:
            raise _error('canvas', 'frozen', 'a running canvas')
        if id is not None and (not isinstance(id, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*', id)):
            raise _error('id', id, 'an XML name')
        if id is not None and any(n.attributes().get('id') == id for n in cv.scene.iter()):
            raise _error('id', id, 'an unused scene ID')
        interval = Interval(at, at + self.end - self.start)
        with scene_transaction(cv.scene, cv):
            group = cv.group(
                parent, id or cv.uid('performance'), start=interval.start, end=interval.end, timeOffset=at - self.start
            )
            place_character(
                cv,
                group,
                self.plan.clip,
                interval=Interval(0, self.plan.duration),
                placement=placement or Placement(),
                id=f'{group.id}-character',
            )
            return group


def compile_performance(rig: ActingRig, score: ActingScore) -> PerformancePlan:
    """Compile and validate bounded intent; no scene supplied by the caller is mutated."""
    from ._acting_compile import compile_score

    try:
        return compile_score(rig, score)
    except ActingError:
        raise
    except SrstudioError as exc:
        details = exc.to_dict()
        code = 'acting.unsupported' if details['code'].endswith('.unsupported') else 'acting.input'
        raise _error(details['path'] or 'score', details['actual'], details['expected'] or str(exc), code) from exc


def parse_score(data: object, *, overrides: Overrides | None = None) -> ActingScore:
    """Strictly parse a decoded acting score (1.0.0 or opt-in-policy 1.1.0).

    Unknown fields and primitive type coercions are refused. HeadPlan/LimbTrack overrides
    are explicit Python runtime bindings, never opaque values forwarded from generated JSON.
    Pass the result to compile_performance to validate its timing, references and capabilities.
    """
    from ._acting_parse import decode

    try:
        return decode(data, overrides)
    except ActingError:
        raise
    except SrstudioError as exc:
        raise _error('alignment', None, str(exc)) from exc


def gloss_actor(who: Literal['nadia', 'gus', 'tamsin', 'sunny']) -> ActingRig:
    """Named acting choices for Gloss's limited faces, disclosed in ``describe()``."""
    if who not in ('nadia', 'gus', 'tamsin', 'sunny'):
        raise _error('who', who, 'nadia, gus, tamsin or sunny')
    host = who == 'sunny'
    choices = (
        ('neutral', 'smile' if host else 'open', 'down'),
        ('happy', 'smile' if host else 'open', 'up'),
        ('concerned', 'flat', 'down'),
        ('surprised', 'alert' if host else 'wide', 'up'),
        ('confident', 'smile' if host else 'open', 'point'),
    )
    return ActingRig(
        f'gloss-{who}',
        'gloss',
        tuple(Emotion(name, Expression(eyes), None if host else gesture) for name, eyes, gesture in choices),
        gloss_character=who,
    )


def _bento() -> ActingRig:
    from .toon_bento import BENTO_RIG, MOODS, pose_of

    poses = [(name, pose_of(0, name)) for name in MOODS]
    return ActingRig(
        'toon-bento',
        'toon',
        tuple(Emotion(name, Expression(p.eyes, p.mouth), p.arms) for name, p in poses),
        head_rig=BENTO_RIG,
    )


BENTO = _bento()

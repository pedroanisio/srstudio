"""Explicit metadata shared by character families; callers declare their semantics at registration.

These factories do not inspect names, invoke builders, import rig families, or change their validation.
Capabilities apply to the registered callable. A separate helper operation describes its own inputs.
"""

from collections.abc import Callable
from typing import Any

from .contracts import Operation, PartContract
from .contracts import ParameterContract as P


def seconds(clock: str, role: str | None = None) -> P:
    return P(unit='seconds', timebase=clock, role=role)


def track(clock: str, values: tuple[str, ...] = ()) -> P:
    return P(items=P(prefix_items=(seconds(clock), P(enum=values))))


POSITION = (
    ('x', P(type=float, unit='parent units')),
    ('y', P(type=float, unit='parent units')),
    ('scale', P(type=float, unit='ratio')),
)
AT = (('at', P(unit='parent units')), ('scale', P(unit='ratio')))


def character(
    *,
    limbs: bool,
    expressions: bool,
    parameters: tuple[tuple[str, P], ...] = (),
    vocabularies: tuple[tuple[str, tuple[str, ...]], ...] = (),
    constraints: tuple[str, ...] = (),
    operations: tuple[Operation, ...] = (),
    capabilities: tuple[tuple[str, bool | None], ...] = (),
) -> PartContract:
    return PartContract(
        parameters=parameters,
        capabilities=(('limbs', limbs), ('expressions', expressions), ('head_motion', False), *capabilities),
        vocabularies=vocabularies,
        constraints=(
            'Capabilities describe this callable; head_motion means accepting an authored HeadPlan. '
            'Built-in idle motion and held head poses do not imply that capability.',
            *constraints,
        ),
        operations=operations,
    )


def toon(
    pose: Callable[..., Any],
    eyes: tuple[str, ...],
    mouths: tuple[str, ...],
    arms: tuple[str, ...],
    *,
    visemes: tuple[str, ...] = (),
    wear: tuple[str, ...] = (),
    limbs: bool = False,
    constraints: tuple[str, ...] = (),
    geometry: str = 'Toon reference geometry is mapped into frame pixels before placement by the drawing parent.',
) -> PartContract:
    fields = (
        ('start', seconds('relative:enter', 'start')),
        ('eyes', P(enum=eyes)),
        ('mouth', P(enum=mouths)),
        ('arms', P(enum=arms)),
        *((('wear', P(items=P(enum=wear))),) if wear else ()),
    )
    return character(
        limbs=limbs,
        expressions=True,
        parameters=(
            ('poses', P(items=P(fields=fields))),
            ('enter', seconds('project', 'start')),
            ('duration', seconds('project', 'end')),
            ('taps', P(items=seconds('project'))),
            *((('mouths', track('project', visemes)),) if visemes else ()),
            *(
                (
                    (
                        'limbs',
                        P(description='Typed LimbTracks: motion seconds plus BakeOptions.offset on the canvas clock.'),
                    ),
                )
                if limbs
                else ()
            ),
        ),
        vocabularies=(('eyes', eyes), ('mouths', mouths), ('arms', arms), ('wear', wear), ('visemes', visemes)),
        constraints=(
            'Pose starts are ordered relative to enter and begin at zero; duration is the project exit time.',
            geometry,
            *constraints,
        ),
        operations=(Operation('pose', pose, PartContract(parameters=fields)),),
    )


def lit(
    visemes: tuple[str, ...],
    *,
    faces: tuple[str, ...] = (),
    poses: tuple[str, ...] = (),
    limbs: bool = False,
    parameters: tuple[tuple[str, P], ...] = (),
    constraints: tuple[str, ...] = (),
) -> PartContract:
    return character(
        limbs=limbs,
        expressions=bool(faces),
        parameters=(
            *AT,
            ('end', seconds('canvas', 'end')),
            ('talk', track('canvas', visemes)),
            *((('face', track('canvas', faces)),) if faces else ()),
            *((('pose', track('canvas', poses)),) if poses else ()),
            *parameters,
        ),
        vocabularies=(('visemes', visemes), ('faces', faces), ('poses', poses)),
        constraints=(
            'Times use the canvas clock: on a shot-local canvas, zero is the shot start.',
            'at is the feet anchor for dolls and the center for Sunny; scale multiplies the local drawing.',
            *constraints,
        ),
    )


def take(
    *,
    expressions: bool = False,
    parameters: tuple[tuple[str, P], ...] = (),
    vocabularies: tuple[tuple[str, tuple[str, ...]], ...] = (),
) -> PartContract:
    return character(
        limbs=False,
        expressions=expressions,
        parameters=(
            *POSITION,
            (
                'take',
                P(fields=(('start', seconds('project', 'start')), ('duration', seconds('relative:take', 'duration')))),
            ),
            *parameters,
        ),
        vocabularies=vocabularies,
        constraints=(
            'Build on a canvas whose local zero is the take start. Animation uses relative take times; '
            'Take.start is project metadata and is not automatically added by this builder.',
            'Take words and phones use relative take seconds. Speaker identity controls whether speech is animated.',
        ),
    )


def anchor(
    pose: Callable[..., Any],
    eyes: tuple[str, ...],
    mouths: tuple[str, ...],
    arms: tuple[str, ...],
    visemes: tuple[str, ...],
    *,
    host: bool = False,
) -> PartContract:
    fields = (
        ('eyes', P(enum=eyes)),
        ('mouth', P(enum=(*mouths, 'talk'))),
        ('arm' if host else 'arms', P(enum=arms)),
        ('head', P(unit='degrees', minimum=-15, maximum=15)),
        *((('pull', P(unit='ratio', minimum=0, maximum=1)),) if host else ()),
    )
    return character(
        limbs=False,
        expressions=True,
        parameters=(
            ('pose', P(fields=fields)),
            ('start', seconds('project', 'start')),
            ('end', seconds('project', 'end')),
            ('mouths', track('project', visemes)),
            *((('x', P(unit='parent units')),) if not host else ()),
        ),
        vocabularies=(('eyes', eyes), ('mouths', (*mouths, 'talk')), ('arms', arms), ('visemes', visemes)),
        operations=(Operation('pose', pose, PartContract(parameters=fields)),),
        constraints=('A held pose is drawn over start..end; mouth="talk" enables the supplied viseme track.',),
    )


def soft(
    cue: Callable[..., Any],
    poses: tuple[str, ...],
    eyes: tuple[str, ...],
    mouths: tuple[str, ...],
    feet: tuple[str, ...],
    visemes: tuple[str, ...],
) -> PartContract:
    fields = (
        ('time', seconds('canvas', 'start')),
        ('pose', P(enum=poses)),
        ('eyes', P(enum=eyes)),
        ('mouth', P(enum=mouths)),
        ('x', P(unit='rig units')),
        ('y', P(unit='rig units')),
        ('turn', P(unit='degrees')),
        ('ease', seconds('canvas', 'duration')),
        ('lift', P(unit='rig units')),
        ('pin', P(enum=(None, *feet))),
        ('overshoot', P(unit='ratio', minimum=0, maximum=0.5)),
    )
    return character(
        limbs=False,
        expressions=True,
        parameters=(
            *POSITION,
            ('cues', P(items=P(fields=fields))),
            ('end', seconds('canvas', 'end')),
            ('mouth_states', track('canvas', visemes)),
            ('fps', P(unit='drawings/second')),
            ('radius', P(unit='rig units')),
        ),
        capabilities=(('pose_tweening', True), ('foot_pinning', True)),
        vocabularies=(('poses', poses), ('eyes', eyes), ('mouths', mouths), ('feet', feet), ('visemes', visemes)),
        operations=(Operation('cue', cue, PartContract(parameters=fields)),),
        constraints=(
            'The first cue is at zero. ease is the interval before arrival; the expression changes on arrival.',
            'A pinned foot solves translation; pin cannot be combined with cue x/y/lift.',
            'mouth_states drive only sing mouths; pose coordinates are scaled into parent units.',
        ),
    )

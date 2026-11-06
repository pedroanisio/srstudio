"""Versioned JSON authoring tasks with explicit runtime bindings and one local clock.

Parse data first; compile with a caller-owned canvas and parent. This is a closed
set of adapters, not arbitrary Python construction or a plugin loader.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, fields
from typing import Any

from sr_core.scene import Composition, Group

from . import registry
from ._authoring_records import FAMILIES, ActorInputs, GlossInputs, InkInputs, SagaInputs, SoftInputs, StickInputs
from ._transaction import scene_transaction
from .canvas import Canvas
from .character_clips import ActorClip, GlossClip, Interval, Placement, _local_keys, place_character
from .errors import SrstudioError
from .limbs.compile import BakeOptions, compile_motion
from .limbs.interaction import AttachedProp, Participant, PropDrawing, PropMesh, bake_interaction
from .limbs.motion import Motion
from .limbs.serialization import MAX_ITEMS, _decode, parse_motion
from .rig import Performance
from .timeline import Take

SCHEMA = 'srstudio.authoring/1.0.0'


class AuthoringError(SrstudioError, ValueError):
    """An authoring document cannot be bound without guessing or dropping data."""


def _fail(path, actual, expected):
    return AuthoringError(
        f'{path}: expected {expected}',
        code='authoring.input',
        path=path,
        actual=actual,
        expected=expected,
        remedy='Use a discovered recipe, local performance seconds, and interval.start_s/end_s.',
    )


def _bounded(value, budget=None, depth=0):
    budget = [MAX_ITEMS] if budget is None else budget
    budget[0] -= 1
    if budget[0] < 0 or depth > 32:
        raise _fail('document', None, 'at most 100000 values and 32 levels')
    if isinstance(value, dict):
        if any(not isinstance(k, str) or len(k) > 1024 for k in value):
            raise _fail('document', None, 'short string object keys')
        for child in value.values():
            _bounded(child, budget, depth + 1)
    elif isinstance(value, list):
        for child in value:
            _bounded(child, budget, depth + 1)
    elif type(value) not in (str, int, float, bool, type(None)):
        raise _fail('document', type(value).__name__, 'JSON data only; runtime objects are separate bindings')
    elif isinstance(value, str) and len(value) > 16384:
        raise _fail('document', None, 'strings of at most 16384 characters')
    elif type(value) in (int, float):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise _fail('document', value, 'finite numbers')


def _object(value, path, allowed, required=()) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) - set(allowed) or set(required) - set(value):
        raise _fail(path, value, {'allowed': sorted(allowed), 'required': sorted(required)})
    return value


@dataclass(frozen=True)
class Request:
    task: str
    interval: Interval
    placement: Placement
    character: str | None = None
    arguments: Any = None
    motion: Motion | None = None
    mesh: PropMesh | None = None
    attachment: str | None = None
    style: str = 'toon'
    fps: int | None = None


def parse_request(document: object) -> Request:
    """Decode a closed JSON task, without drawing or reading files. All motion clocks start at zero."""
    _bounded(document)
    data = _object(
        document,
        'document',
        (
            'schema',
            'task',
            'interval',
            'placement',
            'character',
            'arguments',
            'motion',
            'mesh',
            'attachment',
            'style',
            'fps',
        ),
        ('schema', 'task', 'interval'),
    )
    if data['schema'] != SCHEMA or data['task'] not in ('character', 'gesture', 'carry'):
        raise _fail('schema/task', (data['schema'], data['task']), SCHEMA + ': character, gesture or carry')
    interval = _object(data['interval'], 'interval', ('start_s', 'end_s'), ('start_s', 'end_s'))
    try:
        span = Interval(interval['start_s'], interval['end_s'])
        placement = _decode(Placement, data.get('placement', {}), 'placement', [MAX_ITEMS])
        task = data['task']
        if task == 'character':
            _object(
                data, 'document', ('schema', 'task', 'interval', 'placement', 'character', 'arguments'), ('character',)
            )
            choice = next((record for record, names in FAMILIES.values() if data['character'] in names), None)
            if choice is None:
                raise _fail('character', data['character'], [n for _, names in FAMILIES.values() for n in names])
            arguments = _decode(choice, data.get('arguments', {}), 'arguments', [MAX_ITEMS])
            # All source key schedules are local. The adapters own their lifetime fields.
            for name in (
                'cues',
                'keys',
                'poses',
                'mouth',
                'mouth_states',
                'mouths',
                'talk',
                'face',
                'pose',
                'nods',
                'blinks',
            ):
                for i, key in enumerate(getattr(arguments, name, ())):
                    times = (
                        key
                        if name == 'blinks' and isinstance(key, tuple)
                        else (
                            (key[0],)
                            if isinstance(key, tuple)
                            else (key,)
                            if isinstance(key, (int, float))
                            else (getattr(key, 'time', getattr(key, 'start', None)),)
                        )
                    )
                    if any(t is None or not 0 <= t <= span.duration for t in times):
                        raise _fail(f'arguments.{name}[{i}]', key, f'local seconds within 0..{span.duration}')
            return Request(task, span, placement, data['character'], arguments)
        allowed: tuple[str, ...] = ('schema', 'task', 'interval', 'placement', 'motion', 'style', 'fps')
        if task == 'carry':
            allowed += ('mesh', 'attachment')
        _object(data, 'document', allowed, ('motion',) + (('mesh', 'attachment') if task == 'carry' else ()))
        motion = parse_motion(data['motion'])
        if motion.end > span.duration:
            raise _fail('motion', motion.end, f'a local performance ending by {span.duration}; no implicit crop')
        style = data.get('style', 'toon')
        if style not in ('toon', 'gloss', 'stick', 'cutout'):
            raise _fail('style', style, ['toon', 'gloss', 'stick', 'cutout'])
        fps = data.get('fps')
        BakeOptions(fps=fps)
        mesh = _decode(PropMesh, data['mesh'], 'mesh', [MAX_ITEMS]) if task == 'carry' else None
        attachment = data.get('attachment')
        if task == 'carry' and attachment not in {a.name for a in motion.attachments}:
            raise _fail('attachment', attachment, [a.name for a in motion.attachments])
        return Request(task, span, placement, motion=motion, mesh=mesh, attachment=attachment, style=style, fps=fps)
    except AuthoringError:
        raise
    except (SrstudioError, TypeError, ValueError) as exc:
        if isinstance(exc, SrstudioError):
            detail = exc.to_dict()
            if detail['path']:
                raise _fail(detail['path'], detail['actual'], detail['expected'] or str(exc)) from exc
        raise _fail(
            'arguments' if data['task'] == 'character' else 'motion/placement',
            str(exc),
            'typed values satisfying the selected adapter',
        ) from exc


def _character(cv, parent, request):
    entry = registry.get('character', request.character)
    if entry._current_contract is None:
        raise _fail('character', request.character, 'a registered builder with its current declared contract')
    args, end = request.arguments, request.interval.duration
    kwargs = {f.name: getattr(args, f.name) for f in fields(args)}
    if isinstance(args, ActorInputs):
        place_character(cv, parent, ActorClip(entry.builder, Performance(**kwargs)), interval=Interval(0, end))
    elif isinstance(args, GlossInputs):
        place_character(
            cv, parent, GlossClip(request.character.removeprefix('gloss-'), **kwargs), interval=Interval(0, end)
        )
    elif isinstance(args, SoftInputs):
        entry(cv, parent, **kwargs, end=end, id=cv.uid(request.character.replace('@', '-')))
    elif isinstance(args, StickInputs):
        entry(cv, parent, **kwargs, end=end)
    elif isinstance(args, InkInputs):
        take = Take(cv.uid('take'), 'speaker', '', args.text, 0, end, mood=args.mood)
        entry(cv, parent, take, 0, 0, gesture=args.gesture, blink_after=args.blink_after)
    elif isinstance(args, SagaInputs):
        entry(cv, parent, **kwargs, at=(0, 0), end=end)
    else:
        entry(cv, parent, **kwargs, enter=0, duration=end)


def compile_request(cv: Canvas, parent: Composition | Group, request: Request, *, id: str) -> Group:
    """Bind a parsed request atomically. Interval seconds use the parent clock; performance seconds start at zero."""
    if not isinstance(request, Request):
        raise _fail('request', request, 'parse_request(document)')
    if not isinstance(parent, (Composition, Group)) or not any(n is parent for n in cv.scene.iter()):
        raise _fail('parent', None, 'a group or composition on the supplied canvas')
    if cv._frozen or not isinstance(id, str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_.-]*', id):
        raise _fail('canvas/id', id, 'a running canvas and XML identifier')
    if any(
        str(n.attributes().get('id', '')) == id or str(n.attributes().get('id', '')).startswith(id + '-')
        for n in cv.scene.iter()
    ):
        raise _fail('id', id, 'an unused identifier namespace')
    held, rate, local = len(cv._held), cv._held_rate, cv.local_time
    try:
        with scene_transaction(cv.scene, cv):
            cv.local_time = False
            span, p = request.interval, request.placement
            group = cv.group(
                parent,
                id,
                start=span.start,
                end=span.end,
                timeOffset=span.start,
                x=p.x,
                y=p.y,
                scaleX=p.scale,
                scaleY=p.scale,
                anchorX=p.anchor[0],
                anchorY=p.anchor[1],
                rotation=p.rotation,
            )
            if request.task == 'character':
                _character(cv, group, request)
            else:
                if request.motion is None:
                    raise _fail('motion', None, 'a parsed motion')
                options = BakeOptions(fps=request.fps, duration=span.duration)
                if request.task == 'gesture':
                    compile_motion(cv, group, request.motion, id=id + '-motion', style=request.style, options=options)
                else:
                    if request.mesh is None or request.attachment is None:
                        raise _fail('mesh/attachment', None, 'a parsed mesh and named attachment')
                    bake_interaction(
                        cv,
                        group,
                        (Participant('hand', request.motion, request.style),),
                        (PropDrawing(request.mesh, AttachedProp(request.motion, request.attachment)),),
                        id=id + '-carry',
                        options=options,
                    )
            _local_keys(group)
            return group
    except Exception:
        del cv._held[held:]
        cv._held_rate = rate
        raise
    finally:
        cv.local_time = local


def recipes() -> dict:
    """Fresh executable requests with explicit evidence scope; never imply a render ran during discovery."""
    from ._authoring_recipes import catalog

    return catalog()


def describe_character(name: str) -> dict | None:
    """Link supported registered characters to their exact JSON adapter, without guessing capabilities."""
    for i, (family, (_, names)) in enumerate(FAMILIES.items()):
        if name in names:
            return {
                'schema': SCHEMA,
                'family': family,
                'parser': 'srstudio.authoring.parse_request',
                'compiler': 'srstudio.authoring.compile_request',
                'arguments_schema_pointer': f'/oneOf/{i}/properties/arguments',
                'clock': 'relative:interval.start_s',
                'placement_clock': 'parent',
                'runtime_bindings': ['cv', 'parent'],
                'guide': 'docs/authoring-agents.md',
            }
    return None


def schema(version='1.0.0') -> dict:
    from ._authoring_schema import document

    if version != '1.0.0':
        raise _fail('version', version, ['1.0.0'])
    return document()

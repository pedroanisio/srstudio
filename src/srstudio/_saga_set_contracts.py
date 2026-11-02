"""Saga scenery discovery: actual ownership, Canvas clocks and sampled contact helpers."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import Operation, PartContract
from .contracts import ParameterContract as P
from .lipsync import VISEMES

TIME = P(unit='seconds', timebase='canvas')
PIXELS = P(unit='drawing pixels', space='fixed-layout')
POINT = P(type=tuple[float, float], prefix_items=(PIXELS, PIXELS), space='fixed-layout')
AT = P(prefix_items=(P(unit='parent pixels', space='parent'),) * 2)
RATIO = P(unit='ratio')
DEGREES = P(unit='degrees')
COPY = P(role='display-copy')
FONT = P(role='font-bytes')
SPANS = P(items=P(prefix_items=(TIME, TIME)))
TALK = P(items=P(prefix_items=(TIME, P(enum=VISEMES))))
GROUP = P(type=Group, unit='drawing pixels', space='fixed-layout', role='drawing-group')
LOCAL_GROUP = replace(GROUP, space='returned-group', anchors=(('origin', (0, 0)),))
MUTATION = P(type=type(None), role='parent-mutation')
JAB = P(
    fields=(('at', TIME), ('sleeve', P(role='paint')), ('hand', P(role='paint')), ('elbow', POINT), ('scale', RATIO))
)
CLOCK = (
    'Keyframes and opacity gates follow Canvas.local_time: composition seconds by default, '
    'shot-local seconds when enabled. end must be finite and positive. '
    'It bounds cues but does not universally clip the drawing; gate the caller parent for a lifetime boundary.'
)
ROOM = (
    'Fixed 1080x1920 layout with cast floor y=1270. Returns None after appending scenery under parent; '
    'use a caller-owned group for whole-room movement or gating. Actors and foreground layers are separate calls. '
    'Far scenery uses a 3-pixel blur where present. Call finish explicitly for the shot grade.'
)
TEXT = (
    'Requires a bound Canvas font and matching font bytes for measurement. Copy and speech are preflighted '
    'before drawing. Wrapping raises SagaError on overflow instead of shrinking words.'
)
SPEECH = (
    'talk uses the Saga viseme vocabulary with finite, nonnegative, strictly increasing times. '
    'Speech keys may extend beyond end; no speech synthesis or facial solver is installed.'
)
JAB_LIMITS = (
    'Jab requires a positive finite at and scale, distinct representable phase times, finite elbow coordinates '
    'and a finite nonzero resting forearm length. The console additionally requires at<end. '
    'This is a fixed-layout hand and one stretching forearm, not an articulated arm or whole-body solver.'
)


def draw(
    *parameters: tuple[str, P], returns: P = GROUP, handle: bool = True, constraints: tuple[str, ...] = ()
) -> PartContract:
    return PartContract(
        parameters=(
            ('cv', P(type=Canvas)),
            ('parent', P(type=Composition | Group | Symbol)),
            ('end', replace(TIME, role='end')),
            *parameters,
        ),
        returns=returns,
        capabilities=(('returns_scene_handle', handle), ('spatial_attachment', False)),
        constraints=(
            CLOCK,
            'Draws 2D geometry; no spatial attachment, collision or support solver is supplied.',
            *constraints,
        ),
    )


def room(*parameters: tuple[str, P], constraints: tuple[str, ...]) -> PartContract:
    return draw(*parameters, returns=MUTATION, handle=False, constraints=(ROOM, *constraints))


_HELPERS = {
    'wrap': PartContract(
        parameters=(
            ('font', FONT),
            ('text', COPY),
            ('size', P(unit='drawing pixels')),
            ('width', P(unit='drawing pixels')),
            ('max_lines', P(role='maximum-line-count')),
        ),
        returns=P(type=list[str], items=COPY, role='wrapped-lines'),
        constraints=(
            'Measures font bytes without scene mutation. A word wider than width or too many lines raises '
            'SagaError. Explicit newlines are retained; keep_together can preserve phrase boundaries.',
        ),
    ),
    'stick_ball': PartContract(
        parameters=(('degrees', DEGREES),),
        returns=POINT,
        constraints=(
            'Returns ball center after clockwise rotation about (540,1450); rest center is (602,1210). '
            'Finite numeric degrees required. Does not apply caller transforms.',
        ),
    ),
    'stick_grip': PartContract(
        parameters=(('degrees', DEGREES),),
        returns=POINT,
        constraints=(
            'Returns a point 44 drawing pixels down the shaft from the ball toward the pivot, '
            'rotated clockwise by finite numeric degrees. Does not apply caller transforms.',
        ),
    ),
    'hand_at': PartContract(
        parameters=(('jab', JAB), ('t', TIME)),
        returns=POINT,
        constraints=(
            JAB_LIMITS,
            'Pure analytical grip position at finite numeric t; negative times are allowed. '
            'Pull begins at at-0.16, reaches -6 degrees at at, shoves to 20 at at+0.06, '
            'holds through at+0.3, returns to 10 by at+0.56 and stays there.',
        ),
    ),
    'jab_frames': PartContract(
        parameters=(('jab', JAB), ('end', TIME)),
        returns=P(type=list[tuple[float, float]], items=P(prefix_items=(TIME, DEGREES))),
        constraints=(
            JAB_LIMITS,
            'Samples at a fixed 24 Hz through ceil(end*24), including the terminal sample. '
            'At most 20000 samples; positive finite end must not exceed 19999/24 seconds. '
            'Times round to four decimals and angles to three. Terminal time may extend just under '
            '1/24 second beyond end before rounding. This does not follow project fps.',
        ),
    ),
}


def contract(name: str, *, cast: tuple[str, ...] = (), **helpers: Callable[..., Any]) -> PartContract:
    result = _CONTRACTS[name]
    if name == 'saga-holo':
        panels = P(
            items=P(
                fields=(
                    ('start', TIME),
                    ('title', COPY),
                    ('body', COPY),
                    ('tone', P(enum=('info', 'alert', 'ok', 'gold'))),
                    ('face', P(enum=('', *cast))),
                    ('fade', P(role='opacity-fade')),
                )
            )
        )
        result = replace(result, parameters=(*result.parameters, ('panels', panels)))
    return replace(result, operations=tuple(Operation(key, fn, _HELPERS[key]) for key, fn in helpers.items()))


_CONTRACTS = {
    'saga-space': room(
        constraints=(
            'Seeded nebula and far stars stay still; sharp stars twinkle with linear opacity keys. '
            'planet adds a moon-like disk. The foreground asteroid carries signature marks; '
            'signature code depends on Canvas.signature. No flight path or moving camera is authored.',
        )
    ),
    'saga-bridge': room(
        constraints=(
            'Blurred window stars, moon and struts sit behind a perspective floor. The alert strip and console '
            'lights use held opacity keys; signature marks stay sharp. No cast or camera is installed.',
        )
    ),
    'saga-cantina': room(
        ('stare', SPANS),
        constraints=(
            'Five sharp pairs of glowing eyes watch from blurred patrons. Nonnegative rising stare spans must '
            'start before end; their stops clamp to end and overlapping spans form a visibility union. '
            'No spans means hidden eyes. Draw cantina_front after actors with feet at y=1300. '
            'The background includes signature marks, but no foreground bar.',
        ),
    ),
    'saga-cantina-bar': room(
        constraints=(
            'Static foreground counter and rail beginning at y=940; draw after actors. '
            'end is validated but produces no animation or lifetime gate. This layer has no signature marks.',
        )
    ),
    'saga-desert': room(
        constraints=(
            'Static suns, dunes, hut, tower and signature marks. shade adds a caption gradient beginning at y=1260. '
            'end is validated but produces no animation or lifetime gate.',
        )
    ),
    'saga-cockpit': room(
        ('jump', SPANS),
        ('hit', TIME),
        constraints=(
            'Blurred stars and hyperspace streaks sit behind sharp struts and headrests. Nonnegative rising jump '
            'spans must start before end; stops clamp to end. hit is finite and 0<=hit<end and triggers a seeded '
            'window blast. Draw pilots with feet at y=1330, then cockpit_front. Signature marks live on the console. '
            'The blast is authored 2D animation, not impact physics.',
        ),
    ),
    'saga-cockpit-console': room(
        ('hit', TIME),
        ('jab', JAB),
        constraints=(
            JAB_LIMITS,
            'Draw after pilots. Held switch lights, stick and signature marks form the foreground. '
            'ledge adds a shelf at y=1250. Finite 0<=hit<end triggers seeded sparks and a right-side light wash.',
            'Jab rotation and hand/forearm share jab_frames samples at fixed 24 Hz, bounded to 20000 samples. '
            'Stick pivot is (540,1450), resting ball (602,1210), grip 44 pixels toward the pivot. '
            'Hand coordinates round to two decimals. Rotation, hand and forearm interpolate independently '
            'between keys; exact continuous contact between samples is not guaranteed. Helpers return '
            'fixed-layout positions before any caller transform.',
        ),
    ),
    'saga-compactor': room(
        ('walls', P(prefix_items=(TIME, TIME))),
        ('travel', PIXELS),
        ('door', TIME),
        ('start_px', PIXELS),
        constraints=(
            'start_px and travel must be finite and nonnegative; start_px plus applied travel is at most 300. '
            'Without walls, travel is unused. walls starts nonnegative before end and ends after its start; '
            'motion uses the supplied stop even when it exceeds end. Left and right walls move inward linearly. '
            'start_px preserves an earlier shot displacement. Finite 0<=door<end raises the back slab by 760 pixels '
            'over 0.6 seconds, which may extend beyond end. Rubbish and puddles are static painted shapes. '
            'Signature marks are included.',
        ),
    ),
    'saga-holo': draw(
        ('font', FONT),
        ('box', P(prefix_items=(PIXELS,) * 4)),
        returns=P(type=list[Group], items=GROUP, role='panel-groups'),
        constraints=(
            TEXT,
            'Returns one group per panel, in input order, with fixed-layout geometry. Panels are nonempty with '
            'strictly rising starts inside [0,end). box is (x,y,width,maximum-height), defaults to HOLO_BOX, '
            'and must fit SAFE edges (80,220,920,1420), width>=360 and maximum-height>=150. '
            'All titles/bodies and heights are measured before scene mutation. Title is 50 pixels, at most two '
            'lines; body is 40 pixels with line count bounded by available height.',
            'Panels gate from start to next start or end. fade uses a linear 0.14-second opacity ramp. '
            'Otherwise the first panel opens vertically from 0.06 to 1 in 0.14 seconds; all nonfade panels flicker '
            'for 0.12 seconds. The fill is opaque. face adds a small complete cast drawing in the left frame '
            'with its idle animation, without a head crop, mask or speech track.',
        ),
    ),
    'saga-cube': draw(
        ('at', POINT),
        ('size', PIXELS),
        ('boom', TIME),
        returns=MUTATION,
        handle=False,
        constraints=(
            'Returns None; supply a caller-owned group to move the entire drawing. at is the finite center of '
            'the front face, baked into path coordinates. Positive finite size sets front width; top/right '
            'faces extend another quarter-size above and right. Window lights blink even without boom.',
            'Finite 0<=boom<end triggers cube fade from boom+0.2 to boom+0.45, a growing orange fireball '
            'and 12 seeded debris pieces. Growth is shortened for a late boom; debris remains visible after '
            'its motion ends. No universal lifetime gate or physics simulation is supplied.',
        ),
    ),
    'saga-freighter': draw(
        ('at', AT),
        ('scale', RATIO),
        returns=LOCAL_GROUP,
        constraints=(
            'Static nose-right space van; flip negates horizontal scale. at must be finite and scale positive '
            'and finite. Body runs from x=-220 to 260; engine glow extends to -300 and the fin to y=-170. '
            'The yellow sticker is a blank shape. Caller owns flight motion; end adds no animation or gate.',
        ),
    ),
    'saga-fighter': draw(
        ('at', AT),
        ('scale', RATIO),
        returns=LOCAL_GROUP,
        constraints=(
            'Static nose-right wedge with red running lights, spanning x=-90..110 and y=-60..60. '
            'flip negates horizontal scale. at is finite and scale positive and finite. '
            'Caller owns flight motion; end adds no animation or gate.',
        ),
    ),
    'saga-pebble': draw(
        ('at', AT),
        ('lift', TIME),
        ('rise', PIXELS),
        returns=LOCAL_GROUP,
        constraints=(
            'A 52x34 pebble centered horizontally at at with its top 30 pixels above that origin. '
            'Finite 0<=lift<end starts a linear rise to at.y-rise by min(end,lift+0.8); '
            'then y alternates by 8 pixels every half second while before end. rise is finite and signed; '
            'zero and negative rises are allowed. No physical support or levitation solver is supplied.',
        ),
    ),
    'saga-handbook': draw(
        ('at', AT),
        ('scale', RATIO),
        ('talk', TALK),
        returns=LOCAL_GROUP,
        constraints=(
            SPEECH,
            'at is a finite top-left placement; scale is positive and finite. Body is 220x300 with a shadow '
            'offset by (8,10). RELAX lettering uses paths without a font. The whole device group is returned. '
            'Held screen opacity is 0.25 for silence/closed and 1 for other visemes; no separate screen handle.',
        ),
    ),
    'saga-hook': draw(
        ('text', COPY),
        ('font', FONT),
        ('talk', TALK),
        constraints=(
            TEXT,
            SPEECH,
            'Returns the whole fixed-layout hook gated over [0,end). Text wraps at 50 pixels into at most '
            'three 660-pixel lines. The speaking Handbook sits at (88,236), scale 0.5, with no separate handle.',
        ),
    ),
    'saga-entry': draw(
        ('title', COPY),
        ('body', COPY),
        ('font', FONT),
        ('talk', TALK),
        constraints=(
            TEXT,
            SPEECH,
            'Returns the entire fixed-layout Handbook entry and star field. Title wraps at 64 pixels into '
            'two 700-pixel lines, body at 50 into eight. Height and placement follow line counts; the full '
            'device is not independently constrained to SAFE. legible omits glass sheen over the words. '
            'Signature code is included without a cactus.',
            'With talk, screen opacity starts at 0.7; only states after t=0 change it to 1 for nonclosed or '
            '0.7 for closed. A state at zero is ignored by this screen track. The body uses native '
            'textAnimator typewriter with presetStart=0.3 and presetDuration=round(min(2.4,end*0.6),3). '
            'This engine preset is distinct from Canvas.keys; end does not lifetime-clip the root.',
        ),
    ),
}

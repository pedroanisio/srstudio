"""Measured Cel, optional signatures, call props and projected vehicle discovery."""

import inspect
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import Operation, PartContract
from .contracts import ParameterContract as P

PX = P(type=float, unit='drawing pixels', space='fixed-layout')
PARENT_PX = P(type=float, unit='parent pixels', space='parent')
LOCAL_PX = P(type=float, unit='drawing pixels', space='returned-group')
RATIO = P(unit='ratio')
ANGLE = P(unit='degrees')
TIME = P(unit='seconds', timebase='canvas')
LOCAL_TIME = P(unit='seconds', timebase='local')
LIFETIME = P(unit='seconds', timebase='parent-local')
COPY = P(role='display-copy')
PARENT = P(type=Composition | Group | Symbol, role='drawing-parent')
GROUP = P(type=Group, role='drawing-group', unit='drawing pixels', space='fixed-layout')
LOCAL_GROUP = replace(GROUP, space='returned-group', anchors=(('origin', (0, 0)),))
OPTIONAL_GROUP = replace(LOCAL_GROUP, type=Group | None)
CAMERA_KEYS = P(items=P(fields=(('time', LOCAL_TIME), ('scale', RATIO), ('tx', PX), ('ty', PX))))
PLACE = (('x', PARENT_PX), ('y', PARENT_PX), ('scale', RATIO))
CLOCK = (
    'Animation keys and gates follow Canvas.local_time: composition seconds by default, local seconds when enabled. '
    'Caller owns placement, containing lifetime and any larger motion.'
)
CEL_CLOCK = (
    'Cel camera animation is always local, independent of Canvas.local_time. Linear keys round values to five '
    'decimals and hold the final sample through duration. Use parse_camera for validated input records.'
)


def draw(*parameters: tuple[str, P], returns: P = LOCAL_GROUP, constraints: tuple[str, ...] = ()) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', PARENT), *parameters),
        returns=returns,
        capabilities=(('returns_scene_handle', True), ('spatial_attachment', False)),
        constraints=constraints,
    )


def contract(name: str, **helpers: Callable[..., Any]) -> PartContract:
    return replace(_CONTRACTS[name], operations=tuple(Operation(k, fn, _HELPERS[k]) for k, fn in helpers.items()))


_CONTRACTS = {
    'video-tile': draw(
        ('x', PARENT_PX),
        ('y', PARENT_PX),
        ('width', LOCAL_PX),
        ('height', LOCAL_PX),
        ('plate', COPY),
        (
            'inside',
            P(
                role='drawing-callback',
                space='returned-group',
                description='Called once with the returned '
                'group before its foreground frame. Return value is ignored; inherits parent transforms.',
            ),
        ),
        constraints=(
            'Static invented call tile. Finite x,y place the picture top-left; width and height must be positive '
            'and finite. Frame extends 34 pixels around the picture and 900 below it. inside receives the local '
            'group before the frame is drawn. The frame is not a clip: content beyond its covering rectangles '
            'may remain visible. The builder does not roll back mutations made by a failing callback.',
            'plate is empty or nonblank text of at most 18 characters; a nonempty plate requires the Canvas font '
            'before the callback runs. Nameplate width uses character count, not measured text fit. No caller '
            'content, meeting service or lifetime animation is installed.',
        ),
    ),
    'desk-phone': draw(
        *PLACE,
        ('title', COPY),
        ('lines', P(items=P(prefix_items=(LIFETIME, COPY)))),
        ('buzzes', P(items=P(prefix_items=(TIME, TIME)))),
        ('turns', TIME),
        constraints=(
            CLOCK,
            'Finite x,y place the center of the 470x900 phone; scale is positive and finite. The shadow extends '
            '14 pixels right and 22 down. Title is at most 12 characters; at most two nonblank lines of at most '
            '12 characters have finite nondecreasing start times >=0. Nonempty copy requires the Canvas font. '
            'Fixed 58-pixel text is not measured to fit.',
            'Line groups use parent-local start offsets and remain visible, independently of the Canvas key clock. '
            'Buzz spans require finite 0<=start<end. Body x alternates +/-7 every 0.04 seconds with linear keys, '
            'then returns to zero. turns>=0 foreshortens the back to zero over 0.11 seconds, then opens the front '
            'over another 0.11 seconds. This is flat horizontal scaling, not a 3D rotation or physical vibration.',
        ),
    ),
    'apron-spare': draw(
        *PLACE,
        constraints=(
            'Static apron with the neck-loop top at finite x,y and positive finite scale. Local artwork hangs '
            '330 pixels below the origin; ties extend to the sides. No font, attachment, cloth or contact solver.',
        ),
    ),
    'trial-tag': draw(
        *PLACE,
        ('label', COPY),
        constraints=(
            'Static 112x46 tag centered at finite x,y, rotated -2 degrees with positive finite scale. '
            'Requires the Canvas font before drawing. label.strip() must contain 1..6 characters, but the original '
            'untrimmed label is drawn at 30 pixels. No measured fit or attachment solver is supplied.',
        ),
    ),
    'signature-code': draw(
        ('x', PARENT_PX),
        ('y', PARENT_PX),
        ('height', LOCAL_PX),
        ('color', P(role='paint')),
        ('angle', ANGLE),
        ('opacity', RATIO),
        ('align', P(role='horizontal-alignment')),
        returns=OPTIONAL_GROUP,
        constraints=(
            'Static path lettering from Canvas.signature.code; returns None without mutation when unsigned. '
            'With a signature returns the whole code group. x,y anchor the top-left, or top-right for align=end; '
            'other align strings take start behavior. height scales a 16-unit glyph design; angle rotates it. '
            'No font is used. Unsupported glyphs raise SignatureError before drawing; color defaults to Canvas ink.',
        ),
    ),
    'signature-cactus': draw(
        *PLACE,
        (
            'act',
            P(
                fields=(
                    ('end', TIME),
                    ('turn', P(items=P(prefix_items=(TIME, ANGLE)))),
                    ('bloom', TIME),
                    ('code', P(role='pot-signature-code')),
                )
            ),
        ),
        returns=OPTIONAL_GROUP,
        constraints=(
            CLOCK,
            'Pot base is centered at x,y; artwork is 152 pixels tall at scale 1. MONO uses pen shapes, other '
            'palettes gradients. Without an act the cactus is static. Returns None when unsigned; an unsigned '
            'acting cactus raises SignatureError. Signature group IDs are generated per Canvas.',
            'Act.end is positive and finite. Turn keys rise strictly in [0,end), use sine-in-out easing and '
            'rotate the flower about (0,-140). bloom in [0,end) swaps the bud for petals, with linear scale '
            '0.2 -> 1.3 -> 1 at offsets 0,0.12,0.24. Petals gate until end; the pot/root does not. '
            'Act.code writes signature glyphs on the pot. This is authored flower motion, not biomechanics.',
        ),
    ),
    'show-bug': draw(
        ('number', P(minimum=1, role='release-number')),
        returns=GROUP,
        constraints=(
            'Static path artwork and number chip in fixed box (926,270,1044,332). number must be an integer >=1, '
            'not bool. Digit size shrinks to fit the chip; no font is used. Returns the whole group with '
            'ID show-bug-N. Direct calls inherit parent transforms and lifetime: use the composition for a '
            'stationary overlay. Build stamping places it above the camera; this builder adds no camera or gate.',
        ),
    ),
    'cel-lettering': draw(
        (
            'caption',
            P(
                fields=(
                    ('start', LIFETIME),
                    ('end', LIFETIME),
                    ('text', P(role='spoken-transcript')),
                    ('caption', P(role='caption-transcript')),
                    (
                        'boxes',
                        P(
                            items=P(
                                fields=(
                                    ('x', PX),
                                    ('y', PX),
                                    ('w', PX),
                                    ('h', PX),
                                    ('glyphs', P(role='traced-glyph-path')),
                                    ('fill', P(role='paint')),
                                )
                            )
                        ),
                    ),
                )
            ),
        ),
        returns=GROUP,
        constraints=(
            'A timed group of fixed-layout rectangles and white glyph paths, with parent-local start/end offsets. '
            'Box fill defaults to Canvas shade. No font is used and transcript text is not laid out or drawn: '
            'boxes already contain traced geometry. Use parse_captions to validate external records. '
            'No signature, new camera or motion keys are added.',
        ),
    ),
    'cel-room': PartContract(
        parameters=(
            ('cv', P(type=Canvas)),
            ('world_group', PARENT),
            ('keys', CAMERA_KEYS),
            ('room_keys', CAMERA_KEYS),
            ('duration', LOCAL_TIME),
            ('outline', PX),
            *((name, P(role='paint')) for name in ('wall', 'wood', 'desk', 'plank')),
        ),
        returns=GROUP,
        capabilities=(('returns_scene_handle', True), ('spatial_attachment', False)),
        constraints=(
            CEL_CLOCK,
            'Draw under the group returned by world using the same keys. World and room samples must be '
            'nonempty and share times; duration must reach the final sample. Compensation uses room.scale/world.scale '
            'and (room.translation-world.translation)/world.scale. This aligns measured sample times, but '
            'independently interpolated ratios do not guarantee exact compensation between samples.',
            'Fixed-layout wall, planks and desk extend outside the frame; outline is drawing pixels. '
            'wall defaults to Canvas background. The returned group owns all room geometry; characters and '
            'lettering are separate. This is a measured 2D camera transform, not a spatial room or contact solver.',
        ),
    ),
}

_HELPERS = {
    'text_width': PartContract(
        parameters=(('text', COPY), ('height', PX)),
        returns=P(type=float, unit='drawing pixels'),
        constraints=('Pure glyph advance formula; does not validate supported glyphs or text fit.',),
    ),
    'camera_tracks': PartContract(
        parameters=(('keys', CAMERA_KEYS), ('duration', LOCAL_TIME)),
        constraints=(CEL_CLOCK, 'Returns x,y,scaleX,scaleY tracks, without scene mutation.'),
    ),
    'compensate': PartContract(
        parameters=(('keys', CAMERA_KEYS), ('room_keys', CAMERA_KEYS), ('duration', LOCAL_TIME)),
        constraints=(
            CEL_CLOCK,
            'Returns compensated tracks without scene mutation. '
            'duration=None omits the final hold. Samples must share times.',
        ),
    ),
    'world': draw(('keys', CAMERA_KEYS), ('duration', LOCAL_TIME), returns=GROUP, constraints=(CEL_CLOCK,)),
}

WIRE_COMMON = {
    'at': P(prefix_items=(PARENT_PX, PARENT_PX)),
    'width': P(unit='pixels', minimum=200, maximum=2400),
    'height': P(unit='raster pixels'),
    'weight': RATIO,
    'seed': P(role='deterministic-seed'),
    'around': P(role='model-anchor-name'),
    'span': P(unit='metres'),
    'distance': P(unit='metres'),
    'rows': P(prefix_items=(LOCAL_PX, LOCAL_PX)),
    'tilt': P(unit='pixels per pixel'),
    'light': P(prefix_items=(P(unit='direction component', space='model-world'),) * 3),
    'sweep': ANGLE,
    'spin': P(unit='radians'),
    'wheels': P(enum=('all', 'body', 'front', 'rear')),
    'name': P(role='model-anchor-name'),
    'below': P(unit='metres'),
    'reach': P(unit='metres'),
}
WIRE_RULES = (
    'Static seeded hidden-line projection. at is the finite parent-space picture center; width is 200..2400 '
    'pixels and rounded for rasterization. weight is positive and scales line widths with a 0.8-pixel minimum. '
    'Returned group has local projected geometry: at most one unfilled path per ink. Transparent bodies '
    'do not occlude scene content; use a matching plate below strokes for filled surfaces.',
    'around names an anchor for a close-up and requires span and height: positive finite metres and a positive '
    'integer raster height. Without around, span and height must both be None. distance=None is '
    'orthographic; positive distance uses perspective. A supplied model-world direction towards light '
    'enables the matching cel raster. rows clips a band in pixels relative to the picture center; '
    'tilt is its y/x slope. Use identical projection arguments across strokes, anchors and plates.',
    'Projection is cached with at most 32 entries per vehicle module. Helpers provide projected points '
    'and pictures, not scene attachments, a contact solver or an animated camera. Caller owns motion and lifetime.',
)


def vehicle(
    name: str, *, views: tuple[str, ...], models: tuple[str, ...] = (), **helpers: Callable[..., Any]
) -> PartContract:
    specific = ('wheels', 'spin') if name == 'wire-car' else ('sweep',)
    names = (
        'at',
        'width',
        'height',
        'weight',
        'seed',
        'around',
        'span',
        'distance',
        'rows',
        'tilt',
        'light',
        *specific,
    )
    params = {k: WIRE_COMMON[k] for k in names}
    params.update(view=P(enum=views), palette=P(enum=('night', 'paper')))
    extras = (
        (
            'Car wheels selects all, body, front or rear; spin is a held wheel angle in radians, not angular velocity. '
            'Anchor and edge helpers use the complete unspun model and do not accept wheels/spin.',
        )
        if name == 'wire-car'
        else (
            'Jet model is a case-insensitive airframe name or auto. Bare seeds select the original three-family '
            'pool; auto uses all nine. sweep is accepted only for Switchblade, 20..62 degrees. '
            'Anchor availability depends on airframe; rear-pilot-head exists only on tandem designs.',
        )
    )
    operations = []
    for key, fn in helpers.items():
        candidates = {**WIRE_COMMON, 'view': P(enum=views), 'palette': P(enum=('night',))}
        parameters = tuple((k, candidates[k]) for k in inspect.signature(fn).parameters if k in candidates)
        if key == 'anchor':
            result = P(fields=(('x', PARENT_PX), ('y', PARENT_PX), ('scale', P(unit='pixels per metre'))))
            detail = 'Returns projected parent-space x,y and local pixels-per-metre. Caller transforms are not applied.'
        elif key == 'plate':
            result = P(
                fields=(
                    ('png', P(role='rgba-png-bytes')),
                    ('x', PARENT_PX),
                    ('y', PARENT_PX),
                    ('width', P(unit='pixels')),
                    ('height', P(unit='pixels')),
                )
            )
            detail = 'Returns PNG bytes, top-left x,y and pixel dimensions. Only night ramps exist; '
            detail += 'no scene asset is installed and no file is written.'
        else:
            result = P(type=tuple[float, float], prefix_items=(LOCAL_PX, P(unit='pixels per pixel')))
            detail = 'Requires light and sufficient paint samples below the anchor. Fits a paint boundary '
            detail += 'as (row,tilt) for band cuts; may raise the vehicle error if no reliable edge exists.'
        operations.append(
            Operation(
                key, fn, PartContract(parameters=parameters, returns=result, constraints=(*WIRE_RULES, *extras, detail))
            )
        )
    return replace(
        draw(*params.items(), constraints=(*WIRE_RULES, *extras)),
        operations=tuple(operations),
        vocabularies=(('models', ('auto', *models)),) if models else (),
    )

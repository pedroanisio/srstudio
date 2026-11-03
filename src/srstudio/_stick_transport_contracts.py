"""Authored Stick road and airport contracts: real drawing frames, clocks and ownership."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Annotated

from sr_core.scene import Group

from ._stick_drawing_contracts import END, FIXED, FONT, PIXEL, POINT, POSE, SCALE, TIME, draw, placed
from .contracts import ParameterContract as P
from .contracts import PartContract
from .stick import BROWS, EYES, MOUTHS, RigPose

SCROLL = P(fields=(('speed', P(unit='frame pixels per second', minimum=0)), ('offset', PIXEL)))
POSES = P(type=Mapping[str, Annotated[RigPose, POSE]])
LOOK = P(unit='ratio', minimum=-1, maximum=1)
KEY_BUDGET = P(unit='keys per track', minimum=2, maximum=20000, role='work-budget')
FACE = P(
    fields=(
        ('eyes', P(enum=EYES)),
        ('brows', P(enum=BROWS)),
        ('mouth', P(enum=MOUTHS)),
        ('look', P(prefix_items=(LOOK, LOOK))),
    )
)
KEYS = P(
    items=P(fields=(('start', TIME), ('pose', P(description='Key into the supplied poses mapping.')), ('face', FACE)))
)


def partial_handle(contract: PartContract, description: str) -> PartContract:
    assert contract.returns is not None
    return replace(contract, returns=replace(contract.returns, description=description, role='partial-drawing'))


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_RIDE = draw(
    ('end', END),
    ('amplitude', P(unit='frame pixels', minimum=0)),
    ('phase', P(unit='radians')),
    ('step', P(unit='seconds', role='sampling-interval')),
    ('max_keys', KEY_BUDGET),
    handle=False,
    constraints=(
        'Mutates the existing node y animation about its current y; does not draw or return a new node.',
        'end and step are finite and positive, amplitude is finite and nonnegative; zero amplitude emits no keys.',
        'Two deterministic sine waves use the sample index, so changing step changes their temporal frequency.',
        'Keys interpolate linearly; the last sample is ceil(end/step)*step and can follow end. No visibility gate.',
        'Over-budget, nonfinite or collapsed generated keys raise StickDataError before node mutation.',
        'phase offsets the first wave only; rebuilding from a later cut does not preserve the original '
        'phase automatically.',
    ),
)
_RIDE = replace(
    _RIDE,
    parameters=tuple(
        (
            'node',
            P(
                type=object,
                role='animation-target',
                description='Existing scene node with y and animation support. Its current y is the base.',
            ),
        )
        if name == 'parent'
        else (name, value)
        for name, value in _RIDE.parameters
    ),
)

_CONTRACTS = {
    'stick-car': draw(
        ('end', END),
        ('scroll', SCROLL),
        ('passing', P(items=P(unit='seconds', timebase='canvas', role='crossing-time'))),
        ('defocus', P(unit='frame pixels', minimum=0)),
        handle=False,
        constraints=(
            FIXED,
            'end>0 bounds generated scenery motion, not cabin visibility. passing times are within 0..end.',
            'Scroll speed drives six linear parallax layers. offset changes authored scenery placement; '
            'it is not a source-time offset.',
            'A passing car crosses the frame center at its cue, clipped to the shot interval; no physical '
            'road trajectory.',
            'Scenery also receives index-sampled suspension motion. Use an outer parent to hide the complete cabin.',
            'defocus applies a blur radius to the country behind the glass. No scene camera or spatial '
            'mesh is returned.',
        ),
    ),
    'stick-cockpit': draw(
        ('keys', KEYS),
        ('end', END),
        ('poses', POSES),
        ('scroll', SCROLL),
        handle=False,
        constraints=(
            FIXED,
            'Use the same validated RigKey performance and pose coordinates as the driver; check_keys '
            'runs before drawing.',
            'Pose-specific seatbelts are held; a belt spanning the whole shot omits its opacity gate.',
            'scroll controls moving tree-shadow drawings. The wheel, panels and sun are fixed; no shared '
            'physical light rig.',
            'No root group is returned; caller-owned parents control placement and complete visibility.',
        ),
    ),
    'stick-ride': _RIDE,
    'stick-car-seat': draw(
        handle=False,
        constraints=(FIXED, 'Foreground passenger seat excludes the driver and props; cushion top is CUSHION=1290.'),
    ),
    'stick-laptop': placed(
        ('scale', SCALE),
        local=True,
        constraints=(
            FONT,
            'Origin is the base left reference. Nonblank title and 1..4 nonblank rows; badge is optional.',
            'Text uses fixed local boxes with ellipsis; scaling the group also scales its typography.',
        ),
    ),
    'stick-phone': partial_handle(
        draw(
            ('at', POINT),
            ('buzz', P(items=TIME)),
            local=True,
            constraints=(
                FONT,
                'at is the phone top-left. sender and text are nonblank; text uses fixed boxes with ellipsis.',
                'Ordered nonnegative buzz cues create 0.25-second linear x shakes and 0.35-second opacity-gated marks.',
                'The mount and buzz marks are siblings of the returned case; wrap the whole call to move '
                'or hide everything.',
            ),
        ),
        'Only the phone case group, positioned at at; excludes the mount and buzz-mark sibling groups.',
    ),
    'stick-windshield': draw(
        ('end', END),
        ('speed', P(unit='dashes per second', minimum=0)),
        ('ground', P(enum=('road', 'field'))),
        ('max_keys', KEY_BUDGET),
        handle=False,
        constraints=(
            FIXED,
            'speed=0 parks the road. Positive speed shrinks road dashes and poles about the vanishing '
            'point, then resets.',
            'ground="field" draws two wheel tracks in the grass instead of the road and refuses a nonzero speed.',
            'This is an authored 2D perspective effect, not camera motion. end bounds generated cycles, '
            'not scene visibility.',
            'The final full cycle can end after end; each reset gap is min(0.001 seconds, half a cycle).',
            'Over-budget, nonfinite or collapsed generated keys raise StickDataError before drawing.',
        ),
    ),
    'stick-windshield-dash': draw(
        ('end', P(unit='seconds', timebase='canvas', role='validation-limit')),
        ('buzz', P(items=TIME)),
        ('down', TIME),
        ('code', P(prefix_items=(PIXEL, PIXEL, PIXEL, P(description='Signature color.')))),
        ('cactus', SCALE),
        handle=False,
        constraints=(
            FIXED,
            'end>0 validates cues, not visibility. buzz cues are ordered in [0,end); optional down lies '
            'strictly inside (0,end).',
            'All buzz cues precede down. Shakes and marks can extend past their cue and past down/end; an '
            'outer parent clips them.',
            'down switches between separate mounted and face-down drawings with held opacity; it is not '
            'an interpolated handoff.',
            'code is (x,y,height,color) for the signature on the hood; cactus scales the dashboard cactus. '
            'Both sizes are positive. No scene handle is returned.',
        ),
    ),
    'stick-gate': draw(
        ('boarding_size', P(unit='frame pixels', description='Positive first-line font size.')),
        ('cactus_at', POINT),
        handle=False,
        constraints=(
            FIXED,
            FONT,
            'gate is nonblank with at most four characters; now is nonblank with at most twelve characters.',
            'sign=False omits the sign face, but even then the builder requires a font and validates both strings.',
            'cactus_at must be a finite tuple of two coordinates; it places the signature pot base.',
        ),
    ),
    'stick-gate-podium': draw(
        constraints=(
            FIXED,
            'gate is nonblank with at most four characters. plate=False omits its lettering and requires no font.',
            'Foreground podium covers the agent legs; its returned group owns all podium drawing.',
        )
    ),
    'stick-carry-on': placed(
        constraints=(
            'x/y is the suitcase standing reference; geometry is baked in parent coordinates.',
            'tag=None leaves a blank tag and requires no font. Otherwise the tag is nonblank, at most '
            'eight characters, and requires a font.',
            'hanging=True requires tag=None and changes the blank tag geometry; it does not animate a swing.',
        )
    ),
    'stick-bag-scale': placed(
        ('end', P(type=float, unit='seconds', timebase='canvas', role='end')),
        (
            'readings',
            P(
                type=Sequence[tuple[float, str | None]],
                items=P(
                    prefix_items=(
                        TIME,
                        P(description='Displayed weight text or None for dark; no physical units are inferred.'),
                    )
                ),
            ),
        ),
        ('readout', P(prefix_items=(PIXEL, PIXEL, PIXEL, PIXEL))),
        constraints=(
            FONT,
            'x/y is the platter standing reference. readout is an independent parent-coordinate '
            '(x,y,width,height) box.',
            'Nonempty readings begin at zero, strictly rise, and finish before end. Text is nonblank with '
            'at most five characters.',
            'Readout text is held with canvas opacity gates until its successor or end; None leaves the display dark.',
            'The platter and readout housing remain visible after end. No weighing simulation or numeric '
            'weight conversion.',
        ),
    ),
    'stick-coat-ball': draw(
        ('x', PIXEL),
        ('chin', PIXEL),
        ('radius', P(type=float, unit='frame pixels', minimum=100)),
        ('layers', P(type=int, minimum=1, maximum=4)),
        ('hats', P(type=int, minimum=0, maximum=4)),
        ('scarves', P(type=int, minimum=0, maximum=3)),
        ('trousers', P(type=bool)),
        ('shoes', P(type=bool)),
        constraints=(
            'Draw after the STANDING figure: x is its center, chin its chin y. Geometry is baked in '
            'parent coordinates.',
            'Optional trousers extend to the fixed FLOOR_FEET line; callers must choose geometry that '
            'leaves positive leg height.',
            'Hats, scarves and layers select fixed artwork, not cloth simulation or body constraints.',
        ),
    ),
    'stick-palm': placed(
        ('height', P(type=float, unit='frame pixels', minimum=120)),
        constraints=(
            'x/y is the trunk base; height sets its rise and scales frond geometry. Coordinates are '
            'baked, with no local placement transform.',
        ),
    ),
    'stick-cabin': draw(
        handle=False,
        constraints=(
            FIXED,
            FONT,
            'row is nonblank with at most three characters; seats is exactly three non-whitespace characters.',
            'Returns no handle. Draw passengers after seat backs and armrests after passengers for the '
            'authored occlusion.',
        ),
    ),
    'stick-armrests': draw(
        constraints=(FIXED, 'Front-layer armrests at the fixed cabin seat boundaries; no elbow attachment solver.')
    ),
    'stick-home-street': draw(
        ('tree', SCALE),
        handle=False,
        constraints=(
            FIXED,
            'tree scales a static tree about its base at (180,1240); it does not animate growth. Use '
            'separate window content and frame helpers.',
        ),
    ),
    'stick-side-car': draw(
        local=True,
        constraints=(
            'Origin is the side-view rear reference, nose right. Tire circles extend eight local pixels '
            'below y=0; no ground-contact guarantee.',
            'Includes static roof luggage; animate the returned group to drive. No wheel rotation is generated.',
        ),
    ),
    'stick-suitcases': placed(
        constraints=('x/y is the common base reference; both suitcases and pillow are baked into parent coordinates.',)
    ),
    'stick-road-plan': draw(
        ('scars', P(minimum=0, maximum=8)),
        handle=False,
        constraints=(FIXED, 'scars is an integer count of static skid-mark drawings; no driving simulation.'),
    ),
    'stick-top-car': draw(
        local=True, constraints=('Static overhead car centered at the origin with nose upward; includes roof luggage.',)
    ),
    'stick-stove-knob': draw(constraints=(FIXED, FONT, 'Full-frame static OFF knob; returns the whole insert group.')),
    'stick-door-lock': draw(
        constraints=(FIXED, FONT, 'Full-frame static locked-door insert; returns the whole insert group.')
    ),
    'stick-road-ahead': draw(
        handle=False,
        constraints=(FIXED, 'Static driver-view road perspective and signature marks; no scrolling or scene handle.'),
    ),
    'stick-road-sign': draw(
        ('end', END),
        local=True,
        constraints=(
            FONT,
            'Nonblank text. Root is placed at (540,930); scale grows linearly from 0.7 at zero to 1.15 at '
            'end>0, then holds.',
            'end does not hide the sign. Perspective approach is a scale animation, not a camera or physical distance.',
        ),
    ),
    'stick-rear-view': partial_handle(
        draw(
            (
                'figure',
                P(
                    type=Callable[[Group], object] | None,
                    role='drawing-slot',
                    description='Called once with the masked glass group in parent coordinates; '
                    'callback return is ignored. None draws empty glass.',
                ),
            ),
            constraints=(
                FIXED,
                'Callback runs between the glass fill and the outer glare. No translation to the mirror '
                'origin or automatic scaling is applied.',
                'Housing, background and glare are outside the returned glass; use an outer parent for '
                'the whole insert.',
            ),
        ),
        'The masked glass group only, in parent coordinates; excludes mirror housing, background and glare.',
    ),
    'stick-swim-ring': placed(
        ('rx', P(unit='frame pixels', minimum=30)),
        ('ry', P(unit='frame pixels', minimum=30)),
        local=True,
        constraints=(
            'Origin is the ring center. Radii are finite, at least 30, and their ratio cannot exceed '
            'three; band is #rrggbb.',
            'Radii describe the tube centerline; stroke thickness makes the complete ring larger. No '
            'physical collision geometry.',
        ),
    ),
    'stick-blinker': placed(
        ('end', END),
        ('clicks', P(items=TIME)),
        ('scale', SCALE),
        local=True,
        constraints=(
            'x/y is the arrow center. Strictly rising finite click times lie in [0,end); end and scale are positive.',
            'Each click lights the arrow for min(0.26,end-click) seconds; dark artwork remains outside '
            'those gates. No audio is emitted.',
        ),
    ),
}

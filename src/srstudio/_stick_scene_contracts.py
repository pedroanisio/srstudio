"""Authored Stick scene and prop semantics: clocks, placement and complete versus partial handles."""

from dataclasses import replace

from sr_core.scene import Group, Shape

from ._stick_drawing_contracts import END, FIXED, FONT, PIXEL, SCALE, TIME, draw, placed
from .contracts import ParameterContract as P
from .contracts import PartContract

SECOND = P(unit='seconds', timebase='canvas')
NIGHT = P(items=P(prefix_items=(TIME, P(unit='ratio', minimum=0, maximum=1))))
SPANS = P(items=P(prefix_items=(TIME, TIME)))
LIFT = P(items=P(prefix_items=(SECOND, P(unit='frame pixels', role='vertical-displacement'))))
SLIDE = P(items=P(prefix_items=(SECOND, P(unit='frame pixels', space='parent', role='absolute-x'))))
SCREENS = P(items=P(fields=(('start', TIME), ('tone', P(enum=('idle', 'error', 'help', 'award'))))))


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'stick-entrance': draw(
        ('end', END),
        ('night', NIGHT),
        ('clock', P(unit='turns per second')),
        handle=False,
        constraints=(
            FIXED,
            'night starts at zero, increases in time through end and linearly keys darkness.',
            'clock rotates the long hand; the short hand turns at one twelfth that rate. Zero holds both.',
            'Draw the separate glass door over this background; no doorway or clock handle is returned.',
        ),
    ),
    'stick-street-lens': draw(
        ('end', END),
        ('night', NIGHT),
        handle=False,
        constraints=(
            FIXED,
            'night starts at zero and keys linear darkness through end. The distant buildings '
            'have a fixed blur; this is drawn perspective, not a spatial lens model.',
        ),
    ),
    'stick-glass-door': draw(
        ('end', END),
        ('shut', TIME),
        handle=False,
        constraints=(
            FIXED,
            'closed and shut are mutually exclusive. None holds the open or closed drawing.',
            'A positive shut inside end starts three held intermediate drawings at 1/24-second '
            'intervals, then the closed drawing. No interpolation, collision or hinge solver.',
        ),
    ),
    'stick-snow-cap': replace(
        placed(
            ('step', P(enum=(1, 2, 3))),
            ('width', PIXEL),
            constraints=(
                'x,y is the base center. step chooses one of three heap sizes; no animation.',
                'Placement is baked into the path, not a translated group.',
            ),
        ),
        returns=P(type=Shape, unit='frame pixels', space='parent', role='path-layer'),
    ),
    'stick-marathon': draw(
        ('end', END),
        ('count', P(unit='runners', minimum=1)),
        ('base', PIXEL),
        ('size', PIXEL),
        local=True,
        constraints=(
            FIXED,
            'Returns the moving pack group. base is the drawn foot y and size the runner height.',
            'Pack x moves linearly right to left through end; two stride drawings alternate at '
            '8 drawings per second. No physical gait, depth or contact solver.',
        ),
    ),
    'stick-studio-flat': draw(
        handle=False,
        constraints=(
            'Fixed 2100-pixel-wide set, with floor extending to y=2400. marks controls '
            'signature marks. Draw the separate Murphy bed over its cabinet frame.',
        ),
    ),
    'stick-murphy-bed': draw(
        ('end', END),
        ('drop_at', TIME),
        ('talk', SPANS),
        constraints=(
            'Fixed studio-flat cabinet coordinates; returns the complete bed group.',
            'drop_at=None holds closed; zero holds open; a positive time holds one folding drawing '
            'for 0.125 seconds before opening. This is a drawn substitution, not a hinge trajectory.',
            'talk spans must be ordered, non-overlapping and inside the open part of the shot; '
            'talk requires sleeper. Mouth opens during each span; there is no phoneme timing.',
        ),
    ),
    'stick-gym': draw(
        ('end', P(unit='seconds', timebase='canvas', role='validation-limit')),
        ('sunrise', TIME),
        handle=False,
        constraints=(
            FIXED,
            FONT,
            'sunrise=None holds night; zero holds day. Positive sunrise fades dawn and '
            'raises the sun linearly over 1.5 seconds; the fade may finish after end.',
            'Draw the separate counter after the staff so it hides their legs.',
        ),
    ),
    'stick-gym-counter': draw(
        constraints=(
            FIXED,
            FONT,
            'sign is nonblank and at most 18 characters; fine is at most 60. '
            'Returns the complete foreground desk, reader, sign and cactus group.',
        )
    ),
    'stick-classroom': draw(
        handle=False,
        constraints=(
            FIXED,
            FONT,
            'board is nonblank and at most 22 characters; the separate chair and teacher desk are not drawn.',
        ),
    ),
    'stick-tiny-chair': draw(constraints=(FIXED, 'Fixed chair at the left; seat y=1500. Draw before its sitter.')),
    'stick-teacher-desk': draw(
        constraints=(
            FIXED,
            'Fixed desk at the right with papers, apple and cactus. Draw after the teacher '
            'to hide her legs; this is painter ordering, not physical occlusion.',
        )
    ),
    'stick-essay': draw(
        ('shown', P(unit='lines', minimum=0, maximum=6)),
        ('mark', P(unit='line index', minimum=0)),
        ('mark_at', TIME),
        ('note_at', TIME),
        ('at', P(prefix_items=(PIXEL, PIXEL), space='parent', role='sheet-center')),
        ('scale', P(unit='ratio')),
        local=True,
        constraints=(
            FONT,
            'The sheet center (540,890) is the group anchor; at places that center, '
            'not the local origin. None leaves the sheet centered at its authored position.',
            'Provide 1..6 nonblank lines of at most 48 characters; shown selects the first lines. '
            'mark indexes an already shown line. The highlighter expands linearly over 0.4 seconds.',
            'grade has 1..3 stripped characters; note has 1..24. A positive note_at fades its '
            'opacity over 0.01 seconds, zero shows it immediately.',
        ),
    ),
    'stick-checkout': draw(handle=False, constraints=(FIXED, FONT, 'Draw the separate kiosk over this background.')),
    'stick-kiosk': draw(
        ('screens', SCREENS),
        ('end', END),
        ('alarm', P(items=TIME)),
        constraints=(
            FIXED,
            FONT,
            'screens starts at zero, is strictly time ordered and ends before end; '
            'each screen holds to the next start or end. Text is nonblank and at most 60 characters.',
            'An award screen can show a Look face. alarm times are unique and increasing inside '
            'the shot; each emits three 0.25-second lamp flashes clipped at end.',
        ),
    ),
    'stick-avocado': placed(
        ('scale', SCALE),
        local=True,
        constraints=('x,y places the base center; drawing is about 100 pixels tall at scale 1.',),
    ),
    'stick-name-badge': placed(
        local=True, constraints=(FONT, 'x,y places the top left; name and title must be nonblank.')
    ),
    'stick-duvet': replace(
        draw(
            ('end', END),
            ('x', PIXEL),
            ('y', PIXEL),
            ('near', PIXEL),
            ('width', PIXEL),
            ('lift', LIFT),
            constraints=(
                'x centers the duvet, y is its top edge, near the lower edge; width>0 and near>y.',
                'lift keys only the mound vertical offset, with linear interpolation. The fixed '
                'cover and folds are siblings outside the returned mound.',
                'Draw a prop into the returned group using authored parent coordinates to move it '
                'with the mound. This does not compute cloth deformation or contact.',
            ),
        ),
        returns=P(
            type=Group,
            unit='frame pixels',
            space='parent',
            role='partial-drawing',
            description='Only the moving mound; excludes the cover and fold siblings.',
        ),
    ),
    'stick-eye-mask': placed(
        ('scale', SCALE), local=True, constraints=('x,y places the head center; scale sizes the mask about it.',)
    ),
    'stick-recorder': placed(
        ('end', END),
        ('lines', P(unit='traces', minimum=0, maximum=3)),
        constraints=(
            'x,y is the case center, baked into the drawing. live alternates the final trace with '
            'a straight line at 6 drawings per second; it does not animate when lines=0.',
        ),
    ),
    'stick-lights-low': draw(
        ('area', P(prefix_items=(PIXEL, PIXEL, PIXEL, PIXEL), space='parent', role='rectangle')),
        ('tint', P(description='Six-digit #rrggbb color.')),
        ('strength', P(unit='ratio', minimum=0, maximum=1)),
        ('pool', P(prefix_items=(PIXEL, PIXEL, PIXEL), space='parent', role='light-pool')),
        constraints=(
            'area is x,y,width,height with positive dimensions. pool is x,y,radius with positive radius.',
            'strength is strictly positive through one. Uses a multiply overlay and optional radial '
            'gradient, not a scene light, shadow receiver or physical illumination.',
        ),
    ),
    'stick-clipboard': draw(
        constraints=(
            'The origin is the holding hand. turned and quarter are mutually exclusive views.',
            'Only turned=True requires a font and a nonblank heading of at most 16 characters; '
            'edge and quarter views use paths only. No automatic hand attachment.',
        )
    ),
    'stick-wall-brackets': placed(
        ('span', PIXEL),
        ('scale', SCALE),
        local=True,
        constraints=('x,y is the first bracket top; span>0 is the second bracket offset before group scaling.',),
    ),
    'stick-folded-bedding': placed(
        ('scale', SCALE),
        ('slide', SLIDE),
        local=True,
        constraints=(
            'x,y places the stack foot center. With slide, x is ignored: absolute parent x values '
            'replace it, starting at the first key. slide is empty or has at least two increasing times.',
            'Uses cubic-out interpolation per segment. No table contact, balance or collision solver.',
        ),
    ),
}

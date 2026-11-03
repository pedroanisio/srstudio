"""Authored Host and Mind semantics: measurement callbacks, clock ownership and return types."""

from collections.abc import Callable
from typing import Literal

from sr_core.scene import CaptionTrack, Composition, Group, Symbol

from .canvas import Canvas
from .contracts import ParameterContract as P
from .contracts import PartContract

PIXEL = P(unit='frame pixels')
POINT = P(prefix_items=(PIXEL, PIXEL), space='parent')
RATIO = P(unit='ratio')
PARENT = P(unit='seconds', timebase='parent')
COMP = P(unit='seconds', timebase='composition')
TIME = P(unit='seconds', timebase='canvas')
DURATION = P(unit='seconds', role='duration')
ID = P(role='scene-id', description='Caller-unique ID; some builders derive child IDs from it.')
MEASURE = P(
    type=Callable[[str, float], float],
    role='text-measure',
    description='Called with (text, font_size_in_frame_pixels); return advance width in frame '
    'pixels in the actual font. '
    'May be called repeatedly at several sizes while fitting. Does not draw.',
)
FONT = 'Text needs the bound Canvas font asset. Supply measure for that same font and size.'
LAYOUT = (
    'Fixed frame-pixel layout for 1080x1920; no Toon reference-coordinate conversion or automatic safe-area fitting.'
)
GROUP = P(type=Group, unit='frame pixels', space='parent', role='drawing-group')
NONE = P(type=type(None))
LINE = P(fields=(('start', PARENT), ('end', PARENT)))
LINES = P(items=LINE)
ABS_X = P(items=P(prefix_items=(COMP, P(unit='frame pixels', space='parent', role='absolute-x'))))
INDEX = P(unit='file index', minimum=0)
PULL = P(prefix_items=(INDEX, COMP))
BAR = P(prefix_items=(P(), P(unit='ratio', minimum=0, maximum=1), P()))
CLOCKS = {
    'composition': 'Animation keys use the composition clock even with Canvas.local_time=True. Visibility '
    'start/end attributes use the parent timeline; align these clocks when nesting shots.',
    'canvas': 'Animation keys follow Canvas.local_time: composition by default, local when enabled. Visibility '
    'start/end attributes still use the parent timeline; the same numeric start can drive both.',
    'static': 'Visibility start/end attributes use the parent timeline; ordinary group starts do not shift it.',
}


def draw(
    *parameters: tuple[str, P],
    returns: P = NONE,
    clock: Literal['composition', 'canvas', 'static'] = 'static',
    constraints: tuple[str, ...] = (),
) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', P(type=Composition | Group | Symbol)), *parameters),
        returns=returns,
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', returns.type is Group)),
        constraints=(LAYOUT, CLOCKS[clock], *constraints),
    )


def timed(
    *parameters: tuple[str, P],
    returns: P = NONE,
    clock: Literal['composition', 'canvas', 'static'] = 'static',
    constraints: tuple[str, ...] = (),
) -> PartContract:
    return draw(('start', PARENT), ('end', PARENT), *parameters, returns=returns, clock=clock, constraints=constraints)


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'host-wardrobe': draw(
        ('end', P(unit='seconds', timebase='composition', role='motion-limit')),
        clock='composition',
        constraints=(
            'Background fills past the canvas; dust moves linearly through '
            'max(end,12) seconds. end does not gate visibility. No text or returned handle.',
        ),
    ),
    'host-phone': draw(
        constraints=(
            'Despite the registry name, draws the foreground shelf and its resting phone. '
            'No returned handle; use a caller-owned parent to move both.',
        )
    ),
    'host-punch': PartContract(
        parameters=(
            ('cv', P(type=Canvas)),
            ('group', P(type=Group, role='animation-target')),
            ('who', P(enum=('lint', 'close', 'tight'))),
            ('was', P(enum=('lint', 'close', 'tight'))),
            ('at', TIME),
            ('push', P(prefix_items=(DURATION, RATIO))),
        ),
        returns=NONE,
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', False)),
        constraints=(
            CLOCKS['canvas'],
            'Mutates the supplied group; creates no scene group. Anchors and places '
            'the pivot at x=540 and the authored face pivot y. lint/close/tight scales are 1,1.25,1.5.',
            'push is (duration,target_scale) and keys linear scale from at to at+duration. Without push, '
            'changed framing uses held scale keys; unchanged framing sets a static scale.',
        ),
    ),
    'smallprint-card': timed(
        ('question', P(role='display-copy', description='The question in the words people type; checked as copy.')),
        ('measure', MEASURE),
        ('id', ID),
        returns=GROUP,
        clock='composition',
        constraints=(
            FONT,
            'At most two lines, fitted from size 44 down to 32 in steps of two; a word wider than the card or a '
            'question still over two lines fails. Requires start < end.',
            'The card drops y=-12 to zero over 0.18 seconds with cubic-out composition keys. Returns its group.',
        ),
    ),
    'smallprint-stamp': timed(
        ('finding', P(role='display-copy', description='A Stamp: the finding in capitals and its named source.')),
        ('measure', MEASURE),
        returns=GROUP,
        clock='composition',
        constraints=(
            FONT,
            'The stamp fits from size 58 down to 36 across the safe area, turned -4 degrees; it fails if still too '
            'wide. Requires start < end.',
            'It pops in at start and fades in over 0.06 seconds on the composition clock. The source, at most two '
            'lines, is a sibling group under parent from start+0.2, not inside the returned stamp group.',
        ),
    ),
    'host-label': timed(
        ('measure', MEASURE),
        ('id', ID),
        clock='composition',
        constraints=(
            FONT,
            'At most seven words, fitted down to size 30 in steps of two; fails if still too wide. '
            'The label moves y=-14 to zero over 0.16 seconds with cubic-out interpolation. Returns None.',
        ),
    ),
    'host-sign-off': timed(
        ('measure', MEASURE),
        ('id', ID),
        returns=GROUP,
        constraints=(
            FONT,
            'Complete closing label with show name and phrase; size is reduced toward 50 to fit the authored width.',
        ),
    ),
    'host-screen': timed(
        ('measure', MEASURE),
        ('id', ID),
        ('bubbles', P(items=P(fields=(('at', PARENT), ('status_at', PARENT))))),
        constraints=(
            FONT,
            'A static full-frame chat UI. Message arrival is max(bubble.at,start); status begins at '
            'max(status_at,arrival). Messages hold to end and stack vertically in supplied order.',
            'Messages must wrap into at most four lines. Text is supplied copy, not a live chat connection.',
        ),
    ),
    'host-captions': PartContract(
        parameters=(
            (
                'ep',
                P(
                    type=object,
                    role='episode-context',
                    description='Episode-compatible runtime object '
                    'with cv, comp, spec.safe_area/width/height and native_captions(cues,look=,id=) '
                    'returning CaptionTrack. '
                    'A non-None safe_area is required.',
                ),
            ),
            ('lines', P(items=P(fields=(('start', COMP), ('end', COMP))))),
            ('measure', MEASURE),
            ('words', P(items=P(prefix_items=(COMP, COMP, P())))),
            ('skip', P(description='Speaker names whose caption cues are omitted.')),
        ),
        returns=P(
            type=tuple[Group, CaptionTrack],
            prefix_items=(
                P(
                    role='caption-bands',
                    unit='frame pixels',
                    space='parent',
                    description='Background bands group in the episode composition.',
                ),
                P(
                    role='caption-track',
                    timebase='composition',
                    description='Native karaoke caption track returned by the episode.',
                ),
            ),
        ),
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', True)),
        constraints=(
            'Creates bands on the episode composition and delegates to its native_captions method.',
            'Cue times are composition seconds, not durations. words are (start,end,text) tuples. '
            'The engine owns karaoke timing; the returned pair must be unpacked.',
            'Uses fixed IDs host-caption-bands and host-captions. Measure actual episode font widths; '
            'band layout uses the episode safe-area dimensions.',
        ),
    ),
    'mind-stage': draw(constraints=('Fills the actual canvas with dark ink and a fixed normalized radial glow.',)),
    'mind-stamp': timed(
        ('measure', MEASURE),
        ('y', PIXEL),
        returns=GROUP,
        clock='canvas',
        constraints=(
            FONT,
            'rows and cite are supplied copy fitted to the safe width. y is the top; the returned group '
            'tilts -2.5 degrees about its center and scales 1.25 to 1 over 0.12 seconds.',
        ),
    ),
    'mind-zipper': timed(
        returns=GROUP,
        clock='canvas',
        constraints=(
            'A flat overlay, visible before start and removed at end+0.45 on the parent timeline. '
            'Rows part with cubic-in keys over 0.45 seconds; the pull moves linearly from start to end.',
            'Fits canvas dimensions. This is an authored reveal, not simulated cloth.',
        ),
    ),
    'mind-named': timed(
        ('measure', MEASURE),
        ('scale', P(unit='ratio', minimum=1)),
        ('pivot', POINT),
        returns=GROUP,
        constraints=(
            FONT,
            'Precompensates drawing position and size for an external punch '
            'of scale>=1 about pivot; does not itself apply that punch or scale its returned group.',
        ),
    ),
    'mind-name-card': timed(
        ('reveal', PARENT),
        ('measure', MEASURE),
        ('id', ID),
        clock='composition',
        constraints=(
            FONT,
            '0<=start<reveal<end and end-reveal>=1. Name fits at most three lines. '
            'Visibility uses parent time; the same numeric reveal drives a composition-clock cubic-out '
            'disc scale from 0.7 to 1 over 0.18 seconds. Returns None.',
        ),
    ),
    'mind-evidence-card': timed(
        ('reveal', PARENT),
        ('measure', MEASURE),
        ('id', ID),
        constraints=(
            FONT,
            'evidence contains supplied who, four-digit year, what and result. '
            'No citation lookup or verification is performed. what has at most 12 words, result at most 10.',
            'Holds for at least two seconds. reveal=None shows all; an interior reveal grows the paper '
            'by a held drawing swap while introducing the result. Text does not move.',
        ),
    ),
    'mind-spotlight': timed(
        ('foot', POINT),
        ('radius', PIXEL),
        ('sweep', ABS_X),
        ('id', ID),
        clock='composition',
        constraints=(
            'Flat cone and ellipse; no scene light or illumination calculation. '
            'foot places the ellipse center; radius>0. sweep replaces x with absolute parent positions '
            'using sine-in-out interpolation. The authored top does not remain pinned during a sweep.',
        ),
    ),
    'mind-memory-shelf': draw(
        ('measure', MEASURE),
        ('pull', PULL),
        ('also', P(items=PULL)),
        ('y', PIXEL),
        ('id', ID),
        clock='composition',
        constraints=(
            FONT,
            'One to four labels. pull/also contain (zero-based file index,composition second), each file once. '
            'y is the shelf top; selected files move up 110 pixels over 0.25 seconds with cubic-out keys.',
        ),
    ),
    'mind-two-lines': timed(
        ('expected', BAR),
        ('actual', BAR),
        ('reveal', PARENT),
        ('y', PIXEL),
        ('measure', MEASURE),
        ('id', ID),
        clock='composition',
        constraints=(
            FONT,
            'Rows are (label,value,note) with 0<value<=1; actual uses reveal or start. '
            'The same numeric time controls parent visibility and composition-clock cubic-out growth '
            'from scale 0.02 to 1 over 0.45 seconds. Values are supplied data, not verified claims.',
        ),
    ),
    'mind-lens': timed(
        ('at', POINT),
        ('radius', PIXEL),
        ('path', ABS_X),
        ('id', ID),
        clock='composition',
        constraints=(
            'at is the lens center; radius>0 and tint is #rrggbb. '
            'path replaces x with absolute parent positions using sine-in-out keys. '
            'Drawn tinted glass and handle, rotated -35 degrees; no magnification or optical solver.',
        ),
    ),
    'mind-captions': draw(
        ('lines', LINES),
        ('measure', MEASURE),
        ('id', ID),
        returns=GROUP,
        constraints=(
            FONT,
            'One group per cue, at most two wrapped lines. tints maps speaker names to fills; '
            'ink fill gets paper letters, any other fill gets ink letters. Returns the complete caption group.',
        ),
    ),
}

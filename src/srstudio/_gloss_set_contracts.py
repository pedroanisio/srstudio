"""Gloss scenery contracts: fixed layout, Canvas keys, measured cards and distinct return ownership."""

from collections.abc import Callable
from dataclasses import replace
from typing import Any

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import Operation, PartContract
from .contracts import ParameterContract as P
from .gloss import VISEMES

TIME = P(unit='seconds', timebase='canvas')
END = replace(TIME, role='end')
PIXELS = P(unit='drawing pixels', space='fixed-layout')
PARENT = P(unit='parent pixels', space='parent')
AT = P(prefix_items=(PARENT, PARENT))
COPY = P(role='display-copy')
FONT = P(role='font-bytes')
GROUP = P(type=Group, unit='drawing pixels', space='fixed-layout', role='drawing-group')
LOCAL_GROUP = replace(GROUP, space='returned-group', anchors=(('origin', (0, 0)),))
TALK = P(items=P(prefix_items=(TIME, P(enum=VISEMES))))
CLOCK = (
    'Keyframes and opacity gates follow Canvas.local_time: composition seconds by default, '
    'shot-local seconds when enabled. end must be finite and positive. '
    'It bounds authored cues, not a universal lifetime clip; gate the caller parent when needed.'
)
TEXT = (
    'Requires a bound Canvas font and font bytes for measurement; bind the same face as those bytes. '
    'Copy is measured before drawing. Wrapping preserves literal words and newlines, '
    'and raises GlossError instead of shrinking text to fit.'
)
ROOM = (
    'Fixed 1080x1920 scenery, with cast floor y=1270 and signature artwork; code depends on Canvas.signature. '
    'Returns None after adding a root group under parent. Supply a caller-owned group to move or gate the whole room. '
    'Actors, props and shot grading are separate calls; no callbacks, camera or physical lighting are installed.'
)
WRAP = PartContract(
    parameters=(
        ('font', FONT),
        ('text', COPY),
        ('size', P(unit='drawing pixels')),
        ('width', P(unit='drawing pixels')),
        ('max_lines', P(role='maximum-line-count')),
    ),
    returns=P(type=list[str], items=COPY, role='wrapped-lines'),
    constraints=(
        'Measures the supplied font bytes and returns lines without scene mutation. '
        'A word wider than width or more than max_lines raises GlossError. '
        'keep_together optionally preserves phrase boundaries when a fitting alternative exists; '
        'explicit newlines retain the authored split.',
    ),
)


def draw(
    *parameters: tuple[str, P], returns: P = GROUP, handle: bool = True, constraints: tuple[str, ...] = ()
) -> PartContract:
    return PartContract(
        parameters=(
            ('cv', P(type=Canvas)),
            ('parent', P(type=Composition | Group | Symbol)),
            ('end', END),
            *parameters,
        ),
        returns=returns,
        capabilities=(('returns_scene_handle', handle), ('spatial_attachment', False)),
        constraints=(CLOCK, 'Draws 2D geometry; no spatial grip, support or body solver is supplied.', *constraints),
    )


def room(*parameters: tuple[str, P], constraints: tuple[str, ...]) -> PartContract:
    return draw(
        *parameters, returns=P(type=type(None), role='parent-mutation'), handle=False, constraints=(ROOM, *constraints)
    )


def contract(name: str, *, wrap: Callable[..., Any] | None = None) -> PartContract:
    return replace(_CONTRACTS[name], operations=(Operation('wrap', wrap, WRAP),) if wrap is not None else ())


_CONTRACTS = {
    'gloss-plaza': room(
        constraints=(
            'sign adds a stroked YOU ARE HERE signpost. Clouds drift linearly, blocks bob, '
            'bunting sways and sparkles pulse with sine-in-out keys. Far scenery has a 2.5-pixel blur; '
            'the checker floor and cast are separate. Event generation may extend beyond end.',
        )
    ),
    'gloss-activity': room(
        ('number', P(role='digit-string')),
        constraints=(
            'number is a nonempty ASCII digit string drawn as seven-segment shapes, not font text. '
            'The observation eye dims briefly starting at 0.6*end. '
            'Lamp glow and target-pad highlights are painted effects.',
        ),
    ),
    'gloss-waiting': room(
        ('serving', P(items=P(prefix_items=(TIME, P(role='digit-string'))))),
        constraints=(
            'serving is nonempty, starts at zero and rises strictly before end. Every number is a nonempty ASCII '
            'digit string, validated before drawing. Multiple numbers use held visibility spans; '
            'a single number stays visible without a gate. The wall clock has no hands. No queue service is queried.',
        ),
    ),
    'gloss-board': draw(
        (
            'cards',
            P(
                items=P(
                    fields=(
                        ('start', TIME),
                        ('title', COPY),
                        ('body', COPY),
                        ('label', COPY),
                        ('points', P(role='signed-point-count')),
                        ('tone', P(enum=('', 'info', 'ok', 'alert', 'plum'))),
                        ('carried', P(role='continued-from-previous-shot')),
                    )
                )
            ),
        ),
        ('font', FONT),
        ('box', P(prefix_items=(PIXELS, PIXELS, PIXELS, PIXELS))),
        returns=P(type=list[Group], items=GROUP, role='card-groups'),
        constraints=(
            TEXT,
            'Returns one group per card, in input order; geometry stays in fixed-layout coordinates. '
            'box is (x,y,width,maximum-height), defaults to BOARD_BOX, and must stay inside SAFE edges '
            '(80,220,920,1420), with width>=420 and maximum-height>=150. Card starts rise inside [0,end).',
            'Every title/body is wrapped and height-checked before any drawing. Title is 48 pixels, '
            'body 38, heading 28 and badge 60. Heading and badge copy have no separate width-fit check. '
            'A missing tone follows signed points: positive ok, negative alert, zero/None info.',
            'Cards are gated until the next start or end. The first non-carried card pops vertically '
            'from 0.08 through 1.04 at start+0.16 to 1 at start+0.26; words wait for opening. '
            'Non-carried point badges pop on both axes from 0.2 through 1.15 to 1. These keys are linear. '
            'Only the first card at start=0 can be carried; it skips both pops and keeps words visible at the cut.',
        ),
    ),
    'gloss-door': draw(
        ('at', AT),
        ('scale', P(unit='ratio')),
        ('opens', P(items=TIME)),
        ('depth', P(minimum=1, maximum=3, role='nested-door-count')),
        ('opened', P(role='already-open-door-count')),
        returns=LOCAL_GROUP,
        constraints=(
            'at places the foot center and scale is positive. The outer leaf is 260x440 drawing pixels; '
            'frame, EXIT sign, shadow and painted support extend beyond it. Paths provide all lettering.',
            'depth is 1..3, default max(1,opened+len(opens)); opened>=0 and opened+len(opens)<=depth. '
            'Opening times rise strictly inside [0,end). Each next leaf scales horizontally about its left hinge '
            'from 1 to 0.08 over 0.35 seconds with cubic-out easing. Already-open leaves start at 0.08. '
            'This is flat foreshortening, not a 3D hinge. A painted door refuses opens and opened. '
            'The innermost doorway contains a dispenser when any door opens.',
        ),
    ),
    'gloss-ticket': draw(
        ('at', AT),
        ('scale', P(unit='ratio')),
        ('number', P(role='digit-string')),
        returns=LOCAL_GROUP,
        constraints=(
            'Static ticket centered at at, rotated -6 degrees, 300x160 drawing pixels before positive scale. '
            'end is validated but creates no animation or lifetime gate. number is a nonempty ASCII digit string. '
            'Seven-segment digits are 70 pixels tall for up to four digits, otherwise 46; '
            'arbitrarily long numbers are not fit-checked. No font is needed.',
        ),
    ),
    'gloss-hook': draw(
        ('text', COPY),
        ('font', FONT),
        ('talk', TALK),
        constraints=(
            TEXT,
            'Returns a fixed-layout root group gated over [0,end). Text wraps at 48 pixels into at most four '
            '600-pixel lines. Sunny is drawn at (142,300), scale 0.42; talk uses the real Gloss viseme vocabulary. '
            'Talk is preflighted before drawing. The host has authored hover/blink motion '
            'and is not separately returned.',
        ),
    ),
    'gloss-notice': draw(
        ('title', COPY),
        ('body', COPY),
        ('font', FONT),
        ('talk', TALK),
        ('settle', TIME),
        constraints=(
            TEXT,
            'Returns the whole fixed-layout notice. Only its backdrop takes the Gloss grade; the card stays crisp. '
            'Title wraps at 66 pixels into at most two 700-pixel lines, body at 46 into at most nine. '
            'Card height and vertical position follow line counts. This does not impose the board SAFE box.',
            '0<=settle<end gates words until the crossfade has finished; at settle=0 no words gate is emitted. '
            'The body uses the native textAnimator typewriter preset with presetStart=max(0.3,settle) '
            'and presetDuration=round(min(2.4,0.6*end),3). This is an engine text-layer preset, '
            'not a Canvas.keys track. The root and host are not lifetime-clipped by end.',
            'Sunny speaks validated talk and hovers at the lower card corner. Signature code is drawn at '
            '(920,1700), right aligned; this graphic does not add a cactus.',
        ),
    ),
}

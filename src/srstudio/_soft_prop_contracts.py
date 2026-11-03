"""Soft prop discovery grounded in drawing origins, schedules and callback ownership."""

from dataclasses import replace

from ._drawing_contracts import _slot
from ._soft_scene_contracts import ANGLE, COPY, GROUP, LOCAL, LOCAL_GROUP, PARENT, RATIO, SPANS, TIME, draw, placed
from .contracts import ParameterContract as P
from .contracts import PartContract

PARENT_GROUP = replace(GROUP, unit='parent pixels')
BOX = P(prefix_items=(PARENT, PARENT, PARENT, PARENT))
FONT = 'Text requires a bound Canvas font; no measurement callback or automatic text fitting is performed.'
COLOR = P(role='paint-color')
LEVELS = P(items=P(prefix_items=(TIME, P(minimum=0, maximum=3))))
EXPRESSION = (
    'Procedural expression time follows the renderer expression clock; Canvas.local_time only selects '
    'keyframe clocks and does not rewrite expressions. Expressions cannot be held by Canvas.frozen().'
)
END = replace(TIME, role='effect-limit')
STATIC = 'Static drawing; attach the returned group to caller-owned motion to move it.'


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'soft-status-badge': draw(
        ('states', P(items=P(fields=(('label', COPY), ('dot', COLOR), ('start', TIME), ('end', TIME))))),
        ('box', BOX),
        returns=PARENT_GROUP,
        constraints=(
            FONT,
            'box is (left,top,width,height) in parent pixels with positive size. Each state gets its own '
            'centered pill. States are nonempty, ordered and nonoverlapping with 0<=start<end, unique '
            'lowercase names, #RRGGBB dots and nonblank labels of at most 14 characters.',
            'Pills gate to their spans. At start their scale grows linearly from 0.92 to 1.03 over 0.10 seconds, '
            'then settles to 1 by 0.22 seconds. Gaps show no pill; struck adds a slash across the dot.',
        ),
    ),
    'soft-beach-call': draw(
        ('w', LOCAL),
        ('h', LOCAL),
        ('name', COPY),
        ('tag', P(prefix_items=(LOCAL, LOCAL))),
        (
            'guest',
            _slot(
                'Receives the picture root after the beach and before the name tag. '
                'The supplied drawing is not clipped to the picture.'
            ),
        ),
        returns=LOCAL_GROUP,
        constraints=(
            FONT,
            EXPRESSION,
            'Origin is the picture top-left; w/h are positive drawing dimensions. name is nonblank and at '
            'most 14 characters. tag is its top-left, default (12,h-48); the tag must fit inside the picture.',
            'Sea y oscillates by 2 drawing pixels and palm rotation by 2 degrees using sine expressions. '
            'This draws a call illustration; it does not connect to a video service.',
        ),
    ),
    'soft-cake': placed(
        "the plate's bottom center",
        ('front', COPY),
        ('back', COPY),
        ('turn_at', TIME),
        ('lettering', SPANS),
        constraints=(
            FONT,
            EXPRESSION,
            'Icing is nonblank, at most two lines of 12 characters. back and turn_at must be supplied together '
            'with turn_at>=0. Optional nonempty lettering spans have strictly increasing nonnegative endpoints.',
            'A turn is a flat scaleX squeeze: 1 to 0.04 over 0.15 seconds, then back to 1 over 0.15 seconds. '
            'Front/back opacity swaps at the edge; this is not a spatial rotation. Lettering gates independently; '
            'the cake stays drawn. The candle flame scaleY has a sine expression.',
        ),
    ),
    'soft-bench': draw(
        ('x', PARENT),
        ('seat', PARENT),
        ('width', PARENT),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'x is the bench center, seat is its front edge y and width is positive. '
            'Coordinates are baked into the drawing; the returned group is not translated to x/seat. '
            'The back rises 300 pixels and feet extend below the seat.',
        ),
    ),
    'soft-briefcase': placed('the handle', constraints=(STATIC, '220 pixels wide at scale 1; hangs below the handle.')),
    'soft-necktie': placed('the knot center', constraints=(STATIC, 'The tie extends about 200 pixels below its knot.')),
    'soft-shovel': placed(
        'the shovel balance point',
        ('angle', ANGLE),
        constraints=(STATIC, '620 pixels long at scale 1; grip points up at angle 0. rust toggles drawn patches.'),
    ),
    'soft-hive': placed('the feet center', constraints=(STATIC, '260 pixels wide and 340 tall at scale 1.')),
    'soft-cane': draw(
        ('x', PARENT),
        ('y', PARENT),
        ('height', LOCAL),
        ('lean', ANGLE),
        returns=LOCAL_GROUP,
        constraints=(
            STATIC,
            'x/y places the foot. height is positive; lean rotates about that foot. '
            'flip mirrors the crook to the left. It does not pin a foot or support a body.',
        ),
    ),
    'soft-phone': placed(
        'the phone center',
        (
            'screen',
            _slot(
                'Receives the phone root after the glass, in unscaled drawing pixels. '
                'Suggested screen box is (-65,-130)..(65,130); content is not clipped.'
            ),
        ),
        constraints=(
            STATIC,
            '150x300 pixels at scale 1. With no screen callback it shows the back; with one it '
            'shows the front. Content is not clipped to the glass. It draws no thumbs or hand constraints.',
        ),
    ),
    'soft-glare-lamp': draw(
        ('x', PARENT),
        ('y', PARENT),
        ('scale', RATIO),
        ('reach', PARENT),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'x/y places the lamp base; scale is positive and affects only its body. reach is a '
            'positive parent-pixel radius, independent of scale, centered at (x,y-92*scale). '
            'Draw glare recipients first; this radial overlay does not emit a shared world light.',
        ),
    ),
    'soft-parcels': draw(
        ('x', PARENT),
        ('floor', PARENT),
        ('size', PARENT),
        ('rows', P(minimum=1)),
        ('columns', P(minimum=1)),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'Positive integer rows/columns and positive size define a stack from left x '
            'upward from floor y. Box dimensions and row offsets repeat deterministically; '
            'they are authored variation, not gravity or a stacking solver.',
        ),
    ),
    'soft-whisk': placed('the handle end', constraints=(STATIC, 'Wire loops extend 150 drawing pixels upward.')),
    'soft-time-card': draw(
        ('states', P(items=P(fields=(('label', COPY), ('start', TIME), ('end', TIME))))),
        ('box', BOX),
        ('size', replace(LOCAL, role='font-size')),
        returns=PARENT_GROUP,
        constraints=(
            FONT,
            'box is (left,top,width,height), with positive dimensions. Nonempty ordered '
            'nonoverlapping states have 0<=start<end and nonblank labels of at most 8 characters. '
            'The card and its copy gate off in gaps; the labels do not advance as a clock.',
        ),
    ),
    'soft-tongs': placed(
        'the hinge',
        ('angle', ANGLE),
        ('clicks', P(items=TIME)),
        constraints=(
            (
                'Tips point up at angle 0, 320 pixels from the hinge. Arms hold open at +/-7 degrees, '
                'snap to +/-0.5 degrees for 0.07 seconds from each click, then reopen. '
                'Clicks are nonnegative and at least 0.14 seconds apart. This does not grip another prop.',
            )
        ),
    ),
    'soft-grill': placed(
        'the feet center',
        ('end', END),
        ('burgers', P(minimum=1, maximum=4)),
        ('char', TIME),
        ('flames', LEVELS),
        ('flip', TIME),
        constraints=(
            'end is positive. flames are strictly increasing (time,level) rows from zero, levels 0..3. '
            'Supply rows within end. Flame shapes gate to their levels and hold scaleY flickers every 0.14 seconds.',
            'char gates black burger overlays from 0<=char<end. flip must satisfy 0.12<flip<end: the middle '
            'burger lifts over 0.12 seconds before flip, then falls and rotates 360 degrees over 0.20 seconds. '
            'That motion is linear and may finish after end; the grill body is not gated by end.',
        ),
    ),
    'soft-smoke': placed(
        'the smoke source',
        ('rows', LEVELS),
        ('end', END),
        constraints=(
            (
                'Positive end and strictly increasing (time,level) rows from zero; supply rows within end. '
                'Levels 0..3 select no puffs, 2, 5 or 9 puffs. Stages gate to their spans; puffs linearly rise, '
                'drift right, grow and fade over repeating 1.9-second cycles. Deterministic drawn loops, '
                'not fluid simulation; scale multiplies their travel.',
            )
        ),
    ),
    'soft-pizza-box': placed('the box center', constraints=(STATIC, '340 pixels wide, viewed slightly from above.')),
    'soft-bottle': placed('the bottle center', ('color', COLOR), constraints=(STATIC, '230 pixels tall; blank label.')),
    'soft-washer': placed(
        'the feet center',
        ('end', END),
        ('stop', TIME),
        ('open_at', SPANS),
        ('loads', P(items=P(prefix_items=(TIME, P(enum=('brick', 'ball', 'coins', 'shovel')))))),
        constraints=(
            '460x560 pixels at scale 1. 0<stop<=end, default end; the drum rotates linearly once per 1.6 seconds '
            'until stop, then holds. Its light gates off at stop. Body visibility is caller-owned.',
            'Door open intervals satisfy 0<=start<close<=end; overlapping intervals form a union. '
            'Closed/open drawings are complementary within 0..end; no intervals means closed. '
            'Loads appear at their times (0<=time<end), ride inside the drum and gate off at end.',
        ),
    ),
    'soft-brick': placed('the brick center', ('angle', ANGLE), constraints=(STATIC, '180x84 pixels at scale 1.')),
    'soft-bowling-ball': placed('the ball center', constraints=(STATIC, '190 pixels across at scale 1.')),
    'soft-coin-bag': placed('the sack center', constraints=(STATIC, '190x220 pixels; dollar sign is a drawn path.')),
    'soft-tv': placed(
        'the stand feet',
        ('end', END),
        ('off', TIME),
        constraints=(
            (
                '0<off<=end, default end. Picture opacity holds a repeating 0.4-second pattern until off; '
                'then the screen goes dark. The 420-pixel-wide set stays drawn; no video is fetched.',
            )
        ),
    ),
    'soft-home-fridge': placed(
        'the feet center',
        ('end', END),
        ('off', TIME),
        constraints=(
            (
                '300x760 pixels at scale 1. 0<off<=end, default end. Only its green indicator is gated; '
                'the body remains. This changes no room light or refrigerator state.',
            )
        ),
    ),
    'soft-dust': draw(
        ('x', PARENT),
        ('y', PARENT),
        ('start', TIME),
        ('end', TIME),
        ('width', LOCAL),
        ('fall', LOCAL),
        returns=LOCAL_GROUP,
        constraints=(
            (
                'x/y places the source center. 0<=start<end gates all 14 specks; they fall linearly by fall '
                'drawing pixels over 0.9 seconds, staggered every 0.09 seconds across width. '
                'They hold their first/last positions outside their motion; only the parent gate hides them. '
                'No particle collision, looping or fading is applied.',
            )
        ),
    ),
    'soft-dimmer': draw(
        ('rows', P(items=P(prefix_items=(TIME, P(unit='ratio', minimum=0, maximum=1))))),
        ('color', COLOR),
        returns=PARENT_GROUP,
        constraints=(
            (
                'Rows start at zero and increase strictly, holding opacity 0..1 until the next row. '
                'Fixed veil rectangle (-100,-100,1280,2120) covers the 1080x1920 frame with overscan; '
                'it does not resize with Canvas dimensions or emit world light.',
            )
        ),
    ),
    'soft-notice': placed(
        'the notice center',
        ('text', COPY),
        ('shown', SPANS),
        ('size', replace(LOCAL, role='font-size')),
        constraints=(
            FONT,
            '440x180 pixels at scale 1; nonblank text has at most 24 characters and size is positive. '
            'shown=None leaves it visible; an empty sequence hides it. Text remains a renderer text '
            'layer with its safe-area behavior; gate it when moving out of frame.',
        ),
    ),
    'soft-book': placed(
        'the book center',
        ('angle', ANGLE),
        ('color', COLOR),
        constraints=(STATIC, '170x220 pixels at scale 1; spine on the left at angle 0. No lettering.'),
    ),
    'soft-yogurt': placed('the pot base', constraints=(STATIC, 'About 130 pixels wide and 150 tall at scale 1.')),
    'soft-rumble': placed(
        'the belly center',
        ('spans', SPANS),
        ('color', COLOR),
        constraints=(
            (
                'Nonempty ordered nonoverlapping spans gate the lines. The child shake holds +/-5 drawing '
                'pixels in 0.07-second steps, restarting at +5 for each span; scale multiplies the shake. '
                'This is an illustrated vibration, not audio-driven motion or a body constraint.',
            )
        ),
    ),
    'soft-hush-finger': placed(
        'the hand',
        ('fill', COLOR),
        ('reach', LOCAL),
        constraints=(
            STATIC,
            'Nonzero reach curls the drawn forearm by -reach local x; a negative reach curls '
            'the other way. It draws an extra forearm and short finger, without attaching to rig joints.',
        ),
    ),
}

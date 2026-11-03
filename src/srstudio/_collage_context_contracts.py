"""Collage rooms, photographs and illustrated interfaces with literal layout and timing contracts."""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Annotated, Any

from ._collage_place import Place
from ._collage_thing_contracts import (
    ANGLE,
    COLOR,
    COPY,
    FIXED,
    FONT,
    GROUP,
    LOCAL,
    LOCAL_GROUP,
    PARENT,
    STATIC,
    drawing,
)
from .collage import ARMS, EYES, MOUTHS
from .contracts import Operation, PartContract
from .contracts import ParameterContract as P

TIME = P(unit='seconds', timebase='composition')
CANVAS_TIME = P(unit='seconds', timebase='canvas')
DURATION = P(unit='seconds', role='duration')
RATIO = P(unit='ratio')
POINT = P(unit='drawing pixels', space='fixed-layout', prefix_items=(FIXED, FIXED))
BOUNDS = P(unit='drawing pixels', space='fixed-layout', prefix_items=(FIXED, FIXED, FIXED, FIXED))
PARENT_GROUP = replace(GROUP, space='parent')
CANVAS_CLOCK = 'Keys follow the canvas clock: composition by default, local when Canvas.local_time is enabled.'
PROJECT_CLOCK = 'Keys use project (composition) seconds regardless of Canvas.local_time.'
ROOM_NAMES = (
    'boardroom',
    'meeting-room',
    'classroom',
    'living-room',
    'cafe',
    'newsroom',
    'therapy',
    'stage',
    'bathroom',
    'bedroom',
    'supermarket',
    'dining-room',
    'bus-stop',
    'booth',
)
ROOM = drawing(
    constraints=(
        STATIC,
        'Fixed 1080x1920 room layout. Some background fills use Canvas dimensions, but furniture and signature '
        'positions do not reflow. Returns one untranslated group containing the backdrop and sharp signature shelf.',
        'Backdrop overscans by 1.04 around frame center and has a 3-pixel blur, painted light and vignette. '
        'The signature shelf is outside that effect group. Bedroom and booth omit the warm light overlay. '
        'Draw actors and foreground props separately; no actor, content callback, camera or physical lighting '
        'is supplied.',
        'The newsroom globe, clocks, lamps, sky and furniture are static drawings. Use signature_box and marks_box '
        'to reserve the signature area, and zoom_pivot to preserve its frame margins under a uniform zoom.',
    )
)
PLACE = P(fields=(('x', FIXED), ('base', FIXED), ('scale', RATIO)), role='character-placement')
POSE = P(prefix_items=(P(enum=EYES), P(enum=MOUTHS), P(enum=ARMS)))


def contract(name: str, **helpers: Callable[..., Any]) -> PartContract:
    return replace(
        _CONTRACTS[name],
        operations=tuple(Operation(helper, builder, _HELPERS[helper]) for helper, builder in helpers.items()),
    )


_HELPERS = {
    'signature_box': PartContract(
        parameters=(('name', P(enum=ROOM_NAMES)),),
        returns=BOUNDS,
        constraints=(
            'Returns (left,top,right,bottom) of the shelf, cactus and code in fixed layout pixels. '
            'These are edges, not width/height, and do not include caller transforms.',
        ),
    ),
    'marks_box': PartContract(
        parameters=(('name', P(enum=ROOM_NAMES)),),
        returns=BOUNDS,
        constraints=(
            'Returns (left,top,right,bottom) of the cactus and code, excluding bare shelf ends. '
            'These are fixed-layout coordinates, not transformed world bounds.',
        ),
    ),
    'zoom_pivot': PartContract(
        parameters=(
            ('name', P(enum=ROOM_NAMES)),
            ('face', POINT),
            ('scale', RATIO),
            ('width', P(unit='viewport pixels')),
            ('height', P(unit='viewport pixels')),
        ),
        returns=POINT,
        constraints=(
            'For scale>1, returns the pivot nearest face that keeps marks_box at least 12 pixels '
            'inside the width/height viewport. Raises CollageError if no pivot can fit. '
            'It does not animate a camera or constrain any other scene content.',
        ),
    ),
}

_CONTRACTS = {
    **{'collage-' + name: ROOM for name in ROOM_NAMES},
    'collage-sign': drawing(
        ('text', COPY),
        ('x', PARENT),
        ('y', PARENT),
        ('w', LOCAL),
        ('h', LOCAL),
        ('size', LOCAL),
        ('fill', COLOR),
        ('color', COLOR),
        ('tilt', ANGLE),
        returns=LOCAL_GROUP,
        constraints=(
            STATIC,
            FONT,
            'x/y is the card top-left before rotation about its center. Returns the '
            'centered group; text has a 12-pixel horizontal inset and no fit preflight.',
        ),
    ),
    'collage-chart': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('w', PARENT),
        ('h', PARENT),
        ('values', P(items=P(unit='fraction-of-inner-height', minimum=0, maximum=1))),
        ('colour', COLOR),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'x/y is the card top-left baked into the paths. Nonempty values are in (0,1]. '
            'The drawing uses an inner box reduced by 60 pixels in width and height. '
            'Bars are static at those heights; no growth animation is created.',
        ),
    ),
    'collage-tv': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('w', PARENT),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'x/y is the top-left baked into the paths. Body height is 0.66*w plus a 40-pixel stand. '
            'The screen contains a static wide-eyed, grinning Flush figure. No screen callback, '
            'video playback, mask or character animation is supplied.',
        ),
    ),
    'collage-call-buttons': drawing(
        constraints=(
            STATIC,
            'Three illustrated buttons centered at y=1560 and x=350,540,730, each radius 58. '
            'They draw microphone, hang-up and camera icons; they do not connect or control a real call.',
        )
    ),
    'collage-cake-slice': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('cuts', P(items=TIME)),
        ('size', PARENT),
        returns=PARENT_GROUP,
        constraints=(
            PROJECT_CLOCK,
            'x/y is the plate center baked into the drawing; positive size sets slice width. '
            'Nonnegative strictly increasing cuts halve slice scaleX and scaleY in held steps. '
            'The plate stays full size; the slice scales around its own anchor at (x,y+0.08*size). '
            'No bite or cutting motion is drawn.',
        ),
    ),
    'collage-eye-chart': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('rows', P(items=COPY)),
        ('sharp', P(items=TIME)),
        ('end', TIME),
        ('blur_at', TIME),
        returns=PARENT_GROUP,
        constraints=(
            FONT,
            'x/y is the chart top-left baked into paths. Nonempty rows need one nonnegative '
            'strictly increasing sharp cue each. Width is fixed at 620; rows are 110 pixels apart '
            'with font size 52-6*row_index. Choose row counts and times that remain legible.',
            'Blurred bars use canvas-clock opacity gates. Lettered rows use start/end lifetime groups '
            'from their sharp cue to blur_at, or end when blur_at is absent. Use a project-aligned '
            'parent with Canvas.local_time=False for coordinated cues. This draws bars in place of '
            'unreadable rows; it is not a focus or optical blur effect.',
        ),
    ),
    'collage-lens-frame': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('spread', PARENT),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'Coordinates are baked into the drawing. spread is positive; actual lens centers '
            'are spread+120 pixels apart. The tinted lenses do not refract or magnify a face.',
        ),
    ),
    'collage-sensor-tap': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('runs', P(items=P(prefix_items=(CANVAS_TIME, CANVAS_TIME)))),
        returns=PARENT_GROUP,
        constraints=(
            CANVAS_CLOCK,
            'x is the tap position and y the basin rim, baked into paths. '
            'Finite 0<=start<end run spans form a union, including overlaps. Empty runs draw '
            'no water. The water is a held rectangle, not a fluid simulation.',
        ),
    ),
    'collage-spinach': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('width', PARENT),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'Positive width controls a leaf centered on x/y, baked into the geometry. '
            'It does not track teeth or attach itself to a mouth.',
        ),
    ),
    'collage-full-glass': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('full', P(unit='fill-ratio', minimum=0, maximum=1)),
        ('colour', COLOR),
        ('scale', RATIO),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'full is 0..1 and scale is positive. x/y is the foot position, used as both '
            'translation and anchor; geometry retains x/y coordinates rather than a zero local origin. '
            'full=0 omits wine. Fill is an ellipse whose height is 170*full, not a volume calculation.',
        ),
    ),
    'collage-water-jug': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('scale', RATIO),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            'Positive scale acts around the base at x/y using matching translation and anchor. '
            'Geometry retains parent coordinates. Water level and three ice cubes are static.',
        ),
    ),
    'collage-doctor-scale': drawing(
        ('x', PARENT),
        ('base', PARENT),
        ('bar_at', TIME),
        ('bar_to', PARENT),
        ('end', TIME),
        ('bar_from', PARENT),
        returns=PARENT_GROUP,
        constraints=(
            PROJECT_CLOCK,
            'Geometry is baked into the parent coordinates. base is the floor; '
            'bar_to<base and 620<=bar_from<base. When supplied, 0<=bar_at<end is checked before drawing. '
            'The bar translates by bar_to-bar_from over 0.35 seconds with cubic-out easing. '
            'end bounds the cue, not the full animation or group lifetime.',
        ),
    ),
    'collage-phone-timer': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('start', CANVAS_TIME),
        ('seconds', P(minimum=1, maximum=10, role='countdown-integer')),
        ('tick', DURATION),
        ('scale', RATIO),
        returns=LOCAL_GROUP,
        constraints=(
            FONT,
            CANVAS_CLOCK,
            'x/y places the bottom center of three books with a phone above. '
            'start is nonnegative, tick positive, seconds an integer 1..10 excluding booleans. '
            'The first digit waits from time zero through start+tick, then each digit lasts one '
            'tick until start+seconds*tick. Digits are 120 drawing pixels, scaled with the group.',
        ),
    ),
    'collage-viewfinder': drawing(
        ('start', CANVAS_TIME),
        ('seconds', P(minimum=1, maximum=10, role='countdown-integer')),
        ('tick', DURATION),
        constraints=(
            FONT,
            CANVAS_CLOCK,
            'Same countdown rules as collage-phone-timer. Fixed corner brackets '
            'bound (60,790)..(1020,1780); the disc is centered at (540,660), radius 92. '
            'The disc disappears with the last digit; brackets remain. It is an overlay, not a camera.',
        ),
    ),
    'collage-sofa': drawing(
        constraints=(
            STATIC,
            'Foreground seat front begins at fixed y=1690; width and bottom use Canvas dimensions. '
            'Arms rise above the seat to cover seated bust cutoffs. No seating or support constraint is solved.',
        )
    ),
    'collage-flash': drawing(
        ('at', CANVAS_TIME),
        ('hold', DURATION),
        ('fade', DURATION),
        constraints=(
            CANVAS_CLOCK,
            'Finite at>=0, hold>=0 and fade>0. A full-Canvas white rectangle is gated '
            'from at through at+hold+fade; opacity holds at 1 then fades linearly to 0. '
            'It overlays the image rather than relighting scene objects.',
        ),
    ),
    'collage-photo-print': drawing(
        ('places', P(type=Mapping[str, Annotated[Place, PLACE]], role='ordered-cast-placement')),
        ('poses', P(type=Mapping[str, Annotated[tuple[str, str, str], POSE]])),
        ('x', PARENT),
        ('y', PARENT),
        ('width', LOCAL),
        ('tilt', ANGLE),
        (
            'blur',
            P(
                type=Sequence[str],
                role='blurred-cast-names',
                description='Collection of names, represented as an array.',
            ),
        ),
        ('room', P(enum=ROOM_NAMES)),
        ('crop', BOUNDS),
        returns=LOCAL_GROUP,
        constraints=(
            'x/y is the print top-left and rotation origin. Positive width is image width, excluding the '
            '0.045*width border and 0.16*width bottom margin. crop is (x,y,width,height), unlike room helper '
            'bounds; it must fit the fixed 1080x1920 room with positive dimensions.',
            'places maps cast names to actual collage_group.Place records with x/base in fixed layout pixels '
            'and positive scale. poses must have exactly the same names; mapping order controls layering. '
            'blur names a subset. The room, static figure_shapes and a sofa foreground are drawn inside a '
            'masked image group, even when choosing another room.',
            'No breathing, blinking or pose animation is emitted. Subject blur radius is 9/place.scale, '
            'preserving blur across cast scales before print scaling; different radii receive separate '
            'effects. The room retains its own backdrop blur and signature. A painted gloss overlays the print.',
        ),
    ),
    'collage-article': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('w', LOCAL),
        ('h', LOCAL),
        ('headline', COPY),
        ('size', LOCAL),
        ('sender', COPY),
        returns=PARENT_GROUP,
        constraints=(
            STATIC,
            FONT,
            'x/y is the phone top-left; the return is an untranslated wrapper containing '
            'the whole phone. w/h must exceed 112. Nonblank capital headline uses size at least the '
            '21.6-pixel legibility floor and estimated glyph-width fit checks before drawing. '
            'sender adds an 84-pixel strip; its copy has no separate fit check. The picture is drawn '
            'hills and sky, and body text is four grey bars. No article is fetched.',
        ),
    ),
    'collage-weather-map': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('w', LOCAL),
        ('h', LOCAL),
        ('arrow', COPY),
        ('slide', P(prefix_items=(TIME, TIME))),
        ('clock', P(prefix_items=(COPY, P(prefix_items=(TIME, TIME))))),
        returns=LOCAL_GROUP,
        constraints=(
            FONT,
            PROJECT_CLOCK,
            'x/y is the map top-left; w/h are at least 120. arrow=None omits '
            'the arrow; empty string draws it without words. Other arrow copy is capital and fit-checked. '
            'A finite 0<=slide.start<slide.end moves it from -0.22*h to zero using cubic-out. '
            'clock is literal capital text and a finite 0<=start<end span; its card uses held visibility. '
            'This is invented land with no weather service, location data or advancing clock.',
        ),
    ),
    'collage-thread': drawing(
        ('x', PARENT),
        ('y', PARENT),
        ('w', LOCAL),
        ('h', LOCAL),
        ('contact', COPY),
        ('call', COPY),
        ('tilt', ANGLE),
        ('clock', P(items=P(prefix_items=(TIME, COPY)))),
        ('messages', P(items=P(fields=(('text', COPY), ('at', TIME))))),
        returns=PARENT_GROUP,
        constraints=(
            FONT,
            PROJECT_CLOCK,
            'x/y is the phone top-left before center rotation. Returns an '
            'untranslated wrapper containing the whole phone. w/h exceed 52; w must also keep '
            'the 46*(w/700) clock size above the 21.6-pixel legibility floor. Copy is capital; '
            'contact and messages are nonblank. clock is nonempty with strictly increasing '
            'finite 0<=time<86400; message arrivals are ordered with ties allowed in that range.',
            'Header and every message box are preflighted before drawing. mine selects a right '
            'green bubble; otherwise left grey. At arrival each bubble rises by 30*(w/700) pixels '
            'over 0.12 seconds with cubic-out while visibility turns on at the same project cue. '
            'A call strip is literal copy. No messages are retrieved or sent.',
        ),
    ),
}

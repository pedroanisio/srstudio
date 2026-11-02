"""Authored Stick home, office and everyday semantics, verified against actual drawings and clocks."""

from collections.abc import Mapping, Sequence
from typing import Annotated

from sr_core.scene import Composition, Group, Symbol

from .canvas import Canvas
from .contracts import ParameterContract as P
from .contracts import PartContract
from .stick import RigPose

PIXEL = P(type=float, unit='frame pixels')
SCALE = P(unit='ratio', description='Strictly positive drawing scale.')
TIME = P(unit='seconds', timebase='canvas', minimum=0)
END = P(unit='seconds', timebase='canvas', role='animation-limit')
RATE = P(
    unit='drawings per second', description='Strictly positive; alternates two held drawings, not cycles per second.'
)
FONT = 'Lettering requires a bound Canvas font asset; it is not converted to outlined path geometry.'
FIXED = 'Artwork uses the 1080x1920 Stick layout; canvas-sized backgrounds resize, fixed details do not auto-fit.'
BAKED = 'Placement and scale are baked into the geometry; the returned group has no local placement transform.'
CLOCK = 'Animation keys and opacity gates follow Canvas.local_time: composition by default, local when enabled.'
PAINT = P(description='Paint color passed to the drawing primitives.')
POINT = P(prefix_items=(PIXEL, PIXEL), space='parent')
POSE_POINT = P(prefix_items=(PIXEL, PIXEL), space='pose')
PAIR = P(prefix_items=(POSE_POINT, POSE_POINT), description='Far then near joint.')
POSE = P(
    fields=(
        ('head', POSE_POINT),
        ('neck', POSE_POINT),
        ('hip', POSE_POINT),
        ('knees', PAIR),
        ('feet', PAIR),
        ('elbows', PAIR),
        ('hands', PAIR),
    )
)


def draw(
    *parameters: tuple[str, P], local: bool = False, handle: bool = True, constraints: tuple[str, ...] = ()
) -> PartContract:
    return PartContract(
        parameters=(('cv', P(type=Canvas)), ('parent', P(type=Composition | Group | Symbol)), *parameters),
        returns=P(
            type=Group,
            unit='frame pixels',
            space='returned-group' if local else 'parent',
            anchors=(('origin', (0, 0)),) if local else (),
        )
        if handle
        else P(type=type(None)),
        capabilities=(('spatial_attachment', False), ('returns_scene_handle', handle)),
        constraints=(
            'Draws flat 2D geometry in the supplied parent; no spatial grip, collision or anatomical solver.',
            CLOCK,
            *constraints,
        ),
    )


def placed(*parameters: tuple[str, P], local: bool = False, constraints: tuple[str, ...] = ()) -> PartContract:
    return draw(('x', PIXEL), ('y', PIXEL), *parameters, local=local, constraints=constraints)


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'stick-kitchen': draw(
        handle=False,
        constraints=(
            FIXED,
            'Background excludes the table. safe controls the shut wall safe; marks controls both signature marks.',
        ),
    ),
    'stick-kitchen-plan': draw(
        handle=False, constraints=(FIXED, 'Overhead floor and table at PLAN; includes signature marks.')
    ),
    'stick-bedroom': draw(
        handle=False,
        constraints=(
            FIXED,
            'Static night room with a drawn sleeping figure; right half left clear for another figure.',
        ),
    ),
    'stick-table': draw(
        ('span', P(prefix_items=(PIXEL, PIXEL))),
        ('top', PIXEL),
        ('legs', PIXEL),
        handle=False,
        constraints=(
            'span is finite left/right with left<right; top is the tabletop y, legs>0 is leg length. No '
            'table handle is returned.',
        ),
    ),
    'stick-from-above': draw(
        ('end', END),
        ('rate', RATE),
        ('hair', P(enum=('none', 'side-part', 'bun'))),
        ('phone', PAINT),
        local=True,
        constraints=(
            'Origin is the overhead head/shoulder center, facing upward. Feet alternate from zero to end>0.',
            'Only the feet are gated; the head and body remain visible after end. A complete two-drawing '
            'cycle takes 2/rate seconds.',
        ),
    ),
    'stick-fridge-open': draw(
        constraints=(FIXED, 'Overlay the shut fridge at FRIDGE; this is a static open drawing, not a door animation.')
    ),
    'stick-safe-open': draw(
        constraints=(FIXED, 'Overlay the shut safe at SAFE; this is a static open drawing, not a door animation.')
    ),
    'stick-handset': placed(
        ('scale', SCALE),
        ('colour', PAINT),
        constraints=(BAKED, 'x/y is the phone center; lit selects a static screen color.'),
    ),
    'stick-key': placed(
        ('scale', SCALE), constraints=(BAKED, 'x/y is the bow center, with the shaft extending right.')
    ),
    'stick-chair': placed(
        ('rise', P(unit='frame pixels', minimum=0)),
        constraints=(
            'x is the seat center and y the feet line. rise lengthens the legs and lifts the seat and back.',
            'flip mirrors geometry about x using group x=2*x and scaleX=-1; the unflipped group has no '
            'placement transform.',
        ),
    ),
    'stick-smoke-alarm': placed(
        ('scale', SCALE),
        ('flashes', P(type=Sequence[float], items=TIME)),
        constraints=(
            BAKED,
            'x/y is the alarm center. Each flash gates its LED for 0.18 seconds; overlapping spans merge. '
            'No audio is emitted.',
        ),
    ),
    'stick-mound': placed(
        constraints=(FONT, 'x/y is the earth mound foot center. words must be nonblank and at most six characters.')
    ),
    'stick-shovel': placed(
        constraints=(
            'x/y is the blade ground reference; the blade tip extends 50 pixels below it. Geometry is '
            'baked in parent coordinates.',
        )
    ),
    'stick-message-insert': draw(
        constraints=(
            FIXED,
            FONT,
            'sender and text must be nonblank; text has at most 48 characters, set at 104 pixels over at '
            'most three lines.',
        )
    ),
    'stick-reply-screen': draw(
        constraints=(
            FIXED,
            FONT,
            'name, sent and answer must be nonblank; fixed text boxes do not measure or guarantee fitting '
            'arbitrary strings.',
        )
    ),
    'stick-coffee-corner': draw(
        handle=False,
        constraints=(
            FIXED,
            'Background includes a window-masked city and signature marks. Draw the counter separately in '
            'front of figures.',
        ),
    ),
    'stick-coffee-counter': draw(
        constraints=(
            FIXED,
            'Counter and machine form a foreground group; use a separate parent to change placement or visibility.',
        )
    ),
    'stick-mug': placed(
        ('colour', PAINT),
        constraints=(
            'x/y is the mug body center in the hand; the handle extends right. Coordinates are baked, not '
            'a solved grip.',
        ),
    ),
    'stick-arm-cast': draw(
        ('elbow', POINT),
        ('hand', POINT),
        constraints=(
            'A straight plaster stroke between supplied joint points. Both endpoints are in the drawing '
            'parent; does not solve the arm.',
        ),
    ),
    'stick-neck-brace': placed(
        constraints=('x/y locates the neck under the chin; collar geometry is baked into the returned group.',)
    ),
    'stick-parrot': placed(
        ('facing', P(enum=(-1, 1))),
        constraints=(
            'x/y is the standing reference; facing -1 looks left and 1 right. Direction changes the baked geometry.',
        ),
    ),
    'stick-flames': placed(
        ('end', END),
        ('rate', RATE),
        constraints=(
            'x/y is the flame base. Two drawings alternate from zero to end>0, then both are hidden by opacity keys.',
        ),
    ),
    'stick-tombstone': draw(
        ('x', PIXEL),
        constraints=(
            FONT,
            'x is the stone center; its top is y=740 and its foot is COUNTER_TOP+4. words must be nonblank.',
        ),
    ),
    'stick-meteor': draw(
        ('end', END),
        ('land', TIME),
        constraints=(
            '0<land<end. Rock position interpolates from zero to land, then disappears; glow shows from land to end.',
            'Draw inside stick_office.view for window masking; the returned meteor group itself supplies '
            'no window mask.',
        ),
    ),
    'stick-box': placed(
        ('w', P(unit='frame pixels', description='Positive front width in local drawing units.')),
        ('h', P(unit='frame pixels', description='Positive front height in local drawing units.')),
        ('scale', SCALE),
        local=True,
        constraints=(
            'x/y is the front face foot center. flip reflects locally; shadow=False omits the '
            'contact-shadow drawing when stacked or held.',
        ),
    ),
    'stick-receipt': placed(
        ('length', P(unit='frame pixels', description='Positive local paper length; curl extends below it.')),
        ('w', P(unit='frame pixels', description='Positive local paper width.')),
        (
            'unroll',
            P(
                prefix_items=(
                    P(unit='seconds', timebase='canvas', role='start'),
                    P(unit='seconds', timebase='canvas', role='end'),
                )
            ),
        ),
        local=True,
        constraints=(
            'x/y is the top-edge center. Optional 0<=start<end unrolls scaleY from 0.02 to 1 with sine-out easing.',
            'Unroll does not hide the receipt before start or after end; scrawled rows require no font.',
        ),
    ),
    'stick-poster': placed(
        ('w', PIXEL),
        ('h', PIXEL),
        ('size', PIXEL),
        constraints=(
            FONT,
            'x/y is the top-left. Positive w/h define the paper; the text box is inset 30 pixels on each '
            'side, at most four lines. Caller must choose enough interior room.',
        ),
    ),
    'stick-headset': placed(
        ('scale', SCALE),
        local=True,
        constraints=(
            'Origin is the head center. flip mirrors the headset locally; draw after the figure in '
            'matching coordinates.',
        ),
    ),
    'stick-xray': draw(
        ('end', END),
        (
            'items',
            P(items=P(prefix_items=(P(enum=('chicken', 'lasagna', 'rolling-pin')), PIXEL, PIXEL, P(unit='ratio')))),
        ),
        constraints=(
            FIXED,
            'Nonempty items are (name,x,y,scale), rendered twice for sharp and blurred layers. No mesh or '
            'scan simulation.',
            'end>0 is the scan-line linear travel endpoint from y=0 to canvas height; it does not hide '
            'the screen or objects.',
        ),
    ),
    'stick-plate': placed(
        ('heap', P(minimum=0, maximum=3)),
        ('scale', SCALE),
        local=True,
        constraints=(
            'Origin is the plate standing reference, heap is the number of food tiers. No contact solver is supplied.',
        ),
    ),
    'stick-spoon': draw(
        ('grip', POINT),
        ('bowl', POINT),
        constraints=(
            'grip and bowl are parent-coordinate centers; draws their connecting handle and bowl, '
            'optionally food. No spatial grip solving.',
        ),
    ),
    'stick-robe': draw(
        (
            'keys',
            P(
                items=P(
                    fields=(
                        ('start', TIME),
                        ('pose', P(description='Key into poses.')),
                        ('face', P(description='Face is ignored; only pose geometry and start times are consumed.')),
                    )
                )
            ),
        ),
        ('end', END),
        ('poses', P(type=Mapping[str, Annotated[RigPose, POSE]])),
        ('at', POINT),
        ('scale', SCALE),
        ('colour', PAINT),
        ('belt', PAINT),
        local=True,
        constraints=(
            'Use the same keys, end, poses, at, scale and flip as stick.rig; validate the performance '
            'with stick.check_keys before drawing.',
            'Each pose is held until the next key or end. A pose spanning the whole shot omits its '
            'opacity gate and remains visible beyond end; use an outer visibility parent.',
            'The robe does not validate the full rig performance or interpolate joints; face is ignored.',
        ),
    ),
    'stick-scan-belt': draw(
        constraints=(FIXED, 'Static foreground belt and tunnel at BELT_TOP; draw over figures to cover their legs.')
    ),
    'stick-foil-parcel': placed(
        ('scale', SCALE),
        local=True,
        constraints=('Origin is the 180x120 foil parcel center. Creases are fixed, not random.',),
    ),
    'stick-foil-note': draw(
        ('size', PIXEL),
        constraints=(
            FIXED,
            FONT,
            'Nonblank text is centered in the fixed NOTE_BOX with 60-pixel padding, up to five lines.',
        ),
    ),
    'stick-aisle': draw(
        constraints=(
            FIXED,
            'Static one-point perspective is drawn into 2D paths. HORIZON=620; no camera or depth mesh is returned.',
        )
    ),
    'stick-queue': draw(
        ('end', END),
        ('turn', TIME),
        ('rows', P(minimum=1, maximum=12)),
        constraints=(
            'Rows are integer pairs of passengers with fixed appearance; 0<=turn<=end swaps backs for faces.',
            'Visibility uses canvas opacity gates. A drawing covering the whole interval omits its gate '
            'and can remain visible afterward; an outer parent owns shot visibility.',
            'The queue follows the fixed aisle perspective, not world depth; legs adds static trousers and feet.',
        ),
    ),
    'stick-book': placed(
        ('scale', SCALE),
        ('colour', PAINT),
        local=True,
        constraints=(
            'Origin is the book center. shut selects a static closed cover; it is not an opening transition.',
        ),
    ),
    'stick-duffel': placed(
        ('scale', SCALE),
        ('colour', PAINT),
        local=True,
        constraints=('Origin is the bag body center; its strap extends above it.',),
    ),
    'stick-wheelie-bin': placed(
        ('scale', SCALE),
        ('wheels', P(enum=(0, 1, 2))),
        ('lean', P(unit='degrees')),
        local=True,
        constraints=(
            'Origin is the authored standing reference. lean rotates the whole group about it; wheels '
            'changes the drawn wheel count, not a contact solution.',
        ),
    ),
    'stick-trash-truck': placed(
        ('scale', SCALE),
        local=True,
        constraints=(
            'Origin is the truck rear reference, with a 1000-pixel local body length. CAB_WINDOW is a '
            'local rectangle for separately drawn drivers.',
            'Wheel circles extend 28 local pixels below the authored y reference; y is not an exact '
            'tire-ground contact anchor.',
        ),
    ),
    'stick-slipper': placed(
        ('scale', SCALE),
        local=True,
        constraints=(
            'Origin is the slipper reference center; toe points right. Animate the returned group to throw it.',
        ),
    ),
    'stick-sparks': placed(
        ('end', END),
        ('rate', RATE),
        ('scale', SCALE),
        local=True,
        constraints=(
            'Origin is the spray source; two deterministic sprays alternate from zero to end>0, then '
            'hide. No particle simulation.',
        ),
    ),
    'stick-planks': draw(
        ('x', PIXEL),
        ('floor', PIXEL),
        ('scale', SCALE),
        local=True,
        constraints=(
            'Root translation is x/floor, with leaning boards above and loose boards extending below it; '
            'x is an authored reference, not a complete bounding-box edge.',
        ),
    ),
    'stick-wardrobe': draw(
        ('x', PIXEL),
        ('floor', PIXEL),
        ('scale', SCALE),
        ('stage', P(enum=('half', 'done'))),
        local=True,
        constraints=(
            'Root x/floor locates the 410x860 local cabinet. stage selects a static drawing; no assembly animation.',
            'half requires a bound font for THIS SIDE IN; done has no lettering and requires no font.',
        ),
    ),
    'stick-drill': placed(
        ('scale', SCALE),
        local=True,
        constraints=(
            'Origin is the grip reference; bit points right unless flip reflects locally. No solved hand attachment.',
        ),
    ),
    'stick-screws': placed(
        ('scale', SCALE),
        ('count', P(minimum=1)),
        local=True,
        constraints=(
            'Positive integer count; origin is the first screw reference. Subsequent screws are 44 local '
            'pixels apart with fixed tilts.',
        ),
    ),
    'stick-manual-page': draw(
        ('step', P(minimum=1)),
        ('drawing', P(enum=('smiling', 'argument', 'crossed', 'sofa', 'suitcase', 'hug', 'bun'))),
        constraints=(
            FIXED,
            FONT,
            'Positive step number. Nonblank bubble is required exactly for argument; other drawings '
            'require blank bubble.',
        ),
    ),
    'stick-caller': placed(
        ('scale', SCALE),
        ('ring', P(items=TIME)),
        local=True,
        constraints=(
            FONT,
            'Origin is phone center. Nonblank name is set in a fixed one-line text box.',
            'ring times are finite nonnegative and ordered; each creates a 0.25-second linear shake in '
            'parent x coordinates with offsets -9,+9,-7,+7,0.',
            'Shake amplitude is independent of phone scale; the phone remains visible outside ring intervals.',
        ),
    ),
}

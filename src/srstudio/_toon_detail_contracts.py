"""Authored everyday, insert, study and laptop contracts; no builder execution or parameter-name inference."""

from collections.abc import Callable
from dataclasses import replace

from ._toon_contracts import COMP_TIME, DURATION, FONT, PARENT_END, PARENT_START, REF, draw, point
from ._toon_domestic_contracts import ID, SCALE
from ._toon_household_contracts import group
from .contracts import ParameterContract as P
from .contracts import PartContract

FRAME = P(unit='frame pixels', space='frame')
FRAME_POINT = P(space='frame', prefix_items=(FRAME, FRAME))
DEGREES = P(unit='degrees')
FRACTION = P(unit='ratio', minimum=0, maximum=1)
MEASURE = P(
    type=Callable[[str, float], float],
    role='text-measure',
    description='measure(text,size) returns advance width in frame pixels at the supplied frame-pixel font size.',
)
LETTERED_SCALE = P(unit='ratio', minimum=0.9, maximum=2)
FOOTPRINT_RULES = (
    'Placement checks a reference footprint against the fixed 1080x1920 Toon frame, caption band and signature box.',
    'The returned footprint is (left,top,right,bottom) in reference pixels, including authored motion allowance.',
    'Footprint checks do not transform with an external parent or adapt to different canvas dimensions.',
)
COLOR = P(description='#rrggbb paint color.')


def footprint(*parameters: tuple[str, P], constraints: tuple[str, ...] = ()) -> PartContract:
    return replace(
        draw(*parameters, constraints=(*FOOTPRINT_RULES, *constraints), clock='composition'),
        returns=P(
            type=tuple[float, float, float, float],
            unit='reference pixels',
            space='toon-reference',
            role='footprint',
            prefix_items=(REF, REF, REF, REF),
            description='Reference bounding box, not a scene group or spatial attachment frame.',
        ),
    )


_CONTRACTS = {
    'toon-phone': footprint(
        (
            'screens',
            P(
                items=P(
                    fields=(
                        ('at', COMP_TIME),
                        ('kind', P(enum=('off', 'notify', 'code', 'profile', 'declined', 'loading'))),
                        ('fill', FRACTION),
                    )
                )
            ),
        ),
        ('measure', MEASURE),
        ('at', point('Phone base.')),
        ('scale', LETTERED_SCALE),
        ('id', ID),
        constraints=(
            FONT,
            'Nonempty Screen records begin at zero and rise at least 0.24 seconds apart; opacity keys switch screens.',
            'notify requires title/text; code requires title/text; profile and loading require title.',
            'declined requires title/text; off draws no fields. Fields unsupported by a kind must be empty.',
            'Only loading uses fill; other kinds require fill=1. Loading fills until the next cue, or for 2 seconds.',
            'hand=None draws a contact shadow; a #rrggbb hand draws a thumb instead, without a rig binding.',
        ),
    ),
    'toon-tv-menu': group(
        ('seen', P(unit='ratio', maximum=1, description='Static watched fraction, strictly greater than zero.')),
        ('measure', MEASURE),
        ('id', ID),
        clock='composition',
        constraints=(FONT, 'Fixed reference menu geometry; no footprint-placement checks. Label and heading must fit.'),
    ),
    'toon-remote': group(
        ('at', point('Remote center.')),
        ('scale', SCALE),
        ('tilt', DEGREES),
        ('id', ID),
        constraints=('No footprint-placement checks; the caller owns placement in the supplied parent.',),
    ),
    'toon-stars': draw(
        ('filled', P(minimum=0, maximum=5)),
        ('at', point('Center of the five-star row.')),
        ('start', COMP_TIME),
        ('step', P(unit='seconds', role='duration', minimum=0)),
        ('scale', SCALE),
        ('id', ID),
        clock='composition',
        constraints=(
            'filled is an integer 0..5; start>=0. step=0 fills the selected stars simultaneously.',
            'Empty star outlines are always present; composition opacity keys reveal fills without a visibility end.',
        ),
    ),
    'toon-speaker': footprint(
        ('states', P(items=P(prefix_items=(COMP_TIME, P(enum=('off', 'listen', 'think', 'speak', 'error')))))),
        ('end', P(unit='seconds', timebase='composition', role='animation-limit', maximum=600)),
        ('at', point('Speaker base.')),
        ('scale', P(unit='ratio', minimum=0.5, maximum=2)),
        ('id', ID),
        constraints=(
            'Nonempty strictly rising states begin at zero; last cue<end<=600.',
            'think chases ring segments every 0.12 seconds; speak alternates opacity every 0.2 seconds.',
            'end bounds generated animation, not visibility. Final emitted ring values remain held afterward.',
        ),
    ),
    'toon-receipt': footprint(
        ('measure', MEASURE),
        ('start', COMP_TIME),
        ('pace', P(unit='seconds per row', role='duration', maximum=2)),
        ('at', point('Printer slot center.')),
        ('scale', LETTERED_SCALE),
        ('id', ID),
        constraints=(
            FONT,
            'Nonempty item (name,price) rows; each string is nonblank, single-line and measured to fit.',
            'header empty omits the heading; total=None omits the total row. start>=0 and 0<pace<=2.',
            'Paper grows linearly, row lettering appears through held composition opacity keys; no visibility end.',
        ),
    ),
    'toon-take-a-number': footprint(
        ('serving', P(items=P(prefix_items=(COMP_TIME, P(description='Integer 0..999 or fitted display text.'))))),
        ('ticket', P(description='Integer 0..999 or fitted ticket text; None omits the ticket.')),
        ('measure', MEASURE),
        ('at', point('Pole base.')),
        ('scale', LETTERED_SCALE),
        ('id', ID),
        constraints=(FONT, 'Nonempty serving cues rise strictly from zero. Final number remains shown without an end.'),
    ),
    'toon-clipboard': footprint(
        ('fields', P(items=P(fields=(('at', COMP_TIME),)))),
        ('measure', MEASURE),
        ('stamp', P(prefix_items=(COMP_TIME, P(description='Fitted stamp text.'), P(enum=('bad', 'good', 'deep'))))),
        ('at', point('Board foot.')),
        ('scale', LETTERED_SCALE),
        ('id', ID),
        constraints=(
            FONT,
            '1..5 Field records; each label and nonempty value must fit. Empty values remain blank.',
            'Field.at is a nonnegative composition cue; fields need not be ordered by time.',
            'stamp=None omits the stamp; otherwise (time,text,tone).',
            'Positive stamp cues settle from scale 1.2 over 0.12 seconds.',
            'hand=None draws a shadow; #rrggbb draws a thumb, without a rig binding. Final marks remain visible.',
        ),
    ),
    'toon-eye-drops': draw(
        ('eye', point('Drop landing point.')),
        ('start', PARENT_START),
        ('squeezes', P(items=COMP_TIME)),
        ('leave', PARENT_END),
        ('scale', SCALE),
        ('id', P(role='scene-id')),
        clock='composition',
        constraints=(
            'Nonempty sorted squeeze cues are strictly after start; leave is strictly after the last cue+0.22.',
            'Each cue also supplies drop parent visibility; drops fall linearly for 0.22 seconds.',
            'arm=None omits the drawn arm; otherwise arm is a coat paint color, not an actor or callback.',
            'Bottle placement is static during its visibility span; this is not anatomical eye tracking.',
        ),
    ),
    'toon-reception-glass': draw(
        ('left', REF),
        ('right', REF),
        ('top', REF),
        constraints=(
            'left<right and top<801. Pane bottom is reference y=737, leaving a 64-pixel paperwork gap.',
            'Draw in front of the actor; speaking hole is drawn artwork, not a clipping or collision boundary.',
        ),
    ),
    'toon-voice-note-bar': draw(
        ('stops', P(items=P(prefix_items=(PARENT_START, P(description='Displayed time text.'), FRACTION)))),
        ('end', PARENT_END),
        ('y', REF),
        ('doubled', P(prefix_items=(PARENT_START, PARENT_END))),
        constraints=(
            FONT,
            'Nonempty stops start at zero, rise strictly in time and do not decrease played fraction; last<end.',
            'y is panel top. 26 waveform bars change by visibility; fractions are rounded to a bar count.',
            'doubled=None omits the chip; otherwise 0<=start<end<=player end. The 2x chip does not alter playback.',
            'end hides displayed time/progress; the background panel remains visible. No audio is played.',
        ),
    ),
    'toon-gull-stare': draw(
        ('at', point('Head center.')),
        ('turn', COMP_TIME),
        ('seconds', DURATION),
        ('end', PARENT_END),
        ('scale', SCALE),
        clock='composition',
        constraints=(
            'turn>=0, seconds>0 and turn+seconds<=end. Beak and eye use sine-in-out interpolation.',
            'Stylized 2D eye translation and beak scaling; not a world-space gaze target or anatomical solve.',
        ),
    ),
    'toon-wifi-list': draw(
        ('states', P(items=P(prefix_items=(PARENT_START, P())))),
        ('end', PARENT_END),
        ('top', REF),
        clock='composition',
        constraints=(
            FONT,
            'States begin at zero and rise strictly before end; every page has the same 1..4 names.',
            'Each name wraps at 19 characters into at most two lines. Pages and highlights use parent visibility.',
            'Changed rows highlight for up to 0.9 seconds; the wheel turns every 1.2 seconds on composition time.',
        ),
    ),
    'toon-rain': draw(
        ('start', COMP_TIME),
        ('end', PARENT_END),
        ('left', REF),
        ('right', REF),
        ('top', REF),
        ('bottom', REF),
        ('opacity', P(unit='ratio', maximum=1)),
        clock='composition',
        constraints=(
            '0<=start<end, left<right, top<bottom and 0<opacity<=1. start also sets parent visibility.',
            'A 300-reference-pixel tile falls every 0.4 seconds with a 0.002-second reset.',
            'Edges define pattern placement, not a clip rectangle; repeated streaks extend beyond the given bounds.',
        ),
    ),
    'toon-gnome': draw(
        ('at', point('Feet.')), ('scale', SCALE), constraints=('Static garden figure; no animation keys.',)
    ),
    'toon-noodle-box': draw(
        ('at', point('Box base.')),
        ('scale', SCALE),
        ('full', FRACTION),
        constraints=('full=0 omits the noodle heap; chopsticks remain. This is static geometry, not a timed fill.',),
    ),
    'toon-open-laptop': group(
        (
            'notes',
            P(
                items=P(
                    fields=(
                        ('u', FRACTION),
                        ('v', FRACTION),
                        ('on', COMP_TIME),
                        ('tilt', DEGREES),
                        ('peel', P(prefix_items=(COMP_TIME, COMP_TIME))),
                    )
                )
            ),
        ),
        (
            'quad',
            P(
                fields=tuple(
                    (name, point('Screen corner.')) for name in ('top_left', 'top_right', 'bottom_right', 'bottom_left')
                )
            ),
        ),
        ('foot', P(unit='reference pixels', description='Positive keyboard depth below the hinge.')),
        ('shift', REF),
        clock='composition',
        constraints=(
            'Quad corners are finite; left corners must lie left of right corners, top corners above bottom corners.',
            'Note u,v are fractions 0..1 across/down the bilinear screen; this is not a perspective projection.',
            'Note.on cues are nonnegative and sorted, allowing ties. on also starts parent visibility.',
            'Notes land from scale 1.22 over 0.1 seconds; peel=(a,b) requires on<a and a+0.32<=b.',
            'shift is horizontal keyboard displacement. Notes may overhang the screen; none are clipped or hidden.',
        ),
    ),
    'toon-open-book': draw(
        ('marks', P(description='Map of row indices 0..15 to #rrggbb colors.')),
        ('sweep', P(prefix_items=(P(minimum=0, maximum=15), COLOR, COMP_TIME))),
        ('note_sweep', P(prefix_items=(COLOR, COMP_TIME))),
        ('measure', MEASURE),
        ('at', point('Spine foot.')),
        ('scale', SCALE),
        ('id', ID),
        clock='composition',
        constraints=(
            'note=None draws scrawl on both pages; otherwise 1..2 nonblank rows replace the right page.',
            'A note requires the measure callback.',
            'With a note, marks/sweep may use only rows 0..7. note_sweep requires a note.',
            'Sweeps grow linearly from scale 0.02 to 1 over 0.55 seconds; their cues also start parent visibility.',
            'Note measurement uses 44 frame-pixel type within 196 reference pixels. Whole-book scale also scales text.',
        ),
    ),
    'toon-shut-book': draw(
        ('at', point('Book foot.')),
        ('scale', SCALE),
        ('id', ID),
        constraints=('Static book with a contact shadow; the caller owns external placement and visibility.',),
    ),
    'toon-highlighter': draw(
        ('at', FRAME_POINT),
        ('paw', COLOR),
        ('path', P(items=P(prefix_items=(COMP_TIME, FRAME)))),
        ('scale', SCALE),
        ('id', ID),
        clock='composition',
        constraints=(
            'Exception: marker geometry and at/path x use frame pixels, not Toon reference conversion.',
            'Finite rising path times; linear absolute x keys, fixed y. Empty path leaves the marker still.',
            'paw is a paint color; the drawn paw does not bind to a character hand.',
        ),
    ),
    'toon-study-page': draw(
        ('marks', P(description='Map of row indices 0..8 to #rrggbb colors.')),
        ('measure', MEASURE),
        ('id', ID),
        constraints=(
            FONT,
            'Exception: fixed frame-pixel sheet at (80,440), size 860x1010, tilted -1.2 degrees.',
            'Nonblank heading measured at 66 pixels; key has 1..3 (color,words) rows measured at 44 pixels.',
        ),
    ),
    'toon-quiz-sheet': draw(
        ('measure', MEASURE),
        ('at', FRAME_POINT),
        ('scale', SCALE),
        ('tilt', DEGREES),
        ('start', PARENT_START),
        ('end', PARENT_END),
        ('id', ID),
        constraints=(
            FONT,
            'Exception: sheet geometry and center at use frame pixels; unscaled paper is 800x960.',
            'Title has 1..2 nonblank rows; rule/result are nonblank and all text must fit measured boxes.',
            'start/end independently omit their visibility bound when None; no animation keys.',
            'answers_lettered=False omits answer letters only, retaining title, rule and result.',
        ),
    ),
}


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]

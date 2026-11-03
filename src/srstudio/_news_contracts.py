"""Authored News drawing contracts, including version-specific layout and nested UI clocks."""

from dataclasses import replace

from ._presentation_contracts import COMP, DURATION, FONT, GROUP, ID, LINES, MEASURE, PARENT, PIXEL, draw, timed
from .contracts import ParameterContract as P
from .contracts import PartContract

COPY = P(role='display-copy', description='Literal on-screen copy; not a timeline instant or a data-service request.')
SOURCE = P(
    role='source-credit',
    description='Caller-supplied outlet, date and verbatim headline. '
    'The record checks nonempty fields and a date shaped like Oct 30, 2026; it does not verify the story.',
)
BUBBLES = P(items=P(fields=(('at', PARENT), ('clock', COPY))))
COUNTS = P(items=P(prefix_items=(PARENT, COPY)))
PHONE_X = P(unit='frame pixels', space='phone-map', minimum=0, maximum=700)
PHONE_Y = P(unit='frame pixels', space='phone-map', minimum=0, maximum=678)
PHONE_POINT = P(
    prefix_items=(PHONE_X, PHONE_Y),
    unit='frame pixels',
    space='phone-map',
    anchors=(('origin', (0, 0)),),
    description='Origin at the phone screen under its header; '
    'the builder adds frame offset (190,616). These are not longitude/latitude.',
)
DIRECT_POINT = replace(
    PHONE_POINT,
    prefix_items=(replace(PHONE_X, minimum=None, maximum=None), replace(PHONE_Y, minimum=None, maximum=None)),
    description='Dashed guide in phone-map pixels. Endpoints are not clamped or checked against screen bounds.',
)
PANEL_X = P(unit='frame pixels', space='panel', minimum=214, maximum=486)
PANEL_Y = P(unit='frame pixels', space='panel', minimum=164, maximum=596)
STOPS = P(
    items=P(prefix_items=(COMP, PANEL_X, PANEL_Y)),
    description='First tuple is the initial position. Later times start a 0.22-second step to that target; '
    'positions are relative to panel origin (190,508) in the parent frame.',
)
SAFE = P(
    role='safe-area',
    description='The scene\'s declared layout.SafeArea, or None for a reel delivered before ADR 0218, drawn to x 1000 '
    'as it went out. With an area the words keep inside its region on every frame; an area whose left edge is past '
    'x 80 or whose right edge is short of x 720 is refused (ADR 0222).',
)
UI_SPAN = 'Requires finite 0 <= start < end. Frame-space overlay; a caller-owned parent controls the complete drawing.'
PANEL_COUNTS = (
    'counts is nonempty, begins exactly at start, increases strictly and stays before end. '
    'Each (time,display_copy) is held until the next time; counts are not animated numeric values.'
)


def with_safe(contract: PartContract) -> PartContract:
    """``contract`` with the version 2 drawings' declared safe area (ADR 0222)."""
    return replace(contract, parameters=(*contract.parameters, ('safe', SAFE)))


def graphic(*parameters: tuple[str, P], animated: bool = False, constraints: tuple[str, ...] = ()) -> PartContract:
    return timed(
        ('measure', MEASURE),
        ('id', ID),
        *parameters,
        clock='composition' if animated else 'static',
        constraints=(FONT, UI_SPAN, *constraints),
    )


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_SET = draw(
    (
        'end',
        P(
            unit='seconds',
            role='unused-compatibility',
            description='Accepted for call compatibility; does not affect this drawing.',
        ),
    ),
    clock='composition',
    constraints=(
        'Fixed monitor-light sweep times are 1.12..7.7 seconds regardless of end. '
        'The builder sets no visibility gate. Use a parent to control shot visibility.',
        'Blur, gradients and light pools are flat authored effects, not shared world-space lights.',
    ),
)
_BUG = graphic(constraints=('Static show-name chip on the top row. Uses measure at size 40; no auto-fit.',))
_TAG = graphic(constraints=('Static PARODY chip opposite the show name. Literal show labeling, not a fetched fact.',))
_SOURCE = graphic(
    ('source', SOURCE),
    ('small', PARENT),
    animated=True,
    constraints=(
        'Requires start < small < end. The headline card rises 200 frame pixels over 0.3 seconds using cubic-out '
        'composition keys. At small, a separate outlet/date chip replaces it by parent-clock visibility.',
        'Headline wraps into at most three lines, fitted from size 60 down to 42. No returned group.',
    ),
)
_LOWER = graphic(
    ('y', PIXEL),
    animated=True,
    constraints=(
        'Headline fits one line, reducing font size 60 to 38. Kicker and headline reject engagement bait.',
        'With slide=True the band arrives from x=-1100 over 0.3 seconds using cubic-out keys; words '
        'appear at start+0.3 on the parent timeline. slide=False keeps it static and shows words from start.',
    ),
)
_BANNER = graphic(
    animated=True,
    constraints=(
        'slide=True moves the band x=-1100 to zero in 0.3 seconds with cubic-out keys, then reveals its word. '
        'slide=False removes only the arrival motion; chevrons still move linearly across the full span.',
        'Chevron travel is 120*round((end-start)*2), capped at 3120 frame pixels.',
    ),
)
_TICKER = graphic(
    animated=True,
    constraints=(
        'Nonempty text items are checked for engagement bait, joined and repeated to cover the visible duration. '
        'The text run moves left at 150 frame pixels per second on the composition clock. '
        'measure must return positive advance for the nonempty combined string.',
    ),
)
_CAPTIONS = draw(
    ('lines', LINES),
    ('measure', MEASURE),
    ('id', ID),
    returns=GROUP,
    constraints=(
        FONT,
        'Returns the complete captions group. Each cue is a held parent-clock text panel, at most two lines '
        'at size 56. tints maps speaker names to panel fills; this is not native word-level karaoke.',
    ),
)
_PHONE = graphic(
    ('bubbles', BUBBLES),
    constraints=(
        'At least one bubble. Messages are stacked in input order, each visible from max(bubble.at,start) '
        'until end; arrivals at or after end are refused. clock is literal copy, not parsed or scheduled.',
        'Each clock-plus-message must fit one row at size 46. out selects the right side and mint fill; '
        'incoming messages use the left side and butter fill. Returns None, not a phone group.',
    ),
)

_CONTRACTS = {
    'news-set': _SET,
    'news-set@2': _SET,
    'news-desk': draw(constraints=(FONT, 'Draws the desk front with show lettering. Returns None.')),
    'news-desk@2': draw(
        constraints=(
            'Draws the desk, floor, mug, notepad and foreground camera; no lettering '
            'or bound font required. Contact shadows are authored flat shapes. Returns None.',
        )
    ),
    'news-bug': _BUG,
    'news-bug@2': _BUG,
    'news-parody-tag': replace(_TAG, constraints=(*_TAG.constraints, 'Version 1 measures the tag at size 44.')),
    'news-parody-tag@2': with_safe(
        replace(_TAG, constraints=(*_TAG.constraints, 'Version 2 measures the tag at size 40.'))
    ),
    'news-source-card': _SOURCE,
    'news-source-card@2': with_safe(
        replace(
            _SOURCE,
            constraints=(
                *_SOURCE.constraints,
                'beside_tag=True reserves the right corner for PARODY and refuses a credit that cannot fit between '
                'that tag and the show name. It does not draw the PARODY tag.',
            ),
        )
    ),
    'news-lower-third': _LOWER,
    'news-lower-third@2': with_safe(_LOWER),
    'news-banner': _BANNER,
    'news-banner@2': _BANNER,
    'news-ticker': _TICKER,
    'news-ticker@2': with_safe(_TICKER),
    'news-captions': _CAPTIONS,
    'news-captions@2': with_safe(_CAPTIONS),
    'news-phone': _PHONE,
    'news-phone@2': _PHONE,
    'news-missing-card': graphic(
        constraints=(
            'Static MISSING flyer with a fixed storage-lid drawing, not a caller-supplied object image. '
            'label must be nonblank and fit 212 frame pixels at size 36.',
        )
    ),
    'news-live-door': graphic(
        ('shut', PARENT),
        constraints=(
            'Optional shut must lie strictly inside start..end. At that instant held closed-door geometry '
            'replaces the ajar door and light. This is a cut, not interpolated hinge motion.',
        ),
    ),
    'news-route': graphic(
        ('track', P(items=PHONE_POINT)),
        ('pins', P(items=P(fields=(('x', PHONE_X), ('y', PHONE_Y))))),
        ('direct', P(prefix_items=(DIRECT_POINT, DIRECT_POINT))),
        ('marker', P(enum=('bird', 'dot'))),
        ('draw', DURATION),
        animated=True,
        constraints=(
            'Schematic phone map with no geographic asset binding. track needs at least two points with '
            'positive total length. Track points and pins must fit the phone map; direct is a dashed two-point guide.',
            'draw is duration, positive and at most end-start; None chooses min(2.4,end-start). '
            'Marker segment times are proportional to Euclidean length, rounded to milliseconds, with linear keys.',
            'Each complete route leg appears at its segment start and holds to end. '
            'There is no progressive stroke trim. '
            'Pin labels are horizontally clamped inside the phone; no group is returned.',
        ),
    ),
    'news-money-app': graphic(
        ('taps', P(items=PARENT)),
        ('refused_at', PARENT),
        ('notes', P(items=P(prefix_items=(PARENT, COPY)))),
        constraints=(
            'Drawn UI only: title, amount, action and refused are display copy; there is no payment or service call.',
            'refused_at is in [start,end) or None. The live button is replaced by a held disabled button at that time. '
            'taps are parent-clock instants; each ring holds for 0.28 seconds, clipped at end.',
            'At most two notes, each held from its supplied instant in [start,end) until end. '
            'Text and tap spacing must fit the phone; no gesture interpolation is applied.',
        ),
    ),
    'news-oven-clock': graphic(
        ('time', COPY),
        ('right_at', PARENT),
        constraints=(
            'time must match h:mm on a 12-hour clock. Digits are static seven-segment geometry and never advance. '
            'right_at strictly inside start..end swaps the wrong/right text tags by held visibility.',
        ),
    ),
    'news-forecast-map': graphic(
        ('counts', COUNTS),
        ('rain', P(prefix_items=(COMP, COMP))),
        animated=True,
        constraints=(
            PANEL_COUNTS,
            'Invented county and named pin; no weather lookup or geographic projection. rain is an interval '
            '(arrival,departure), not a duration; start < arrival and arrival+1.4 < departure <= end.',
            'Cloud travels linearly for 1.4 seconds on the composition clock, then rain oscillates by 12 pixels '
            'at 0.14-second key spacing. Cloud/rain visibility also uses these numbers on the parent timeline.',
        ),
    ),
    'news-corridor-map': graphic(
        ('one', STOPS),
        ('other', STOPS),
        ('counts', COUNTS),
        animated=True,
        constraints=(
            PANEL_COUNTS,
            'Two schematic dots, not skeletal people or a collision solver. Each nonempty stop track begins '
            'at start, increases strictly and leaves 0.22 seconds before end for its final step.',
            'Later stop times begin linear 0.22-second movements after held positions. Pixel bounds include '
            'the 44-pixel radius of each dot inside the corridor. Coordinates are panel-local, not world space.',
        ),
    ),
}

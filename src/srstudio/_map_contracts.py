"""Map kit discovery: geographic asset binding is distinct from world-space scene attachment."""

from dataclasses import replace
from typing import Annotated, TypedDict

from sr_core.scene import MapAsset

from ._presentation_contracts import COMP, DURATION, FONT, GROUP, ID, LINES, MEASURE, PARENT, PIXEL, draw, timed
from .contracts import ParameterContract as P
from .contracts import PartContract

LON = P(unit='degrees longitude', minimum=-180, maximum=180)
LAT = P(unit='degrees latitude', minimum=-90, maximum=90)
ZOOM = P(unit='zoom levels')
PLACE = P(fields=(('lon', LON), ('lat', LAT)))
SPAN = P(prefix_items=(COMP, COMP))
TimedSpan = Annotated[tuple[float, float], SPAN]


class Waves(TypedDict, total=False):
    inside: TimedSpan | None
    adelaide: TimedSpan | None
    rest: TimedSpan | None


class Fades(TypedDict, total=False):
    inside: TimedSpan
    adelaide: TimedSpan
    rest: TimedSpan


VIEW = P(
    type=MapAsset, role='map-asset', description='Existing map asset from this canvas; not a scene group or layer.'
)
RETURN = P(
    type=MapAsset,
    role='map-asset',
    description='Map asset for geographic overlays and further keys. '
    'The displayed layer and decorations are separate nodes in the supplied parent.',
)
RESOURCES = (
    'Map builders declare hashed and credited GeoJSON references under assets/maps. '
    'Use map_kit.install(project_root) to copy the shipped data before rendering; drawing does not copy files.'
)
GEOGRAPHIC = (
    'Geographic binding uses the engine map projection via geo(map_id,lon,lat), '
    'not 3D world-space grip, contact or collision constraints.'
)
LON_KEYS = P(items=P(prefix_items=(COMP, P(unit='degrees longitude'))))
LAT_KEYS = P(items=P(prefix_items=(COMP, P(unit='degrees latitude'))))
MOVE = P(
    fields=(
        ('begin', COMP),
        ('seconds', DURATION),
        ('lon', LON),
        ('lat', LAT),
        ('zoom', ZOOM),
        ('rho', P(unit='ratio', description='Native flyTo path-curvature parameter.')),
    )
)
DIVE = P(fields=(('begin', COMP), ('seconds', DURATION), ('lon', LON), ('lat', LAT), ('zoom', ZOOM)))


def geographic(contract: PartContract, *, asset: bool = False) -> PartContract:
    return replace(
        contract,
        returns=RETURN if asset else contract.returns,
        capabilities=(*contract.capabilities, ('geographic_attachment', True), ('returns_map_asset', asset)),
        constraints=(*contract.constraints, RESOURCES, GEOGRAPHIC),
    )


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


def on_asset(contract: PartContract) -> PartContract:
    return replace(contract, parameters=tuple((n, p) for n, p in contract.parameters if n != 'parent'))


_CONTRACTS = {
    'map-ground': draw(constraints=('Pale background and normalized radial glow fill the canvas.',)),
    'map-globe': geographic(
        timed(
            ('lon', LON),
            ('lat', LAT),
            ('spin', LON_KEYS),
            ('id', ID),
            ('padding', PIXEL),
            ('dive', DIVE),
            clock='composition',
            constraints=(
                'Orthographic map at zoom zero. padding is the frame-pixel fit inset; spin linearly '
                'keys center longitude.',
                'A dive fits inside the visible span and starts after spin keys. It keys longitude, latitude and zoom '
                'with sine-in-out interpolation; the decorative globe shade fades out halfway through the dive.',
            ),
        ),
        asset=True,
    ),
    'map-flat': geographic(
        timed(
            ('lon', LON),
            ('lat', LAT),
            ('zoom', ZOOM),
            ('moves', P(items=MOVE)),
            ('id', ID),
            clock='composition',
            constraints=(
                'Equirectangular map. Ordered nonoverlapping moves emit native flyTo '
                'operations with composition begin times and duration seconds; a fast-flight '
                'overlay blurs the same asset.',
                'end gates display, not necessarily the last flyTo endpoint. borders controls a separate border layer.',
            ),
        ),
        asset=True,
    ),
    'map-far-side': geographic(
        timed(
            ('zoom', ZOOM),
            ('flip', SPAN),
            ('what', P(enum=('land', 'people'))),
            ('id', ID),
            clock='composition',
            constraints=(
                'Flat overlay for a world centered on 0,0. flip must lie within '
                'start..end; center longitude shifts 0 to 180 and the display group scaleY changes 1 to -1. '
                'The input data stays unchanged. Returns only the map asset, not the mirrored display group.',
            ),
        ),
        asset=True,
    ),
    'map-equal-area': geographic(
        timed(
            ('lon', LON),
            ('lat', LAT),
            ('zoom', ZOOM),
            ('id', ID),
            ('shift', P(prefix_items=(LON_KEYS, LAT_KEYS))),
            clock='composition',
            constraints=(
                'Lambert azimuthal equal-area map. shift contains (longitude_keys,latitude_keys), each linear '
                'on the composition clock; it is not a point list or a duration.',
            ),
        ),
        asset=True,
    ),
    'map-pin': geographic(
        timed(
            ('view', VIEW),
            ('place', PLACE),
            ('measure', MEASURE),
            ('side', P(enum=('right', 'left', 'above', 'below'))),
            ('id', ID),
            clock='composition',
            constraints=(
                FONT,
                'Creates a scene overlay following the supplied map projection. place is name,lat,lon, in that order.',
                'figure adds the one-decimal latitude text; pop adds scale animation. The label is horizontally '
                'clamped to the safe width by a runtime expression. Returns None, not the pin group.',
            ),
        )
    ),
    'map-parallel': geographic(
        timed(
            ('view', VIEW),
            ('place', PLACE),
            ('drawn', DURATION),
            ('tag_from', PARENT),
            ('measure', MEASURE),
            ('id', ID),
            ('x', PIXEL),
            clock='composition',
            constraints=(
                'Mutates view by adding west/east routes, keyed from zero to full progress over drawn seconds, '
                'then reset at end. drawn is positive and shorter than end-start.',
                'tag_from=None draws no text and needs no measure or font. Otherwise measure and the bound font '
                'are required; a scene tag follows projected latitude at the fixed frame x. Returns None.',
            ),
        )
    ),
    'map-population': geographic(
        on_asset(
            draw(
                ('view', VIEW),
                ('waves', P(type=Waves)),
                ('id', ID),
                ('radius', PIXEL),
                ('fades', P(type=Fades | None)),
                clock='composition',
                constraints=(
                    'Mutates only the map asset with dot layers; no scene parent or returned handle. waves is nonempty '
                    'and selects inside/adelaide/rest. None shows a zone immediately; a span '
                    'reveals its feature batches.',
                    'Dots come from the shipped population dataset; this function does not retrieve '
                    'current population. '
                    'fades may name only selected zones and starts after their reveal. colours overrides zone paints.',
                    'Individual reveal fades last at least 0.05 seconds and can extend beyond a requested wave end.',
                ),
            )
        )
    ),
    'map-ring': timed(
        ('radius', PIXEL),
        ('x', PIXEL),
        ('y', PIXEL),
        ('measure', MEASURE),
        ('id', ID),
        constraints=(
            'A fixed frame-space ring plus outer veil; it does not attach to or track a map. radius>0 is pixels, '
            'not kilometers. Use ring_px with the appropriate equal-area view to convert a geographic radius.',
            'label=None needs no font or measure. A label requires both; its words are supplied copy.',
        ),
    ),
    'map-clock': timed(
        ('x', PIXEL),
        ('y', PIXEL),
        ('radius', PIXEL),
        ('hour', P(unit='hours')),
        ('runs', P(unit='hours', minimum=0)),
        ('id', ID),
        returns=replace(GROUP, space='returned-group', anchors=(('origin', (0, 0)),)),
        clock='composition',
        constraints=(
            'Returns a group centered on x,y. hour is the initial 24-hour reading; runs is total elapsed hours '
            'across start..end, not hours per second. Hour/minute hands rotate 30/360 degrees per elapsed hour.',
            'pop adds scale keys; no font or timezone lookup is used.',
        ),
    ),
    'map-daylight': geographic(
        timed(
            ('view', VIEW),
            ('places', P(items=PLACE)),
            ('day', P(unit='UTC datetime', role='day-start', description='Timezone-aware Python datetime instant.')),
            ('id', ID),
            clock='composition',
            constraints=(
                (
                    'Maps the next 24 hours from day into start..end. '
                    'Held gold/dark state uses the kit solar-altitude approximation at five-minute steps. '
                    'Each place follows the map projection; no timezone service, text or returned handle.',
                )
            ),
        )
    ),
    'map-stamp': timed(
        ('measure', MEASURE),
        ('y', PIXEL),
        ('id', ID),
        constraints=(
            FONT,
            'One or two lines of supplied evidence text fitted onto a paper strip; y is the top. '
            'No data-source verification or returned handle.',
        ),
    ),
    'map-captions': draw(
        ('lines', LINES),
        ('measure', MEASURE),
        ('id', ID),
        returns=GROUP,
        constraints=(
            FONT,
            'At most three wrapped lines per cue. tints maps speakers to fills; paper uses ink letters, '
            'any other fill uses paper letters. Returns the group containing parent-timed caption boxes.',
        ),
    ),
}

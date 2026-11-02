"""Retro Orbit discovery: baked foot placement, explicit lettering assets and no returned handles."""

from dataclasses import replace

from ._toon_contracts import draw, point
from .contracts import ParameterContract as P
from .contracts import PartContract

ID = P(role='scene-id', description='Caller-unique group ID; None or an empty string generates one.')
FONT_ID = P(role='font-asset-id', description='Existing scene font asset ID; this function does not load fonts.')
LETTERING = P(fields=(('display', FONT_ID), ('body', FONT_ID)))
LETTER_RULE = (
    'Lettering names explicit display/body font assets independently of Canvas.font_asset. '
    'None leaves signs blank; lettering is live text, not outlined paths. Both IDs are nonempty.'
)
STATIC = 'Static flat print paths; no animation, print finish or signature marks are emitted by this builder.'
FOOT = replace(point('Foot placement baked into reference-coordinate geometry, not a translated group.'), role='foot')


def prop(foot: tuple[float, float], size: float, *, lettered: bool = False) -> PartContract:
    return draw(
        ('at', FOOT),
        ('scale', P(unit='ratio', description='Strictly positive multiplier of the authored prop size.')),
        ('id', ID),
        *((('lettering', LETTERING),) if lettered else ()),
        constraints=(
            STATIC,
            f'Authored plate foot {foot} maps to at, with plate dimensions multiplied by {size}*scale '
            'before Toon reference conversion. Group position remains untransformed; no handle is returned.',
            'Use a caller-owned parent to move or hide the whole prop. No physical grip or standing constraint.',
            *(
                (
                    LETTER_RULE,
                    'Only Lettering.display is used for the FIELD NOTES label; body is retained in the record.',
                )
                if lettered
                else ()
            ),
        ),
    )


def contract(name: str) -> PartContract:
    return _CONTRACTS[name]


_CONTRACTS = {
    'toon-telescope': prop((310.0, 700.0), 0.66),
    'toon-moon-globe': prop((304.0, 572.0), 0.4),
    'toon-saturn-model': prop((304.0, 576.0), 0.4),
    'toon-field-notebook': prop((300.0, 545.0), 0.4, lettered=True),
    'toon-signal-clicker': prop((280.0, 590.0), 0.4),
    'toon-planetarium-salon': draw(
        ('lettering', LETTERING),
        constraints=(
            STATIC,
            LETTER_RULE,
            'Fixed 9:16 set with panoramic window, telescope and desk. display letters ORBIT and TODAY: SATURN; '
            'body letters WITH LYRA. Add signature marks and the shared print finish separately.',
        ),
    ),
    'toon-starlight-terrace': draw(
        ('lettering', LETTERING),
        constraints=(
            STATIC,
            LETTER_RULE,
            'Fixed 9:16 set with night sky, observatory, telescope and field table. Only display letters FIELD '
            'STATION; body is unused. Add signature marks and the shared print finish separately.',
        ),
    ),
}

"""Representative core Stick and Toon orbit calls, with explicit records and font asset IDs."""

from srstudio import registry, stick, toon_orbit
from support.stick_car import canvas

ENTRIES = [
    e for e in registry.entries() if e.kind != 'character' and e.module in ('srstudio.stick', 'srstudio.toon_orbit')
]
PLATE = stick.Plate('#654321', 'M 100 100 L 180 100 L 180 150 L 100 150 Z')
OPTIONS = {
    'stick-yard': dict(foliage=(PLATE,), seed=19),
    'stick-hook': dict(lettering=PLATE, start=1, end=2),
    'stick-headline': dict(outline=PLATE, fill=stick.Plate('#fefefe', PLATE.path), start=1, end=2),
    'stick-captions': dict(lines=(stick.Line(1, 2, 'READY', 48),), outline='layer'),
    'stick-words': dict(cues=(stick.Line(1, 1.5, 'Ready', 90), stick.Line(1.5, 2, 'now', 90)), y=1200, scrim=0.6),
    'stick-card': dict(text='Ready to draw', width=720, size=50),
    'stick-call': dict(
        tiles=(stick.Tile('Alex'), stick.Tile('Sam')),
        inbox=(stick.Mail('Sam', 'Ready', True),),
        speaking='Alex',
        highlight=0,
    ),
    'toon-telescope': dict(at=(300, 900), scale=0.8, id='telescope'),
    'toon-moon-globe': dict(at=(300, 900), scale=0.8, id='moon'),
    'toon-saturn-model': dict(at=(300, 900), scale=0.8, id='saturn'),
    'toon-field-notebook': dict(
        at=(300, 900), scale=0.8, id='notebook', lettering=toon_orbit.Lettering('display', 'body')
    ),
    'toon-signal-clicker': dict(at=(300, 900), scale=0.8, id='clicker'),
    'toon-planetarium-salon': dict(lettering=toon_orbit.Lettering('display', 'body')),
    'toon-starlight-terrace': dict(lettering=toon_orbit.Lettering('display', 'body')),
}
HANDLES = {'stick-hook', 'stick-headline', 'stick-card', 'stick-call'}


def drawing(entry):
    cv = canvas()
    return cv, entry.builder(cv, cv.comp, **OPTIONS.get(entry.name, {}))

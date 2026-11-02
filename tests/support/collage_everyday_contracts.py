"""Representative everyday paper drawings, including typed copy and authored motion."""

from srstudio import anatomy, registry
from support.collage import canvas

ENTRIES = tuple(e for e in registry.entries() if e.module == 'srstudio.collage_everyday')
SCREEN_RETURNS = {'collage-phone', 'collage-battery-insert'}
OPTIONS = {
    'collage-food': dict(kind='sushi', x=400, y=800, size=480, tilt=20),
    'collage-lasagna': dict(x=400, y=800, w=260, tilt=-10),
    'collage-flip-card': dict(sides=((0, 'YES'), (3, 'NO'))),
    'collage-magnifying-glass': dict(x=400, y=800, size=210),
    'collage-router': dict(light=((0, 'off'), (1, 'green'), (3, 'red')), unplugged=3),
    'collage-phone': dict(x=100, y=200, w=400, h=700, tilt=15),
    'collage-battery-insert': dict(levels=((0, 80), (1, 20), (2, 0)), dead=3),
    'collage-bubble': dict(text='Hello', x=100, y=200, w=400, h=160, size=48, mine=True),
    'collage-thumb': dict(x=400, y=800, size=340),
    'collage-alarm-clock': dict(x=100, y=200, w=400, text='07:00'),
    'collage-cereal-box': dict(x=100, y=200, w=400, h=600, tilt=10),
    'collage-duvet': dict(top=1600),
    'collage-tablecloth': dict(top=1500),
    'collage-salt-shaker': dict(x=400, y=800, size=70),
    'collage-chip-bag': dict(x=400, y=800, w=450, h=600, label='CHIPS', size=80),
    'collage-chip': dict(x=400, y=800, part='half', size=105, tilt=15),
    'collage-certificate': dict(text='WELL DONE', x=100, y=200, w=600, h=400, size=60, tilt=10),
    'collage-snapshot': dict(x=100, y=200, w=400, tilt=10),
    'collage-gust': dict(frm=(100, 200), to=(700, 500), start=1, end=3, lines=2),
    'collage-bill': dict(text='RENT', x=400, y=800, legs=False),
    'collage-confetti': dict(start=1, end=4, turn=2, count=3, key='discovery'),
    'collage-arm': dict(who='deb', frm=(600, 1200), to=(400, 800), side=1, view=anatomy.View.POV),
}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    return cv, entry.builder(cv, cv.comp, **OPTIONS[entry.name])

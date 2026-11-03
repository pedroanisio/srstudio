"""Collage room, photo, forecast and clinic drawings for authored discovery."""

from srstudio import collage_forecast, collage_sets, registry
from srstudio.collage_group import Place
from support.collage import canvas

MODULES = {
    'srstudio.collage_sets',
    'srstudio.collage_photo',
    'srstudio.collage_odds',
    'srstudio.collage_article',
    'srstudio.collage_forecast',
}
ENTRIES = tuple(e for e in registry.entries() if e.module in MODULES)
PLACES = {'gary': Place(320, 1800, 0.55), 'rosa': Place(780, 1800, 0.6)}
POSES = {'gary': ('wide', 'grin', 'shrug'), 'rosa': ('closed', 'smile', 'hold')}
OPTIONS = {
    **{'collage-' + name: {} for name in collage_sets.SETS},
    'collage-sign': dict(text='HELLO', x=100, y=200, w=400, h=160, size=50, tilt=10),
    'collage-chart': dict(x=100, y=200, w=400, h=500, values=(0.25, 0.5, 1)),
    'collage-tv': dict(x=100, y=800, w=600),
    'collage-call-buttons': {},
    'collage-cake-slice': dict(x=500, y=900, cuts=(1, 2)),
    'collage-eye-chart': dict(x=200, y=400, rows=('E', 'FP'), sharp=(1, 2), end=5, blur_at=4),
    'collage-lens-frame': dict(x=540, y=900, spread=160),
    'collage-sensor-tap': dict(x=500, y=1500, runs=((1, 2), (1.5, 3))),
    'collage-spinach': dict(x=540, y=1000, width=120),
    'collage-full-glass': dict(x=500, y=1500, full=0.75, scale=1.5),
    'collage-water-jug': dict(x=500, y=1500, scale=0.75),
    'collage-doctor-scale': dict(x=400, base=1880, bar_at=2, bar_to=1100, bar_from=790, end=4),
    'collage-phone-timer': dict(x=800, y=1500, start=1, seconds=3, tick=0.5, scale=1.2),
    'collage-viewfinder': dict(start=1, seconds=3, tick=0.5),
    'collage-sofa': {},
    'collage-flash': dict(at=2, hold=0.25, fade=0.5),
    'collage-photo-print': dict(places=PLACES, poses=POSES, x=90, y=600, width=900, tilt=-3, blur=('gary', 'rosa')),
    'collage-article': dict(x=190, y=400, w=700, h=1200, headline='THE BIG NEWS', sender='FROM A FRIEND'),
    'collage-weather-map': dict(x=100, y=200, w=450, h=600, arrow='EXES', slide=(1, 2), clock=('8:59', (1, 4))),
    'collage-thread': dict(
        x=190,
        y=800,
        w=700,
        h=1040,
        contact='PRIYA',
        clock=((0, '8:59'), (3, '9:00')),
        call='GARY',
        messages=(collage_forecast.Message('HEY', 1), collage_forecast.Message('HELLO', 2, True)),
    ),
}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    return cv, entry.builder(cv, cv.comp, **OPTIONS[entry.name])

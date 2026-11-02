"""Actual Saga scenery, props and graphics used by discovery examples."""

from srstudio import registry, saga
from srstudio import saga_sets as sets
from support.gloss import font
from support.saga import canvas

ENTRIES = tuple(e for e in registry.entries() if e.module == 'srstudio.saga_sets' or e.name == 'saga-handbook')
JAB = sets.Jab(1, '#efe2c4', saga.SKIN['deep'], (404, 1040), 1.55)
OPTIONS = {
    'saga-space': dict(planet=True),
    'saga-bridge': {},
    'saga-cantina': dict(stare=((1, 2), (3, 6))),
    'saga-cantina-bar': {},
    'saga-desert': dict(shade=True),
    'saga-cockpit': dict(jump=((0.5, 1.5),), hit=2),
    'saga-cockpit-console': dict(jab=JAB, hit=2, ledge=True),
    'saga-compactor': dict(walls=(1, 3), travel=120, start_px=40, door=2.5),
    'saga-holo': dict(panels=(sets.Panel(0, 'STATUS', 'A call', face='juno', fade=True), sets.Panel(2, 'NEXT'))),
    'saga-cube': dict(at=(540, 900), size=400, boom=1),
    'saga-freighter': dict(at=(500, 900), scale=0.8, flip=True),
    'saga-pebble': dict(at=(700, 1500), lift=1, rise=160),
    'saga-fighter': dict(at=(500, 900), scale=1.2, flip=True),
    'saga-handbook': dict(at=(100, 300), scale=0.5, talk=((0, 'closed'), (1, 'open'))),
    'saga-hook': dict(text='Where is the exit?', talk=((0, 'closed'), (1, 'open'))),
    'saga-entry': dict(title='An entry', body='A body.', talk=((0, 'closed'), (1, 'open')), legible=True),
}
TEXT = {'saga-holo', 'saga-hook', 'saga-entry'}
STATIC = {'saga-cantina-bar', 'saga-desert', 'saga-freighter', 'saga-fighter'}


def drawing(part, *, local=False):
    cv = canvas()
    cv.local_time = local
    kwargs = dict(OPTIONS[part.name], end=4)
    if part.name in TEXT:
        kwargs['font'] = font()
    return cv, part.builder(cv, cv.comp, **kwargs)

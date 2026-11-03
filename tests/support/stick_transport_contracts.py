"""Representative transport drawings with explicit scene objects and performance records."""

from srstudio import registry, stick, stick_car
from support.stick_car import canvas

MODULES = {
    'srstudio.stick_airport',
    'srstudio.stick_car',
    'srstudio.stick_street',
    'srstudio.stick_windshield',
    'srstudio.stick_roadtrip',
}
ENTRIES = [e for e in registry.entries() if e.module in MODULES]
OPTIONS = {
    'stick-car': dict(end=3, scroll=stick_car.Scroll(160, 27), passing=(1.5,), defocus=2),
    'stick-cockpit': dict(keys=(stick.RigKey(0, 'drive'), stick.RigKey(1.5, 'turn')), end=3),
    'stick-ride': dict(end=1.03, amplitude=2, phase=0.7, step=0.25),
    'stick-laptop': dict(x=100, y=1290, title='INBOX', rows=('Ready',)),
    'stick-phone': dict(sender='Alex', text='Ready?', buzz=(1,)),
    'stick-windshield': dict(end=3, speed=2.5),
    'stick-windshield-dash': dict(end=3, buzz=(0.5,), down=2),
    'stick-carry-on': dict(x=300, y=1700),
    'stick-bag-scale': dict(x=300, y=1700, readings=((0, None), (1, '23.1')), end=3),
    'stick-coat-ball': dict(x=540, chin=900, radius=200, layers=4, hats=2, scarves=2, shoes=True),
    'stick-palm': dict(x=500, y=1500),
    'stick-suitcases': dict(x=500, y=1300),
    'stick-road-sign': dict(end=3, text='AIRPORT'),
    'stick-swim-ring': dict(x=500, y=1300, rx=100, ry=140),
    'stick-blinker': dict(x=500, y=1300, end=3, clicks=(0.5, 2.9)),
}
NONE = {
    'stick-car',
    'stick-cockpit',
    'stick-ride',
    'stick-car-seat',
    'stick-windshield',
    'stick-windshield-dash',
    'stick-gate',
    'stick-cabin',
    'stick-home-street',
    'stick-road-plan',
    'stick-road-ahead',
}
LOCAL = {
    'stick-laptop',
    'stick-phone',
    'stick-top-car',
    'stick-side-car',
    'stick-road-sign',
    'stick-swim-ring',
    'stick-blinker',
}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    parent = cv.group(cv.comp, 'ride-target', y=300) if entry.name == 'stick-ride' else cv.comp
    return cv, entry(cv, parent, **OPTIONS.get(entry.name, {}))

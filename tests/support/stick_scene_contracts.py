"""Actual Stick scene drawings used to verify discovery without changing drawing output."""

from srstudio import registry, stick, stick_shop
from support.stick_car import canvas

MODULES = {
    'srstudio.stick_door',
    'srstudio.stick_flat',
    'srstudio.stick_gym',
    'srstudio.stick_school',
    'srstudio.stick_shop',
    'srstudio.stick_bed',
    'srstudio.stick_table',
}
ENTRIES = [e for e in registry.entries() if e.module in MODULES]
OPTIONS = {
    'stick-entrance': dict(end=3, night=((0, 0.2), (2, 0.8)), clock=0.25),
    'stick-street-lens': dict(end=3, night=((0, 0.2), (2, 0.8))),
    'stick-glass-door': dict(end=3, shut=1),
    'stick-snow-cap': dict(x=300, y=500, step=2, width=140),
    'stick-marathon': dict(end=3, count=3, base=952, size=96),
    'stick-murphy-bed': dict(end=3, drop_at=0.5, sleeper=stick.PLAIN, talk=((1, 1.5),)),
    'stick-gym': dict(end=3, sunrise=0.5),
    'stick-gym-counter': dict(sign='WELCOME', fine='Ask at the desk'),
    'stick-essay': dict(
        lines=('My dad works.', 'He takes a nap.'),
        title='DAD',
        by='ALEX',
        shown=2,
        mark=1,
        mark_at=0.5,
        grade='A',
        note='Good work',
        note_at=1.5,
        at=(400, 800),
        scale=0.6,
    ),
    'stick-kiosk': dict(
        screens=(
            stick_shop.Screen(0, 'Ready'),
            stick_shop.Screen(1, 'Help', 'error'),
            stick_shop.Screen(2, 'Employee', 'award', stick.PLAIN),
        ),
        end=3,
        alarm=(0.5, 2),
    ),
    'stick-avocado': dict(x=100, y=500, scale=0.8),
    'stick-name-badge': dict(x=100, y=500, name='Alex', title='Staff'),
    'stick-duvet': dict(end=3, x=1480, y=1510, lift=((0, 0), (1.5, -25), (3, 10))),
    'stick-eye-mask': dict(x=300, y=500, scale=0.8),
    'stick-recorder': dict(x=300, y=500, end=3, lines=2, live=True),
    'stick-lights-low': dict(area=(100, 200, 600, 900), pool=(400, 500, 180)),
    'stick-clipboard': dict(turned=True, heading='SIGN HERE'),
    'stick-wall-brackets': dict(x=300, y=500, span=200, scale=0.8),
    'stick-folded-bedding': dict(x=999, y=500, scale=0.8, slide=((0, 700), (2, 300))),
}
NONE = {
    'stick-entrance',
    'stick-street-lens',
    'stick-glass-door',
    'stick-studio-flat',
    'stick-gym',
    'stick-classroom',
    'stick-checkout',
}
LOCAL = {
    'stick-marathon',
    'stick-essay',
    'stick-avocado',
    'stick-name-badge',
    'stick-eye-mask',
    'stick-wall-brackets',
    'stick-folded-bedding',
}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    result = entry.builder(cv, cv.comp, **OPTIONS.get(entry.name, {}))
    return cv, result

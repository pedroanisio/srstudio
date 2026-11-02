"""Real Soft prop builds covering schedules, dimensions, copy and callback ownership."""

from srstudio import registry, soft_props
from support.soft_props import canvas

MODULES = {'srstudio.soft_props', 'srstudio.soft_odds'}
ENTRIES = tuple(e for e in registry.entries() if e.module in MODULES)
OPTIONS = {
    'soft-status-badge': dict(
        states=(
            soft_props.BadgeState('ready', 'READY', '#44AA66', 1, 3),
            soft_props.BadgeState('off', 'OFF', '#AA4444', 4, 6, True),
        ),
        box=(100, 400, 420, 92),
    ),
    'soft-beach-call': dict(w=600, h=400, name='SAM', tag=(20, 330)),
    'soft-cake': dict(front='HELLO', back='AGAIN', turn_at=2, lettering=((1, 3), (4, 6))),
    'soft-bench': dict(x=500, seat=1400, width=800),
    'soft-briefcase': {},
    'soft-necktie': {},
    'soft-shovel': dict(angle=25, rust=False),
    'soft-hive': {},
    'soft-cane': dict(x=400, y=1500, height=500, lean=20, flip=True),
    'soft-phone': {},
    'soft-glare-lamp': dict(x=400, y=1500, scale=2, reach=300),
    'soft-parcels': dict(x=100, floor=1500, columns=3, rows=2, size=100),
    'soft-whisk': {},
    'soft-time-card': dict(
        states=(soft_props.TimeState('2000', 1, 3), soft_props.TimeState('2026', 4, 6)),
        box=(100, 400, 420, 120),
        size=70,
    ),
    'soft-tongs': dict(angle=30, clicks=(1, 2)),
    'soft-grill': dict(end=6, burgers=3, char=3, flames=((0, 0), (1, 1), (3, 3)), flip=2),
    'soft-smoke': dict(end=6, rows=((0, 0), (1, 1), (3, 3))),
    'soft-pizza-box': {},
    'soft-bottle': dict(color='#336699'),
    'soft-washer': dict(end=6, stop=4, open_at=((1, 5), (2, 3)), loads=((1, 'brick'), (2, 'coins'))),
    'soft-brick': dict(angle=20),
    'soft-bowling-ball': {},
    'soft-coin-bag': {},
    'soft-tv': dict(end=6, off=4),
    'soft-home-fridge': dict(end=6, off=4),
    'soft-dust': dict(x=400, y=500, start=1, end=4, width=200, fall=600),
    'soft-dimmer': dict(rows=((0, 0), (1, 0.4), (4, 0.8))),
    'soft-notice': dict(text='KEEP QUIET', shown=((1, 3), (4, 6)), size=48),
    'soft-book': dict(angle=20, color='#336699'),
    'soft-yogurt': {},
    'soft-rumble': dict(spans=((1, 2), (3, 4)), color='#336699'),
    'soft-hush-finger': dict(reach=-100, fill='#D8A477'),
}
ABSOLUTE = {
    'soft-status-badge',
    'soft-beach-call',
    'soft-bench',
    'soft-cane',
    'soft-glare-lamp',
    'soft-parcels',
    'soft-time-card',
    'soft-dust',
    'soft-dimmer',
}
PLACED = tuple(e for e in ENTRIES if e.name not in ABSOLUTE)
KEYED = {
    'soft-status-badge',
    'soft-cake',
    'soft-time-card',
    'soft-tongs',
    'soft-grill',
    'soft-smoke',
    'soft-washer',
    'soft-tv',
    'soft-home-fridge',
    'soft-dust',
    'soft-dimmer',
    'soft-notice',
    'soft-rumble',
}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    kw = dict(OPTIONS[entry.name])
    if entry.name not in ABSOLUTE:
        kw = dict(x=400, y=900, scale=2) | kw
    if entry.name in ('soft-beach-call', 'soft-phone'):
        slot = 'guest' if entry.name == 'soft-beach-call' else 'screen'

        def content(parent):
            cv.rect(cv.group(parent, 'slot-' + slot), 0, 0, 20, 20, '#FF0000')
            return object()

        kw[slot] = content
    return cv, entry.builder(cv, cv.comp, id=entry.name, **kw)

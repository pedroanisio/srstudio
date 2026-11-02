"""Explicit representative inputs for the Stick home, office and everyday drawing contracts."""

from srstudio import registry, stick
from support.tip_tablet import canvas

MODULES = {'srstudio.stick_home', 'srstudio.stick_office', 'srstudio.stick_odds'}
ENTRIES = [e for e in registry.entries() if e.module in MODULES]
XY = dict(x=500, y=1100)
OPTIONS = {
    'stick-from-above': dict(end=3, hair='bun', phone='#123456'),
    'stick-handset': XY,
    'stick-key': XY,
    'stick-chair': XY,
    'stick-smoke-alarm': {**XY, 'flashes': (0.5, 2)},
    'stick-mound': XY,
    'stick-shovel': XY,
    'stick-message-insert': dict(sender='Alex', text='Meet me here'),
    'stick-reply-screen': dict(name='Alex', sent='Ready?', answer='Yes'),
    'stick-box': XY,
    'stick-receipt': {**XY, 'length': 300, 'unroll': (0.5, 2)},
    'stick-poster': {**XY, 'w': 400, 'h': 300, 'text': 'OPEN'},
    'stick-headset': XY,
    'stick-xray': dict(end=3, items=(('chicken', 540, 900, 1), ('rolling-pin', 540, 1300, 0.5))),
    'stick-plate': XY,
    'stick-spoon': dict(grip=(500, 1000), bowl=(700, 900), full=True),
    'stick-robe': dict(keys=(stick.RigKey(0, 'stand'), stick.RigKey(1.5, 'wave')), end=3, poses=stick.STANDING),
    'stick-foil-parcel': XY,
    'stick-foil-note': dict(text='Back soon'),
    'stick-queue': dict(end=3, turn=1.5, rows=3, legs=True),
    'stick-book': XY,
    'stick-duffel': XY,
    'stick-wheelie-bin': XY,
    'stick-trash-truck': XY,
    'stick-slipper': XY,
    'stick-sparks': {**XY, 'end': 3},
    'stick-planks': dict(x=120, floor=1400),
    'stick-wardrobe': dict(x=120, floor=1400, stage='half'),
    'stick-drill': XY,
    'stick-screws': XY,
    'stick-manual-page': dict(step=2, drawing='argument', bubble='This side in!'),
    'stick-caller': {**XY, 'name': 'Alex', 'ring': (0.5, 2)},
    'stick-mug': XY,
    'stick-arm-cast': dict(elbow=(400, 1000), hand=(550, 900)),
    'stick-neck-brace': XY,
    'stick-parrot': XY,
    'stick-flames': {**XY, 'end': 3},
    'stick-tombstone': dict(x=500, words='MONDAY'),
    'stick-meteor': dict(end=3, land=1.5),
}
NONE = {'stick-kitchen', 'stick-kitchen-plan', 'stick-bedroom', 'stick-table', 'stick-coffee-corner'}
LOCAL = {
    'stick-from-above',
    'stick-box',
    'stick-receipt',
    'stick-headset',
    'stick-plate',
    'stick-robe',
    'stick-foil-parcel',
    'stick-book',
    'stick-duffel',
    'stick-wheelie-bin',
    'stick-trash-truck',
    'stick-slipper',
    'stick-sparks',
    'stick-planks',
    'stick-wardrobe',
    'stick-drill',
    'stick-screws',
    'stick-caller',
}


def drawing(entry):
    cv = canvas()
    return cv, entry(cv, cv.comp, **OPTIONS.get(entry.name, {}))

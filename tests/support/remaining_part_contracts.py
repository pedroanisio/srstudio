"""Representative drawings for the last default non-character discovery families."""

from srstudio import cel, registry, signature
from support.saga import canvas

NAMES = (
    'cel-room',
    'cel-lettering',
    'signature-cactus',
    'signature-code',
    'video-tile',
    'desk-phone',
    'apron-spare',
    'trial-tag',
    'wire-car',
    'wire-jet',
    'show-bug',
)
ENTRIES = tuple(e for e in registry.entries() if e.name in NAMES)
KEYS = (cel.CameraKey(0, 1, 0, 0), cel.CameraKey(1, 1.2, -20, -30))
ROOM_KEYS = (cel.CameraKey(0, 1, 0, 0), cel.CameraKey(1, 1.1, -10, -15))
CAPTION = cel.Caption('caption', 0.5, 2, 'Hello', 'Hello', (cel.Box(100, 200, 300, 60, 'M110 210 L120 240'),))
OPTIONS = {
    'cel-room': dict(keys=KEYS, room_keys=ROOM_KEYS, duration=4),
    'cel-lettering': dict(caption=CAPTION),
    'signature-cactus': dict(x=800, y=1500, scale=0.5, act=signature.Act(4, ((0, 0), (1, 20)), 1)),
    'signature-code': dict(x=100, y=200, height=16, angle=-5, align='end'),
    'video-tile': dict(x=80, y=300, plate='HOST'),
    'desk-phone': dict(x=500, y=900, scale=0.5, title='CALL', lines=((1, 'HELLO'),), buzzes=((0.5, 0.7),), turns=1.5),
    'apron-spare': dict(x=540, y=800, scale=0.8),
    'trial-tag': dict(x=540, y=800, label='TRIAL'),
    'wire-car': dict(width=200, seed='contract', view='side'),
    'wire-jet': dict(width=200, seed='contract', view='side'),
    'show-bug': dict(number=123),
}


def drawing(part, *, local=False):
    cv = canvas()
    cv.local_time = local
    parent = cel.world(cv, cv.comp, KEYS, 4) if part.name == 'cel-room' else cv.comp
    return cv, part.builder(cv, parent, **OPTIONS[part.name])

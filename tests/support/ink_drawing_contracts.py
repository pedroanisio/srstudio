"""Real Ink drawings with take clocks, delegated options and literal interface copy."""

from srstudio import ink_meter, ink_phone, registry
from support.ink_meter import canvas, take

MODULES = {
    'srstudio.ink',
    'srstudio.ink_phone',
    'srstudio.ink_meter',
    'srstudio.ink_doorbell',
    'srstudio.ink_vacuum',
    'srstudio.ink_captcha',
}
ENTRIES = tuple(e for e in registry.entries() if e.module in MODULES and e.kind != 'character')
PARENT_RETURNS = {'ink-desk-shot', 'ink-wide', 'ink-router-wide'}
PARTIAL_RETURNS = {
    'ink-router-shot',
    'ink-phone-shot',
    'ink-kerb',
    'ink-doorstep',
    'ink-vacuum-shot',
    'ink-doorbell-view',
}
DELEGATES = {'ink-phone-shot': 'phone', 'ink-kerb': 'meter', 'ink-doorstep': 'doorbell', 'ink-vacuum-shot': 'vacuum'}
CHAT = dict(
    contact='Ada',
    bubbles=(ink_phone.Bubble('Hello', at=1), ink_phone.Bubble('Hi', False, 2.5)),
    status=((0.5, 'sending'), (1.5, 'sent'), (3, 'read')),
    typing=(1.6, 2.5),
)
OPTIONS = {
    'ink-laptop': dict(x=100, y=200, scale=1.5),
    'ink-desk': {},
    'ink-hand': dict(x=400, y=500, scale=2, action='press', at=1),
    'ink-desk-shot': dict(take=take('human', 4, mood='angry'), scale=0.8),
    'ink-closeup': dict(take=take('human', 4, mood='question'), zoom=1.5, gesture=True),
    'ink-printer-shot': dict(take=take('sfx', 4), close=True, fps=8),
    'ink-wide': dict(take=take('human', 4, mood='angry'), fps=8),
    'ink-router-shot': dict(
        take=take('router', 4), close=True, power='down', drop_at=2, hand_action='press', hand_at=1
    ),
    'ink-router-wide': dict(take=take('router', 4)),
    'ink-phone': CHAT,
    'ink-phone-shot': CHAT,
    'ink-kerb': dict(
        take=take('human', 4, mood='angry'), tow=-0.25, view=ink_meter.TOW_TIGHT, display=((0, 'PAY'), (2, 'DONE'))
    ),
    'ink-doorstep': dict(take=take('doorbell', 4), close=True, number='12', mark=('allow', 1)),
    'ink-vacuum-shot': dict(take=take('vacuum', 4), state='stop', display='HOME'),
    'ink-app-screen': dict(
        take=take(duration=4),
        title='Park',
        rows=(ink_meter.AppRow('Name', 0.5, tick=1), ink_meter.AppRow('Code', 1, taken=2)),
        progress=(1, 2),
        stars=3,
    ),
    'ink-doorbell-view': dict(take=take('human', 4), tags=((0, 'VISITOR'), (2, 'FRIEND')), clock='22:40', shades=True),
    'ink-floor-map': dict(take=take('vacuum', 4), trace=(0.5, 3.5), relabel=('BATH', 'OFFICE', 2)),
    'ink-captcha': dict(
        prompt='Select traffic lights',
        tiles=('light', 'car', 'tree', 'laptop', 'happy-light', 'car', 'tree', 'laptop', 'sad-light'),
        picks=((1, 0), (2, 8)),
        verdict=(3, 'TRY AGAIN'),
    ),
    'ink-checkbox': dict(label="I'm not a robot", tick_at=1),
}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    return cv, entry.builder(cv, cv.comp, **OPTIONS[entry.name])

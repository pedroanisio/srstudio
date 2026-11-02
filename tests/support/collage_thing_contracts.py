"""Actual Collage table and corner props for discovery and drawing parity."""

from srstudio import registry
from support.collage import canvas

ENTRIES = tuple(e for e in registry.entries() if e.module == 'srstudio.collage_things')
FIXED = {'collage-counter', 'collage-ring-corner', 'collage-eye-twitch'}
OPTIONS = {
    'collage-handset': dict(x=500, y=900, tilt=20),
    'collage-desk-phone': dict(x=540, y=1500, w=420, display='PARIS', off_hook=True, size=40),
    'collage-resume': dict(x=540, y=900, w=500, turn=3),
    'collage-fork': dict(x=200, y=900, tilt=-20),
    'collage-gravy-boat': dict(x=540, y=1500, forks=5),
    'collage-tiny-cup': dict(x=540, y=1500),
    'collage-wine-glass': dict(x=540, y=1500),
    'collage-bank-card': dict(x=540, y=900, name='GARY'),
    'collage-receipt': dict(x=540, y=900, torn=True),
    'collage-wallet': dict(x=540, y=900, cards=('#e63946', '#2a9d8f')),
    'collage-counter': dict(top=1500),
    'collage-till': dict(x=540, y=1300, text='PAID', size=40),
    'collage-stool': dict(x=540, y=1500),
    'collage-towel': dict(x=540, y=900, tilt=15),
    'collage-ring-corner': dict(x=960, y=900, h=720, reach=1100),
    'collage-eye-twitch': dict(who='brent', times=(1, 1.04, 2)),
}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    return cv, entry.builder(cv, cv.comp, **OPTIONS[entry.name])

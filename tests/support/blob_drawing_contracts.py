"""Deterministic real Blob room and furniture drawings for semantic discovery checks."""

from srstudio import registry
from support.soft_props import canvas

ENTRIES = tuple(e for e in registry.entries() if e.module == 'srstudio.blob' and e.kind != 'character')
SLOTS = {'soft-sofa': 'on_sofa', 'soft-home': 'on_sofa', 'soft-meeting-room': 'on_screen'}
HELPERS = {
    'soft-laptop': ('keyboard',),
    'soft-office': ('keyboard',),
    'soft-sofa': ('sofa_seat',),
    'soft-home': ('sofa_seat',),
    'soft-swivel-chair': ('swivel_seat',),
    'soft-meeting-room': ('meeting_screen', 'meeting_table_top', 'swivel_seat', 'keyboard', 'room_point', 'wall_quad'),
    'soft-break-room': ('room_point', 'wall_quad', 'floor_quad'),
}


def drawing(entry, *, local=False, id=None):
    cv = canvas()
    cv.local_time = local
    kw = dict(id=id or entry.name)
    if entry.kind == 'location':
        kw['shots'] = ((1, 3), (4, 6))
    if entry.name == 'soft-home':
        kw['lamp_talk'] = ((1, 2), (4, 5))
    if entry.name in SLOTS:
        slot = SLOTS[entry.name]

        def content(parent):
            cv.rect(cv.group(parent, 'slot-' + slot), 0, 0, 20, 20, '#FF0000')
            return object()

        kw[slot] = content
    return cv, entry.builder(cv, cv.comp, **kw)

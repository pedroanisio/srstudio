"""Real Soft room and insert drawings, including callbacks and optional motion."""

from srstudio import registry, soft_bedtime, soft_closet, soft_inbox, soft_sets
from support.soft_props import canvas

MODULES = {
    'srstudio.soft_sets',
    'srstudio.soft_front',
    'srstudio.soft_bedtime',
    'srstudio.soft_closet',
    'srstudio.soft_inbox',
}
ENTRIES = [e for e in registry.entries() if e.module in MODULES and e.kind != 'character']
SHOTS = (soft_sets.Shot(0), soft_sets.Shot(2, 1.4, 300, 900))
OPTIONS = {
    'soft-park': dict(growth=((0, 0), (2, 2), (5, 4)), seated=((1, 3),), shots=SHOTS),
    'soft-bedroom': dict(
        lights=(
            soft_sets.Light(0, 'day'),
            soft_sets.Light(1, 'phone', 400, 900),
            soft_sets.Light(3, 'lamp', 100, 1200),
            soft_sets.Light(5, 'dark'),
            soft_sets.Light(7, 'day'),
        ),
        shots=SHOTS,
    ),
    'soft-playroom': dict(dim=soft_sets.Dim(1, 0.5, 5, 450, 900), shots=SHOTS),
    'soft-front-room': dict(wedged=((1, 2), (4, 5)), shots=SHOTS),
    'soft-wall-clock': dict(x=400, y=600, time='20:15', scale=1.2),
    'soft-picture-book': dict(slide=soft_bedtime.BookSlide(1, 0.5, 120, 50, 30), scale=2),
    'soft-bedside-lamp': dict(on=1, off=4),
    'soft-open-briefcase': dict(shut=3),
    'soft-handshake': dict(start=1, end=3, pumps=2),
    'soft-quilt-pull': dict(to=1300, at=1, seconds=0.5),
    'soft-door': dict(rows=(soft_closet.Door(150, 340, 640, ((1, 3), (2, 2.5))),), end=7),
    'soft-mop': dict(x=300, y=1500, scale=1.5, tips=(1, 3), to=50),
    'soft-closet': dict(start=1, end=5, veil=0.85),
    'soft-mug': dict(x=500, y=1200, scale=1.5, empty=True),
    'soft-mail-screen': dict(counts=(soft_inbox.Count('1', 1, 3), soft_inbox.Count('2', 3, 5)), scale=2),
    'soft-mail-list': dict(rows=('First', 'Second'), marked=1, scroll=((0, 0), (1, -20), (2, -30)), scale=2),
    'soft-call-screen': dict(pressed=2),
    'soft-star-card': dict(x=500, y=1200, tap=1, stars=3, scale=2),
}
SLOTS = {
    'soft-park': ('cast',),
    'soft-bedroom': ('cast', 'held'),
    'soft-playroom': ('cast',),
    'soft-front-room': ('hall', 'behind', 'cast'),
    'soft-door': ('between',),
    'soft-closet': ('behind',),
}


def drawing(part, *, local=False):
    cv = canvas()
    cv.local_time = local

    def slot(name):
        def draw(g):
            node = cv.group(g, f'slot-{name}')
            cv.rect(node, 300, 900, 20, 20, '#ff0000')
            return object()  # builders ignore the callback return; the supplied group owns the drawing

        return draw

    options = dict(OPTIONS[part.name], **{n: slot(n) for n in SLOTS.get(part.name, ())})
    result = part.builder(cv, cv.comp, **options)
    return cv, result

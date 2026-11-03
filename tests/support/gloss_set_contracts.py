"""All Gloss scenery and graphic builders, including their return ownership."""

from srstudio import gloss_sets as sets
from srstudio import registry
from support.gloss import canvas, font

ENTRIES = tuple(e for e in registry.entries() if e.module == 'srstudio.gloss_sets')
OPTIONS = {
    'gloss-plaza': dict(sign=True),
    'gloss-activity': dict(number='12'),
    'gloss-waiting': dict(serving=((0, '3'), (2, '4'))),
    'gloss-board': dict(cards=(sets.Card(0, 'A card', 'Some body', points=2), sets.Card(2, 'A second', tone='plum'))),
    'gloss-door': dict(at=(540, 1200), opens=(1, 2, 3)),
    'gloss-ticket': dict(at=(700, 1000), number='1234567'),
    'gloss-hook': dict(text='Where is the exit?', talk=((0, 'closed'), (1, 'open'))),
    'gloss-notice': dict(title='A notice', body='A longer notice body.', settle=0.3, talk=((0, 'closed'), (1, 'open'))),
}
TEXT = {'gloss-board', 'gloss-hook', 'gloss-notice'}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    kwargs = dict(OPTIONS[entry.name], end=4)
    if entry.name in TEXT:
        kwargs['font'] = font()
    return cv, entry.builder(cv, cv.comp, **kwargs)

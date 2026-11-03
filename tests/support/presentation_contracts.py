"""Presentation-kit examples using real scene nodes, map assets and native caption construction."""

from datetime import datetime, timezone
from types import SimpleNamespace

from srstudio import host_kit, map_kit, mind_kit, native, registry, toon
from srstudio.layout import VERTICAL
from support.stick_car import canvas

MODULES = {'srstudio.host_kit', 'srstudio.mind_kit', 'srstudio.map_kit'}
ENTRIES = [e for e in registry.entries() if e.kind != 'character' and e.module in MODULES]
LINE = toon.Line('line', 'Ready now.', 1, 3, 'host')
PLACE = map_kit.Place('Rome', 41.89193, 12.51133)


def measure(text, size):
    return len(text) * size * 0.45


class CaptionContext:
    """The public episode protocol, delegating to the real native-caption implementation."""

    def __init__(self, cv):
        self.cv, self.comp = cv, cv.comp
        self.spec = SimpleNamespace(safe_area=VERTICAL, width=cv.width, height=cv.height)

    def native_captions(self, cues, *, look, id):
        return native.caption_track(
            self.cv.scene,
            cues,
            font_asset=self.cv.font_asset,
            safe_area=self.spec.safe_area,
            width=self.cv.width,
            height=self.cv.height,
            look=look,
            id=id,
            canvas=self.cv,
        )


OPTIONS = {
    'host-wardrobe': dict(end=3),
    'host-punch': dict(who='close', at=1, was='lint', push=(0.5, 1.5)),
    'host-label': dict(text='READY', start=1, end=3, measure=measure),
    'host-captions': dict(lines=(LINE,), measure=measure, words=((1, 2, 'Ready'), (2, 3, 'now.'))),
    'host-sign-off': dict(phrase='See you soon.', start=1, end=3, measure=measure),
    'host-screen': dict(
        chat='Studio', bubbles=(host_kit.Bubble('Ready', 1, 'Alex', 'Seen', 2),), start=1, end=3, measure=measure
    ),
    'mind-stamp': dict(rows=('A finding',), cite='Example, 2020', start=1, end=3, measure=measure),
    'mind-zipper': dict(start=0.5, end=2),
    'mind-named': dict(name='Attention', start=1, end=3, measure=measure, scale=1.25),
    'mind-name-card': dict(name='Attention', start=0, reveal=1, end=3, measure=measure),
    'mind-evidence-card': dict(
        evidence=mind_kit.Evidence('Lee', '2020', 'People saw a card.', 'Some recalled it.'),
        start=0,
        end=3,
        reveal=1,
        measure=measure,
    ),
    'mind-spotlight': dict(foot=(400, 900), start=0, end=3, sweep=((0, 400), (2, 700))),
    'mind-memory-shelf': dict(labels=('Past', 'Present'), measure=measure, pull=(0, 1), also=((1, 2),)),
    'mind-two-lines': dict(
        expected=('Expected', 0.8, '80%'), actual=('Actual', 0.4, '40%'), start=0, end=3, reveal=1, measure=measure
    ),
    'mind-lens': dict(at=(400, 900), start=0, end=3, path=((0, 400), (2, 700))),
    'mind-captions': dict(lines=(LINE,), measure=measure, tints={'host': '#ffd770'}),
    'map-globe': dict(lon=0, lat=0, start=0, end=3, spin=((0, 0), (1, 30)), dive=map_kit.Dive(1.5, 1, 12, 42, 1)),
    'map-flat': dict(lon=0, lat=0, zoom=0, start=0, end=3, moves=(map_kit.Move(1, 1, 12, 42, 1),)),
    'map-far-side': dict(zoom=0, start=0, flip=(1, 2), end=3),
    'map-equal-area': dict(lon=0, lat=0, zoom=0, start=0, end=3, shift=(((0, 0), (2, 12)), ((0, 0), (2, 42)))),
    'map-pin': dict(place=PLACE, start=0, end=3, measure=measure),
    'map-parallel': dict(place=PLACE, start=0, end=3, drawn=0.5, tag_from=1, measure=measure),
    'map-population': dict(waves={'adelaide': (0, 1)}, fades={'adelaide': (2, 3)}),
    'map-ring': dict(radius=300, start=0, end=3, label='Example', measure=measure),
    'map-clock': dict(x=300, y=500, radius=100, hour=9.5, start=0, end=3, runs=2),
    'map-daylight': dict(places=(PLACE,), day=datetime(2026, 1, 1, tzinfo=timezone.utc), start=0, end=3),
    'map-stamp': dict(text='A finding, 2020', start=0, end=3, measure=measure),
    'map-captions': dict(lines=(LINE,), measure=measure),
}
GROUPS = {'host-sign-off', 'mind-stamp', 'mind-zipper', 'mind-named', 'mind-captions', 'map-clock', 'map-captions'}
MAPS = {'map-globe', 'map-flat', 'map-far-side', 'map-equal-area'}
VIEW_INPUT = {'map-pin', 'map-parallel', 'map-population', 'map-daylight'}


def drawing(entry, *, local=False):
    cv = canvas()
    cv.local_time = local
    options = dict(OPTIONS.get(entry.name, {}))
    if entry.name == 'host-captions':
        return cv, entry.builder(CaptionContext(cv), **options)
    if entry.name == 'host-punch':
        return cv, entry.builder(cv, cv.group(cv.comp, 'camera'), **options)
    if entry.name in VIEW_INPUT:
        options['view'] = map_kit.flat(cv, cv.comp, 0, 0, 0, 0, 3, id='view')
    if entry.name == 'map-population':
        return cv, entry.builder(cv, **options)
    return cv, entry.builder(cv, cv.comp, **options)

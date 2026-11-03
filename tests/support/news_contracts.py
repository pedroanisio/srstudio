"""Real News kit examples for versioned discovery and drawing preservation."""

from sr_core.scene import Scene

from srstudio import Canvas, flat_counter, news_inked, news_kit, registry, toon

MODULES = {'srstudio.news_kit', 'srstudio.news_inked'}
ENTRIES = [e for e in registry.entries() if e.module in MODULES and e.kind != 'character']


def measure(text, size):
    return len(text) * size * 0.42


def canvas(local=False):
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='30', duration=8, background=news_kit.PLUM_DEEP)
    cv = Canvas(scene, news_kit.NEWS.palette(), font_asset='barlow-condensed', namer=flat_counter('n'))
    cv.local_time = local
    return cv


COMMON = dict(start=1, end=7, measure=measure)
OPTIONS = {
    'news-set': dict(end=2),
    'news-desk': {},
    'news-bug': COMMON,
    'news-parody-tag': COMMON,
    'news-source-card': dict(COMMON, source=news_kit.Source('Example', 'Oct 30, 2026', 'A plain headline'), small=3),
    'news-lower-third': dict(COMMON, kicker='TODAY', headline='A plain headline'),
    'news-banner': COMMON,
    'news-ticker': dict(COMMON, items=('A plain headline', 'Another story')),
    'news-captions': dict(lines=(toon.Line('line', 'Ready now.', 1, 3, 'vera'),), measure=measure),
    'news-phone': dict(
        COMMON,
        chat='Family',
        bubbles=(news_kit.Bubble('9:00', 'Ready', at=0), news_kit.Bubble('9:01', 'Yes', out=False, at=3)),
    ),
    'news-missing-card': dict(COMMON, label='LID'),
    'news-live-door': dict(COMMON, label='HOME', shut=3),
    'news-route': dict(
        COMMON,
        title='Route',
        track=((100, 100), (200, 100), (200, 300)),
        pins=(news_inked.Pin(100, 100, 'Home', '#ffd23f'),),
        direct=((100, 100), (200, 300)),
        draw=3,
        marker='dot',
    ),
    'news-money-app': dict(
        COMMON,
        title='Balance',
        amount='$20',
        action='PAY',
        refused='NO',
        taps=(2, 6.9),
        refused_at=3,
        notes=((4, 'Try again'),),
    ),
    'news-oven-clock': dict(COMMON, label='OVEN', time='9:30', wrong='LATE', right='EARLY', right_at=3),
    'news-forecast-map': dict(
        COMMON, title='Forecast', pin='Home', counter='Rain', counts=((1, '0'), (4, '1')), rain=(2, 6)
    ),
    'news-corridor-map': dict(
        COMMON,
        title='Hall',
        counter='Steps',
        counts=((1, '0'), (4, '1')),
        one=((1, 250, 250), (3, 400, 250)),
        other=((1, 400, 450), (3, 250, 450)),
    ),
}


def drawing(part, *, local=False):
    cv = canvas(local)
    result = part.builder(cv, cv.comp, **OPTIONS[part.name.removesuffix('@2')])
    return cv, result

"""Story parts declare what their builders do: the handle they return, the arguments and the vocabularies they take."""

import json

import pytest
from sr_core.scene import Group

from srstudio import collage_home, cutout_hats, registry, soft_home, stick_satnav
from srstudio.readings import Reading
from srstudio.toon_chat import Bubble
from srstudio.toon_drafts import Draft, Note
from support.saga import canvas as saga_canvas
from support.stick_car import canvas


def measure(text: str, size: float) -> float:
    return len(text) * size * 0.55


MODULES = {
    f'srstudio.{name}'
    for name in (
        'collage_home',
        'cutout_hats',
        'cutout_recording',
        'saga_everyday',
        'soft_home',
        'stick_interview',
        'stick_porch',
        'stick_satnav',
        'toon_alarm',
        'toon_cables',
        'toon_chat',
        'toon_drafts',
        'toon_interview',
        'toon_night',
        'toon_screens',
        'toon_signal',
        'toon_tie',
    )
}
ENTRIES = tuple(e for e in registry.entries() if e.module in MODULES)
SAGA = {e.name for e in ENTRIES if e.module == 'srstudio.saga_everyday'}
AT = dict(at=(300.0, 900.0), end=4.0)
OPTIONS = {
    'collage-headset': dict(cx=500, cy=700),
    'collage-wall-tv': dict(x=100, y=200, w=600),
    'collage-staircase': dict(x=100, y=1200, w=500, h=300),
    'collage-snowy-window': dict(x=100, y=200, w=300, h=400),
    'saga-hut': dict(end=4.0),
    'saga-hut-table': dict(end=4.0),
    'saga-returns': dict(end=4.0),
    'saga-returns-desk': dict(end=4.0),
    'saga-wince': dict(spans=((1.0, 2.0),), **AT),
    'saga-coupon': dict(track=((0.0, 300.0, 900.0, 1.0), (1.0, 320.0, 900.0, 0.0)), **AT),
    'saga-dim': dict(spans=((1.0, 2.0),), **AT),
    'soft-den': dict(end=4.0),
    'soft-chip-bag': dict(x=500, y=900),
    'soft-slippers': dict(x=500, y=900),
    'soft-hook-card': dict(text='WAIT', box=(100, 200, 500, 160), end=3.0),
    'stick-interview-room': dict(end=4.0),
    'stick-interview-desk': dict(end=4.0),
    'stick-desk-page': dict(x=500, y=1100),
    'stick-resume-insert': dict(end=4.0),
    'stick-hall': dict(end=4.0),
    'stick-front-door': dict(end=4.0),
    'stick-tow-truck': dict(end=4.0),
    'stick-rough-road': dict(end=4.0),
    'stick-nav-insert': dict(end=4.0),
    'toon-cable-drawer': dict(opens=1.0),
    'toon-gray-cable': dict(moves=((0.0, 300.0, 400.0),), start=0.0, end=2.0),
    'toon-chat-phone': dict(bubbles=(Bubble(0.5, 'hi'),), measure=measure),
    'toon-chat-chip': dict(text='NO', start=0.0, end=2.0, measure=measure),
    'toon-laptop-screen': dict(drafts=(Draft(0.0, 2.0, 'DRAFT 1', 'Hi'),)),
    'toon-stuck-notes': dict(notes=(Note(0.0, 'Hi'),)),
    'toon-call-chip': dict(name='Mom', reads=(0.0, 12), start=0.0, end=3.0, measure=measure),
    'toon-raised-phone': dict(
        hand=(300.0, 600.0), colour='#112233', dark='#001122', bars=((0.0, 2),), start=0.0, end=2.0
    ),
    'toon-upload-chip': dict(readings=(Reading(0.0, 2.0, '40%'),), shares=(0.4,), measure=measure),
    'toon-sandwich-broom': dict(moves=((0.0, 300.0, 400.0), (1.0, 320.0, 420.0)), start=0.0, end=2.0, bite=1.0),
}
for _name in SAGA - set(OPTIONS):
    OPTIONS[_name] = dict(AT)
for _entry in ENTRIES:
    if _entry.module == 'srstudio.collage_home':
        OPTIONS.setdefault(_entry.name, dict(x=300, y=900))


def contract(entry):
    return entry.describe()['contract']


def test_every_story_part_is_declared_and_exercised():
    assert len(ENTRIES) == 95
    assert not [e.name for e in ENTRIES if e.contract is None]


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_a_story_contract_explains_every_argument_and_is_json(entry):
    data = contract(entry)
    assert not [n for n, p in data['arguments']['properties'].items() if p.get('x-status') == 'unknown']
    assert data['constraints'] and all(len(c) > 8 for c in data['constraints'])
    assert json.loads(json.dumps(data, allow_nan=False)) == data
    assert data['capabilities']['spatial_attachment'] is False


@pytest.mark.parametrize('entry', ENTRIES, ids=lambda e: e.name)
def test_a_story_part_returns_what_its_contract_says(entry):
    cv = saga_canvas() if entry.name in SAGA else canvas()
    result = entry.builder(cv, cv.comp, **OPTIONS.get(entry.name, {}))
    declared = contract(entry)
    if declared['returns'].get('type') == 'null':
        assert result is None
    else:
        assert isinstance(result, Group | tuple) and result is not None
    if 'returns_scene_handle' in declared['capabilities']:
        assert declared['capabilities']['returns_scene_handle'] is (result is not None)


def enum(name, *path):
    node = registry.describe('prop', name)['contract']['arguments']['properties']
    for key in path:
        node = node[key] if not isinstance(node, list) else node[key]
    return node['enum']


def test_the_declared_vocabularies_are_the_ones_the_builders_know():
    assert enum('hat-stack', 'hats', 'items', 'prefixItems', 0) == list(cutout_hats.HATS)
    assert enum('stick-nav-insert', 'screen') == list(stick_satnav.SCREENS)
    assert enum('collage-plate', 'dish') == list(collage_home.DISHES)
    road = registry.describe('location', 'stick-rough-road')['contract']['arguments']['properties']
    assert road['surface']['enum'] == list(stick_satnav.SURFACES)


def test_the_declared_clock_of_a_drawer_is_the_clock_its_keys_use():
    entry = registry.entries('prop')
    drawer = next(e for e in entry if e.name == 'toon-cable-drawer')
    assert contract(drawer)['arguments']['properties']['opens']['x-timebase'] == 'composition'
    cv = canvas()
    cv.local_time = True
    drawer.builder(cv, cv.comp, opens=1.0)
    assert 'timeBase="local"' not in cv.scene.to_bytes().decode()


def test_a_den_declares_its_room_colours_and_a_refusal_still_raises():
    den = registry.describe('location', 'soft-den')['contract']['arguments']['properties']
    assert den['room_colors']['properties']['wall']['prefixItems'][0]['x-role'] == 'paint-color'
    cv = canvas()
    with pytest.raises(soft_home.SoftHomeError):
        registry.get('location', 'soft-den')(cv, cv.comp, end=-1.0)

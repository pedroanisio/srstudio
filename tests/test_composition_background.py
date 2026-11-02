"""Native project backgrounds preserve information compositing and opt-out identity."""

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import asdict, replace

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from support.composition import paper


def test_omitted_background_keeps_legacy_plan_timeline_and_xml_identities():
    from srstudio._composition_preflight import _graph

    spec, binding, xml = paper()
    legacy = asdict(spec)
    legacy.pop('background', None)
    assert c.parse_scene(legacy) == spec
    plan = c.preflight(spec, (binding,))
    timeline = m.plan_scene(spec, (binding,), m.SceneMotion())
    compiled = c.compile_scene(plan, (c.VectorSource(binding.id, xml),))
    assert plan.digest == '2c4d987d798e77917fd14a8e64de22607e06fd8f66f6398a59ee520df67a2a91'
    assert timeline.digest == '5b6d069f4e94b9d8e58f2f19d830fcf44aa770ef00772ec0a2fcd54646cd30d3'
    assert (
        hashlib.sha256(compiled.xml).hexdigest() == '0a42eedbc50ab57df2ee2a0bb8e57719cb7f8d855a527eca7151b53306e2ef06'
    )
    assert ET.fromstring(compiled.xml).find('project').get('background') is None
    visits = [0]
    _graph((spec, (binding,)), visits)
    assert visits == [101]


@pytest.mark.parametrize('route', ['single', 'bundle', 'timeline'])
def test_background_round_trips_and_emits_as_native_project_setting(tmp_path, route):
    spec, binding, xml = paper()
    colored = replace(spec, background='#efe8df')
    assert c.parse_scene(asdict(colored)) == colored
    plan = c.preflight(colored, (binding,))
    source = c.VectorSource(binding.id, xml)
    if route == 'single':
        result = c.compile_scene(plan, (source,))
    elif route == 'bundle':
        result = c.emit_bundle(
            plan, (source,), tmp_path / 'bundle', engine=tmp_path / 'unused', cache=tmp_path / 'cache'
        )
    else:
        timeline = m.plan_scene(colored, (binding,), m.SceneMotion())
        result = m.emit_timeline(
            timeline, (source,), tmp_path / 'bundle', engine=tmp_path / 'unused', cache=tmp_path / 'cache'
        )
    assert ET.fromstring(result.xml).find('project').get('background') == '#efe8df'
    assert not (tmp_path / 'cache').exists()
    assert plan.digest != c.preflight(spec, (binding,)).digest


@pytest.mark.parametrize('color', ['', '#fff', '#12345678', '#GG0000', 'red', 'url(#paint)', True, 1, []])
def test_invalid_background_is_refused_before_output_or_cache(tmp_path, color):
    spec, binding, xml = paper()
    with pytest.raises(c.CompositionError):
        colored = replace(spec, background=color)
        c.emit_bundle(
            c.preflight(colored, (binding,)),
            (c.VectorSource(binding.id, xml),),
            tmp_path / 'bundle',
            engine=tmp_path / 'unused',
            cache=tmp_path / 'cache',
        )
    assert list(tmp_path.iterdir()) == []


def test_vector_source_cannot_override_the_composition_background():
    _, binding, xml = paper()
    root = ET.fromstring(xml)
    root.find('project').set('background', '#ffffff')
    with pytest.raises(c.CompositionError):
        c.prepare_vector(binding, ET.tostring(root))

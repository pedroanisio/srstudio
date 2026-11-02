"""An explicit native ink group owns its shapes without duplicating their drawing."""

import xml.etree.ElementTree as ET
from dataclasses import replace

import pytest

from srstudio import composition as c


def fixture():
    from support.composition_forms import form

    plan, _ = form()
    source = c.VectorSource(
        'face',
        b'<scene version="1.1"><project width="64" height="64" fps="4" duration="1"/>'
        b'<composition><group id="ink" opacity="0.5" x="-10" y="-10">'
        b'<shape id="outline" shape="rect" width="20" height="20" fill="#aabbcc"/>'
        b'<group id="nested"><shape id="detail" shape="rect" width="10" height="10" fill="#778899"/>'
        b'</group></group><shape id="lit" shape="rect" width="10" height="10" fill="#ffffff"/>'
        b'</composition></scene>',
    )
    forms = (c.FormSurface('ink', mode='ink'), c.FormSurface('lit', ('#000000', '#ffffff')))
    binding = replace(
        plan.bindings[0], forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
    )
    return c.preflight(plan.spec, (binding,), purpose=plan.purpose), source


@pytest.fixture(params=['public', 'worker'])
def prepare(request):
    from srstudio import _composition_vector

    return c.prepare_vector if request.param == 'public' else _composition_vector.prepare_vector


def test_group_ink_preserves_native_group_and_shades_only_explicit_diffuse_shape(prepare):
    plan, source = fixture()
    prepared = prepare(plan.bindings[0], source.xml)
    assert prepared.xml == source.xml
    compiled = c.compile_scene(plan, (source,))
    root = ET.fromstring(compiled.xml)
    shapes = list(root.iter('shape'))
    assert [n.get('fill') for n in shapes] == ['#aabbcc', '#778899', '#ffffff']
    assert any(g.get('opacity') == '0.5' and len(list(g.iter('shape'))) == 2 for g in root.iter('group'))
    fields = c.form_lighting(plan, 'face', 0)
    assert fields[0].color is None
    dark = replace(plan.spec, lights=c.LightRig('lit', (c.LightSpec('key', 'directional', '#ffffff', 1),)))
    compiled = c.compile_scene(c.preflight(dark, plan.bindings, purpose=plan.purpose), (source,))
    assert [n.get('fill') for n in ET.fromstring(compiled.xml).iter('shape')] == ['#aabbcc', '#778899', '#000000']


@pytest.mark.parametrize(
    'bad',
    [
        'unknown',
        'unused-field',
        'diffuse-group',
        'path-group',
        'empty',
        'unclaimed',
        'overlap-shape',
        'overlap-group',
        'text',
    ],
)
def test_invalid_group_ownership_is_refused_before_publication(prepare, tmp_path, bad):
    plan, source = fixture()
    root = ET.fromstring(source.xml)
    forms = plan.bindings[0].forms
    if bad == 'unknown':
        forms = (replace(forms[0], node='missing'), forms[1])
    elif bad == 'unused-field':
        forms += (c.FormSurface('missing', mode='ink'),)
    elif bad == 'diffuse-group':
        forms = (replace(forms[0], mode='diffuse', palette=('#000000', '#ffffff')), forms[1])
    elif bad == 'path-group':
        forms = (replace(forms[0], path=c.FormPath(((0, 0, 0), (1, 0, 0), (1, 1, 0)))),)
        root.find('.//shape[@id="lit"]').set('id', 'unused')
    elif bad == 'empty':
        root.find('.//group[@id="ink"]').clear()
        root.find('.//group').set('id', 'ink')
    elif bad == 'unclaimed':
        forms = forms[:1]
    elif bad.startswith('overlap'):
        forms += (c.FormSurface('detail' if bad == 'overlap-shape' else 'nested', mode='ink'),)
    else:
        assets = ET.SubElement(root, 'assets')
        ET.SubElement(assets, 'text', id='caption', text='not picture content', width='10', height='10')
    xml = ET.tostring(root)
    source = c.VectorSource(source.id, xml)
    binding = replace(
        plan.bindings[0], forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
    )
    with pytest.raises(c.CompositionError):
        prepare(binding, xml)
    with pytest.raises(c.CompositionError):
        c.emit_bundle(
            c.preflight(plan.spec, (binding,), purpose=plan.purpose),
            (source,),
            tmp_path / 'out',
            engine=tmp_path / 'missing',
            cache=tmp_path / 'cache',
        )
    assert not list(tmp_path.iterdir())


def test_actual_figure_is_one_explicit_world_ink_group(monkeypatch):
    from support.composition_curves import figure_source

    binding, xml = figure_source(monkeypatch)
    source = c.VectorSource(binding.id, xml)
    forms = (c.FormSurface('figure', mode='ink'),)
    binding = replace(
        binding, forms=forms, candidate=c.CandidateSource('toon', c.vector_source_digest(source, forms=forms))
    )
    prepared = c.prepare_vector(binding, xml)
    assert prepared.xml == xml
    assert len(list(ET.fromstring(xml).iter('shape'))) == 977
    assert len(binding.forms) == 1

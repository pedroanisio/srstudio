"""Regression coverage for automated authoring and recovery."""

import pytest

from srstudio import Episode, EpisodeSpec, Timeline, sample
from srstudio.episode import EpisodeError
from srstudio.narration import NarrationError
from srstudio.sample import SampleError
from srstudio.timeline import TimelineError


def make_episode(project):
    return Episode(EpisodeSpec(slug='agent', title='agent', description='test', root=project, seed=1, signature=False))


def test_scene_outside_project_rebases_inputs_without_mutating_episode(project, tmp_path):
    import xml.etree.ElementTree as ET

    ep = make_episode(project)
    before = ep.scene.to_bytes()
    out, report = tmp_path / 'build' / 'scene.xml', tmp_path / 'report.json'
    ep.finish(out=out, report=report)
    for node in ET.parse(out).getroot().find('assets'):
        if node.get('src'):
            assert (out.parent / node.get('src')).resolve().is_file()
    assert ep.scene.to_bytes() == before
    assert report.is_file()


@pytest.mark.parametrize('field,value', [('role', None), ('text', 5), ('caption', []), ('role', ''), ('text', ' ')])
def test_bad_phrase_fields_are_rejected(field, value):
    phrase = {'role': 'a', 'text': 'hi', 'start': 0, 'end': 1}
    phrase[field] = value
    with pytest.raises(TimelineError, match=field):
        Timeline.from_dict({'duration': 2, 'phrases': [phrase]})


@pytest.mark.parametrize('angle', [None, [], '', '  ', 5])
def test_bad_cut_angle_is_rejected(angle):
    with pytest.raises(TimelineError, match='angle'):
        Timeline.from_dict({'duration': 2, 'phrases': [], 'camera_cuts': [{'time': 0, 'angle': angle}]})


@pytest.mark.parametrize('angle', [None, [], '', '  ', 5])
def test_bad_sample_angle_does_not_write(tmp_path, angle):
    root = tmp_path / 'sample'
    with pytest.raises(SampleError, match='angle'):
        sample.write_sample_project(root, [sample.Line('a', 'hi')], angles=[angle])
    assert not root.exists()


@pytest.mark.parametrize('value', [None, [], 'bad', True, float('nan')])
def test_bad_beat_is_rejected(value):
    with pytest.raises(TimelineError, match='end_card_start'):
        Timeline.from_dict({'duration': 2, 'phrases': [], 'end_card_start': value})


def test_numeric_string_beat_is_parsed():
    assert Timeline.from_dict({'duration': 2, 'phrases': [], 'end_card_start': '1.5'}).ending == 1.5


def test_bad_narration_manifest_does_not_mutate_episode(project, tmp_path):
    ep = make_episode(project)
    ep.mix(loudness='-23')
    before = ep.scene.to_bytes()
    with pytest.raises(NarrationError, match='missing.json'):
        ep.audio(narration=tmp_path / 'missing.json', loudness='-10')
    assert ep.scene.to_bytes() == before
    assert ep.mix() is ep._mix


def test_failed_duck_can_be_retried_without_duplicate_tracks(project, monkeypatch):
    ep = make_episode(project)
    monkeypatch.setattr(type(ep), 'audio_source', property(lambda self: 'takes'))
    before = ep.scene.to_bytes()
    with pytest.raises(EpisodeError, match='no music'):
        ep.audio(extra=[('extra', 'assets/dialogue.wav', {'role': 'dialogue'})], duck=-4)
    assert ep.scene.to_bytes() == before
    assert ep._mix is None
    ep.audio(extra=[('extra', 'assets/dialogue.wav', {'role': 'dialogue'})])
    assert len(ep._mix.find_all('audioTrack')) == 1


def test_failed_audio_restores_existing_mix_and_tracks(project, monkeypatch):
    ep = make_episode(project)
    mix = ep.mix(loudness='-23')
    ep.add_track('original', 'dialogue', role='dialogue')
    before = ep.scene.to_bytes()
    monkeypatch.setattr(type(ep), 'audio_source', property(lambda self: 'takes'))
    with pytest.raises(EpisodeError, match='no music'):
        ep.audio(extra=[('extra', 'assets/dialogue.wav', {'role': 'dialogue'})], duck=-4, loudness='-10')
    assert ep.scene.to_bytes() == before
    assert ep.mix() is mix
    assert ep._master_kw['loudness'] == '-23'
    ep.audio(extra=[('extra', 'assets/dialogue.wav', {'role': 'dialogue'})])
    assert len(mix.find_all('audioTrack')) == 2


def test_rebased_input_uris_keep_remote_and_output_paths(tmp_path):
    import xml.etree.ElementTree as ET

    from sr_core.scene import Scene

    from srstudio.episode import _document_at

    project = tmp_path / 'project space'
    scene = Scene(version='auto')
    assets = scene.add_assets()
    assets.add_image(id='local', src='assets/a%20b.png')
    assets.add_image(id='remote', src='https://example.org/a.png')
    scene.add_output(id='main', path='renders/out.mp4')
    output = tmp_path / 'build'
    xml = ET.fromstring(_document_at(scene, project, output))
    images = {node.get('id'): node.get('src') for node in xml.iter('image')}
    assert images == {'local': '../project%20space/assets/a%20b.png', 'remote': 'https://example.org/a.png'}
    assert xml.find('output').get('path') == 'renders/out.mp4'
    assert assets.find_all('image')[0].src == 'assets/a%20b.png'

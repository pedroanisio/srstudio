"""Recovery and validation for iterative episode authoring."""

import json
import xml.etree.ElementTree as ET

import pytest

from srstudio import CEL, Episode, EpisodeSpec, Timeline, locations
from srstudio.episode import EpisodeFileError
from srstudio.timeline import TimelineError


def episode(project):
    return Episode(EpisodeSpec(slug='agent', title='agent', description='test', root=project, seed=1, signature=False))


def test_empty_shot_selection_is_never_visible(project):
    ep = episode(project)
    group = ep.setup(locations.office_wide, ep.t.shots('not-an-angle'))
    xml = ET.fromstring(ep.scene.to_bytes())
    node = xml.find(f".//group[@id='{group.id}']")
    animation = node.find("animate[@property='opacity']")
    assert animation is not None
    assert all(float(key.get('value')) == 0 for key in animation.findall('key'))


def test_setup_failure_rolls_back_scene_and_cached_resources(project):
    ep = episode(project)
    before = ep.scene.to_bytes()

    def fail(group):
        ep.cv.symbol('custom-symbol', lambda parent: ep.cv.rect(parent, 0, 0, 4, 4, "#000000"))
        raise ValueError('callback failed')

    with pytest.raises(ValueError, match='callback failed'):
        ep.setup(locations.office_wide, [(0, 1)], at_desk=fail, instanced=True)
    assert ep.scene.to_bytes() == before
    assert 'custom-symbol' not in ep.cv._symbols
    ep.setup(locations.office_wide, [(0, 1)], instanced=True)
    assert ep.check() == []


def take_episode(tmp_path, audio):
    item = {'id': 'a', 'actor': 'speaker', 'shot': 'wide', 'text': 'hi', 'start': 0, 'duration': 1, 'audio': audio}
    (tmp_path / 'script.json').write_text(json.dumps({'duration': 1, 'items': [item]}))
    return Episode(
        EpisodeSpec(slug='agent', title='agent', description='test', root=tmp_path, seed=1, style=CEL, signature=False)
    )


@pytest.mark.parametrize('audio', ['missing.wav', None, ''])
def test_missing_take_audio_fails_without_scene_mutation(tmp_path, audio):
    ep = take_episode(tmp_path, audio)
    before = ep.scene.to_bytes()
    with pytest.raises(EpisodeFileError, match='take a'):
        ep.audio()
    assert ep.scene.to_bytes() == before
    assert ep._mix is None
    assert not (tmp_path / 'agent.scene.xml').exists()


def test_direct_take_audio_refuses_missing_file_before_mutation(tmp_path):
    ep = take_episode(tmp_path, 'missing.wav')
    before = ep.scene.to_bytes()
    with pytest.raises(EpisodeFileError, match='missing.wav'):
        ep.take_audio(ep.takes[0])
    assert ep.scene.to_bytes() == before


def timeline(root, filename='timing.json'):
    return Timeline.from_dict(
        {'duration': 2, 'phrases': [{'role': 'a', 'text': 'hi', 'start': 0, 'end': 1, 'timing_file': filename}]},
        root=root,
    )


def test_word_time_missing_file_has_typed_path_and_phrase(tmp_path):
    with pytest.raises(TimelineError, match=r'phrase 0.*timing.json') as caught:
        timeline(tmp_path).word_time(0, 'hi')
    assert isinstance(caught.value.__cause__, FileNotFoundError)


@pytest.mark.parametrize(
    'content',
    [
        '{bad',
        json.dumps({}),
        json.dumps({'alignment': {'characters': ['h', 'i'], 'character_start_times_seconds': []}}),
        json.dumps({'alignment': {'characters': ['h', 'i'], 'character_start_times_seconds': [0, 'bad']}}),
        json.dumps({'alignment': {'characters': ['hi'], 'character_start_times_seconds': [0]}}),
    ],
)
def test_word_time_malformed_alignment_has_typed_path_and_phrase(tmp_path, content):
    (tmp_path / 'timing.json').write_text(content)
    with pytest.raises(TimelineError, match=r'phrase 0.*timing.json'):
        timeline(tmp_path).word_time(0, 'hi')

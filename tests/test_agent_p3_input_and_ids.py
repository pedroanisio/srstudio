"""The documented timeline inputs and retry-stable built-in ID generators."""

import json
import re
from pathlib import Path

import pytest

from srstudio import CEL, Episode, EpisodeSpec, Timeline, flat_counter, shared_counter
from srstudio._transaction import scene_transaction


@pytest.mark.parametrize('factory', [lambda: shared_counter(7), lambda: flat_counter('n', 7)])
def test_failed_setup_restores_id_counter_and_scene(project, factory):
    def make():
        return Episode(
            EpisodeSpec(slug='x', title='x', description='x', root=project, seed=1, signature=False, namer=factory())
        )

    retried, fresh = make(), make()
    assert retried.cv.uid('pre') == fresh.cv.uid('pre')

    def room(cv, parent, *, shots, fail=False):
        group = cv.group(parent, cv.uid('group'))
        cv.rect(group, 0, 0, 4, 4, '#000000')
        if fail:
            raise ValueError('retry')
        return group

    with pytest.raises(ValueError, match='retry'):
        retried.setup(room, [(0, 1)], fail=True)
    retried.setup(room, [(0, 1)])
    fresh.setup(room, [(0, 1)])
    assert retried.scene.to_bytes() == fresh.scene.to_bytes()


def test_nested_transaction_restores_only_failed_scope(project):
    ep = Episode(
        EpisodeSpec(slug='x', title='x', description='x', root=project, seed=1, signature=False, namer=shared_counter())
    )
    with scene_transaction(ep.scene, ep.cv):
        assert ep.cv.uid('g') == 'g1'
        with pytest.raises(ValueError):
            with scene_transaction(ep.scene, ep.cv):
                assert ep.cv.uid('g') == 'g2'
                raise ValueError('inner')
        assert ep.cv.uid('g') == 'g2'
    assert ep.cv.uid('g') == 'g3'


def test_default_style_counter_is_retry_stable(tmp_path):
    (tmp_path / 'script.json').write_text(json.dumps([{'start': 0, 'end': 1, 'text': 'hi'}]))
    spec = EpisodeSpec(slug='x', title='x', description='x', root=tmp_path, seed=1, style=CEL, signature=False)
    a, b = Episode(spec), Episode(spec)

    def builder(cv, parent, *, shots, fail=False):
        group = cv.group(parent, cv.uid('g'))
        if fail:
            raise ValueError('retry')
        return group

    with pytest.raises(ValueError):
        a.setup(builder, [(0, 1)], fail=True)
    assert a.setup(builder, [(0, 1)]).id == b.setup(builder, [(0, 1)]).id


def test_documented_timeline_examples_load_and_have_expected_semantics(tmp_path):
    docs = (Path(__file__).resolve().parents[1] / 'docs' / 'authoring-reference.md').read_text()
    assert '## Timeline input formats' in docs
    section = docs.split('## Timeline input formats', 1)[1].split('\n## ', 1)[0]
    examples = re.findall(r'```json\n(.*?)\n```', section, re.DOTALL)
    assert len(examples) == 3
    dialogue, takes, captions = [json.loads(example) for example in examples]
    for i, data in enumerate((dialogue, takes, captions)):
        path = tmp_path / f'example-{i}.json'
        path.write_text(json.dumps(data))
        assert Timeline.load(path) == Timeline.from_dict(data, root=tmp_path)
    d, t, c = [Timeline.from_dict(value) for value in (dialogue, takes, captions)]
    assert d.phrases and d.shots('wide') and not d.takes
    assert t.takes and t.takes[0].audio and t.takes[1].start == t.takes[0].end
    assert len(c.phrases) >= 1 and not c.takes and not c.cuts
    readme = (Path(__file__).resolve().parents[1] / 'README.md').read_text()
    assert 'authoring-reference.md#timeline-input-formats' in readme


def test_outer_failure_rewinds_successful_inner_transaction(project):
    ep = Episode(
        EpisodeSpec(
            slug='x', title='x', description='x', root=project, seed=1, signature=False, namer=flat_counter('v')
        )
    )
    with pytest.raises(ValueError, match='outer'):
        with scene_transaction(ep.scene, ep.cv):
            assert ep.cv.uid('g') == 'v1'
            with scene_transaction(ep.scene, ep.cv):
                assert ep.cv.uid('g') == 'v2'
            raise ValueError('outer')
    assert ep.cv.uid('g') == 'v1'

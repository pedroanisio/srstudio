"""Legacy bookmarks and runnable recipes survive the task/history documentation split."""

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from support.authoring_docs import anchors, fences

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
LAYOUT = json.loads((ROOT / 'tests/data/authoring-reference-layout.json').read_text())
# The episode history moved to srstudio-episodes with the reels it records (ADR 0220); its sections and recipes are
# held there by tests/test_docs.py, and only the index's links to it are checked here.
EPISODE_HISTORY = 'https://github.com/pedroanisio/srstudio-episodes/blob/develop/docs/episode-history.md'
OWNERS = sorted({s['owner'] for s in LAYOUT['sections']} - {'authoring-reference.md', EPISODE_HISTORY})
EXTRA_GUIDES = ['authoring-audio.md']


def test_task_index_routes_to_focused_guides_without_embedded_recipes():
    text = (DOCS / 'authoring-reference.md').read_text()
    for owner in [*OWNERS, *EXTRA_GUIDES]:
        assert f']({owner}' in text, owner
    assert '<!-- diagnostic-repair:start -->' not in text
    assert '```python' not in text
    assert 'Episode history' in text
    assert f']({EPISODE_HISTORY})' in text
    assert not (DOCS / 'episode-history.md').exists()


def test_every_owner_is_a_guide_here_or_the_episode_history():
    assert {s['owner'] for s in LAYOUT['sections']} == {'authoring-reference.md', EPISODE_HISTORY, *OWNERS}
    assert all(not urlsplit(owner).scheme and (DOCS / owner).is_file() for owner in OWNERS)
    assert EPISODE_HISTORY in {s['owner'] for s in LAYOUT['sections']}


@pytest.mark.parametrize('section', LAYOUT['sections'], ids=lambda s: s['anchor'])
def test_legacy_bookmarks_resolve_to_their_owned_sections(section):
    index = (DOCS / 'authoring-reference.md').read_text()
    assert section['anchor'] in anchors(index)
    if section['owner'] != 'authoring-reference.md':
        destination = section['owner'] + '#' + section['anchor']
        assert f']({destination})' in index
    if section['owner'] in OWNERS:
        assert section['anchor'] in anchors((DOCS / section['owner']).read_text())


def test_every_existing_code_fence_is_preserved_in_its_task_or_history_owner():
    expected = Counter((f['owner'], f['language'], f['sha256']) for f in LAYOUT['fences'])
    actual = Counter(
        (owner, language, hashlib.sha256(code.encode()).hexdigest())
        for owner in OWNERS
        for language, code in fences((DOCS / owner).read_text())
    )
    # The migration snapshot pins legacy recipes; new, independently tested
    # recipes may be added without rewriting that historical evidence.
    assert actual >= expected


@pytest.mark.parametrize(
    'owner', ['../README.md', 'catalog/limbs.md', 'authoring-reference.md', *OWNERS, *EXTRA_GUIDES]
)
def test_moved_local_links_and_fragments_resolve(owner):
    document = DOCS / owner
    text = document.read_text()
    for target in re.findall(r'\]\(([^\s)]+)\)', text):
        url = urlsplit(target)
        if url.scheme or url.netloc:
            continue
        path = (document.parent / unquote(url.path)).resolve() if url.path else document
        assert path.exists(), (owner, target)
        if url.fragment and path.suffix == '.md':
            assert unquote(url.fragment) in anchors(path.read_text()), (owner, target)

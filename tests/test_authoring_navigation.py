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
OWNERS = sorted({s['owner'] for s in LAYOUT['sections']} - {'authoring-reference.md'})
EXTRA_GUIDES = ['authoring-audio.md']


def test_task_index_routes_to_focused_guides_without_embedded_recipes():
    text = (DOCS / 'authoring-reference.md').read_text()
    for owner in [*OWNERS, *EXTRA_GUIDES]:
        assert f']({owner}' in text, owner
    assert '<!-- diagnostic-repair:start -->' not in text
    assert '```python' not in text
    assert 'Episode history' in text


@pytest.mark.parametrize('section', LAYOUT['sections'], ids=lambda s: s['anchor'])
def test_legacy_bookmarks_resolve_to_their_owned_sections(section):
    index = (DOCS / 'authoring-reference.md').read_text()
    assert section['anchor'] in anchors(index)
    if section['owner'] != 'authoring-reference.md':
        destination = section['owner'] + '#' + section['anchor']
        assert f']({destination})' in index
        assert section['anchor'] in anchors((DOCS / section['owner']).read_text())


def test_every_existing_code_fence_is_preserved_in_its_task_or_history_owner():
    expected = Counter((f['owner'], f['language'], f['sha256']) for f in LAYOUT['fences'])
    actual = Counter(
        (owner, language, hashlib.sha256(code.encode()).hexdigest())
        for owner in OWNERS
        for language, code in fences((DOCS / owner).read_text())
    )
    assert actual == expected


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

"""Opt-in Okayville delivery changes preserve the drawings and captions already delivered."""

from dataclasses import replace
from pathlib import Path

import pytest

from srstudio import Episode, EpisodeSpec, locations, signature
from srstudio.releases import Release, items, load
from srstudio.sample import Line, write_sample_project
from srstudio.social import InstagramPost, fingerprint


def episode(root, **kw):
    write_sample_project(root, [Line('manager', 'Hello.', 1.0)])
    return Episode(EpisodeSpec(slug='t', title='t', description='t', root=root, seed=1, audio=None, font=None, **kw))


def test_explicit_code_keeps_pre_change_bytes(tmp_path):
    """Published reels pass SR-1028 explicitly since the default became None (ADR 0253); their bytes hold."""
    ep = episode(tmp_path, signature_code='SR-1028')
    locations.office_wide(ep.cv, ep.comp)
    assert ep.scene.to_bytes() == (Path(__file__).parent / 'data/okay-default.scene.xml').read_bytes()


@pytest.mark.parametrize('performing', [False, True])
def test_cactus_only_episode_and_cover_have_no_code(tmp_path, performing):
    ep = episode(tmp_path / 'project', signature_code=None)
    if performing:
        signature.cactus(ep.cv, ep.comp, 500, 900, act=signature.Act(end=ep.t.duration))
    else:
        locations.office_wide(ep.cv, ep.comp)
    hidden = ep.cv.rect(ep.comp, 0, 0, 20, 20, '#ffffff')
    ep.hide_on_cover(hidden)
    document = ep.finish(tmp_path / 't.scene.xml').read_bytes()
    assert b'sig-cactus' in document and b'sig-code' not in document and b'SR-1028' not in document
    assert b'id="cover"' in document


def test_cactus_only_still_requires_the_cactus(tmp_path):
    ep = episode(tmp_path / 'project', signature_code=None)
    with pytest.raises(signature.SignatureError, match='sig-cactus'):
        ep.finish(tmp_path / 't.scene.xml')


def test_explicit_code_still_requires_requested_code(tmp_path):
    ep = episode(tmp_path / 'project', signature_code='SR-1028')
    signature.cactus(ep.cv, ep.comp, 500, 900)
    with pytest.raises(signature.SignatureError, match='sig-code'):
        ep.finish(tmp_path / 't.scene.xml')


@pytest.mark.parametrize('last', [False, True])
@pytest.mark.parametrize('credit', ['', ' Credit '])
@pytest.mark.parametrize('tags', [(), ('#tag',)])
def test_caption_block_order(last, credit, tags):
    post = InstagramPost(title=' t ', description=' d ', credit=credit, hashtags=tags, credit_last=last)
    tail = ([credit.strip()] if credit.strip() else []) + (['#tag'] if tags else [])
    if last:
        tail.reverse()
    assert post.text() == '\n\n'.join(['t', 'd', *tail]) + '\n'


def test_existing_fingerprint_and_opt_in_caption_fingerprint(tmp_path):
    font = tmp_path / 'font'
    font.write_bytes(b'baseline font')
    post = InstagramPost(title='t', description='d', credit='Credit', hashtags=('#tag',))
    old = fingerprint(post, tmp_path / 'video', font)
    assert old == '477984470076ac4dbb198368916a78328595cc4524ffe447c8feb249f3362d31'
    last = replace(post, credit_last=True)
    assert fingerprint(last, tmp_path / 'video', font) != old
    # The resulting caption, rather than a new schema field, is fingerprinted.
    same_text = InstagramPost(title='t', description='d\n\n#tag', credit='Credit')
    assert fingerprint(last, tmp_path / 'video', font) == fingerprint(same_text, tmp_path / 'video', font)


def test_release_loading_and_items_preserve_credit_last(tmp_path):
    folder = tmp_path / 'releases'
    folder.mkdir()
    (folder / '__init__.py').write_text('')
    (folder / 'a_b.py').write_text(
        'from srstudio.releases import Release\nfrom srstudio.social import InstagramPost\n'
        'RELEASE = Release("a-b", InstagramPost(title="t", description="d", '
        'hashtags=("#tag",), credit="Credit", credit_last=True))\n'
    )
    releases = load(folder)
    post = releases['a-b'].post
    assert isinstance(releases['a-b'], Release)
    assert items(releases, tmp_path / 'renders', tmp_path / 'episodes')['a-b'].post is post
    assert post.text() == 't\n\nd\n\n#tag\n\nCredit\n'

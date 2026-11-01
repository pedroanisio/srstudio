"""The phone open on an invented article: it draws what it was given, refuses a headline it could not show whole, and
carries no name a real paper or site could own."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import Canvas, collage, collage_article, flat_counter, registry
from srstudio.canvas import Signature
from srstudio.collage_article import ArticleError, article
from srstudio.errors import SrstudioError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=10.0, background=collage.PAPER.background)
    cv = Canvas(scene, collage.PAPER, namer=flat_counter("k"), signature=Signature())
    cv.font_asset = "font"
    return cv


def drawn(**kw) -> tuple[bytes, object]:
    cv = canvas()
    args = dict(x=190.0, y=830.0, w=700.0, h=960.0, headline="LOCAL MAN HAS NOT CALLED HIS MOTHER")
    g = article(cv, cv.comp, **{**args, **kw})
    return cv.scene.to_bytes(layout="pretty"), g


def test_it_is_a_registered_collage_prop():
    assert registry.get("prop", "collage-article").builder is collage_article.article


def test_the_headline_and_the_sender_are_on_the_page():
    body, g = drawn(sender="FROM: MOM")
    assert b"LOCAL MAN HAS NOT CALLED HIS MOTHER" in body and b"FROM: MOM" in body
    assert g is not None


def test_no_sender_leaves_the_strip_out():
    body, _ = drawn()
    assert b"FROM:" not in body


def test_the_only_words_on_the_page_are_the_callers():
    cv = canvas()
    headline = "YOUR KIDNEYS: NINE SILENT WARNINGS"
    article(cv, cv.comp, 190.0, 830.0, 700.0, 960.0, headline, sender="FROM: MOM")
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    words = [e.get("text") for e in root.iter() if e.get("text")]
    assert sorted(words) == ["FROM: MOM", headline]  # no masthead, byline, date or address


@pytest.mark.parametrize("w", [0.0, -700.0, float("nan")])
def test_a_page_with_no_width_is_refused(w):
    with pytest.raises(ArticleError):
        drawn(w=w)


def test_a_headline_that_would_clip_is_refused():
    with pytest.raises(ArticleError, match="does not fit"):
        drawn(headline="ANTIDISESTABLISHMENTARIANISM IS COMING FOR YOUR GUTTERS", size=120.0)


def test_a_headline_below_the_legibility_floor_is_refused():
    with pytest.raises(ArticleError, match="legib"):
        drawn(size=20.0)


def test_an_empty_headline_is_refused():
    with pytest.raises(ArticleError, match="headline"):
        drawn(headline="   ")


def test_a_lower_case_headline_is_refused_as_the_font_has_only_capitals():
    with pytest.raises(ArticleError, match="capitals"):
        drawn(headline="Local man has not called his mother")


def test_its_error_is_the_librarys():
    assert issubclass(ArticleError, SrstudioError)

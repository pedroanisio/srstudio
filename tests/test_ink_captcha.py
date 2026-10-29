"""The Ink captcha: the checkbox card, the 3×3 picture grid with its prompt, picks and verdict."""

import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import MONO, Canvas, ink_captcha, registry, shared_counter
from srstudio.canvas import Signature
from srstudio.ink_captcha import CaptchaError

LIGHTS = ("light", "car", "light", "tree", "light", "car", "tree", "car", "light")


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=6.0, background=MONO.background)
    return Canvas(scene, MONO, font_asset="patrick-hand", namer=shared_counter(), signature=Signature())


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas):
    return [t.get("text") for t in tree(cv).iter("text")]


def opacity_keys(cv: Canvas):
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == "opacity"
    ]


def test_the_checkbox_card_shows_its_label_and_ticks_at_the_click():
    cv = canvas()
    ink_captcha.checkbox(cv, cv.comp, "I'm not a robot", tick_at=1.2)
    assert "I'm not a robot" in texts(cv)
    assert [(0.0, 0.0), (1.2, 1.0)] in opacity_keys(cv)  # the tick appears on the click
    cv2 = canvas()
    ink_captcha.checkbox(cv2, cv2.comp, "I'm not a router")
    assert opacity_keys(cv2) == []  # no click: an empty box


def test_the_grid_shows_the_prompt_nine_tiles_and_each_pick_from_its_moment():
    cv = canvas()
    ink_captcha.captcha(
        cv, cv.comp, prompt="Select all images with traffic lights.", tiles=LIGHTS, picks=[(0.5, 0), (0.9, 4)]
    )
    assert texts(cv)[0] == "Select all images with traffic lights."
    groups = [g.get("id") for g in tree(cv).iter("group")]
    assert sum(1 for g in groups if g and g.startswith("tile-")) == 9
    picked = opacity_keys(cv)
    assert [(0.0, 0.0), (0.5, 1.0)] in picked and [(0.0, 0.0), (0.9, 1.0)] in picked


def test_the_verdict_covers_the_grid_from_its_moment():
    cv = canvas()
    ink_captcha.captcha(cv, cv.comp, prompt="Pick one.", tiles=("laptop",) * 9, verdict=(0.4, "VERIFICATION FAILED"))
    assert "VERIFICATION FAILED" in texts(cv)
    assert [(0.0, 0.0), (0.4, 1.0)] in opacity_keys(cv)


def test_every_tile_kind_draws_and_the_grid_carries_the_signature_code():
    cv = canvas()
    ink_captcha.captcha(
        cv, cv.comp, prompt="All of them.", tiles=ink_captcha.TILES + ("light",) * (9 - len(ink_captcha.TILES))
    )
    assert len(list(tree(cv).iter("shape"))) > 60
    assert any((g.get("id") or "").startswith("sig-code") for g in tree(cv).iter("group"))


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        (dict(prompt="", tiles=LIGHTS), "prompt"),
        (dict(prompt="x" * 61, tiles=LIGHTS), "prompt"),
        (dict(prompt="Pick.", tiles=LIGHTS[:8]), "nine tiles"),
        (dict(prompt="Pick.", tiles=("light",) * 8 + ("dragon",)), "dragon"),
        (dict(prompt="Pick.", tiles=LIGHTS, picks=[(0.5, 9)]), "tile 9"),
        (dict(prompt="Pick.", tiles=LIGHTS, picks=[(0.5, 1), (0.8, 1)]), "twice"),
        (dict(prompt="Pick.", tiles=LIGHTS, picks=[(-0.1, 1)]), "time"),
        (dict(prompt="Pick.", tiles=LIGHTS, verdict=(-1.0, "NO")), "time"),
        (dict(prompt="Pick.", tiles=LIGHTS, verdict=(1.0, "")), "verdict"),
    ],
)
def test_the_grid_refuses_what_it_cannot_show(kwargs, match):
    cv = canvas()
    with pytest.raises(CaptchaError, match=match):
        ink_captcha.captcha(cv, cv.comp, **kwargs)


@pytest.mark.parametrize(
    ("label", "tick", "match"), [("", None, "label"), ("x" * 25, None, "label"), ("ok", -1.0, "time")]
)
def test_the_checkbox_refuses_what_it_cannot_show(label, tick, match):
    cv = canvas()
    with pytest.raises(CaptchaError, match=match):
        ink_captcha.checkbox(cv, cv.comp, label, tick_at=tick)


def test_both_cards_are_registered_ink_props():
    for name in ("ink-captcha", "ink-checkbox"):
        part = registry.get("prop", name)
        assert part.style == "ink"


def test_a_pick_at_the_first_frame_is_shown_without_keys():
    cv = canvas()
    ink_captcha.captcha(cv, cv.comp, prompt="Pick.", tiles=LIGHTS, picks=[(0.0, 2)])
    assert opacity_keys(cv) == []

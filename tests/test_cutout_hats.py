"""Hats that stack, sway and come down."""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from srstudio import cutout_hats
from srstudio.show import BUG_BOX
from support.tip_tablet import canvas

FULL = tuple((kind, 1.0 + n) for n, kind in enumerate(cutout_hats.HATS))


def ids(cv) -> list[str]:
    return [e.get("id", "") for e in ET.fromstring(cv.scene.to_bytes()).iter("group")]


def test_every_kind_of_hat_stands_on_the_one_under_it():
    cv = canvas()
    cutout_hats.hat_stack(cv, cv.comp, 540, 800, FULL)
    for n, kind in enumerate(cutout_hats.HATS):
        assert f"hat-stack-{n}-{kind}" in ids(cv)


def test_a_full_stack_is_taller_than_the_room_above_a_seated_head():
    assert cutout_hats.stack_height(cutout_hats.HATS) * 1.6 > 650


def test_a_hat_of_no_known_kind_is_refused():
    cv = canvas()
    with pytest.raises(cutout_hats.CutoutHatsError, match="sombrero"):
        cutout_hats.hat_stack(cv, cv.comp, 540, 800, (("sombrero", 1.0),))


@pytest.mark.parametrize(
    "hats", [(), (("trilby", -1.0),), (("trilby", float("nan")),), (("trilby", 2.0), ("boater", 1.0))]
)
def test_a_stack_it_cannot_grow_is_refused(hats):
    cv = canvas()
    with pytest.raises(cutout_hats.CutoutHatsError):
        cutout_hats.hat_stack(cv, cv.comp, 540, 800, hats)


@pytest.mark.parametrize("topple", [(1.0, -1), (9.0, 0), (float("inf"), 1), (9.0,)])
def test_a_fall_it_cannot_play_is_refused(topple):
    cv = canvas()
    with pytest.raises(cutout_hats.CutoutHatsError):
        cutout_hats.hat_stack(cv, cv.comp, 540, 800, FULL[:3], topple=topple)


@pytest.mark.parametrize("scale", [0, -1, float("nan")])
def test_a_scale_of_no_size_is_refused(scale):
    cv = canvas()
    with pytest.raises(cutout_hats.CutoutHatsError):
        cutout_hats.hat_stack(cv, cv.comp, 540, 800, scale=scale)
    with pytest.raises(cutout_hats.CutoutHatsError):
        cutout_hats.tiny_hat(cv, cv.comp, scale=scale)


def test_the_default_stack_clears_the_bug_at_the_defaults():
    half_brim = 118
    assert 540 + half_brim < BUG_BOX[0]


def test_a_stack_that_falls_is_gone_by_the_end_of_the_fall():
    cv = canvas()
    cutout_hats.hat_stack(cv, cv.comp, 540, 800, FULL, topple=(9.0, -1))
    text = cv.scene.to_bytes().decode()
    assert str(9.0 + cutout_hats.TOPPLE) in text

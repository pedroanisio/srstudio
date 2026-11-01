"""What a trial shift hands out: a spare apron, and a small tag that says so."""

from __future__ import annotations

import pytest

from srstudio import cutout_trial
from srstudio.cutout_trial import CutoutTrialError, apron_spare, trial_tag
from support.tip_tablet import canvas


def test_a_spare_apron_hangs_from_its_neck_loop():
    cv = canvas()
    g = apron_spare(cv, cv.comp, 300, 400, scale=0.8)
    assert (float(g.x), float(g.y), float(g.scaleX)) == (300, 400, 0.8)
    assert cutout_trial.GREEN in cv.scene.to_bytes().decode()


def test_a_tag_carries_its_word_and_is_centered_on_its_place():
    cv = canvas()
    g = trial_tag(cv, cv.comp, 120, 90)
    drawn = cv.scene.to_bytes().decode()
    assert (float(g.x), float(g.y)) == (120, 90)
    assert "TRIAL" in drawn


def test_a_tag_can_say_another_short_word():
    cv = canvas()
    trial_tag(cv, cv.comp, label="TEMP")
    assert "TEMP" in cv.scene.to_bytes().decode()


def test_a_tag_needs_a_font():
    cv = canvas(font=None)
    with pytest.raises(CutoutTrialError, match="font"):
        trial_tag(cv, cv.comp)


@pytest.mark.parametrize("label", ["", "   ", "PROBATIONARY", 7])
def test_a_tag_holds_one_short_word(label):
    cv = canvas()
    with pytest.raises(CutoutTrialError, match="label"):
        trial_tag(cv, cv.comp, label=label)


@pytest.mark.parametrize("build", [apron_spare, trial_tag])
@pytest.mark.parametrize("scale", [0, -1, float("nan"), "big"])
def test_a_scale_is_a_positive_number(build, scale):
    cv = canvas()
    with pytest.raises(CutoutTrialError, match="scale"):
        build(cv, cv.comp, scale=scale)


@pytest.mark.parametrize("build", [apron_spare, trial_tag])
def test_a_place_is_two_numbers(build):
    cv = canvas()
    with pytest.raises(CutoutTrialError, match="place"):
        build(cv, cv.comp, "left", 3)

"""The set modules' refusals are their own SrstudioError subclasses and still the ValueError they always were
(ADR 0034): props, locations and the signature."""

from __future__ import annotations

import pytest
from sr_core.scene import Scene

from srstudio import OFFICE, Canvas, Signature, locations, props, signature
from srstudio.errors import SrstudioError


def canvas(code: str = "SR-1028") -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12, background=OFFICE.background)
    return Canvas(scene, OFFICE, signature=Signature(code=code))


def refused(call, error: type[Exception], match: str) -> None:
    with pytest.raises(error, match=match) as caught:
        call()
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, ValueError)


def test_prop_refusals_are_prop_errors():
    cv = canvas()
    refused(lambda: props.crumbs(cv, cv.comp, 500, 1200, 1500, toss=1.5, count=0), props.PropError, "at least one")
    refused(lambda: props.whiteboard(cv, cv.comp, 0, 0, 40, 40), props.PropError, "whiteboard")
    refused(lambda: props.speakerphone(cv, cv.comp, 0, 0, talk=[(1.0, 0.5)]), props.PropError, "talk spans")


def test_location_refusals_are_location_errors():
    cv = canvas()
    refused(lambda: locations.elevator(cv, cv.comp, going="sideways"), locations.LocationError, "going")
    refused(lambda: locations.elevator(cv, cv.comp, floors=((1.0, 1),)), locations.LocationError, "starting at 0")
    refused(lambda: locations.elevator(cv, cv.comp, lit=99), locations.LocationError, "lit is a button")


def test_a_signature_code_without_glyphs_is_a_signature_error():
    cv = canvas("S@")
    refused(lambda: signature.code(cv, cv.comp, 0, 0), signature.SignatureError, "without a glyph")

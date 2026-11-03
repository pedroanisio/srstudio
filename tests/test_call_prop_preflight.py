"""Call props reject invalid placement and absent text resources before drawing."""

import pytest

from srstudio import cutout_call as call
from support.saga import canvas


@pytest.mark.parametrize('builder', [call.video_tile, call.desk_phone])
@pytest.mark.parametrize('position', [dict(x=float('nan')), dict(y=float('inf')), dict(x=True), dict(y='900')])
def test_call_position_is_finite_numeric_and_atomic(builder, position):
    cv = canvas()
    before = cv.scene.to_bytes(), dict(cv.__dict__)
    with pytest.raises(call.CutoutCallError):
        builder(cv, cv.comp, **position)
    assert cv.scene.to_bytes() == before[0]
    assert cv.__dict__ == before[1]


@pytest.mark.parametrize(
    'builder,options',
    [
        (call.video_tile, dict(plate='HOST')),
        (call.desk_phone, dict(title='CALL')),
        (call.desk_phone, dict(lines=((1, 'HELLO'),))),
    ],
)
def test_text_requires_font_before_geometry_or_user_callback(builder, options):
    cv = canvas()
    cv.font_asset = None
    seen = []
    if builder is call.video_tile:
        options = dict(options, inside=lambda g: seen.append(g))
    before = cv.scene.to_bytes()
    with pytest.raises(call.CutoutCallError):
        builder(cv, cv.comp, **options)
    assert cv.scene.to_bytes() == before and seen == []


@pytest.mark.parametrize(
    'builder,options',
    [(call.video_tile, dict(plate=12)), (call.desk_phone, dict(title=None)), (call.desk_phone, dict(lines=((1,),)))],
)
def test_malformed_copy_and_line_records_have_typed_atomic_errors(builder, options):
    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(call.CutoutCallError):
        builder(cv, cv.comp, **options)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('builder', [call.video_tile, call.desk_phone])
def test_unlettered_call_props_still_need_no_font(builder):
    cv = canvas()
    cv.font_asset = None
    assert builder(cv, cv.comp) is not None

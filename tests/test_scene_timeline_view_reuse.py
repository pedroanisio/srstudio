"""Internal view resolution reuses a checked scene; public boundaries still verify it."""

from dataclasses import replace

import pytest

from srstudio import composition as c
from srstudio import scene_motion as m
from support.composition import plate_source, prepared_plate_plan


def test_each_distinct_timeline_scene_is_validated_once_not_per_raster_layer(monkeypatch):
    source = plate_source()
    base = prepared_plate_plan(source)
    layer = base.spec.layers[0]
    spec = replace(base.spec, fps=c.FrameRate(4), layers=(layer, replace(layer, id='copy')))
    motion = m.SceneMotion(
        camera=(m.CameraKey(0, spec.camera), m.CameraKey(1, replace(spec.camera, position=(0.1, 0, 10))))
    )
    checked = []
    preflight = c.preflight

    def observe(*args, **kwargs):
        plan = preflight(*args, **kwargs)
        checked.append(plan.digest)
        return plan

    monkeypatch.setattr(c, 'preflight', observe)
    timeline = m.plan_scene(spec, base.bindings, motion, rasters=(source,))
    expected = {p.digest for p in (*timeline.samples, timeline.terminal)}
    assert set(checked) == expected
    assert len(checked) == len(expected)
    for plan in (*timeline.samples, timeline.terminal):
        assert c.plate_view(plan, layer.id).plan_digest == plan.digest
    assert len(checked) > len(expected)  # The public API still checks callers' evidence.


@pytest.mark.parametrize('field,value', [('digest', '0' * 64), ('purpose', 'candidate-review')])
def test_public_view_refuses_forged_validation_evidence(field, value):
    base = prepared_plate_plan(plate_source())
    with pytest.raises(c.CompositionError):
        c.plate_view(replace(base, **{field: value}), base.spec.layers[0].id)

"""Bento's rendered paws sit where, and point the way, the body solver says, in every shot.

Two limits bound what these frames can prove. The paw is a flat front-view card, so a
heel-to-toe reflection through its plane moves no point and no pixel test can see it; the
reversed (180 degree) control is caught only by its stray-pixel margin. And every solved sole
in this motion has yaw 0, so the frames show feet facing the camera, never a turned foot.
"""

import importlib
import math
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

# Both painter windows, both steps, the held opening, and both sides of the 4 s camera cut.
TIMES = (0.25, 0.85, 1.1, 1.35, 2.2, 2.45, 2.95, 3.1, 3.95, 4.05, 4.35, 5.2, 5.45, 5.95)
PAW = (212, 154, 101)  # Bento's paw fill; nothing else in the component uses it.
COVERED, STRAY = 0.75, 0.02  # A paw fits when its fill covers this share of the outline with this little spill.
CONTROLS = {'turned45': 45.0, 'reversed': 180.0}


def margins(covered, stray, area):
    """Signed distance to each fit threshold; a fit passes only when both are non-negative."""
    return {'coverage': round(covered / area - COVERED, 4), 'stray': round(STRAY - stray / max(covered, 1), 4)}


@pytest.fixture
def example(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))
    return importlib.import_module('examples.drawing_body')


def paw_outline(example, leg, time, *, turn=0.0):
    """The paw fill contour in frame pixels for the foot transform, optionally turned about its sole."""
    from examples.drawing_proof import sample

    from srstudio.limbs import Quaternion, Vec3

    transform = example.foot_transform(leg, time)
    rotation = Quaternion.axis_angle(Vec3(0, 1, 0), math.radians(transform.rotation[1] + turn))
    origin = Vec3(*transform.translation)
    binding, _ = example.foot_source()
    points = [origin + rotation.rotate(Vec3(*p)) for p in binding.forms[0].path.points]
    return sample(time).view.project([(p.x, p.y, -p.z) for p in points])


def test_paw_outline_matches_the_composition_camera(example):
    from srstudio import composition as c
    from srstudio.limbs import Vec3

    timeline = example.body_scene(fps=2, size=(1080, 1920)).timeline
    binding, _ = example.foot_source()
    for span in timeline.spans:
        time = span.start
        plan = timeline.samples[span.scene]
        pose = example.body_plan().sample(time if time < 3 else time - 3)
        for leg in pose.legs:
            layer = f'{leg.side}-foot-{"back" if time < 3 else "front"}'
            camera = c.spatial_camera(plan, layer)
            projected = np.array([camera.project(Vec3(*p)).xy for p in binding.forms[0].path.points])
            assert projected == pytest.approx(paw_outline(example, leg, time), abs=1e-6)


def test_a_heel_toe_reflection_of_the_flat_paw_projects_identically(example):
    """The paw is a flat card: reflecting it through its own plane moves no point, so no frame can show it."""
    binding, _ = example.foot_source()
    assert {point[2] for form in binding.forms for point in form.path.points} == {0.0}
    for time in (0.25, 4.05):
        for leg in example.body_plan().sample(time if time < 3 else time - 3).legs:
            outline = paw_outline(example, leg, time)
            transform = example.foot_transform(leg, time)
            assert paw_outline(example, leg, time, turn=0.0) == pytest.approx(outline)
            assert transform.rotation[0] == transform.rotation[2] == 0


def test_feet_render_at_full_size_in_every_shot(example, scene_render, tmp_path):
    import shapely

    from srstudio import plates
    from srstudio import scene_motion as m
    from srstudio._bounded_process import ProcessLimits, run
    from srstudio.gpu import held

    study = example.body_scene()
    full = study.timeline
    layers = tuple(layer for layer in full.base.spec.layers if layer.asset not in ('car', 'hand', 'shadow'))
    names, assets = {layer.id for layer in layers}, {layer.asset for layer in layers}
    timeline = m.plan_scene(
        replace(full.base.spec, layers=layers, background='#efe8df'),
        tuple(binding for binding in full.base.bindings if binding.id in assets),
        replace(full.motion, transforms=tuple(track for track in full.motion.transforms if track.layer in names)),
        purpose=full.base.purpose,
    )
    result = m.emit_timeline(
        timeline,
        tuple(source for source in study.vectors if source.id in assets),
        tmp_path / 'feet',
        engine=scene_render,
        cache=tmp_path / 'cache',
    )
    assert result.work.engine_invocations == 0 and len(result.xml) < 8 * 1024**2
    report = []
    for time in TIMES:
        output = tmp_path / f'feet-{time:.2f}.png'
        with held():
            run(
                (
                    str(scene_render),
                    'render',
                    str(tmp_path / 'feet/scene.xml'),
                    '--time',
                    str(time),
                    '--output',
                    str(output),
                    '--strict',
                    '--quality',
                    'final',
                    '--json',
                ),
                input=b'',
                limits=ProcessLimits(timeout=120, memory_bytes=8 * 1024**3),
            )
        pixels = plates.pixels(output)
        assert pixels.shape == (1920, 1080, 4) and np.all(pixels[..., 3] == 255)
        paw = np.all(pixels[..., :3] == PAW, axis=2)
        rows, cols = np.nonzero(paw)
        centers = (cols + 0.5, rows + 0.5)
        # The frame shows the pose and camera held from the start of its span.
        held_at = next(span.start for span in timeline.spans if span.start <= time < span.end)
        pose = example.body_plan().sample(held_at if held_at < 3 else held_at - 3)
        outlines = {leg.side: shapely.Polygon(paw_outline(example, leg, held_at)) for leg in pose.legs}

        def fit(outline, other, centers=centers):
            """Paw pixels inside the outline, and paw pixels around it that belong to neither paw."""
            inside = shapely.contains_xy(outline.buffer(1.5), *centers)
            near = shapely.contains_xy(outline.envelope.buffer(12), *centers)
            elsewhere = shapely.contains_xy(other.buffer(1.5), *centers)
            return int(np.count_nonzero(inside)), int(np.count_nonzero(near & ~inside & ~elsewhere))

        for leg in pose.legs:
            outline = outlines[leg.side]
            other = next(shape for side, shape in outlines.items() if side != leg.side)
            covered, stray = fit(outline, other)
            # 88% of the outline is visible fill; toe and edge marks cover the rest.
            assert covered >= COVERED * outline.area, (time, leg.side, covered, outline.area)
            assert stray <= STRAY * covered, (time, leg.side, stray, covered)
            row = {
                'time': time,
                'held_from': held_at,
                'side': leg.side,
                'planted': leg.planted,
                'outline_px': round(outline.area, 1),
                'covered_px': covered,
                'stray_px': stray,
                'margin': margins(covered, stray, outline.area),
            }
            # Controls: the same paw turned 45 degrees, and reversed (turned 180 degrees, toes pointing
            # backwards), each about its sole, must fail the same fit.
            for name, turn in CONTROLS.items():
                control = shapely.Polygon(paw_outline(example, leg, held_at, turn=turn))
                control_covered, control_stray = fit(control, other)
                margin = margins(control_covered, control_stray, control.area)
                assert min(margin.values()) < 0, (time, leg.side, name, margin)
                row[name] = {
                    'outline_px': round(control.area, 1),
                    'covered_px': control_covered,
                    'stray_px': control_stray,
                    'margin': margin,
                }
            report.append(row)
    (tmp_path / 'feet.json').write_text(__import__('json').dumps(report, indent=1) + '\n')

"""World-anchored per-foot support for the candidate's native figure."""

import importlib
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import body
from srstudio import composition as c
from srstudio.limbs import Vec3


@pytest.fixture(autouse=True)
def example_path(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).parents[1]))


@pytest.fixture
def support():
    return importlib.import_module('examples.drawing_support')


@pytest.fixture(scope='module')
def study():
    with pytest.MonkeyPatch.context() as patch:
        patch.syspath_prepend(str(Path(__file__).parents[1]))
        return importlib.import_module('examples.drawing_attached').attached_scene()


def _xyz(point):
    return (point.x, point.y, point.z)


def _planted_runs(plan, side, times):
    runs, current = [], []
    for time in times:
        leg = next(leg for leg in plan.sample(time).legs if leg.side == side)
        if leg.planted:
            current.append((time, leg.sole.origin))
        elif current:
            runs.append(current)
            current = []
    if current:
        runs.append(current)
    return runs


@pytest.mark.parametrize('window', ['back', 'front'])
def test_each_window_compiles_quasi_static_support_with_alternating_steps(support, window):
    plan = support.body_plan(window)
    assert isinstance(plan, body.BodyPlan)
    assert plan.duration == 3
    assert [step.side for step in plan.score.steps] == (['left', 'right'] if window == 'back' else ['right', 'left'])
    times = [i / 240 for i in range(721)]
    margins = [plan.sample(time).support_margin for time in times]
    assert min(margins) >= plan.profile.support_margin - 1e-9
    for side in ('left', 'right'):
        runs = _planted_runs(plan, side, times)
        assert len(runs) == 2  # Planted, one authored step, planted again.
        for run in runs:
            assert all(origin == run[0][1] for _, origin in run)  # A planted sole never slides.
            assert run[0][1].y == 0


def test_window_travel_follows_the_declared_depth_cut_along_the_card_axis(support):
    for window, start, travel in (('back', Vec3(-2.10, 0, -1.15), -0.20), ('front', Vec3(-1.10, 0, 1.15), 0.20)):
        plan = support.body_plan(window)
        rotation = support.card_rotation(window)
        lateral = rotation.rotate(Vec3(1, 0, 0))
        first, last = plan.sample(0).root, plan.sample(3).root
        assert _xyz(first.origin) == pytest.approx(_xyz(start - Vec3(0, support.PELVIS_HEIGHT, 0)), abs=1e-12)
        assert _xyz(last.origin - first.origin) == pytest.approx(_xyz(lateral * travel), abs=1e-12)
        assert first.rotation == last.rotation == rotation
        for time in (0, 0.9, 2.2, 3):
            assert all(leg.sole.rotation == rotation for leg in plan.sample(time).legs)
    assert support.body_pose(2.999).root == support.body_plan('back').sample(2.999).root
    assert support.body_pose(3).root == support.body_plan('front').sample(0).root


def test_profile_is_measured_from_the_drawn_legs(support):
    from srstudio import toon_bento as bento
    from srstudio.toon import fx

    meters = (fx(bento._at(1000, 0)[0]) - fx(bento._at(0, 0)[0])) / 1000 * support.SCALE / 100
    profile = support.PROFILE
    assert profile.hip_width == pytest.approx(110 * meters, abs=1e-5)
    assert profile.foot_width == pytest.approx(120 * meters, abs=1e-5)
    assert support.PELVIS_HEIGHT == pytest.approx(181 * meters, abs=1e-5)


def test_rest_legs_are_the_unchanged_native_drawing(support):
    from srstudio import toon_bento as bento

    for x in support.LEG_X.values():
        assert bento._leg(x, bento._same) == bento._leg(x)
    identity = support.deformation(0, 1, (0, 0))
    assert all(bento._leg(x, identity) == bento._leg(x) for x in support.LEG_X.values())
    layers = support.leg_layers(2.35)
    for side, x in support.LEG_X.items():
        assert layers[side] == tuple(bento._leg(x, support.leg_place(2.35, side)))
        assert layers[side] != tuple(bento._leg(x))
    assert bento.trunk_layers() == (
        *bento._leg(support.LEG_X['left']),
        *bento._leg(support.LEG_X['right']),
        *bento._blazer_layers(),
    )


@pytest.mark.parametrize('time', [0, 0.5, 0.75, 1.2, 1.9, 2.95, 3, 3.5, 4, 4.4, 5, 5.99])
def test_drawn_soles_are_the_world_soles_on_the_figure_card(support, time):
    moment = support.held(time)
    transform = support.card_transform(moment)
    for leg in support.body_pose(moment).legs:
        world = leg.sole.origin * 100
        point = support.to_world(transform, support.native(support.drawn_sole(time, leg.side)))
        assert (point.x, point.y, point.z) == pytest.approx((world.x, world.y, world.z), abs=1e-6)


@pytest.mark.parametrize('fps', [1, 2, 12, 24])
def test_every_shared_camera_sample_stays_inside_the_frontal_envelope(support, fps):
    from examples.drawing_proof import schedule

    angles = [support.view_angle(frame) for frame in schedule(fps=fps, events=support.EVENTS)]
    assert max(angles) <= support.VIEW_ENVELOPE
    assert max(angles) > 25  # The front window spans both sides of the camera cut.


def test_camera_outside_the_envelope_is_refused(support, monkeypatch):
    from examples.drawing_proof import sample

    monkeypatch.setattr(support, 'VIEW_ENVELOPE', 10.0)
    with pytest.raises(ValueError, match='frontal card'):
        support.support_transform(sample(4.5))


def test_card_orientation_is_actor_state_through_the_camera_cut(support):
    from examples.drawing_attached import attached_mesh, shoulder_frame
    from examples.drawing_proof import sample

    assert support.support_transform(sample(3.95)).rotation == support.support_transform(sample(4.05)).rotation
    before, after = shoulder_frame(3.95), shoulder_frame(4.05)
    root = support.body_pose(4.05).root.origin - support.body_pose(3.95).root.origin
    assert (after.origin - before.origin - root * 100).length < 0.5
    cups = [next(m for m in attached_mesh(t) if m.material == 'cup').vertices.mean(axis=0) for t in (3.95, 4.05)]
    carried = (cups[1][0] - cups[0][0], cups[1][1] - cups[0][1], cups[0][2] - cups[1][2])  # Clay +z is away.
    assert math.dist(carried, _xyz(root * 100)) < 2  # Develop's camera-facing card moved the cup 70 cm here.


@pytest.mark.parametrize('time', [0.25, 2.35, 3.0, 4.1])
def test_hip_line_follows_the_native_torso_lean_and_breath(support, time):
    from examples.drawing_proof import figure_performance

    head = figure_performance().sample(time).head
    seat = support.SEAT
    stretch = 1 + head.breath * figure_performance().rig.head_rig.style.breath_scale
    angle = math.radians(head.lean)
    for side, x in support.LEG_X.items():
        place = support.leg_place(time, side)
        for px in (x, x + 34.5, x + 69):
            dx, dy = px - seat[0], (700 - seat[1]) * stretch
            expected = (
                seat[0] + dx * math.cos(angle) - dy * math.sin(angle),
                seat[1] + dx * math.sin(angle) + dy * math.cos(angle),
            )
            assert place(px, 700) == pytest.approx(expected, abs=1e-9)


def test_lifted_foot_rises_and_lands_on_its_new_world_anchor(support):
    plan = support.body_plan('back')
    step = plan.score.steps[0]
    middle = (step.start + step.end) / 2
    lifted = next(leg for leg in plan.sample(middle).legs if leg.side == step.side)
    assert not lifted.planted and lifted.sole.origin.y < -0.01
    assert support.drawn_sole(middle, step.side)[1] < support.drawn_sole(step.start, step.side)[1] - 5
    landed = next(leg for leg in plan.sample(step.end).legs if leg.side == step.side)
    assert landed.planted and landed.sole == step.target


def test_supported_scene_owns_legs_once_and_registers_every_planted_sole(support, study):
    timeline = study.timeline
    layers = [layer.id for layer in timeline.base.spec.layers]
    assert layers == [
        'floor',
        'shadow',
        'legs-back',
        'figure-back',
        'hand-back',
        'car',
        'legs-front',
        'figure-front',
        'hand-front',
    ]
    figure = next(s for s in study.vectors if s.id == 'figure')
    legs = next(s for s in study.vectors if s.id == 'legs')
    trouser = b'#101F49'  # Only Bento's legs use this fill.
    assert trouser not in figure.xml
    assert trouser in legs.xml
    binding = next(b for b in timeline.base.bindings if b.id == 'legs')
    assert binding.forms == (c.FormSurface('legs', mode='ink'),)
    assert binding.candidate.source_digest == c.vector_source_digest(legs, forms=binding.forms)
    assert binding.nodes == sum(1 for _ in ET.fromstring(legs.xml).iter())
    assert timeline.cost.nodes <= timeline.base.spec.budget.max_nodes
    from examples.drawing_proof import sample

    checked = 0
    for span in timeline.spans:
        plan = timeline.samples[span.scene]
        layer = 'legs-back' if span.start < 3 else 'legs-front'
        camera = c.spatial_camera(plan, layer)
        for leg in support.body_pose(span.start).legs:
            if not leg.planted:
                continue
            world = leg.sole.origin * 100
            drawn = support.native(support.drawn_sole(span.start, leg.side))
            assert camera.project(Vec3(drawn[0], drawn[1], 0)).xy == pytest.approx(
                sample(span.start).view.project(((world.x, world.y, -world.z),))[0], abs=1e-6
            )
            checked += 1
    assert checked >= 2 * len(timeline.spans) - 20


def test_hand_shoulder_rides_the_supported_root(support):
    from examples.drawing_attached import shoulder_frame
    from examples.drawing_proof import sample

    first, later = shoulder_frame(1.2), shoulder_frame(2.2)
    shift = support.body_pose(2.2).root.origin.x - support.body_pose(1.2).root.origin.x
    assert later.origin.x - first.origin.x == pytest.approx(shift * 100, abs=2)
    assert support.support_transform(sample(1.2)).translation != support.support_transform(sample(2.2)).translation
    assert support.support_transform(sample(2.2)) == support.card_transform(2.2)


@pytest.mark.parametrize('time', [-0.01, 6.01, float('nan'), True, '1'])
def test_invalid_support_clock_is_refused(support, time):
    with pytest.raises(ValueError, match='support time'):
        support.body_pose(time)


def test_unknown_window_and_side_are_refused(support):
    with pytest.raises(ValueError, match='window'):
        support.body_plan('middle')
    with pytest.raises(ValueError, match='side'):
        support.drawn_sole(1, 'center')


def test_points_off_the_figure_card_are_refused(support):
    leg = support.body_pose(1).legs[0]
    support.register(1, leg.sole.origin * 100)
    with pytest.raises(ValueError, match='off the figure card'):
        support.register(1, leg.sole.origin * 100 + Vec3(0, 0, 5))

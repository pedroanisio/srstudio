"""Validate authored geometry, endpoint equivalence and deterministic work bounds."""

from dataclasses import replace

import pytest

from srstudio import acting
from srstudio import toon_bento as b
from srstudio._bento_blends import BentoBlender
from srstudio.character_clips import Interval, ToonClip, place_character
from srstudio.face_blends import FaceBlend, FaceBlendError, FaceLayers, FacePose, FaceSample, FaceTrack, segments
from srstudio.toon import Pose
from support.acting import canvas

NEUTRAL = FacePose('neutral', 'neutral')
CONCERNED = FacePose('concerned', 'frown')


def track():
    return FaceTrack((FaceBlend(1, 2, NEUTRAL, CONCERNED),), fps=12)


def poses():
    return (Pose(0, 'neutral', 'neutral', 'tablet'), Pose(2, 'concerned', 'frown', 'tablet'))


@pytest.mark.parametrize('pair', BentoBlender.transitions)
def test_every_declared_pair_has_exact_static_endpoints_and_deformed_middle(pair):
    driver = BentoBlender()
    a, z = pair
    for endpoint, weight in ((a, 0), (z, 1)):
        layers = driver.layers(FaceSample(a, z, weight))
        mood = b.MOODS[endpoint.eyes]
        assert layers.eyes == tuple(b._eye_layers(mood, None, 0, (0, 0)) + b._eye_layers(mood, None, 1, (0, 0)))
        assert layers.mouth == tuple(b._mouth_layers(endpoint.mouth))
    middle = driver.layers(FaceSample(a, z, 0.5))
    assert middle != driver.layers(FaceSample(a, z, 0))
    assert middle != driver.layers(FaceSample(a, z, 1))
    assert middle == driver.layers(FaceSample(a, z, 0.5))


def test_grid_stays_on_performance_zero_with_offgrid_launch_and_cut():
    authored = FaceTrack((FaceBlend(1.01, 2, NEUTRAL, CONCERNED),), fps=12)
    rig = acting.bento_blends().head_rig
    frames = authored.prepare(rig, poses(), 3)
    assert frames[0].start == 1.01
    assert frames[1].start == round(13 / 12, 6)
    assert frames[-1].end == 2
    sliced = list(segments(frames, 1.12, 1.9))
    assert sliced[0][0] == 1.12
    assert sliced[0][2] == frames[1].layers
    assert sliced[-1][1] == 1.9
    assert list(segments(frames, 0, 0.5)) == [(0, 0.5, None)]


@pytest.mark.parametrize(
    'kwargs',
    [
        {'start': True},
        {'end': float('nan')},
        {'start': 1.0000001},
        {'end': 1},
        {'source': None},
        {'target': NEUTRAL},
        {'curve': 'bounce-in'},
        {'curve': []},
    ],
)
def test_invalid_intervals_and_easing_are_typed(kwargs):
    with pytest.raises(FaceBlendError):
        replace(track().blends[0], **kwargs)


@pytest.mark.parametrize(
    'kwargs',
    [
        {'fps': True},
        {'fps': 0},
        {'fps': 121},
        {'blends': []},
        {'blends': ()},
        {'blends': (None,)},
        {'blends': (FaceBlend(1, 2, NEUTRAL, CONCERNED),) * 2},
        {'blends': (FaceBlend(0, 600, NEUTRAL, CONCERNED),)},
    ],
)
def test_invalid_tracks_are_bounded(kwargs):
    with pytest.raises(FaceBlendError):
        replace(track(), **kwargs)


@pytest.mark.parametrize('weight', [True, '0.5', float('nan'), -0.1, 1.1])
def test_malformed_samples_are_typed(weight):
    with pytest.raises(FaceBlendError):
        FaceSample(NEUTRAL, CONCERNED, weight)


def test_rejected_geometry_never_draws_or_allocates_ids():
    class Broken:
        transitions = ((NEUTRAL, CONCERNED),)

        def layers(self, sample):
            return FaceLayers((((0, 0, 1, 1, float('nan'), 1, 0, 0), 'ink'),), ())

    rig = replace(acting.bento_blends().head_rig, face_blender=Broken())
    clip = ToonClip(rig, poses(), face_blends=track())
    cv = canvas()
    before = cv.scene.to_bytes()
    counter = cv.uid
    calls = []

    def uid(prefix):
        calls.append(prefix)
        return counter(prefix)

    cv.uid = uid
    with pytest.raises(FaceBlendError):
        place_character(cv, cv.comp, clip, interval=Interval(0, 3))
    assert cv.scene.to_bytes() == before
    assert calls == []


def test_pair_and_pose_contract_failures():
    rig = acting.bento_blends().head_rig
    for bad_poses in (
        (Pose(0, 'deadpan', 'neutral', 'tablet'), poses()[1]),
        (poses()[0], Pose(2, 'neutral', 'neutral', 'tablet')),
        (poses()[0], Pose(1.5, 'neutral', 'neutral', 'present'), poses()[1]),
    ):
        with pytest.raises(FaceBlendError):
            track().prepare(rig, bad_poses, 3)
    with pytest.raises(FaceBlendError):
        track().prepare(rig, poses(), 2)
    for invalid in ((), (None,), (poses()[1], poses()[0])):
        with pytest.raises(FaceBlendError):
            track().prepare(rig, invalid, 3)


def test_driver_must_match_bound_rig_endpoints():
    class Incorrect:
        transitions = BentoBlender.transitions

        def layers(self, sample):
            return BentoBlender().layers(replace(sample, weight=0.5))

    with pytest.raises(FaceBlendError, match='endpoints'):
        track().prepare(replace(acting.bento_blends().head_rig, face_blender=Incorrect()), poses(), 3)


def test_bento_driver_refuses_undeclared_pairs_even_without_a_track():
    with pytest.raises(FaceBlendError) as caught:
        BentoBlender().layers(FaceSample(NEUTRAL, FacePose('happy', 'grin'), 0.5))
    assert caught.value.to_dict()['code'] == 'face_blend.unsupported'


@pytest.mark.parametrize('time', [True, float('inf'), '1'])
def test_sample_rejects_invalid_time(time):
    with pytest.raises(FaceBlendError):
        track().sample(time)
    with pytest.raises(FaceBlendError):
        track().blends[0].sample(time)


@pytest.mark.parametrize('kind', ['type', 'region', 'row', 'color', 'coordinates', 'declarations'])
def test_driver_failures_are_typed_and_bounded(kind, monkeypatch):
    import srstudio.face_blends as module

    class Broken:
        transitions = BentoBlender.transitions if kind != 'declarations' else ('anything',)

        def layers(self, sample):
            layers = BentoBlender().layers(sample)
            if sample.weight == 0 or sample.weight == 1:
                return layers
            if kind == 'type':
                return None
            if kind == 'region':
                return replace(layers, eyes=())
            if kind == 'row':
                return replace(layers, eyes=(None,))
            if kind == 'color':
                return replace(layers, eyes=((layers.eyes[0][0], 'not-a-color'),))
            return layers

    if kind == 'coordinates':
        monkeypatch.setattr(module, 'MAX_COORDINATES', 1)
    rig = replace(acting.bento_blends().head_rig, face_blender=Broken())
    with pytest.raises(FaceBlendError):
        track().prepare(rig, poses(), 3)

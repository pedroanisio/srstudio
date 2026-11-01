"""A character's local performance survives placement on another parent clock."""

import json
import subprocess

import numpy as np
import pytest
from sr_core.scene import Scene

from srstudio import Canvas, cast
from srstudio.character_clips import (
    ActorClip,
    CharacterClipError,
    GlossClip,
    Interval,
    Placement,
    PlateClip,
    PlateFrame,
    PlateLayer,
    ToonClip,
    place_character,
)
from srstudio.head_motion import Channel, HeadPlan
from srstudio.plates import write_png
from srstudio.rig import Performance
from srstudio.toon_bento import BENTO_RIG, pose_of


def canvas(local=False):
    scene = Scene(version='auto')
    scene.add_project(width=1080, height=1920, fps='30', duration=12)
    return Canvas(scene, font_asset=None, local_time=local)


def evaluate(engine, path, time):
    result = subprocess.run(
        [str(engine), 'eval', str(path), '--time', str(time), '--json'], capture_output=True, text=True, check=True
    )
    return json.loads(result.stdout)['result']['nodes']


def clips():
    return [
        ActorClip(cast.Manager, Performance(mouth=((0, 'rest'), (0.5, 'open')), nods=((0, 0), (1, 8)))),
        ToonClip(
            BENTO_RIG, (pose_of(0, 'neutral'), pose_of(0.5, 'happy')), head=HeadPlan(turn=Channel(((0, 0), (1, 2))))
        ),
        GlossClip('nadia', face=((0, 'open'), (0.5, 'flat')), pose=((0, 'down'), (0.5, 'up'))),
        GlossClip('sunny', face=((0, 'smile'), (0.5, 'alert'))),
        PlateClip((PlateFrame(0, (PlateLayer('plate', (0, 0)),)), PlateFrame(0.5, (PlateLayer('plate', (20, 30)),)))),
    ]


@pytest.mark.parametrize('index', range(5))
@pytest.mark.parametrize('local', [False, True])
def test_offset_preserves_actual_engine_pose_and_procedural_phase(scene_render, tmp_path, index, local):
    write_png(tmp_path / 'plate.png', np.full((80, 100, 4), 255, np.uint8))
    snapshots = []
    for offset in (0, 3):
        cv = canvas(local)
        cv.assets.add_image(id='plate', src='plate.png', width=100, height=80)
        group = place_character(cv, cv.comp, clips()[index], interval=Interval(offset, offset + 2), id='character')
        assert group.start == offset and group.end == offset + 2
        assert cv.local_time is local
        path = tmp_path / f'{offset}.xml'
        path.write_bytes(cv.scene.to_bytes())
        frames = []
        for second in (0, 0.25, 0.75, 1.5):
            nodes = evaluate(scene_render, path, offset + second)
            frames.append(
                [(n['id'], n['world'], n['world_opacity'], n['draw']) for n in nodes if n['id'] != 'character']
            )
        assert not any(n['id'] == 'character' for n in evaluate(scene_render, path, offset + 2))
        if offset:
            assert not any(n['id'] == 'character' for n in evaluate(scene_render, path, offset - 0.1))
        snapshots.append(frames)
    assert snapshots[0] == snapshots[1]


def test_parent_clock_and_source_anchor_are_explicit(scene_render, tmp_path):
    cv = canvas()
    sequence = cv.comp.add_sequence(id='shots')
    sequence.add_group(id='lead', end=3)
    shot = sequence.add_group(id='shot', end=5)
    place_character(
        cv,
        shot,
        ActorClip(cast.Manager),
        id='character',
        interval=Interval(1, 3),
        placement=Placement(400, 600, scale=2, anchor=(10, 20)),
    )
    path = tmp_path / 'nested.xml'
    path.write_bytes(cv.scene.to_bytes())
    nodes = evaluate(scene_render, path, 4.5)
    node = next(n for n in nodes if n['id'] == 'character')
    assert node['world'] == [2, 0, 0, 2, 380, 560]
    assert not any(n['id'] == 'character' for n in evaluate(scene_render, path, 3.5))
    assert not any(n['id'] == 'character' for n in evaluate(scene_render, path, 6))


@pytest.mark.parametrize('index', range(5))
def test_sequence_shot_keeps_animation_phase_and_state(scene_render, tmp_path, index):
    write_png(tmp_path / 'plate.png', np.full((80, 100, 4), 255, np.uint8))
    samples = []
    for lead in (0, 3):
        cv = canvas()
        cv.assets.add_image(id='plate', src='plate.png', width=100, height=80)
        sequence = cv.comp.add_sequence(id='shots')
        if lead:
            sequence.add_group(id='lead', end=lead)
        parent = sequence.add_group(id='shot', end=4)
        place_character(cv, parent, clips()[index], interval=Interval(1, 3), id='character')
        path = tmp_path / f'{lead}.xml'
        path.write_bytes(cv.scene.to_bytes())
        samples.append(
            [
                [
                    (n['id'], n['world'], n['world_opacity'], n['draw'])
                    for n in evaluate(scene_render, path, lead + 1 + time)
                    if n['id'] not in ('shots', 'shot')
                ]
                for time in (0, 0.25, 0.75, 1.5)
            ]
        )
    assert samples[0] == samples[1]


@pytest.mark.parametrize('start,end', [(True, 2), (-1, 2), (1, 1), (2, 1), (0, float('inf')), (0, 601)])
def test_invalid_intervals_have_repair_fields(start, end):
    with pytest.raises(CharacterClipError) as caught:
        Interval(start, end)
    details = caught.value.to_dict()
    assert details['code'] == 'character.interval'
    assert details['path'] == 'interval'
    assert details['expected'] and details['remedy']
    json.dumps(details, allow_nan=False)


@pytest.mark.parametrize('kw', [{'scale': 0}, {'x': float('nan')}, {'anchor': (1,)}, {'rotation': True}])
def test_invalid_placement_is_typed(kw):
    with pytest.raises(CharacterClipError):
        Placement(**{'x': 0, 'y': 0, **kw})


@pytest.mark.parametrize(
    'clip',
    [
        GlossClip('sunny', pose=((0, 'up'),)),
        GlossClip('missing'),
        ActorClip(cast.Manager, Performance(extras={'facepalm': [(0, 1)]})),
        ActorClip(cast.Manager, Performance(mouth=((2.5, 'open'),))),
        GlossClip('nadia', face=((0, 'bogus'),)),
        PlateClip((PlateFrame(0, (PlateLayer('missing'),)),)),
        'untyped',
    ],
)
def test_unsupported_or_invalid_input_does_not_draw_or_consume_ids(clip):
    cv = canvas(True)
    before = cv.scene.to_bytes()
    with pytest.raises(CharacterClipError):
        place_character(cv, cv.comp, clip, interval=Interval(3, 5))
    assert cv.scene.to_bytes() == before
    assert cv._serial == 0
    assert cv.local_time is True


def test_builder_failure_rolls_back_assets_geometry_ids_and_clock():
    class Broken(cast.Manager):
        def draw_body(self, group, perf):
            self.cv.rgrad('failed-paint', [(0, '#FFFFFF'), (1, '#000000')])
            super().draw_body(group, perf)
            raise RuntimeError('drawing failed')

    cv = canvas(True)
    before = cv.scene.to_bytes()
    with pytest.raises(RuntimeError, match='drawing failed'):
        place_character(cv, cv.comp, ActorClip(Broken), interval=Interval(3, 5))
    assert cv.scene.to_bytes() == before
    assert cv._serial == 0
    assert not cv._gradients
    assert cv.local_time is True


def test_duplicate_ids_and_foreign_parents_are_refused_atomically():
    cv = canvas()
    other = canvas()
    place_character(cv, cv.comp, ActorClip(cast.Manager), interval=Interval(0, 2), id='character')
    before = cv.scene.to_bytes()
    for parent, name in ((cv.comp, 'character'), (other.comp, 'elsewhere')):
        with pytest.raises(CharacterClipError):
            place_character(cv, parent, ActorClip(cast.Manager), interval=Interval(3, 5), id=name)
        assert cv.scene.to_bytes() == before


def test_rafa_sheet_conversion_keeps_registered_assets_and_patch_coordinates():
    from pathlib import Path

    from srstudio.plates import Patch
    from srstudio.rafa import Face
    from srstudio.rafa_host import Sheet, eye_key, mouth_key

    face = Face()
    body, eye, mouth = Path('body.png'), Path('eye.png'), Path('mouth.png')
    sheet = Sheet(
        {(face.turn, face.nod): body},
        {eye_key(face): Patch(eye, 10, 20, 30, 40)},
        {mouth_key(face): Patch(mouth, 50, 60, 70, 80)},
    )
    clip = PlateClip.from_rafa((face, face), sheet, {body: 'body', eye: 'eye', mouth: 'mouth'})
    assert clip.frames == (
        PlateFrame(0, (PlateLayer('body'), PlateLayer('eye', (10, 20)), PlateLayer('mouth', (50, 60)))),
    )
    assert clip.duration == pytest.approx(2 / 30)
    with pytest.raises(CharacterClipError, match='asset'):
        PlateClip.from_rafa((face,), sheet, {})


def test_legacy_actor_output_is_unchanged_by_adapter_use():
    control, cv = canvas(True), canvas(True)
    cast.Manager(control, tag='legacy').build(control.comp, 10, 20, perf=Performance(nods=((0, 0), (1, 8))))
    group = place_character(cv, cv.comp, ActorClip(cast.Manager), interval=Interval(3, 5), id='new')
    cv.comp.remove(group)
    cast.Manager(cv, tag='legacy').build(cv.comp, 10, 20, perf=Performance(nods=((0, 0), (1, 8))))

    # Compare the untouched legacy subtree; caches/serial may legitimately include the earlier successful drawing.
    def drawing(group):
        return [(n.xml_name, {k: v for k, v in n.attributes().items() if k != 'id'}) for n in group.iter()]

    assert drawing(cv.comp.nodes[-1]) == drawing(control.comp.nodes[-1])


def limb_track(style='cutout', offset=0, backend='baked'):
    from srstudio.limbs import HUMAN, ArmProfile, Camera
    from srstudio.limbs.compile import BakeOptions
    from srstudio.limbs.integration import LimbTrack
    from srstudio.limbs.math3d import Vec3
    from srstudio.limbs.motion import Action, Motion, Target

    return LimbTrack(
        Motion(ArmProfile(), HUMAN, (Action('point', duration=1, target=Target(Vec3(0.65, 0.3, 0))),)),
        style=style,
        camera=Camera(origin=(0, 0), scale=100),
        options=BakeOptions(fps=4, offset=offset, max_frames=12),
        backend=backend,
    )


@pytest.mark.parametrize('family', ['actor', 'gloss'])
@pytest.mark.parametrize('backend', ['baked', 'native'])
@pytest.mark.parametrize('sequence_shot', [False, True])
def test_limb_offset_is_local_and_holds_only_through_clip_end(scene_render, tmp_path, family, backend, sequence_shot):
    snapshots = []
    for offset in (0, 3):
        cv = canvas()
        track = limb_track('cutout' if family == 'actor' else 'gloss', offset=0.25, backend=backend)
        clip = (
            ActorClip(cast.Manager, Performance(limbs=(track,)))
            if family == 'actor'
            else GlossClip('gus', limbs=(track,))
        )
        parent = cv.comp
        start = offset
        if sequence_shot:
            sequence = cv.comp.add_sequence(id='shots')
            if offset:
                sequence.add_group(id='lead', end=offset)
            parent = sequence.add_group(id='shot', end=2)
            start = 0
        place_character(cv, parent, clip, interval=Interval(start, start + 2), id='character')
        path = tmp_path / f'{offset}.xml'
        path.write_bytes(cv.scene.to_bytes())
        snapshots.append(
            [
                [
                    (n['id'], n['world'], n['world_opacity'])
                    for n in evaluate(scene_render, path, offset + time)
                    if 'limb' in n['id']
                ]
                for time in (0.25, 0.75, 1.75)
            ]
        )
    assert snapshots[0] == snapshots[1]
    assert all(snapshots[0])


@pytest.mark.parametrize(
    'clip',
    [
        ActorClip('manager'),
        ActorClip(cast.Manager, {}),
        ActorClip(cast.Manager, Performance(mouth=((0,),))),
        ActorClip(cast.Manager, Performance(nods=((0, float('nan')),))),
        ActorClip(cast.Manager, Performance(blinks=((0.2, 3),))),
        ToonClip(BENTO_RIG, ()),
        ToonClip(BENTO_RIG, ('bad',)),
        ToonClip(BENTO_RIG, (pose_of(0.2, 'happy'),)),
        ToonClip(BENTO_RIG, (pose_of(0, 'happy'),), mouths=((0, 'bogus'),)),
        ToonClip(BENTO_RIG, (pose_of(0, 'happy'),), head='bad'),
        GlossClip('gus', talk=((0, 'bogus'),)),
        GlossClip('gus', face=((0.5, 'open'), (0.1, 'flat'))),
        GlossClip('nadia', limbs=('bad',)),
        PlateClip(()),
        PlateClip(('bad',)),
        PlateClip((PlateFrame(0, ()),)),
        PlateClip((PlateFrame(0.1, (PlateLayer('plate'),)),)),
        PlateClip((PlateFrame(0, (PlateLayer('plate', (0, float('inf'))),)),)),
        PlateClip((PlateFrame(0, (PlateLayer('plate'),)),), duration=3),
    ],
)
def test_malformed_clip_fields_are_bounded_typed_errors_without_emission(clip):
    cv = canvas()
    cv.assets.add_image(id='plate', src='plate.png', width=100, height=80)
    before = cv.scene.to_bytes()
    with pytest.raises(CharacterClipError):
        place_character(cv, cv.comp, clip, interval=Interval(0, 2))
    assert cv.scene.to_bytes() == before


def test_canvas_freeze_and_untyped_placement_are_refused_before_drawing():
    cv = canvas()
    before = cv.scene.to_bytes()
    with cv.frozen(), pytest.raises(CharacterClipError, match='running canvas'):
        place_character(cv, cv.comp, ActorClip(cast.Manager), interval=Interval(0, 2))
    with pytest.raises(CharacterClipError, match='Interval'):
        place_character(cv, cv.comp, ActorClip(cast.Manager), interval=(0, 2))
    assert cv.scene.to_bytes() == before


def test_very_large_offsets_that_lose_subframe_precision_are_refused():
    with pytest.raises(CharacterClipError):
        Interval(1e15, 1e15 + 2)


def test_actor_motion_root_baking_is_bounded_by_the_clip_not_the_whole_project():
    from dataclasses import replace

    from srstudio.limbs.math3d import Frame, Vec3
    from srstudio.limbs.motion import TransformKey, TransformTrack

    track = limb_track()
    root = TransformTrack((TransformKey(0, Frame()), TransformKey(10, Frame(origin=Vec3(0.2, 0, 0)))))
    track = replace(track, motion=replace(track.motion, root=root))
    cv = canvas()
    place_character(cv, cv.comp, ActorClip(cast.Manager, Performance(limbs=(track,))), interval=Interval(3, 5))
    assert cv.scene.check(schema=True) == []


@pytest.mark.parametrize('field', ['eyes', 'mouth', 'arms', 'wear'])
def test_unknown_toon_pose_control_fails_before_geometry(monkeypatch, field):
    from dataclasses import replace

    pose = replace(pose_of(0, 'happy'), **{field: ('invented',) if field == 'wear' else 'invented'})
    cv = canvas()
    monkeypatch.setattr(cv, 'path', lambda *a, **kw: pytest.fail('invalid pose reached geometry'))
    with pytest.raises(CharacterClipError):
        place_character(cv, cv.comp, ToonClip(BENTO_RIG, (pose,)), interval=Interval(0, 2))


@pytest.mark.parametrize('name', ['', 'has spaces', '9starts-with-number'])
def test_invalid_scene_ids_are_preflighted(name):
    cv = canvas()
    with pytest.raises(CharacterClipError):
        place_character(cv, cv.comp, ActorClip(cast.Manager), interval=Interval(0, 2), id=name)


def test_rosa_uses_the_shared_lifecycle_and_preflights_stitch_before_drawing():
    from srstudio.rig import Actor

    assert cast.Rosa.build is Actor.build
    cv = canvas()
    cv.font_asset = 'caption-font'
    place_character(cv, cv.comp, ActorClip(cast.Rosa), interval=Interval(3, 5))
    assert next(cv.scene.iter('text')).text == 'ROSA'
    before = cv.scene.to_bytes()
    with pytest.raises(cast.CastError, match='stitch'):
        cast.Rosa(cv).build(cv.comp, 0, 0, perf=Performance(extras={'stitch': 'TOO-LONG'}), end=2)
    assert cv.scene.to_bytes() == before


@pytest.mark.parametrize('end', [0, -1, float('nan'), True])
def test_actor_rejects_invalid_explicit_end_before_mutation(end):
    from srstudio.rig import RigError

    cv = canvas()
    before = cv.scene.to_bytes()
    with pytest.raises(RigError, match='end'):
        cast.Manager(cv).build(cv.comp, 0, 0, end=end)
    assert cv.scene.to_bytes() == before


def test_unsupported_toon_gaze_fails_before_geometry(monkeypatch):
    from dataclasses import replace

    cv = canvas()
    rig = replace(BENTO_RIG, look=replace(BENTO_RIG.look, drawing=None), pose_tilt=None)
    from srstudio.toon import Pose

    clip = ToonClip(rig, (Pose(0, 'wide', 'flat', 'desk'),), head=HeadPlan(gaze=((0, 'left'),)))
    monkeypatch.setattr(cv, 'path', lambda *a, **kw: pytest.fail('unsupported gaze reached geometry'))
    with pytest.raises(CharacterClipError, match='gaze'):
        place_character(cv, cv.comp, clip, interval=Interval(0, 2))


def test_inner_id_collision_rolls_back_the_entire_clip():
    cv = canvas()
    cv.group(cv.comp, 'character-actor-head')
    before = cv.scene.to_bytes()
    with pytest.raises(CharacterClipError, match='unique IDs'):
        place_character(cv, cv.comp, ActorClip(cast.Manager), interval=Interval(0, 2), id='character')
    assert cv.scene.to_bytes() == before


def test_track_seconds_must_remain_distinct_at_scene_precision():
    cv = canvas()
    with pytest.raises(CharacterClipError, match='seconds'):
        place_character(cv, cv.comp, GlossClip('sunny', face=((0, 'smile'), (1e-8, 'flat'))), interval=Interval(0, 2))

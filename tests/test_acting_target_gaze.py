"""Coordinated performances retain target gaze and head follow across cut windows."""

from dataclasses import replace

import pytest

from srstudio import acting, gaze, toon_critters
from srstudio.character_clips import ToonClip
from support.acting import canvas


def rig():
    return acting.ActingRig(
        'sloth-tracking',
        'toon',
        (acting.Emotion('neutral', acting.Expression('wide', 'flat'), 'desk'),),
        head_rig=toon_critters.SLOTH_RIG,
    )


def target():
    return gaze.GazePlan(
        gaze.GazeSpec(gaze.TargetTrack((gaze.TargetKey(0, (0, 0, 2)), gaze.TargetKey(0.5, (0.6, 0.2, 2)))), 1, fps=24)
    )


def test_documented_target_gaze_recipe_is_executable():
    from pathlib import Path

    text = (Path(__file__).resolve().parents[1] / 'docs/authoring-acting.md').read_text()
    section = text.split('### Opt-in target gaze')[1].split('### Opt-in acting transition policies')[0]
    code = section.split('```python\n')[1].split('```')[0]
    namespace = {}
    exec(compile(code, 'target-gaze-recipe', 'exec'), namespace)
    assert isinstance(namespace['plan'].sample(0.7).gaze, gaze.GazeSample)
    assert namespace['base'].clip.target_gaze is None


def test_binding_target_gaze_is_explicit_and_preserves_original_performance():
    base = acting.compile_performance(rig(), acting.ActingScore(1, overrides=acting.Overrides(gaze=()), idle=False))
    tracked = base.with_target_gaze(target())
    assert base.clip.target_gaze is None and tracked.clip.target_gaze is not None
    assert isinstance(tracked.sample(0.7).gaze, gaze.GazeSample)
    assert tracked.sample(0.7).gaze == target().sample(0.7)
    assert tracked.sample(0.7).head.face_x > base.sample(0.7).head.face_x
    assert tracked.window(0.31, 1).sample(0.39) == tracked.sample(0.7)
    assert dict(tracked.owners)['gaze'] == 'target'
    assert isinstance(tracked.clip, ToonClip)
    cv = canvas()
    tracked.window(0.31, 1).place(cv, cv.comp, at=2, id='cut')
    assert cv.scene.check() == []


def test_binding_again_replaces_the_target_instead_of_adding_head_follow_twice():
    base = acting.compile_performance(rig(), acting.ActingScore(1, idle=False))
    first = base.with_target_gaze(target())
    again = first.with_target_gaze(target())
    assert first.sample(0.7) == again.sample(0.7)


def test_profiles_disclose_target_support_and_do_not_fall_back_to_named_states():
    assert rig().describe()['capabilities']['target_gaze'] is True
    assert acting.BENTO.describe()['capabilities']['target_gaze'] is False
    for profile in (acting.BENTO, acting.gloss_actor('nadia')):
        score = acting.ActingScore(1) if profile.family == 'gloss' else acting.ActingScore(1, idle=False)
        base = acting.compile_performance(profile, score)
        with pytest.raises(gaze.GazeError) as caught:
            base.with_target_gaze(target())
        assert caught.value.to_dict()['code'] == 'gaze.unsupported'


def test_existing_authored_eye_direction_is_not_silently_replaced():
    score = acting.ActingScore(1, (acting.ActingBeat(0, gaze='left'),), idle=False)
    base = acting.compile_performance(rig(), score)
    with pytest.raises(gaze.GazeError):
        base.with_target_gaze(target())


def test_duration_mismatch_fails_before_a_window_can_be_drawn():
    base = acting.compile_performance(rig(), acting.ActingScore(1, idle=False))
    longer = gaze.GazePlan(replace(target().spec, duration=2))
    with pytest.raises(gaze.GazeError):
        base.with_target_gaze(longer)


def test_real_engine_keeps_pupils_and_head_continuous_in_later_sequence_shots(scene_render, tmp_path):
    import json
    import subprocess

    from sr_core.scene import Scene

    from srstudio import Canvas

    score = acting.ActingScore(
        1,
        (acting.ActingBeat(0.5, expression=acting.Expression('half'), transition=0),),
        overrides=acting.Overrides(gaze=()),
        idle=False,
    )
    performance = acting.compile_performance(rig(), score).with_target_gaze(target())

    def build(cut):
        scene = Scene(version='auto')
        scene.add_project(width=1080, height=1920, fps='24', duration=1)
        cv = Canvas(scene, font_asset=None)
        if cut:
            sequence = cv.comp.add_sequence(id='shots')
            first = sequence.add_group(id='first', end=0.31)
            second = sequence.add_group(id='second', end=0.69)
            performance.window(0, 0.31).place(cv, first, id='first-performance')
            root = performance.window(0.31, 1).place(cv, second, id='second-performance')
        else:
            root = performance.window(0, 1).place(cv, cv.comp, id='uncut')
        pupils = [node.id for node in root.iter('group') if node.id.startswith('gaze-pupil-')]
        path = tmp_path / ('cut.scene.xml' if cut else 'uncut.scene.xml')
        path.write_bytes(scene.to_bytes())
        return path, pupils

    uncut, uncut_ids = build(False)
    cut, cut_ids = build(True)
    for time in (0.31, 0.37, 0.57, 0.97):
        rows = []
        for path, ids in ((uncut, uncut_ids), (cut, cut_ids)):
            done = subprocess.run(
                [str(scene_render), 'eval', str(path), '--time', str(time), '--json'],
                capture_output=True,
                text=True,
                check=True,
                timeout=60,
            )
            nodes = {n['id']: n for n in json.loads(done.stdout)['result']['nodes']}
            # Evaluation omits inactive pose groups. Compare their absence too,
            # so a cut cannot accidentally select a different expression.
            rows.append([(nodes[id]['world'], nodes[id]['world_opacity']) if id in nodes else None for id in ids])
        assert len(rows[0]) == len(rows[1]) == 4
        assert sum(row is not None for row in rows[0]) == 2
        for a, b in zip(rows[0], rows[1], strict=True):
            if a is None or b is None:
                assert a is b is None
                continue
            assert a[0] == pytest.approx(b[0], abs=1e-5)
            assert a[1] == pytest.approx(b[1], abs=1e-6)

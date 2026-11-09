"""A toon export with beats builds as a Toon sketch: its cast on the beats, each take in its set, each prop on its
event, the captions fitted to the pill and the safe area (srstudio.export_toon, ADR 0255)."""

import json
import struct
import subprocess
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import sketch
from srstudio.export_build import ExportError, build_export
from srstudio.export_toon import Take, beats_of, captions, cast_of, pill_room
from srstudio.layout import Box

RATE = 48000
LONG = 'Ela se afasta quase quatro centímetros por ano, devagar demais para alguém notar numa noite comum.'
TAKES = (
    ('01', 'A Lua está indo embora.', 2.0),
    ('02', LONG, 7.0),  # 17 words at a narrator's pace, 2.4 a second
    ('03', 'E ninguém percebeu.', 2.0),
)
SETS = {'01': 'toon-planetarium-salon', '02': 'toon-starlight-terrace'}


def _wav(path: Path, seconds: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(struct.pack('<h', 0) * int(RATE * seconds))


def _items() -> list[dict]:
    items, start = [], 0.0
    for take_id, text, duration in TAKES:
        step = (duration - 0.4) / len(text.split())
        words = [
            {'text': word, 'start': round(0.1 + step * i, 3), 'end': round(0.1 + step * i + step * 0.8, 3)}
            for i, word in enumerate(text.split())
        ]
        items.append(
            dict(id=take_id, actor='lyra-host', shot='hook', text=text, start=start, duration=duration,
                 speech_duration=words[-1]['end'], audio=f'audio/take-{take_id}.wav', sha256='0' * 64, words=words)
        )  # fmt: skip
        start += duration
    return items


def _export(folder: Path, *, staging: dict | None = None, events: list | None = None, rig: str = 'toon-lyra') -> Path:
    """A toon export laid out as sreditor writes it: Lyra's rig under look.drawing, her poses, events and staging."""
    folder.mkdir(parents=True)
    episode = dict(slug='a-lua', title='A Lua', seed=3, style='toon', width=1080, height=1920, fps=24, language='pt-BR')
    (folder / 'episode.json').write_text(json.dumps(episode))
    items = _items()
    for item in items:
        _wav(folder / item['audio'], item['duration'])
    duration = sum(take[2] for take in TAKES)
    (folder / 'timeline.json').write_text(json.dumps({'duration': duration, 'items': items}))
    (folder / 'bible').mkdir()
    lyra = {'slug': 'lyra-host', 'name': 'Lyra', 'look': {'drawing': [{'part': rig, 'version': None}]}}
    (folder / 'bible/cast.json').write_text(json.dumps({'schema': '1.0.0', 'characters': [lyra]}))
    (folder / 'assets').mkdir()
    poses = [
        {'start': 0.0, 'eyes': 'wide', 'mouth': 'open', 'arms': 'desk'},
        {'start': 2.0, 'eyes': 'half', 'mouth': 'flat', 'arms': 'crossed'},
        {'start': 7.5, 'eyes': 'up', 'mouth': 'grin', 'arms': 'desk'},
    ]
    (folder / 'assets/poses.json').write_text(json.dumps([{'who': 'lyra', 'start': 0.0, 'end': duration,
                                                           'poses': poses}]))  # fmt: skip
    (folder / 'assets/events.json').write_text(json.dumps(events if events is not None else
                                                          [{'start': 3.0, 'event': 'moon'}]))  # fmt: skip
    staged = staging if staging is not None else {'sets': SETS, 'props': {'moon': 'toon-moon-globe'}}
    (folder / 'assets/staging.json').write_text(json.dumps(staged))
    return folder


def _groups(scene: Path, prefix: str) -> list[ET.Element]:
    root = ET.parse(scene).getroot()
    return [n for n in root.iter() if n.tag.rsplit('}', 1)[-1] == 'group' and n.get('id', '').startswith(prefix)]


def _build(tmp_path: Path, **kw) -> Path:
    return build_export(_export(tmp_path / 'export', **kw), tmp_path / 'job' / 'episode.scene.xml')


def test_toon_export_stands_each_take_in_its_set_for_the_take(tmp_path):
    sets = _groups(_build(tmp_path), 'set-')
    assert sorted((float(g.get('start')), float(g.get('end'))) for g in sets) == [(0.0, 2.0), (2.0, 9.0)]


def test_toon_export_shows_a_prop_from_its_event_to_the_end_of_its_take(tmp_path):
    props = _groups(_build(tmp_path), 'prop-')
    assert [(float(g.get('start')), float(g.get('end'))) for g in props] == [(3.0, 9.0)]


def test_toon_export_writes_the_recording_the_voiced_build_reads(tmp_path):
    job = _build(tmp_path).parent
    beats, end = sketch.load_beats(job / 'voiced' / 'beats.json')
    mouths, _ = sketch.load_mouths(job / 'voiced' / 'mouths.json')
    assert end >= 11.0 and {b.who for b in beats} == {'lyra'}
    assert [b.line for b in beats if b.word == 0] == [0, 1, 2]
    assert mouths['lyra'] and mouths['lyra'][-1][1] == 'closed'
    narration = json.loads((job / 'narration.json').read_text())
    assert [item['audio'] for item in narration['items']] == ['audio/vo-01.wav', 'audio/vo-02.wav', 'audio/vo-03.wav']
    assert narration['language'] == 'pt-BR'


def test_toon_export_signs_every_shot_with_both_marks(tmp_path):
    text = _build(tmp_path).read_text(encoding='utf-8')
    assert 'sig-cactus' in text and 'sig-code' in text


def test_toon_export_with_a_set_the_catalogue_lacks_names_the_take(tmp_path):
    with pytest.raises(ExportError) as caught:
        _build(tmp_path, staging={'sets': {'02': 'toon-moon-base'}, 'props': {}})
    assert caught.value.path == 'assets/staging.json sets.02'
    assert not (tmp_path / 'job' / 'episode.scene.xml').exists()


def test_toon_export_with_an_event_for_a_prop_without_a_drawing_is_refused(tmp_path):
    with pytest.raises(ExportError) as caught:
        _build(tmp_path, staging={'sets': SETS, 'props': {}})
    assert 'moon' in str(caught.value)


def test_toon_export_without_beats_keeps_the_default_staging(tmp_path):
    export = _export(tmp_path / 'export')
    (export / 'assets/poses.json').write_text('[]')
    scene = build_export(export, tmp_path / 'job' / 'episode.scene.xml')
    assert not _groups(scene, 'set-') and not (scene.parent / 'voiced').exists()


def test_cast_of_reads_the_toon_a_bible_entry_draws_under_look(tmp_path):
    export = _export(tmp_path / 'export')
    assert cast_of(export) == ({'lyra-host': 'lyra'}, {})


def test_cast_of_leaves_out_a_rig_outside_the_toon_cast(tmp_path):
    export = _export(tmp_path / 'export', rig='host-kit')
    assert cast_of(export) == ({}, {})


def _take(start: float, words: list[tuple[str, float, float]], duration: float = 3.0) -> Take:
    return Take('01', 'a', start, duration, 'audio/take-01.wav', tuple(words))


def _words(*texts: str, step: float = 1.0) -> list[tuple[str, float, float]]:
    return [(text, i * step, i * step + step * 0.8) for i, text in enumerate(texts)]


def _cut(take: Take, width: int, after: float | None = None, until: float = 10.0) -> list[tuple[int, str, float]]:
    return [(c.word, c.text, c.at) for c in captions(take, lambda text: len(text) <= width, after, until)]


def test_captions_cut_the_words_where_the_next_would_not_fit():
    assert _cut(_take(0.0, _words('aa', 'bb', 'cc', 'dd')), 5) == [(0, 'aa bb', 0.0), (2, 'cc dd', 2.0)]


def test_captions_keep_a_word_too_wide_alone():
    assert _cut(_take(0.0, _words('abcdefgh', 'b')), 3) == [(0, 'abcdefgh', 0.0), (1, 'b', 1.0)]


def test_captions_cut_where_every_caption_is_read_its_least():
    words = _words('aa', 'bb', 'cc', 'dd', step=0.3)  # 'cc dd' waits 0.25 s after its word for 'aa bb' to be read
    assert _cut(_take(0.0, words), 8, until=2.0) == [(0, 'aa bb', 0.0), (2, 'cc dd', 0.85)]


def test_captions_wait_for_the_caption_before_the_take_up_to_the_lag():
    take = _take(5.0, _words('aa', step=1.0))
    assert _cut(take, 5, after=4.5) == [(0, 'aa', 5.35)]


def test_pill_room_is_the_centred_width_inside_the_safe_area():
    assert pill_room(Box(80.0, 0.0, 920.0, 100.0), 1080.0) == 760.0


POSE = [(0.0, 'lyra', {'eyes': 'wide', 'mouth': 'open', 'arms': 'desk'})]


def test_beats_hold_a_caption_its_least_before_the_next_replaces_it():
    words = [('um', 0.0, 0.2), ('dois', 0.3, 0.5)]
    beats = beats_of([_take(0.0, words)], POSE, [], lambda text: len(text) <= 3, 3.0)
    assert [(b.start, b.caption) for b in beats] == [(0.0, 'um'), (0.75, 'dois')]


def test_beats_join_a_pose_change_closer_than_the_least_step_to_the_beat_before():
    poses = [*POSE, (0.05, 'lyra', {'eyes': 'half', 'mouth': 'flat', 'arms': 'desk'})]
    beats = beats_of([_take(0.0, [('um', 0.0, 0.2)])], poses, [], lambda text: True, 3.0)
    assert [(b.start, b.eyes) for b in beats] == [(0.0, 'half')]


def test_beats_put_a_prop_event_on_a_silent_beat_with_the_caption_on_screen():
    beats = beats_of([_take(0.0, [('um', 0.0, 0.2)])], POSE, [(1.0, 'moon')], lambda text: True, 3.0)
    assert [(b.start, b.caption, b.line, b.event) for b in beats] == [(0.0, 'um', 0, ''), (1.0, 'um', None, 'moon')]


def test_toon_export_scene_encodes_in_the_engine(tmp_path, scene_render):
    scene = _build(tmp_path)
    for command in (['validate', str(scene)],
                    ['encode', str(scene), '--output', 'main', '-o', str(scene.parent / 'video.mp4'), '--no-upload',
                     '--quality', 'draft']):  # fmt: skip
        run = subprocess.run([str(scene_render), *command], capture_output=True, text=True, timeout=600)
        assert run.returncode == 0, run.stdout[-2000:] + run.stderr[-2000:]
        assert 'legibilityCheck' not in run.stdout + run.stderr

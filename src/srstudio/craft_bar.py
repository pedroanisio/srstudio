"""The C4/C7 craft bar on a master and its cached recording (ADR 0239).

Word timing comes from the recording, not fresh recognition of the mix. Levels come
from the master. No client is constructed and a cache miss never makes a request.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from . import master_gate, proof, prosody
from .phrasing import words_of
from .voice import Alignment, Word


class CraftError(proof.ProofError):
    """A craft bar cannot be established from the available evidence."""


class NoRecordedLines(CraftError):
    """The project has no recorded speech lines."""


class WordsNotHeard(CraftError):
    """A recorded line lacks usable heard words or cached word timing."""


class NoAudio(CraftError):
    """The master has no audio stream."""


@dataclass(frozen=True)
class Measure:
    """One value, its explicit bar, and its verdict; source states its evidence."""

    name: str
    value: float | bool | None
    bar: str
    status: Literal['PASS', 'SHIP', 'FAIL']
    source: str

    @property
    def passed(self) -> bool:
        """Strict PASS; SHIP still needs a later re-take."""
        return self.status == 'PASS'

    @property
    def ok(self) -> bool:
        """Eligible to ship; callers needing a strict pass must use passed."""
        return self.status in ('PASS', 'SHIP')


@dataclass(frozen=True)
class Result:
    measures: tuple[Measure, ...]

    @property
    def passed(self) -> bool:
        return all(m.passed for m in self.measures)

    @property
    def ok(self) -> bool:
        return all(m.ok for m in self.measures)

    def retakes(self) -> tuple[Measure, ...]:
        """SHIP rows to list for the next re-takes, even when proof exits zero."""
        return tuple(m for m in self.measures if m.status == 'SHIP')

    def lines(self) -> list[str]:
        return [f"{m.status} {m.name}: {m.value} | {m.bar} | {m.source}" for m in self.measures]


@dataclass(frozen=True)
class RecordedLine:
    id: str
    start: float
    duration: float
    words: tuple[Word, ...]  # relative to kept clip, already trimmed
    stress: tuple[str, ...]
    source: str


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise CraftError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CraftError(f"{path}: expected an object")
    return value


def _marks(item: dict[str, Any]) -> tuple[str, ...]:
    value = item.get('direction', {}).get('stress', item.get('stress', ()))
    return (value,) if isinstance(value, str) else tuple(value)


def _words(rows: list[dict[str, Any]], clip_in: float, duration: float) -> tuple[Word, ...]:
    return tuple(
        Word(w['text'], max(0, float(w['start']) - clip_in), min(duration, float(w['end']) - clip_in), 'word')
        for w in rows
        if w.get('type', 'word') == 'word' and float(w['end']) > clip_in and float(w['start']) < clip_in + duration
    )


def _cached_words(project: Path, generated: dict[str, Any], language: str) -> list[dict[str, Any]]:
    audio = project / generated['cache']
    # Same content-addressed key as voice.transcribe; read the record directly, never invoke a client.
    try:
        digest = hashlib.sha256(
            json.dumps(
                {
                    'stt': {'model_id': 'scribe_v1', 'language_code': language},
                    'audio': hashlib.sha256(audio.read_bytes()).hexdigest(),
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()[:20]
        return _read(project / f'assets/elevenlabs/stt-{digest}.json')['response']['words']
    except (OSError, CraftError, KeyError) as exc:
        raise WordsNotHeard(f"{generated['id']}: no cached transcript for {audio}") from exc


def recorded_lines(project: Path) -> tuple[RecordedLine, ...]:
    """Read timeline, flat dialogue placements, or narration's kept character alignment."""
    out: list[RecordedLine] = []
    try:
        if (project / 'timeline.json').is_file():
            data = _read(project / 'timeline.json')
            for item in data.get('items', ()):
                if item.get('actor') == 'sfx':
                    continue
                p = item.get('prosody', {})
                duration = float(item['duration'])
                out.append(
                    RecordedLine(
                        str(item['id']),
                        float(item['start']),
                        duration,
                        _words(p.get('words', []), 0, duration),
                        _marks(item),
                        'timeline recorded word timing',
                    )
                )
        elif (project / 'dialogue.json').is_file():
            data = _read(project / 'dialogue.json')
            stresses = {f"line-{s['line']}": tuple(s['words']) for s in data.get('stress', ())}
            sources = {s['clip']: s for s in data.get('stress', ()) if 'source' in s}
            for clip in data.get('clips', ()):
                g = clip.get('generated', {})
                if g.get('kind') != 'speech':
                    continue
                pl = clip['placement']
                duration = float(pl['clip_out']) - float(pl['clip_in'])
                language = g.get('language', data.get('language', 'en').split('-')[0])
                timing = g
                source = sources.get(g['cache'])
                if source is not None:
                    # emphasis.lean changes levels only. Require both identities before reusing source timing.
                    for field, sha in (('clip', 'sha256'), ('source', 'source_sha256')):
                        if hashlib.sha256((project / source[field]).read_bytes()).hexdigest() != source[sha]:
                            raise WordsNotHeard(f"{g['id']}: emphasis source identity mismatch")
                    timing = g | {'cache': source['source']}
                rows = _cached_words(project, timing, language)
                out.append(
                    RecordedLine(
                        g['id'],
                        float(pl['start']),
                        duration,
                        _words(rows, float(pl['clip_in']), duration),
                        stresses.get(g['id'], _marks(clip)),
                        'cached transcript + dialogue placement',
                    )
                )
        elif (project / 'voiced/speech.json').is_file():
            data = _read(project / 'voiced/speech.json')
            narration = _read(project / 'narration.json') if (project / 'narration.json').is_file() else {}
            items = {i['id']: i for i in narration.get('items', ()) if i.get('phase') == 'line'}
            for take in data.get('takes', ()):
                alignment = Alignment(tuple(take['characters']), tuple(take['starts']), tuple(take['ends']))
                rows = [dict(text=t, start=a, end=b) for t, a, b in words_of(alignment)]
                duration = float(take['kept'])
                out.append(
                    RecordedLine(
                        str(take['id']),
                        float(take['at']),
                        duration,
                        _words(rows, float(take.get('clip_in', 0)), duration),
                        _marks(take) or _marks(items.get(take['id'], {})),
                        'speech.json kept alignment',
                    )
                )
    except (KeyError, TypeError, ValueError, AttributeError, OSError) as exc:
        if isinstance(exc, CraftError):
            raise
        raise CraftError(f"malformed recording in {project}: {exc}") from exc
    if not out:
        raise NoRecordedLines(f"{project}: no recorded lines")
    for line in out:
        if (
            not line.words
            or not math.isfinite(line.start)
            or line.start < 0
            or not math.isfinite(line.duration)
            or line.duration <= 0
            or any(not math.isfinite(w.start) or not math.isfinite(w.end) or w.end <= w.start for w in line.words)
        ):
            raise WordsNotHeard(f"{line.id}: no usable heard words")
    return tuple(sorted(out, key=lambda line: line.start))


def pace_measure(line: str, value: float) -> Measure:
    return Measure(
        f'pace:{line}',
        value,
        'PASS <= 3.6; SHIP <= 4.2; FAIL > 4.2 words/s',
        'PASS' if value <= 3.6 else 'SHIP' if value <= 4.2 else 'FAIL',
        'heard word count / phrase duration (edge silences included)',
    )


def frozen_run(video: Path) -> float:
    """Longest detected C4 run, including EOF; zero means none reached the detector duration.

    master_gate.changes/runs use different pixel-share criteria and are not C4.
    """
    done = proof._run(
        [
            'ffmpeg',
            '-hide_banner',
            '-nostats',
            '-i',
            str(video),
            '-an',
            '-vf',
            'crop=1080:1340:0:0,freezedetect=n=0.003:d=1.5',
            '-f',
            'null',
            '-',
        ],
        'C4 freezedetect',
    )
    starts = re.findall(r'freeze_start: ([\d.]+)', done.stderr)
    ends = re.findall(r'freeze_end: ([\d.]+)', done.stderr)
    if len(ends) < len(starts):
        probe = proof._run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(video)],
            'freeze EOF duration',
        )
        ends.append(probe.stdout.strip())
    return max((float(b) - float(a) for a, b in zip(starts, ends, strict=True)), default=0.0)


def _beds(project: Path) -> list[tuple[Path, float]]:
    found = []
    for name in ('timeline.json', 'dialogue.json', 'narration.json'):
        if not (project / name).is_file():
            continue
        data = _read(project / name)
        music = data.get('music')
        if isinstance(music, dict) and music.get('file'):
            found.append((project / music['file'], float(music.get('fade', 0))))
        for effect in data.get('effects', ()):
            if effect.get('role') == 'music':
                found.append((project / effect['audio'], float(effect.get('fade', 0))))
        for clip in data.get('clips', ()):
            if clip.get('placement', {}).get('role') == 'music':
                found.append((project / clip['generated']['cache'], float(clip['placement'].get('fade_out', 0))))
    return found


def measure(video: Path, project: Path, *, loudness: proof.Measures | None = None) -> Result:
    """Measure C4/C7. Integrated loudness is reported with a finite-value bar: no LUFS target was specified."""
    try:
        lines = recorded_lines(project)
        probe = proof._run(
            [
                'ffprobe',
                '-v',
                'error',
                '-select_streams',
                'a:0',
                '-show_entries',
                'stream=index',
                '-of',
                'json',
                str(video),
            ],
            'craft audio probe',
        )
        if not json.loads(probe.stdout)['streams']:
            raise NoAudio(f'{video}: no audio stream')
        values: list[Measure] = []
        with tempfile.TemporaryDirectory(prefix='craft-bar-') as tmp:
            first = math.inf
            for line in lines:
                wav = Path(tmp) / 'line.wav'
                proof._run(
                    [
                        'ffmpeg',
                        '-v',
                        'error',
                        '-y',
                        '-i',
                        str(video),
                        '-ss',
                        str(line.start),
                        '-t',
                        str(line.duration),
                        '-map',
                        '0:a:0',
                        '-ac',
                        '1',
                        '-ar',
                        '16000',
                        '-c:a',
                        'pcm_s16le',
                        str(wav),
                    ],
                    f'{line.id}: master mix',
                )
                measured = prosody.measure(wav, line.words, line.stress)
                if measured.pace is None or any(w.db is None or w.db <= -119 for w in measured.words):
                    raise WordsNotHeard(f'{line.id}: words not audible on master at cached timing')
                first = min(first, line.start + (measured.first or 0))
                count = len(measured.words)
                if count >= 3:
                    values.append(pace_measure(line.id, count / line.duration))
                    span_pace = count / measured.span
                    values.append(
                        Measure(
                            f'pace_span:{line.id}',
                            span_pace,
                            '<= 4.5 words/s',
                            'PASS' if span_pace <= 4.5 else 'FAIL',
                            'heard word count / cached first-to-last word span',
                        )
                    )
                for stress in measured.stressed:
                    if not stress.heard:
                        raise WordsNotHeard(f'{line.id}: stressed word {stress.word!r} not heard')
                    values.append(
                        Measure(
                            f'stress:{line.id}:{stress.word}',
                            stress.db,
                            f'>= {prosody.STRESS_DB:g} dB',
                            'PASS' if stress.db is not None and stress.db >= prosody.STRESS_DB else 'FAIL',
                            'prosody.measure on master mix; ' + line.source,
                        )
                    )
        loudness = loudness or proof.measure(video)
        values[0:0] = [
            Measure(
                'integrated_lufs',
                loudness.lufs,
                'finite (no LUFS target specified)',
                'PASS' if math.isfinite(loudness.lufs) else 'FAIL',
                'master ebur128',
            ),
            Measure(
                'lra',
                loudness.range_lu,
                '>= 4.5 LU',
                'PASS' if loudness.range_lu >= master_gate.MIN_LRA else 'FAIL',
                'master ebur128',
            ),
        ]
        values.append(
            Measure(
                'first_word',
                round(first, 6),
                '<= 0.25 s',
                'PASS' if first <= 0.25 else 'FAIL',
                'cached word timing + placement; audibility checked on master',
            )
        )
        beds = _beds(project)
        constant = any(master_gate.constant_bed(p, fade=f) for p, f in beds)
        values.append(
            Measure(
                'constant_bed',
                constant,
                'false',
                'FAIL' if constant else 'PASS',
                'master_gate.constant_bed on declared music stems' if beds else 'no declared music stem',
            )
        )
        frozen = frozen_run(video)
        values.append(
            Measure(
                'frozen',
                frozen,
                '< 1.5 s',
                'PASS' if frozen < 1.5 else 'FAIL',
                'crop=1080:1340:0:0,freezedetect=n=0.003:d=1.5; EOF closed at duration',
            )
        )
        return Result(tuple(values))
    except (proof.ProofError, master_gate.MasterError, prosody.ProsodyError) as exc:
        if isinstance(exc, CraftError):
            raise
        raise CraftError(str(exc)) from exc

"""The C4/C7 craft bar on a master and its cached recording (ADR 0239).

Voice timing requires hash-bound final-master alignment evidence (ADR 0245).
Levels come from the master mix. No client is constructed and missing evidence refuses.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import tempfile
import wave
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
    master_sha256: str = ''
    voices: tuple[VoiceLine, ...] = ()

    @property
    def fail_retakes(self) -> tuple[str, ...]:
        return tuple(v.id for v in self.voices if v.pace_status == 'FAIL' or v.stress_status == 'FAIL')

    @property
    def ship_retakes(self) -> tuple[str, ...]:
        return tuple(v.id for v in self.voices if v.pace_status == 'SHIP')

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
        return [f"{m.status} {m.name}: {m.value} | {m.bar} | {m.source}" for m in self.measures] + (
            [
                f'master sha256: {self.master_sha256}',
                *(str(v) for v in self.voices),
                f'SHIP retakes: {self.ship_retakes}; FAIL retakes: {self.fail_retakes}',
            ]
            if self.master_sha256
            else []
        )


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
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list | tuple | dict) or any(not isinstance(v, str) or not v.strip() for v in value):
        raise WordsNotHeard('invalid key word identification')
    return tuple(value)


def _words(rows: list[dict[str, Any]], clip_in: float, duration: float) -> tuple[Word, ...]:
    return tuple(
        Word(
            w['text'],
            max(0, _finite(w['start'], 'word start') - clip_in),
            min(duration, _finite(w['end'], 'word end') - clip_in),
            'word',
        )
        for w in rows
        if w.get('type', 'word') == 'word'
        and _finite(w['end'], 'word end') > clip_in
        and _finite(w['start'], 'word start') < clip_in + duration
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
                duration = _finite(item['duration'], 'duration')
                out.append(
                    RecordedLine(
                        str(item['id']),
                        _finite(item['start'], 'start'),
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
                duration = _finite(pl['clip_out'], 'clip out') - _finite(pl['clip_in'], 'clip in')
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
                        _finite(pl['start'], 'start'),
                        duration,
                        _words(rows, _finite(pl['clip_in'], 'clip in'), duration),
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
                duration = _finite(take['kept'], 'kept')
                out.append(
                    RecordedLine(
                        str(take['id']),
                        _finite(take['at'], 'start'),
                        duration,
                        _words(rows, _finite(take.get('clip_in', 0), 'clip in'), duration),
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
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value) or value <= 0:
        raise CraftError(f'{line}: invalid pace measurement {value!r}')
    return Measure(
        f'pace:{line}',
        value,
        'PASS <= 3.6; SHIP <= 4.2; FAIL > 4.2 words/s',
        'PASS' if value <= 3.6 + 1e-12 else 'SHIP' if value <= 4.2 + 1e-12 else 'FAIL',
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
        voice = measure_voice(video, project)
        values = list(voice.measures)
        first = min(v.start + v.words[0].start for v in voice.voices)
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
        return Result(tuple(values), voice.master_sha256, voice.voices)
    except (proof.ProofError, master_gate.MasterError, prosody.ProsodyError) as exc:
        if isinstance(exc, CraftError):
            raise
        raise CraftError(str(exc)) from exc


@dataclass(frozen=True)
class VoiceLine:
    id: str
    start: float
    count: int
    phrase_duration: float
    word_span: float
    phrase_pace: float
    span_pace: float
    pace_status: Literal['PASS', 'SHIP', 'FAIL', 'exempt']
    words: tuple[prosody.WordLevel, ...]
    median_db: float | None
    key_words: tuple[str, ...]
    stress_margin: float | None
    preceding_margin: float | None  # N/A when the key word has no predecessor
    stress_status: Literal['PASS', 'FAIL']
    source: str


def _finite(value: object, where: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise WordsNotHeard(f'{where}: expected finite number')
    return float(value)


def _master_lines(project: Path, digest: str) -> tuple[RecordedLine, ...]:
    """Final-master alignment is evidence, never inferred from an isolated take (ADR 0245)."""
    recorded = recorded_lines(project)
    data = _read(project / 'master-voice.json')
    if data.get('master_sha256') != digest:
        raise WordsNotHeard('missing or stale final-master alignment sha256')
    source = data.get('source')
    rows = data.get('lines')
    if not isinstance(source, str) or not source.strip() or not isinstance(rows, list):
        raise WordsNotHeard('final-master alignment needs source and lines')
    expected = {line.id: line for line in recorded}
    if len(expected) != len(recorded):
        raise WordsNotHeard('duplicate recorded line identity')
    out = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get('id'), str):
            raise WordsNotHeard('invalid final-master line')
        ident = row['id']
        if ident not in expected or ident in seen:
            raise WordsNotHeard(f'{ident}: unknown or duplicate final-master line')
        seen.add(ident)
        start = _finite(row.get('start'), ident)
        duration = _finite(row.get('duration'), ident)
        if start < 0 or duration <= 0:
            raise WordsNotHeard(f'{ident}: invalid phrase bounds')
        words = row.get('words')
        if not isinstance(words, list) or not words:
            raise WordsNotHeard(f'{ident}: missing word timing')
        aligned = []
        previous = 0.0
        for word in words:
            if not isinstance(word, dict) or not isinstance(word.get('text'), str) or not word['text'].strip():
                raise WordsNotHeard(f'{ident}: invalid word')
            a, b = _finite(word.get('start'), ident), _finite(word.get('end'), ident)
            if not previous <= a < b <= duration:
                raise WordsNotHeard(f'{ident}: invalid or unordered word bounds')
            previous = b
            aligned.append(Word(word['text'], a, b, 'word'))
        if [prosody.normalize_words(w.text) for w in aligned] != [
            prosody.normalize_words(w.text) for w in expected[ident].words
        ]:
            raise WordsNotHeard(f'{ident}: final-master words differ from recorded line')
        out.append(RecordedLine(ident, start, duration, tuple(aligned), expected[ident].stress, source))
    if seen != set(expected):
        raise WordsNotHeard('final-master alignment omits recorded lines')
    return tuple(sorted(out, key=lambda line: line.start))


def measure_voice(video: Path, project: Path) -> Result:
    """Public delivery C7/stress check on the exact master bytes, using master-voice.json alignment.

    No recognition service or take-level measurements are used. Missing or stale evidence
    raises CraftError. Measured refusals are FAIL results; SHIP remains eligible.
    """
    try:
        digest = hashlib.sha256(video.read_bytes()).hexdigest()
        lines = _master_lines(project, digest)
        values: list[Measure] = []
        reports: list[VoiceLine] = []
        with tempfile.TemporaryDirectory(prefix='voice-') as tmp:
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
                with wave.open(str(wav), 'rb') as audio:
                    if audio.getnframes() / audio.getframerate() + 1 / audio.getframerate() < line.duration:
                        raise WordsNotHeard(f'{line.id}: phrase extends past master audio')
                heard = prosody.measure(wav, line.words, line.stress)
                count = len(line.words)
                span = line.words[-1].end - line.words[0].start
                phrase, speech = count / line.duration, count / span
                pace_status: Literal['PASS', 'SHIP', 'FAIL', 'exempt'] = 'exempt'
                source = f'master mix sha256={digest}; {line.source}'
                if count >= 3:
                    pace = pace_measure(line.id, phrase)
                    pace = Measure(pace.name, pace.value, pace.bar, pace.status, source + '; ' + pace.source)
                    guard = Measure(
                        f'pace_span:{line.id}',
                        speech,
                        '<= 4.5 words/s',
                        'PASS' if speech <= 4.5 else 'FAIL',
                        source + '; first-to-last word span',
                    )
                    values.extend((pace, guard))
                    pace_status = 'FAIL' if not guard.ok else pace.status
                audible = len(heard.words) == count and all(
                    w.db is not None and math.isfinite(w.db) and w.db > prosody.VOICED_DB for w in heard.words
                )
                median = prosody._median([w.db for w in heard.words if w.db is not None]) if audible else None
                stress_status: Literal['PASS', 'FAIL'] = 'PASS'
                margins: list[float] = []
                preceding: list[float] = []
                marks = heard.stressed if line.stress else ()
                if not audible or not marks or len(marks) != len(line.stress):
                    stress_status = 'FAIL'
                    values.append(
                        Measure(f'stress:{line.id}', None, 'identified audible key word on every line', 'FAIL', source)
                    )
                for mark in marks:
                    at = mark.at
                    margin = None
                    before = None
                    if audible and median is not None and mark.heard and at is not None and 0 <= at < count:
                        db = heard.words[at].db
                        margin = db - median if db is not None else None
                        before_db = heard.words[at - 1].db if at else None
                        before = before_db - median if before_db is not None else None
                    good = margin is not None and margin >= 3
                    previous_good = good and (at == 0 or (before is not None and before >= -3))
                    if not good or not previous_good:
                        stress_status = 'FAIL'
                    values.extend(
                        (
                            Measure(
                                f'stress:{line.id}:{mark.word}',
                                margin,
                                '>= 3 dB over line median',
                                'PASS' if good else 'FAIL',
                                source,
                            ),
                            Measure(
                                f'preceding:{line.id}:{mark.word}',
                                before,
                                '>= -3 dB; N/A if no preceding word',
                                'PASS' if previous_good else 'FAIL',
                                source + ('; N/A' if at == 0 else ''),
                            ),
                        )
                    )
                    if margin is not None:
                        margins.append(margin)
                    if before is not None:
                        preceding.append(before)
                reports.append(
                    VoiceLine(
                        line.id,
                        line.start,
                        count,
                        line.duration,
                        span,
                        phrase,
                        speech,
                        pace_status,
                        heard.words,
                        median,
                        line.stress,
                        min(margins) if margins else None,
                        min(preceding) if preceding else None,
                        stress_status,
                        source,
                    )
                )
        if hashlib.sha256(video.read_bytes()).hexdigest() != digest:
            raise CraftError('master changed during voice measurement')
        return Result(tuple(values), digest, tuple(reports))
    except (OSError, ValueError, wave.Error, EOFError, proof.ProofError) as exc:
        if isinstance(exc, CraftError):
            raise
        raise CraftError(f'final-master voice check: {exc}') from exc

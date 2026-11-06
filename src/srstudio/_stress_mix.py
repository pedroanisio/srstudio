"""Keep the integrated target and verify named stress before installation (ADR 0241)."""

from __future__ import annotations

import copy
import json
import math
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path

from . import craft_bar, emphasis, master_gate, prosody
from .voice import normalize_words

_AUDIO_ARGS = ('--start', '--end', '--param', '--row', '--data', '--representation', '--threads')
DUCK_DB = -6.0
LOUDNESS_TOLERANCE = 0.2  # LU; decoded ebur128 summary is rounded to one decimal
PEAK_TOLERANCE = 0.1  # dB; same meter precision


def _audio_args(args: Sequence[str]) -> list[str]:
    out: list[str] = []
    it = iter(args)
    for arg in it:
        if arg in _AUDIO_ARGS:
            out.extend((arg, next(it)))
        elif any(arg.startswith(key + '=') for key in _AUDIO_ARGS):
            out.append(arg)
    return out


def _contrasts(audio: Path, project: Path) -> dict[str, float | None]:
    measured = {m.name: m.value for m in craft_bar.measure_voice(audio, project).measures}
    return {
        f'{line.id}:{word}': float(value) if value is not None else None
        for line in craft_bar.recorded_lines(project)
        for word in line.stress
        for value in [measured.get(f'stress:{line.id}:{word}')]
    }


def _duck(root: ET.Element, lines: Sequence[craft_bar.RecordedLine]) -> None:
    spans: list[tuple[float, float]] = []
    for line in lines:
        if not line.stress:
            continue
        # Same first-normalised-occurrence matching as prosody.measure.
        for named in line.stress:
            if not any(normalize_words(w.text) == normalize_words(named) for w in line.words):
                raise craft_bar.CraftError(f'{line.id}: {named!r}: no timed stressed word')
        # The stress meter weighs a word against the line's other words on the mixed master; a bed left under
        # those words lifts them more than the loud one and flattens the contrast, so the duck spans the line.
        timed = [w for w in line.words if w.type == 'word'] or list(line.words)
        spans.append((line.start + min(w.start for w in timed), line.start + max(w.end for w in timed)))
    # Merge ramp extents: overlapping words must duck once, without a recovery between them.
    merged: list[tuple[float, float]] = []
    for start, end in sorted(spans):
        if merged and start - emphasis.RAMP <= merged[-1][1] + emphasis.RAMP:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    for track in root.findall('audioMix/audioTrack'):
        if track.get('role', 'other') not in ('music', 'effects', 'ambience'):
            continue
        animation = ET.SubElement(track, 'animate', property='gain', additive='true', timeBase='composition')
        keys: dict[float, float] = {}
        for start, end in merged:
            for time, db in (
                (max(0, start - emphasis.RAMP), 0),
                (start, DUCK_DB),
                (end, DUCK_DB),
                (end + emphasis.RAMP, 0),
            ):
                keys[time] = db
        for time, db in sorted(keys.items()):
            ET.SubElement(animation, 'key', time=str(time), value=str(db))


@contextmanager
def constrained(
    scene: Path, scratch: Path, engine: str, args: Sequence[str], run: Callable[..., subprocess.CompletedProcess[str]]
) -> Iterator[tuple[Path, Callable[[Path], str]]]:
    """Prepare word-span ducking, then validate the actual staged outputs at the authored target.

    No named stress means no extra engine invocation or scene rewrite. Analysis is
    the authored mix before normalization/limiting; the final measurement includes
    ducking, normalization, limiting and the delivery codec. Neither take gain nor
    the integrated target is changed. Scratch scenes stay beside their assets.
    """
    try:
        lines = craft_bar.recorded_lines(scene.parent)
    except craft_bar.NoRecordedLines:
        yield scene, lambda stage: ''
        return
    root = ET.parse(scene).getroot()
    master = root.find('audioMix/master')
    if not any(line.stress for line in lines) or master is None or master.get('normalize') != 'integrated':
        yield scene, lambda stage: ''
        return
    # Cached placements are in composition time; edits to programme time need remapped evidence.
    if root.findall('output/segment') or any(arg.split('=')[0] in ('--start', '--end') for arg in args):
        raise craft_bar.CraftError('named stress: programme ranges/segments need remapped word timings')
    target, ceiling = float(master.get('loudness', '-14')), float(master.get('truePeak', '-1'))
    if not all(math.isfinite(n) for n in (target, ceiling)):
        raise craft_bar.CraftError('stress mix: non-finite master target')
    analysis = copy.deepcopy(root)
    analysis_master = analysis.find('audioMix/master')
    assert analysis_master is not None
    analysis_master.set('normalize', 'none')
    analysis_master.set('limiter', 'false')
    output_index = next(i for i, child in enumerate(analysis) if child.tag == 'output')
    for output in analysis.findall('output'):
        analysis.remove(output)
    analysis.insert(
        output_index, ET.Element('output', id='stress-analysis', path='mix.wav', codec='audio-only', container='wav')
    )
    with tempfile.TemporaryDirectory(prefix='.stress-mix-', dir=scratch) as tmp:
        with tempfile.NamedTemporaryFile(prefix='.stress-', suffix='.scene.xml', dir=scene.parent) as source:
            path = Path(source.name)
            ET.ElementTree(analysis).write(path, encoding='unicode')
            done = run(
                [
                    engine,
                    'encode',
                    path.name,
                    *_audio_args(args),
                    '--no-upload',
                    '--json',
                    '--out-dir',
                    str(Path(tmp).resolve()),
                ],
                cwd=scene.parent.resolve(),
                capture_output=True,
                text=True,
            )
            try:
                if done.returncode:
                    raise ValueError(done.stderr)
                measured = json.loads(done.stdout)['result']['outputs'][0]
                if not all(math.isfinite(float(measured[k])) for k in ('loudness', 'true_peak')):
                    raise ValueError('non-finite audio meter')
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise craft_bar.CraftError(f'stress mix analysis failed: {exc}') from exc
            before = _contrasts(Path(tmp) / 'mix.wav', scene.parent)
            _duck(root, lines)
            ET.ElementTree(root).write(path, encoding='unicode')

            def verify(stage: Path) -> str:
                reports = []
                for output in root.findall('output'):
                    audio = stage / output.get('path', '')
                    after = _contrasts(audio, scene.parent)
                    words = []
                    failures = []
                    for name, initial in before.items():
                        final = after.get(name)
                        evidence = f'{name} before={initial} dB after={final} dB'
                        words.append(evidence)
                        if initial is None or final is None or not math.isfinite(final) or final < prosody.STRESS_DB:
                            failures.append(evidence)
                    if not words:
                        raise craft_bar.CraftError('stress mix: no measured named words')
                    lufs, _, peak, _ = master_gate.audio_levels(audio)
                    report = (
                        f'stress mix {audio.name}: target={target:g} LUFS measured={lufs:g} LUFS '
                        f'true_peak={peak:g} dBTP; ' + '; '.join(words)
                    )
                    if failures:
                        raise craft_bar.CraftError(
                            report + f'; requires >= {prosody.STRESS_DB:g} dB '
                            f'(take aim {prosody.STRESS_DB + emphasis.MARGIN:g} dB); failed: ' + '; '.join(failures)
                        )
                    if abs(lufs - target) > LOUDNESS_TOLERANCE or peak > ceiling + PEAK_TOLERANCE:
                        raise craft_bar.CraftError(report + '; master misses authored loudness/peak target')
                    reports.append(report)
                return '\n'.join(reports)

            yield path, verify

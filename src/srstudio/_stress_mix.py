"""Keep integrated mastering out of the limiter on recordings with named stress (ADR 0241)."""

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

from . import craft_bar

# These affect the measured programme; output, upload and picture options do not.
_AUDIO_ARGS = ('--start', '--end', '--param', '--row', '--data', '--representation', '--threads')


def _audio_args(args: Sequence[str]) -> list[str]:
    out: list[str] = []
    it = iter(args)
    for arg in it:
        if arg in _AUDIO_ARGS:
            out.extend((arg, next(it)))
        elif any(arg.startswith(key + '=') for key in _AUDIO_ARGS):
            out.append(arg)
    return out


@contextmanager
def constrained(
    scene: Path, scratch: Path, engine: str, args: Sequence[str], run: Callable[..., subprocess.CompletedProcess[str]]
) -> Iterator[tuple[Path, str]]:
    """Yield a sibling scene with a measured loudness ceiling; leave the authored document intact.

    A sibling keeps all document-relative paths and report semantics. The audio-only
    analysis includes every authored track, effect and master fader, but no normalization
    or limiting. Its exact engine meters set the maximum constant gain, without raising
    any word. Only projects with recorded, named stress opt in.
    """
    try:
        lines = craft_bar.recorded_lines(scene.parent)
    except craft_bar.NoRecordedLines:
        yield scene, ''
        return
    root = ET.parse(scene).getroot()
    master = root.find('audioMix/master')
    if not any(line.stress for line in lines) or master is None or master.get('normalize') != 'integrated':
        yield scene, ''
        return
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
        # Keep analysis products outside the install stage.
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
                loudness, peak = float(measured['loudness']), float(measured['true_peak'])
                target, ceiling = float(master.get('loudness', '-16')), float(master.get('truePeak', '-1.5'))
                if not all(math.isfinite(n) for n in (loudness, peak, target, ceiling)):
                    raise ValueError('non-finite audio meter')
            except (ValueError, KeyError, IndexError, TypeError) as exc:
                raise craft_bar.CraftError(f'stress mix analysis failed: {exc}') from exc
            safe = min(target, loudness + ceiling - peak)
            if safe == target:
                yield scene, ''
                return
            master.set('loudness', repr(safe))
            ET.ElementTree(root).write(path, encoding='unicode')
            yield path, f'stress mix: loudness capped from {target:g} to {safe:.6f} LUFS to preserve word contrast'

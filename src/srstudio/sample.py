"""A synthetic project for tests and examples: ``dialogue.json``, a tone-burst WAV and the caption font.

The WAV carries a sine burst inside every phrase, so amplitude-driven mouths have something to chew
on without a TTS call. The font is DejaVu Sans Bold from the system (the shipped episodes use the same
face), or a supplied font file. A missing or invalid font is refused before writing the project.
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import tempfile
import wave
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

from . import checks
from ._outputs import write_outputs
from .errors import SrstudioError
from .fonts import FontError, inspect_ttf
from .timeline import Timeline, TimelineError


class SampleError(SrstudioError, ValueError):
    """A sample project cannot be built with the supplied inputs."""


SYSTEM_FONTS = (
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"),
)
# The DejaVu fonts' LICENSE, verbatim from upstream: the Bitstream Vera notice (DejaVu's changes are in the public
# domain), the Arev notice for the glyphs imported from Tavmjong Bah's Arev fonts, and DejaVu Math TeX Gyre's notices.
DEJAVU_LICENSE_FILE = "assets/fonts/DejaVu-LICENSE.txt"


def dejavu_license() -> str:
    """The notice the DejaVu licence requires in every copy of the font."""
    return files("srstudio").joinpath(DEJAVU_LICENSE_FILE).read_text(encoding="utf-8")


def copy_dejavu(source: Path, folder: Path, name: str = "DejaVuSans-Bold.ttf") -> Path:
    """Copy the DejaVu font ``source`` into ``folder`` as ``name``, its notice beside it as ``FONT-LICENSE.txt``."""
    target = Path(folder) / name
    if not (target.exists() and Path(source).samefile(target)):
        shutil.copyfile(source, target)
    (Path(folder) / "FONT-LICENSE.txt").write_text(dejavu_license(), encoding="utf-8")
    return target


@dataclass(frozen=True)
class Line:
    role: str
    text: str
    seconds: float = 1.2
    gap: float = 0.35
    caption: str | None = None


def write_wav(
    path: Path, spans: Sequence[tuple[float, float]], duration: float, rate: int = 24000, amplitude: float = 0.35
) -> None:
    frames = int(round(duration * rate))
    data = bytearray()
    for i in range(frames):
        t = i / rate
        inside = any(a <= t < b for a, b in spans)
        v = amplitude * math.sin(2 * math.pi * 180 * t) * (0.6 + 0.4 * math.sin(2 * math.pi * 3 * t)) if inside else 0.0
        data += struct.pack("<h", int(v * 32767))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(bytes(data))


def write_sample_project(
    root: Path,
    lines: Sequence[Line],
    *,
    angles: Sequence[str] | None = None,
    lead: float = 0.3,
    tail: float = 2.4,
    reaction_after_last: float = 0.25,
    end_card_after_last: float = 1.2,
    font: Path | None = None,
    overwrite: bool = False,
) -> dict:
    """Write a synthetic project and return its dialogue data; existing artifacts require ``overwrite=True``."""
    source = Path(font) if font is not None else next((f for f in SYSTEM_FONTS if f.is_file()), None)
    if source is None:
        raise SampleError(
            "DejaVu Sans Bold is required: install DejaVu fonts or pass font=Path('/path/to/DejaVuSans-Bold.ttf')"
        )
    try:
        facts = inspect_ttf(source.read_bytes())
    except (OSError, FontError) as exc:
        raise SampleError(f"{source}: cannot use this font; supply a valid TrueType file with font=: {exc}") from exc
    if facts.family != "DejaVu Sans" or facts.weight != 700 or facts.italic:
        raise SampleError(f"{source}: expected upright DejaVu Sans weight 700, got {facts}")
    if not lines:
        raise SampleError("lines: at least one line is required")
    if angles is not None and len(angles) != len(lines):
        raise SampleError(f"angles: expected {len(lines)} names, got {len(angles)}")
    if angles is not None:
        for i, angle in enumerate(angles):
            if not isinstance(angle, str) or not angle.strip():
                raise SampleError(f"angles {i}: expected a nonempty string")
    for name, value, positive in (
        ("lead", lead, False),
        ("tail", tail, True),
        ("reaction_after_last", reaction_after_last, False),
        ("end_card_after_last", end_card_after_last, False),
    ):
        if not checks.number(value) or (value <= 0 if positive else value < 0):
            raise SampleError(f"{name}: expected a finite {'positive' if positive else 'non-negative'} number")
    for i, line in enumerate(lines):
        if not isinstance(line.role, str) or not line.role.strip():
            raise SampleError(f"line {i}.role: expected a nonempty string")
        if not isinstance(line.text, str) or not line.text.strip():
            raise SampleError(f"line {i}.text: expected a nonempty string")
        if line.caption is not None and (not isinstance(line.caption, str) or not line.caption.strip()):
            raise SampleError(f"line {i}.caption: expected a nonempty string or None")
        if not checks.number(line.seconds) or line.seconds <= 0:
            raise SampleError(f"line {i}.seconds: expected a finite positive number")
        if not checks.number(line.gap) or line.gap < 0:
            raise SampleError(f"line {i}.gap: expected a finite non-negative number")
    t = lead
    phrases: list[dict[str, Any]] = []
    cuts: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        phrases.append(
            {
                "role": line.role,
                "text": line.text,
                "caption": line.caption or line.text,
                "start": round(t, 6),
                "end": round(t + line.seconds, 6),
            }
        )
        cuts.append(
            {
                "time": 0 if i == 0 else round(t - 0.06, 6),
                "angle": angles[i] if angles is not None else ("wide" if i % 2 == 0 else "close"),
            }
        )
        t += line.seconds + line.gap
    last_end = phrases[-1]["end"]
    data: dict[str, Any] = {
        "title": "Sample episode",
        "language": "en-US",
        "duration": round(last_end + tail, 6),
        "phrases": phrases,
        "sound_effects": [],
        "camera_cuts": cuts,
        "reaction_start": round(last_end + reaction_after_last, 6),
        "end_card_start": round(last_end + end_card_after_last, 6),
        "font_real": True,
    }
    try:
        Timeline.from_dict(data)
    except TimelineError as exc:
        raise SampleError(f"sample timeline: {exc}") from exc
    root = Path(root)
    artifacts = (
        Path("dialogue.json"),
        Path("assets/dialogue.wav"),
        Path("assets/DejaVuSans-Bold.ttf"),
        Path("assets/FONT-LICENSE.txt"),
    )
    for relative in artifacts:
        target = root / relative
        if target.is_dir():
            raise SampleError(f"{target}: expected a file, found a directory")
        if not overwrite and (target.exists() or target.is_symlink()):
            raise SampleError(f"{target}: already exists; pass overwrite=True to replace sample artifacts")
    try:
        root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".srstudio-sample-", dir=root.parent) as temporary:
            stage = Path(temporary) / "project"
            (stage / "assets").mkdir(parents=True)
            (stage / "dialogue.json").write_text(json.dumps(data, indent=2) + "\n")
            write_wav(stage / "assets" / "dialogue.wav", [(p["start"], p["end"]) for p in phrases], data["duration"])
            copy_dejavu(source, stage / "assets")
            write_outputs(
                [(root / relative, (stage / relative).read_bytes()) for relative in artifacts], overwrite=overwrite
            )
    except OSError as exc:
        raise SampleError(f"{root}: cannot write sample project: {exc}") from exc
    return data

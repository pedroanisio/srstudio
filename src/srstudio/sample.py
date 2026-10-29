"""A synthetic project for tests and examples: ``dialogue.json``, a tone-burst WAV and the caption font.

The WAV carries a sine burst inside every phrase, so amplitude-driven mouths have something to chew
on without a TTS call. The font is DejaVu Sans Bold from the system when present (the shipped
episodes use the same face); otherwise a placeholder file is written and ``font_real`` is False.
"""

from __future__ import annotations

import json
import math
import shutil
import struct
import wave
from collections.abc import Sequence
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from typing import Any

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
) -> dict:
    """Write a project under ``root`` and return the dialogue data (also written as JSON)."""
    root = Path(root)
    (root / "assets").mkdir(parents=True, exist_ok=True)
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
                "angle": angles[i] if angles else ("wide" if i % 2 == 0 else "close"),
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
    }
    (root / "dialogue.json").write_text(json.dumps(data, indent=2) + "\n")
    write_wav(root / "assets" / "dialogue.wav", [(p["start"], p["end"]) for p in phrases], data["duration"])
    source = font or next((f for f in SYSTEM_FONTS if f.exists()), None)
    target = root / "assets" / "DejaVuSans-Bold.ttf"
    if source:
        copy_dejavu(source, target.parent, target.name)
    else:
        target.write_bytes(b"\0")
    data["font_real"] = bool(source)
    return data

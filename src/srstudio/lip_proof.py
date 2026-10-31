"""The lip proof: which frames of a master to compare with the words said over them (ADR 0020).

Lip sync can only be judged on the file that ships, looking at a mouth in the middle of a word. :func:`instants` reads
a project's recording and picks those moments, spread evenly over the reel: the middle of each chosen word's longest
sounded letter, on the master's clock, moved to the frame nearest it, with the pose the mouth track holds on that frame.
:func:`frames` pulls exactly that frame out of the master at full size. A person compares them;
:attr:`Instant.suspect` only names the plainest defect, a mouth shut on a vowel.
"""

from __future__ import annotations

import json
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import SrstudioError

__all__ = ["COUNT", "Instant", "LipProofError", "frames", "instants"]

COUNT = 16
FPS = 30
VOWELS = "aeiou"
SHUT = "closed"
Run = Callable[[list[str]], None]


class LipProofError(SrstudioError, ValueError):
    """The recording cannot be read, or a frame cannot be pulled from the master."""


@dataclass(frozen=True)
class Instant:
    """A moment to look at: ``letter`` of ``word`` said by ``who`` at ``at`` seconds, the mouth track on ``shown``."""

    who: str
    word: str
    letter: str
    at: float
    shown: str

    @property
    def suspect(self) -> bool:
        return self.shown == SHUT and self.letter.lower() in VOWELS


def _read(path: Path) -> dict[str, Any]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LipProofError(f"cannot read {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise LipProofError(f"{path} is not a JSON object")
    return doc


def _words(take: dict[str, Any]) -> list[tuple[str, str, float]]:
    """Every word of a take as ``(word, its longest letter, the middle of that letter on the master's clock)``."""
    try:
        said, starts, ends = take["characters"], take["starts"], take["ends"]
        at, clip_in, tid = float(take["at"]), float(take.get("clip_in", 0.0)), take["id"]
    except (KeyError, TypeError, ValueError) as exc:
        raise LipProofError(f"a take has no usable timing: {exc!r}") from exc
    if not len(said) == len(starts) == len(ends):
        raise LipProofError(f"take {tid}: {len(said)} characters, {len(starts)} starts, {len(ends)} ends")
    out: list[tuple[str, str, float]] = []
    word: list[int] = []
    for k, char in enumerate([*said, " "]):
        if str(char).isalnum() or (char == "'" and word):
            word.append(k)
            continue
        if word:
            letters = [i for i in word if str(said[i]).isalpha()] or word
            sounded = letters[:-1] if len(letters) > 2 and str(said[letters[-1]]).lower() == "e" else letters
            longest = max(sounded, key=lambda i: ends[i] - starts[i])
            middle = at + (starts[longest] + ends[longest]) / 2 - clip_in
            out.append(("".join(said[i] for i in word), str(said[longest]), round(middle, 3)))
        word = []
    return out


def _shown(track: Sequence[Sequence[Any]], at: float) -> str:
    held = str(track[0][1]) if track else ""
    for start, pose in track:
        if start > at:
            break
        held = str(pose)
    return held


def instants(project: Path, *, count: int = COUNT, fps: int = FPS) -> list[Instant]:
    """Up to ``count`` instants of the project's recording, evenly spread over its words, each on a frame of ``fps``."""
    if count < 1:
        raise LipProofError(f"count must be at least 1, got {count}")
    voiced = Path(project) / "voiced"
    takes = _read(voiced / "speech.json").get("takes") or []
    mouths = _read(voiced / "mouths.json").get("mouths") or {}
    said = [(str(take.get("who", "")), *word) for take in takes for word in _words(take)]
    step = max(len(said) / count, 1.0)
    out = []
    for k in range(min(count, len(said))):
        who, word, letter, middle = said[int(k * step)]
        if who not in mouths:
            raise LipProofError(f"no mouth track for {who!r}")
        at = round(middle * fps) / fps
        out.append(Instant(who, word, letter, at, _shown(mouths[who], at)))
    return out


def _ffmpeg(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


def frames(
    picks: Sequence[Instant], master: Path, out: Path, *, crop: str | None = None, fps: int = FPS, run: Run = _ffmpeg
) -> list[Path]:
    """Each instant's frame of ``master``, written to ``out`` as ``lipNN.png``. ``crop`` is ffmpeg's ``w:h:x:y``. The
    seek is half a frame early, as ffmpeg gives the first frame at or after it and a frame's own time may round past."""
    Path(out).mkdir(parents=True, exist_ok=True, mode=0o700)
    made = []
    for n, pick in enumerate(picks):
        path = Path(out) / f"lip{n:02d}.png"
        extra = ["-vf", f"crop={crop}"] if crop else []
        seek = max(pick.at - 0.5 / fps, 0.0)
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{seek:.3f}", "-i", str(master), "-frames:v", "1"]
        try:
            run([*cmd, *extra, str(path)])
        except (OSError, subprocess.CalledProcessError) as exc:
            raise LipProofError(f"ffmpeg could not pull {pick.at:.3f} s from {master}: {exc}") from exc
        made.append(path)
    return made

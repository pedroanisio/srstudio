"""The soundtrack, read with the standard library, and the mouth poses it drives.

The rig animates five mouth shapes (rest, round, open, small, smile) with hold keys; the
pose at each frame follows the RMS amplitude of the dialogue track while a role speaks.
``numpy`` is used when installed and is not required.
"""

from __future__ import annotations

import math
import struct
import wave
from array import array
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from . import checks
from .errors import SrstudioError
from .timeline import Timeline

if TYPE_CHECKING:
    from .generated import Placement

_np: Any
try:  # optional, only for speed
    import numpy as _np
except Exception:  # pragma: no cover
    _np = None

MOUTHS = ("rest", "round", "open", "small", "smile")


class SoundtrackError(SrstudioError, ValueError):
    """A clip the mix cannot read, or a mouth style it cannot follow."""


def validate_wav(path: Path) -> None:
    """Check WAV structure and supported format tags without decoding or loading samples."""
    try:
        with path.open("rb") as source:
            header = source.read(12)
            if len(header) != 12 or header[:4] not in (b"RIFF", b"RF64") or header[8:] != b"WAVE":
                raise ValueError("expected a RIFF or RF64 WAVE header")
            size = source.seek(0, 2)
            source.seek(12)
            rf64 = header[:4] == b"RF64"
            table: dict[bytes, list[int]] = {}
            first_data_size = None
            if rf64:
                if struct.unpack_from("<I", header, 4)[0] != 0xFFFFFFFF:
                    raise ValueError("invalid RF64 size marker")
                ds_header = source.read(8)
                if len(ds_header) != 8:
                    raise ValueError("missing RF64 ds64 chunk")
                name, ds_length = struct.unpack("<4sI", ds_header)
                if name != b"ds64" or ds_length < 28 or source.tell() + ds_length > size:
                    raise ValueError("missing or truncated RF64 ds64 chunk")
                riff_size, first_data_size, _, count = struct.unpack("<QQQI", source.read(28))
                if count > (ds_length - 28) // 12:
                    raise ValueError("truncated RF64 ds64 table")
                for _ in range(count):
                    key, length = struct.unpack("<4sQ", source.read(12))
                    table.setdefault(key, []).append(length)
                limit = riff_size + 8
            else:
                limit = struct.unpack_from("<I", header, 4)[0] + 8
            if limit > size or limit < 12:
                raise ValueError("truncated WAV container")
            source.seek(12)
            fmt = None
            data_sizes = []
            while source.tell() < limit:
                chunk = source.read(8)
                if len(chunk) != 8:
                    raise ValueError("truncated chunk header")
                name, length = struct.unpack("<4sI", chunk)
                if length == 0xFFFFFFFF and rf64:
                    if name == b"data" and first_data_size is not None:
                        length, first_data_size = first_data_size, None
                    elif table.get(name):
                        length = table[name].pop(0)
                    else:
                        raise ValueError(f"missing RF64 size for {name!r} chunk")
                end = source.tell() + length
                if end > limit:
                    raise ValueError(f"truncated {name!r} chunk")
                if name == b"fmt ":
                    if length < 16:
                        raise ValueError("invalid fmt chunk")
                    fmt = struct.unpack("<HHIIHH", source.read(16))
                    if fmt[0] == 0x11:
                        extension = source.read(min(length - 16, 4))
                        if len(extension) < 4:
                            raise ValueError("invalid IMA ADPCM format extension")
                        extra_size, samples_per_block = struct.unpack("<HH", extension)
                        if extra_size < 2 or extra_size > length - 18 or not samples_per_block or fmt[5] != 4:
                            raise ValueError("invalid IMA ADPCM format extension")
                    elif fmt[0] == 0xFFFE:
                        extension = source.read(min(length - 16, 24))
                        if len(extension) < 24 or struct.unpack_from("<H", extension)[0] < 22:
                            raise ValueError("invalid extensible WAV format")
                        subtype = extension[8:24]
                        if subtype[2:] != bytes.fromhex("000000001000800000aa00389b71"):
                            raise ValueError("unsupported extensible WAV encoding; convert to PCM or IEEE float")
                        encoding = struct.unpack_from("<H", subtype)[0]
                        if encoding not in (1, 3):
                            raise ValueError("unsupported extensible WAV encoding; convert to PCM or IEEE float")
                elif name == b"data":
                    data_sizes.append(length)
                source.seek(end + (length % 2))
            if fmt is None or not data_sizes:
                raise ValueError("missing fmt or data chunk")
            encoding, channels, rate, _, alignment, bits = fmt
            if not encoding or not channels or not rate or not alignment or not bits:
                raise ValueError("invalid audio format")
            if encoding not in (1, 3, 6, 7, 0x11, 0xFFFE):
                raise ValueError(f"unsupported WAV encoding 0x{encoding:04x}; convert to PCM or IEEE float")
            if any(length % alignment for length in data_sizes):
                raise ValueError("truncated audio frame")
    except (OSError, ValueError, struct.error) as exc:
        raise SoundtrackError(f"{path}: cannot read WAV: {exc}") from exc


def _read_mono(path: Path) -> tuple[Any, int]:
    """A 16-bit PCM WAV as mono floats in -1..1 (a numpy array when available), and its rate."""
    try:
        with wave.open(str(path), "rb") as wav:
            rate = wav.getframerate()
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            frames = wav.getnframes()
            raw = wav.readframes(frames)
    except (OSError, EOFError, wave.Error) as exc:
        raise SoundtrackError(f"{path}: cannot read PCM WAV: {exc}") from exc
    if width != 2:
        raise SoundtrackError(f"{path}: only 16-bit PCM is supported")
    if len(raw) != frames * channels * width:
        raise SoundtrackError(f"{path}: truncated PCM WAV data")
    if _np is not None:
        return _np.frombuffer(raw, dtype=_np.int16).astype(float).reshape(-1, channels).mean(1) / 32768, rate
    samples = array("h")
    samples.frombytes(raw)
    if channels == 1:
        return [v / 32768 for v in samples], rate
    return [sum(samples[i : i + channels]) / channels / 32768 for i in range(0, len(samples), channels)], rate


def _fade(k: int, n: int, fade_in: int, fade_out: int) -> float:
    """Linear fade weight of sample ``k`` of ``n``: rising over ``fade_in``, falling over the last ``fade_out``."""
    w = 1.0
    if k < fade_in:
        w *= k / fade_in
    if fade_out and k >= n - fade_out:
        w *= (n - 1 - k) / fade_out
    return w


class Soundtrack:
    """A mono, normalised view of the dialogue with a fast RMS window: one WAV file, or
    generated clips placed as the mix plays them (:meth:`from_clips`)."""

    def __init__(self, path: str | Path):
        self.path: Path | None = Path(path)
        self._samples, self.rate = _read_mono(self.path)

    @classmethod
    def from_clips(cls, clips: Iterable[tuple[Path, Placement]], duration: float, rate: int = 48000) -> Soundtrack:
        """The mono sum of ``clips`` over ``duration`` seconds, each trimmed, gained and faded
        (linearly, the mix's default curve) as its :class:`~srstudio.generated.Placement` says."""
        total = round(duration * rate)
        mix: Any = _np.zeros(total) if _np is not None else [0.0] * total
        for path, place in clips:
            mono, clip_rate = _read_mono(Path(path))
            if clip_rate != rate:
                raise SoundtrackError(f"{path}: {clip_rate} Hz, but the mix runs at {rate} Hz")
            a = round(place.clip_in * rate)
            b = len(mono) if place.clip_out is None else min(len(mono), round(place.clip_out * rate))
            gain = 10 ** (place.gain_db / 20)
            fade_in, fade_out = round(place.fade_in * rate), round(place.fade_out * rate)
            n = max(0, b - a)
            at = round(place.start * rate)
            count = max(0, min(n, total - at))
            envelope = [gain * _fade(k, n, fade_in, fade_out) for k in range(count)]
            if _np is not None:
                mix[at : at + count] += _np.asarray(mono[a : a + count]) * _np.asarray(envelope)
            else:
                for k in range(count):
                    mix[at + k] += mono[a + k] * envelope[k]
        track = cls.__new__(cls)
        track.path = None
        track._samples, track.rate = mix, rate
        return track

    @property
    def frames(self) -> int:
        return len(self._samples)

    @property
    def duration(self) -> float:
        return self.frames / self.rate

    def rms(self, t0: float, t1: float) -> float:
        a, b = int(t0 * self.rate), int(t1 * self.rate)
        chunk = self._samples[a:b]
        if _np is not None and not isinstance(chunk, list):
            return math.sqrt(float(_np.mean(chunk * chunk))) if len(chunk) else 0.0
        return math.sqrt(sum(v * v for v in chunk) / len(chunk)) if len(chunk) else 0.0


@dataclass(frozen=True)
class MouthStyle:
    """How amplitude turns into poses; two presets reproduce the office and café scripts."""

    window: tuple[float, float] = (0.015, 0.055)  # seconds after the frame time
    threshold: float = 0.012  # below this the mouth rests
    loud: float = 0.04  # above this the mouth is fully open
    rounding: Callable[[float], bool] = lambda t: int(t * 12) % 5 in (0, 3)
    idle: str = "rest"  # pose while not speaking
    letters: bool = False  # the line's letters pick round, closed or open (srstudio.lipsync.letter_track)


OFFICE_MOUTH = MouthStyle()
CAFE_MOUTH = MouthStyle(window=(0.01, 0.05), loud=0.045, rounding=lambda t: int(t * 11) % 4 == 0)
# Sung, beat-timed lines: a quicker window and a wider open mouth for the blob's chant.
SOFT_MOUTH = MouthStyle(window=(0.0, 0.04), threshold=0.015, loud=0.05, rounding=lambda t: int(t * 8) % 4 == 2)


def mouth_states(
    track: Soundtrack,
    timeline: Timeline,
    role: str,
    fps: int = 30,
    smile: Iterable[tuple[float, float]] = (),
    style: MouthStyle = OFFICE_MOUTH,
    speaking: Sequence[tuple[float, float]] | None = None,
) -> list[tuple[float, str]]:
    """One ``(time, pose)`` per frame for ``role``; ``smile`` spans force the smile."""
    if style.letters and speaking is not None:
        raise SoundtrackError("letters guide the mouth from the role's phrases; bare speaking spans have no text")
    spans = list(timeline.spans(role) if speaking is None else speaking)
    smile = list(smile)
    frames = math.ceil(timeline.duration * fps - 1e-9)
    energy = [track.rms(f / fps + style.window[0], f / fps + style.window[1]) for f in range(frames)]
    talking = [any(a <= f / fps < b for a, b in spans) and energy[f] > style.threshold for f in range(frames)]
    guide: dict[int, str] = {}
    if style.letters:
        from .lipsync import letter_track

        for phrase in timeline.phrases:
            if phrase.role == role:
                voiced = [f for f in range(frames) if talking[f] and phrase.start <= f / fps < phrase.end]
                guide.update(zip(voiced, letter_track(phrase.text, len(voiced)), strict=False))
    out: list[tuple[float, str]] = []
    for frame in range(frames):
        t = frame / fps
        if talking[frame] and frame in guide:
            state = _GUIDED[guide[frame]] if guide[frame] != "open" or energy[frame] > style.loud else "small"
        elif talking[frame]:
            state = "round" if style.rounding(t) else "open" if energy[frame] > style.loud else "small"
        else:
            state = style.idle
        if any(a <= t < b for a, b in smile) and not talking[frame]:
            state = "smile"
        out.append((t, state))
    return out


_GUIDED = {"round": "round", "closed": "rest", "open": "open", "teeth": "small"}  # letter pose -> amplitude mouth


def pose_keys(states: Sequence[tuple[float, str]], pose: str) -> list[tuple[float, int]]:
    """Compress per-frame poses into opacity change points for one mouth shape."""
    keys: list[tuple[float, int]] = []
    last = None
    for t, state in states:
        value = int(state == pose)
        if value != last:
            keys.append((t, value))
            last = value
    return keys


# -- character-timestamp (phoneme) driver ------------------------------------------------------------
INK_POSES = ("closed", "open", "round", "teeth", "shout")


@dataclass(frozen=True)
class PhonemeStyle:
    """Letters → mouth poses, sampled at ``rate`` Hz; the hand-drawn cartoons speak this way."""

    rate: int = 12
    round_letters: str = "ou"
    open_letters: str = "aehiy"
    closed_letters: str = "bmp"
    scream_moods: tuple[str, ...] = ("scream",)
    angry_moods: tuple[str, ...] = ("angry",)
    # opt-in improvements, all on in srstudio.lipsync.SPEECH_MOUTH; the defaults sample as the packages shipped
    spelling: bool = False  # English spelling: ph, w, qu, silent final e and gh
    close_bilabials: bool = False  # every b, m, p closes the mouth on its nearest sample
    lead: float = 0.0  # seconds the mouth shows a sound early
    min_rest: float = 0.0  # a pause between letters shorter than this keeps the pose before it
    fine: bool = False  # two more poses for a mouth seen large: wide for e, i and y, lip for f and v
    first_sound: bool = False  # a trimmed take opens on the sound due at its first second, not shut until a sample

    def __post_init__(self):
        if isinstance(self.rate, bool) or not isinstance(self.rate, int) or self.rate <= 0:
            raise SoundtrackError(
                f"a phoneme style's rate is a positive whole number of samples a second, got {self.rate!r}"
            )
        for name in ("lead", "min_rest"):
            value = getattr(self, name)
            if not checks.number(value) or value < 0:
                raise SoundtrackError(f"a phoneme style's {name} is a finite number of seconds >= 0, got {value!r}")
        if not isinstance(self.first_sound, bool):
            raise SoundtrackError(f"a phoneme style's first_sound is True or False, got {self.first_sound!r}")


INK_MOUTH = PhonemeStyle()


def phoneme_states(
    phones: Sequence[dict], duration: float, mood: str = "", style: PhonemeStyle = INK_MOUTH
) -> list[tuple[float, str]]:
    """``(time, pose)`` samples from character timestamps ``{c, start, end}`` relative to the take
    (:func:`srstudio.lipsync.phoneme_states`)."""
    from .lipsync import phoneme_states as sample

    return sample(phones, duration, mood, style)

"""The voices a reel may cast: the premade ElevenLabs voices published reels already use, by name.

A reel names a voice and gets its id, so an id cannot be mistyped and a new voice cannot slip in through a data file: a
voice joins this table in a commit of its own, reviewed as a voice. :func:`speaker` builds a sketch's speaker with the
settings a cast has settled on: ``deadpan`` for a held line, ``plain`` for most people, ``big`` for a shout.
"""

from __future__ import annotations

from dataclasses import replace

from . import sketch
from .sketch import Speaker
from .toon import ToonDataError
from .voice import Voice, VoiceSettings

__all__ = ["DELIVERIES", "MOUTH", "VOICES", "speaker", "tinted"]

VOICES = {
    "Alice": "Xb7hH8MSUJpSbSDYk0k2",
    "Bill": "pqHfZKP75CvOlQylNhV4",
    "Brian": "nPczCjzI2devNBz1zQrb",
    "Charlie": "IKne3meq5aSn9XLyUdCD",
    "Chris": "iP95p4xoKVk53GoZ742B",
    "Daniel": "onwK4e9ZLuTAKqWW03F9",
    "Jessica": "cgSgspJ2msm6clMCkdW9",
    "Laura": "FGY2WhTYpPnrIDTdsKH5",
    "Liam": "TX3LPaxmHKxFdv7VOQHJ",
    "Matilda": "XrExE9yKIg1WjnnlVkGX",
    "River": "SAz9YHcvj6GT2YYXdXww",
    "Roger": "CwhRBWXzGAHq8TQ4Fs17",
    "Sarah": "EXAVITQu4vr4xnSDxMaL",
    "Will": "bIHbv24MWmeRgasZH58o",
}
DELIVERIES = {
    "deadpan": VoiceSettings(stability=0.65, similarity_boost=0.75, style=0.15),
    "plain": VoiceSettings(stability=0.5, similarity_boost=0.75, style=0.3),
    "big": VoiceSettings(stability=0.32, similarity_boost=0.75, style=0.55),
}
MOUTH = replace(sketch.MOUTH_STYLE, spelling=True, close_bilabials=True, lead=0.04, min_rest=0.12)


def speaker(role: str, voice: str, character: str | None = None, delivery: str = "plain") -> Speaker:
    """``role`` said by the premade ``voice``, played by ``character`` (None: heard, not seen), at a ``delivery`` of
    :data:`DELIVERIES`."""
    if voice not in VOICES:
        raise ToonDataError(f"{voice!r} is not a voice published reels use: {sorted(VOICES)}")
    if delivery not in DELIVERIES:
        raise ToonDataError(f"a delivery is one of {sorted(DELIVERIES)}, got {delivery!r}")
    return Speaker(role, Voice(role=role, id=VOICES[voice], name=voice), DELIVERIES[delivery], character)


def tinted(*speakers: Speaker, palette: tuple[str, ...] = ("#ecdcc4", "#d6f0c8", "#ffd9e4", "#d9e8ff", "#ffe9a8")):
    """A pill tint per speaker, in cast order."""
    if len(speakers) > len(palette):
        raise ToonDataError(f"{len(palette)} tints for {len(speakers)} speakers")
    return {s.name: tint for s, tint in zip(speakers, palette, strict=False)}

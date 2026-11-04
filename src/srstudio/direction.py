"""Per-line voice direction: which model says a line, the audio tags before it, the words it stresses, the pauses in it
and the silence around it, how many takes it gets and which one is kept (ADR 0234).

A line's words stay what the captions show and what speech-to-text must hear. :func:`render` turns the words and a
:class:`Direction` into the text the provider is sent, and keeps, letter by letter, where each sent letter came from
in the line, so :func:`spoken` can take the provider's alignment of the sent text back to the line's own letters:
a tag, a break or a capital never reaches a caption, a word timing or the speech check.

What each model takes was read in the ElevenLabs documentation and checked with a real request (ADR 0234):

* ``eleven_multilingual_v2`` (the default, every published reel): ``<break time="x.xs" />`` pauses up to 3 s, the
  previous and next text for continuity, and style, speed and speaker boost. An audio tag is SPOKEN aloud on it
  ("[sighs] Allergies." was heard as "Size allergies?"), so a tag is refused there; capitals as stress are not
  documented for it, so emphasis is refused there too.
* ``eleven_v3``: audio tags and capitals; no break tags, no previous or next text (the API answers 400), no style,
  speed or speaker boost.
* ``eleven_v4``: audio tags and capitals and the previous and next text; no break tags (ignored, measured), no style,
  speed (ignored, measured) or speaker boost.

Every refusal is a :class:`DirectionError`, raised before anything is requested.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace

from . import checks
from .voice import Alignment, VoiceOutputError, VoiceRequestError

__all__ = [
    "AUDIO_TAGS",
    "MAX_BREAK",
    "MAX_HOLD",
    "MAX_TAKES",
    "MODELS",
    "LINE_CHECKS",
    "REEL_CHECKS",
    "Direction",
    "DirectionError",
    "ModelSpec",
    "Pause",
    "Rendered",
    "Waiver",
    "model_spec",
    "render",
    "seeds",
    "spoken",
]

MAX_BREAK = 3.0  # the longest ``<break>`` the provider documents, seconds
MAX_HOLD = 6.0  # the longest silence cut in before or after a line, seconds
MAX_TAKES = 6  # the most takes one line may ask for
MAX_PAUSES = 3  # "too many break tags in a single generation can cause instability" (ElevenLabs controls guide)
MAX_QUALITY = 40  # the longest described quality, in characters

# The audio tags the ElevenLabs documentation names for Eleven v3 and v4: the best-practices guide's voice, sound and
# special lists, and the help centre's [shouts] and [clears throat]. A described quality goes in Direction.quality.
AUDIO_TAGS = frozenset(
    {
        # voice: delivery and emotion
        "laughs",
        "laughs harder",
        "starts laughing",
        "wheezing",
        "whispers",
        "sighs",
        "exhales",
        "sarcastic",
        "curious",
        "excited",
        "crying",
        "snorts",
        "mischievously",
        "shouts",
        "clears throat",
        # sounds
        "gunshot",
        "applause",
        "clapping",
        "explosion",
        "swallows",
        "gulps",
        # special (experimental in the guide)
        "sings",
        "woo",
    }
)
ACCENT = re.compile(r"strong [a-z]+(?: [a-z]+)? accent")  # the guide's "[strong X accent]"
QUALITY = re.compile(r"[a-z]+(?:[ ,'-]+[a-z]+)*")  # "quietly, holding back": words, commas, hyphens
WORD = re.compile(r"[A-Za-z][A-Za-z'’-]*")

# The checks of the prosody gate (srstudio.prosody, ADR 0234 c) a take's direction may waive, and the one a script may.
LINE_CHECKS = ("line_pace", "first_word", "turn_gap", "punch_gap", "answer_gap", "end_breath", "stress", "hold")
REEL_CHECKS = ("reel_pace",)
RANGED = ("line_pace", "first_word", "turn_gap", "punch_gap", "answer_gap", "end_breath", "reel_pace")
MIN_REASON_WORDS = 3
MAX_REASON = 200


class DirectionError(VoiceRequestError):
    """A direction the line or its model cannot take; refused before any request."""


@dataclass(frozen=True)
class ModelSpec:
    """What a speech model takes, as documented and measured (ADR 0234)."""

    id: str
    tags: bool  # audio tags are performed, not spoken
    breaks: bool  # ``<break time="x.xs" />`` is a pause
    context: bool  # previous_text / next_text are accepted
    capitals: bool  # capitals are documented as stress
    style: bool  # style, speed and speaker boost are in effect


MODELS = {
    "eleven_multilingual_v2": ModelSpec(
        "eleven_multilingual_v2", tags=False, breaks=True, context=True, capitals=False, style=True
    ),
    "eleven_v3": ModelSpec("eleven_v3", tags=True, breaks=False, context=False, capitals=True, style=False),
    "eleven_v4": ModelSpec("eleven_v4", tags=True, breaks=False, context=True, capitals=True, style=False),
}


def model_spec(model: str) -> ModelSpec:
    """The :class:`ModelSpec` of ``model``; a model this kit has not checked is a :class:`DirectionError`."""
    if model not in MODELS:
        raise DirectionError(f"model {model!r} is not one this kit has checked: {sorted(MODELS)}")
    return MODELS[model]


@dataclass(frozen=True)
class Pause:
    """A pause of ``seconds`` after the ``nth`` (0-based) occurrence of the word ``after`` inside the line: a break tag,
    so only on a model that takes one."""

    after: str
    seconds: float
    nth: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.after, str) or not WORD.fullmatch(self.after):
            raise DirectionError(f"a pause comes after one word, got {self.after!r}")
        if not (checks.number(self.seconds) and 0.1 <= self.seconds <= MAX_BREAK):
            raise DirectionError(f"a pause lasts 0.1 to {MAX_BREAK} s, got {self.seconds!r}")
        if isinstance(self.nth, bool) or not isinstance(self.nth, int) or self.nth < 0:
            raise DirectionError(f"nth is a non-negative integer, got {self.nth!r}")


@dataclass(frozen=True)
class Waiver:
    """A prosody target this line (or, for ``reel_pace``, this script) does not keep, and why. ``bounds`` replaces the
    target's (low, high) for a check measured against a range (seconds, or words per second); without it the check is
    off for this take. ``stress`` and ``hold`` take no bounds."""

    check: str
    reason: str
    bounds: tuple[float, float] | None = None

    def __post_init__(self) -> None:
        if self.check not in (*LINE_CHECKS, *REEL_CHECKS):
            raise DirectionError(f"waiver of {self.check!r}: the checks are {[*LINE_CHECKS, *REEL_CHECKS]}")
        if not (
            isinstance(self.reason, str)
            and len(self.reason) <= MAX_REASON
            and len(self.reason.split()) >= MIN_REASON_WORDS
        ):
            raise DirectionError(
                f"waiver of {self.check}: the reason is a sentence of at least {MIN_REASON_WORDS} words and at most "
                f"{MAX_REASON} characters, got {self.reason!r}"
            )
        if self.bounds is None:
            return
        if self.check not in RANGED:
            raise DirectionError(f"waiver of {self.check}: it has no bounds to replace; waive it without bounds")
        if not (
            isinstance(self.bounds, tuple)
            and len(self.bounds) == 2
            and all(checks.number(b) and b >= 0 for b in self.bounds)
            and self.bounds[0] <= self.bounds[1]
        ):
            raise DirectionError(
                f"waiver of {self.check}: bounds are (low, high), 0 <= low <= high, got {self.bounds!r}"
            )

    def record(self) -> dict:
        return {"check": self.check, "reason": self.reason} | (
            {"bounds": list(self.bounds)} if self.bounds is not None else {}
        )


@dataclass(frozen=True)
class Direction:
    """How one line is said, besides its words.

    ``model``: the speech model for this line (None: the voice's or the client's). ``tags``: audio tags said before
    the line, by name from :data:`AUDIO_TAGS` (``"sighs"``, ``"whispers"``) or a ``strong X accent``. ``quality``: a
    described quality as one more tag (``"quietly, holding back"``). ``emphasis``: words of the line said in capitals.
    ``pauses``: break tags inside the line. ``pre_hold`` and ``post_hold``: exact silence cut into the edit before and
    after the take, seconds. ``speed``: the pace, 0.7..1.2, on a model where it is in effect. ``takes``: how many
    takes to record, each on its own seed; ``pick``: the take kept (0-based), required once there is more than one.
    ``context``: send the neighbouring lines as previous and next text, on a model that takes them.

    Two fields change nothing in the request; the prosody gate reads them (``srstudio.prosody``). ``punchline``: this
    line is a punchline, and this word of it carries the stress (the gate wants the 1.0-1.8 s gap before it and the
    word +3 dB and +2 semitones over the rest of the line). ``waive``: the gate's targets this line does not keep,
    each with its reason."""

    model: str | None = None
    tags: tuple[str, ...] = ()
    quality: str = ""
    emphasis: tuple[str, ...] = ()
    pauses: tuple[Pause, ...] = ()
    pre_hold: float = 0.0
    post_hold: float = 0.0
    speed: float | None = None
    takes: int = 1
    pick: int | None = None
    context: bool = False
    punchline: str = ""
    waive: tuple[Waiver, ...] = ()

    def __post_init__(self) -> None:
        if self.model is not None:
            model_spec(self.model)
        for name in ("tags", "emphasis", "pauses"):
            if not isinstance(getattr(self, name), tuple):
                raise DirectionError(f"{name} is a tuple, got {type(getattr(self, name)).__name__}")
        for tag in self.tags:
            if not isinstance(tag, str) or not (tag in AUDIO_TAGS or ACCENT.fullmatch(tag)):
                raise DirectionError(
                    f"audio tag {tag!r} is not documented: use one of {sorted(AUDIO_TAGS)}, 'strong X accent', "
                    "or describe the delivery in quality="
                )
        if len(set(self.tags)) != len(self.tags):
            raise DirectionError(f"an audio tag is named twice: {self.tags}")
        if not isinstance(self.quality, str) or (
            self.quality and not (len(self.quality) <= MAX_QUALITY and QUALITY.fullmatch(self.quality))
        ):
            raise DirectionError(
                f"quality is a short lowercase description (letters, spaces, commas, at most {MAX_QUALITY} "
                f"characters), got {self.quality!r}"
            )
        for word in self.emphasis:
            if not isinstance(word, str) or not WORD.fullmatch(word):
                raise DirectionError(f"emphasis names single words of the line, got {word!r}")
        if len({w.lower() for w in self.emphasis}) != len(self.emphasis):
            raise DirectionError(f"a stressed word is named twice: {self.emphasis}")
        if len(self.pauses) > MAX_PAUSES:
            raise DirectionError(f"at most {MAX_PAUSES} pauses in a line, got {len(self.pauses)}")
        if not all(isinstance(p, Pause) for p in self.pauses):
            raise DirectionError("pauses are Pause values")
        for name in ("pre_hold", "post_hold"):
            value = getattr(self, name)
            if not (checks.number(value) and 0 <= value <= MAX_HOLD):
                raise DirectionError(f"{name} is 0 to {MAX_HOLD} s of silence, got {value!r}")
        if self.speed is not None and not (checks.number(self.speed) and 0.7 <= self.speed <= 1.2):
            raise DirectionError(f"speed must be within 0.7..1.2, got {self.speed!r}")
        if isinstance(self.takes, bool) or not isinstance(self.takes, int) or not 1 <= self.takes <= MAX_TAKES:
            raise DirectionError(f"takes is 1 to {MAX_TAKES}, got {self.takes!r}")
        if self.pick is not None and (
            isinstance(self.pick, bool) or not isinstance(self.pick, int) or not 0 <= self.pick < self.takes
        ):
            raise DirectionError(f"pick is a take of 0..{self.takes - 1}, got {self.pick!r}")
        if not isinstance(self.context, bool):
            raise DirectionError(f"context is True or False, got {self.context!r}")
        if not isinstance(self.punchline, str) or (self.punchline and not WORD.fullmatch(self.punchline)):
            raise DirectionError(f"punchline names the one word of the line that lands it, got {self.punchline!r}")
        if not isinstance(self.waive, tuple) or not all(isinstance(w, Waiver) for w in self.waive):
            raise DirectionError("waive is a tuple of Waiver values")
        named = [w.check for w in self.waive]
        if len(set(named)) != len(named):
            raise DirectionError(f"a check is waived twice: {named}")
        if set(named) & set(REEL_CHECKS):
            raise DirectionError(f"{REEL_CHECKS} are the reel's: waive them on the script, not on a line")

    @property
    def asks(self) -> bool:
        """Whether the direction changes what is requested or cut: anything but ``punchline`` and ``waive``. A take
        whose direction only marks it for the gate is sent as an undirected take, with the same cache key."""
        return replace(self, punchline="", waive=()) != Direction()

    @property
    def stressed(self) -> tuple[str, ...]:
        """The words the gate measures as stressed: the emphasis, then the punchline's word."""
        lowered = {w.lower() for w in self.emphasis}
        return self.emphasis + ((self.punchline,) if self.punchline and self.punchline.lower() not in lowered else ())

    @property
    def shapes_text(self) -> bool:
        """Whether the sent text differs from the line's words."""
        return bool(self.tags or self.quality or self.emphasis or self.pauses)

    @property
    def performed(self) -> bool:
        """Whether the line asks for a performed sound (a tag), which speech-to-text reports as an event."""
        return bool(self.tags or self.quality)

    def check_for(self, model: str) -> ModelSpec:
        """The direction fits ``model``; returns its :class:`ModelSpec`."""
        spec = model_spec(model)
        if (self.tags or self.quality) and not spec.tags:
            raise DirectionError(f"{model} speaks an audio tag aloud: tags need eleven_v3 or eleven_v4")
        if self.emphasis and not spec.capitals:
            raise DirectionError(f"{model} has no documented stress by capitals: emphasis needs eleven_v3 or eleven_v4")
        if self.pauses and not spec.breaks:
            raise DirectionError(
                f"{model} takes no break tag: cut the line into two takes with post_hold/pre_hold, or write an "
                "ellipsis for a hesitation"
            )
        if self.context and not spec.context:
            raise DirectionError(f"{model} refuses previous and next text (HTTP 400): context needs another model")
        if self.speed is not None and self.speed != 1.0 and not spec.style:
            raise DirectionError(f"{model} ignores speed: pace the line with holds and punctuation")
        return spec


def seeds(base: int, takes: int) -> tuple[int, ...]:
    """The seed of each take: the first is ``base``, so a one-take line is the request it always was."""
    return tuple((base + k) % 2**32 for k in range(takes))


@dataclass(frozen=True)
class Rendered:
    """The text sent to the provider and, per sent character, the index of the line's letter it says (None: a tag,
    a break or a space the direction added)."""

    line: str
    text: str
    source: tuple[int | None, ...]

    def __post_init__(self) -> None:
        if len(self.source) != len(self.text):
            raise DirectionError("a rendered line maps every sent character")


def _word_spans(text: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in WORD.finditer(text)]


def render(line: str, direction: Direction | None, model: str) -> Rendered:
    """The text ``model`` is sent for ``line`` under ``direction``, and where each sent letter comes from in ``line``.

    Tags go first, as ``[tag] `` each; a stressed word is written in capitals wherever it is in the line; a pause is a
    ``<break time="x.xs" />`` after its word. A stressed word or a pause's word the line does not have is a
    :class:`DirectionError`."""
    if not isinstance(line, str) or not line.strip():
        raise DirectionError("a directed line needs words")
    if "[" in line or "]" in line or "<" in line or ">" in line:
        raise DirectionError(f"the line's words carry no tags or markup; direct them in Direction: {line!r}")
    if direction is None:
        return Rendered(line, line, tuple(range(len(line))))
    direction.check_for(model)
    spans = _word_spans(line)
    lowered = [w.lower() for _, _, w in spans]
    for word in direction.emphasis:
        if word.lower() not in lowered:
            raise DirectionError(f"stressed word {word!r} is not in the line {line!r}")
    stressed = {w.lower() for w in direction.emphasis}
    breaks: dict[int, float] = {}  # end index of a word in the line -> seconds
    for pause in direction.pauses:
        hits = [end for _, end, w in spans if w.lower() == pause.after.lower()]
        if len(hits) <= pause.nth:
            raise DirectionError(f"a pause after {pause.after!r} (occurrence {pause.nth}) has no such word in {line!r}")
        end = hits[pause.nth]
        if end in breaks:
            raise DirectionError(f"two pauses after the same word {pause.after!r}")
        breaks[end] = pause.seconds
    upper = {i for start, end, w in spans if w.lower() in stressed for i in range(start, end)}
    text: list[str] = []
    source: list[int | None] = []

    def added(s: str) -> None:
        text.append(s)
        source.extend([None] * len(s))

    for tag in (*direction.tags, *((direction.quality,) if direction.quality else ())):
        added(f"[{tag}] ")
    for i, c in enumerate(line):
        if i in breaks:
            added(f' <break time="{breaks[i]:.1f}s" />')
        text.append(c.upper() if i in upper else c)
        source.append(i)
    if len(line) in breaks:
        added(f' <break time="{breaks[len(line)]:.1f}s" />')
    return Rendered(line, "".join(text), tuple(source))


def spoken(alignment: Alignment, rendered: Rendered) -> Alignment:
    """The provider's ``alignment`` of the sent text taken back to the line's own letters: it must spell the sent text
    exactly (else :class:`~srstudio.voice.VoiceOutputError`); the letters a tag or break added are dropped, a capital
    written for stress is the line's letter again, and every kept letter keeps its time."""
    if alignment.text != rendered.text:
        raise VoiceOutputError(f"aligned text {alignment.text!r} does not match the requested {rendered.text!r}")
    kept = [(rendered.line[j], a, b) for j, a, b in zip(rendered.source, alignment.starts, alignment.ends, strict=True)
            if j is not None]  # fmt: skip
    out = Alignment(tuple(c for c, _, _ in kept), tuple(a for _, a, _ in kept), tuple(b for _, _, b in kept))
    if out.text != rendered.line:
        raise VoiceOutputError(f"the spoken letters {out.text!r} do not spell the line {rendered.line!r}")
    return out

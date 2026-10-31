"""What every real roast of News Compiler shares, so that a reel's data file holds only its own story.

A :class:`Story` carries the words over the picture: the outlet's card, the ticker, the lower-thirds and the post. It
checks them against the show's rules, and it lays them over the reel on version 2 of the kit. The card is up from the
first frame and goes small on ``small``, a beat index, and stays to the last frame, so the source is never off screen.
A lower-third is a text, so it stops while a phone is up (``inserts``) rather than sit half-hidden behind one.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from srstudio import news_inked, news_kit, scripting, sketch
from srstudio.news_kit import Act, Source
from srstudio.sketch import Sketch
from srstudio.social import InstagramPost

COVER_HIDES = ("news-ticker", "news-lower-", "news-source-card", "news-bug")
Span = tuple[float, float]
Lower = tuple[int, str, str]  # the beat it arrives on, its kicker, its one line


def clipped(start: float, end: float, inserts: Sequence[Span]) -> list[Span]:
    """What is left of ``start``..``end`` once the phone's windows are taken out of it."""
    left, at = [], start
    for a, b in sorted(inserts):
        if a > at:
            left.append((at, min(a, end)))
        at = max(at, b)
    if at < end:
        left.append((at, end))
    return [(a, b) for a, b in left if b > a]


def hide_on_cover(episode) -> None:
    """Keep the show's graphics off the cover's backdrop: its headline replaces them, and a ghost of them under it reads
    as a mistake."""
    hidden = [g for g in episode.comp.find_all("group") if str(g.id).startswith(COVER_HIDES)]
    if hidden:
        episode.hide_on_cover(*hidden)


@dataclass(frozen=True)
class Story:
    """The words of one real roast over its picture."""

    source: Source
    ticker: tuple[str, ...]
    lowers: tuple[Lower, ...]
    acts: tuple[Act, ...]
    events: tuple[str, ...]
    post: InstagramPost
    small: int = 2

    def validate(self, sk: Sketch, shown: Sequence[str] = ()) -> None:
        """The sketch is consistent, its events happen once and in order, the first picture speaks, the acts match the
        beats, and no word the reel shows, ``shown`` included, is one the show keeps off it."""
        sketch.check(sk)
        if len(self.acts) != len(sk.beats):
            raise sketch.SketchError(f"{len(self.acts)} acts for {len(sk.beats)} beats")
        for event in self.events:
            scripting.exactly_once(sk.beats, event, f"{event} happens once")
        scripting.only_events(sk.beats, set(self.events))
        if sk.beats[0].line is None or sk.beats[0].event != "card":
            raise sketch.SketchError("the reel opens on the anchor's line, with the card up")
        if not all(index < len(sk.beats) for index, _, _ in self.lowers) or self.small >= len(sk.beats):
            raise sketch.SketchError("a lower-third or the card points past the last beat")
        if any(index < self.small for index, _, _ in self.lowers):
            raise sketch.SketchError("a lower-third would sit behind the large card")
        words = (
            *(q.text for q in sk.lines),
            *self.ticker,
            *(w for row in self.lowers for w in row[1:]),
            self.post.title,
            self.post.description,
            *shown,
        )
        for text in words:
            news_kit.check_copy(text)

    def spans(self, beats, end: float, inserts: Sequence[Span] = ()) -> list[tuple[float, float, str, str]]:
        """The lower-thirds on a clock: each from its beat to the next one, the last to the end, none over a phone."""
        starts = [beats[index].start for index, _, _ in self.lowers]
        return [
            (a, b, kicker, line)
            for start, stop, (_, kicker, line) in zip(starts, [*starts[1:], end], self.lowers, strict=True)
            for a, b in clipped(start, stop, inserts)
        ]

    def overlay(
        self, cv, parent, beats, end, measure, inserts: Sequence[Span] = (), phone: Callable[[], None] | None = None
    ) -> None:
        """Everything over the picture. ``phone`` draws the inserts, which dim the room, so the show's name and the
        source go on after them and stay as bright as on any other frame."""
        news_inked.sign(cv, parent)
        card = sketch.events(beats, "card")[0][0]
        news_inked.ticker(cv, parent, self.ticker, card + news_kit.SLIDE, end, measure)  # the card rises first
        last = ""
        for number, (a, b, kicker, line) in enumerate(self.spans(beats, end, inserts)):
            slide = line != last  # the same story stays up
            news_inked.lower_third(cv, parent, kicker, line, a, b, measure, id=f"news-lower-{number}", slide=slide)
            last = line
        if phone is not None:
            phone()
        news_inked.bug(cv, parent, 0.0, end, measure)
        news_inked.source_card(cv, parent, self.source, card, beats[self.small].start, end, measure)

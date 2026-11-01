"""Each registered part alone, rendered by the engine for the catalog's cards (ADR 0051).

A gallery still is a crop of a reel, so five objects of one café all show that café. A specimen is one part drawn by
its real builder through the real engine on a plain background, framed so the part fills the image: a character in
the first pose of its :data:`srstudio.specimens.SPECIMENS` drawing, a location as the empty set with its own stage
colour, a prop or graphic as the single object.

Characters are drawn only by :mod:`srstudio.specimens`, which owns their one recipe and their digest; this module
holds the recipes of the locations, props and graphics that need data of their own, in :data:`RECIPES`; a part that
needs only a place and a clock draws itself (:func:`auto`), so it shows with no entry. A part that cannot honestly
stand alone is in :data:`REFUSED` with a typed :class:`Reason`, so it has no image and says why. It never gets a scene
still in its place, and a registered part in neither table stops the build (:func:`plan`).

A framed part takes two renders: the first, at half scale with room around the frame, finds what the part covers
(:func:`bounds`); the second scales the composition so that fills a square, and ``ffmpeg`` crops and resizes it. Files
are named by the digest of the drawing (:func:`key`), so a part that did not change is not rendered again.
"""

from __future__ import annotations

import hashlib
import inspect
import os
import re
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sr_core.scene import Scene

from . import (
    cel,
    collage_group,
    gloss_sets,
    host_kit,
    ink_meter,
    ink_phone,
    map_kit,
    mind_kit,
    news_inked,
    news_kit,
    parts,
    plates,
    rafa,
    rafa_host,
    registry,
    saga_sets,
    soft_props,
    specimens,
    stick,
    stick_shop,
    toon,
    toon_everyday,
    toon_props,
)
from .canvas import Canvas, Signature
from .errors import SrstudioError
from .fonts import text_width
from .parts import Reason, Refused
from .styles import CUTOUT, STYLES, Style
from .timeline import Take

SIZE = 480  # the side of a framed specimen, and the width of a set
BACKGROUND = "#E7E4DD"  # warm grey: no style's ink, paper or stage colour
MARGIN = 0.06  # of the side, left clear around a framed part
SECONDS = 4.0  # the clock a recipe's drawing runs on
THRESHOLD = 10  # a pixel this far from the background, on any channel, is drawn
BLANK = 16  # a part with fewer drawn pixels than this, in the half-scale render, drew nothing
WORKERS = 4
POSTER_WIDTH = 540  # as wide as a card's web video
POSTER_AT = 0.35  # of the film's length: past the hook, inside the sketch
FRAMING = "1"  # part of every key: raise it when the framing changes what comes out
TEAM, MUSHROOM = "check-with-my-team", "mushroom-training"  # the projects that hold traced data a part needs


_VERSION = re.compile(r"(\d+)\.(\d+)\.(\d+)")


class SpecimenRenderError(SrstudioError):
    """A part with no recipe and no refusal, a recipe that drew nothing, or a render that failed."""


@dataclass(frozen=True)
class Context:
    """What a recipe may need besides the canvas."""

    font: bytes  # the style's font
    episodes: Path  # where the projects are, for the parts drawn from a project's traced data
    work: Path  # the folder the document renders in, for the files a part reads beside it

    def assets(self, project: str) -> Path:
        folder = self.episodes / project / "assets"
        if not folder.is_dir():
            raise SpecimenRenderError(f"{folder} is missing, and a specimen is drawn from its traced data")
        return folder

    def measure(self, text: str, size: float) -> float:
        return text_width(self.font, text, size)


Draw = Callable[[Canvas, Any, registry.Entry, Context], object]


@dataclass(frozen=True)
class Recipe:
    draw: Draw
    at: float = 1.0  # the second shown


@dataclass(frozen=True)
class Specimen:
    """A rendered part."""

    name: str
    png: Path
    width: int
    height: int


@dataclass(frozen=True)
class Shelf:
    """What a build has: every drawn part, every refusal, and how many drawings had to be rendered."""

    done: dict[str, Specimen]
    refused: dict[str, Refused]
    made: int


@dataclass(frozen=True)
class Plan:
    entry: registry.Entry
    document: bytes
    at: float
    key: str
    set: bool  # a location: the whole frame on its own stage colour, not framed


FILLED = {
    "x": 540,
    "y": 960,
    "end": SECONDS,
    "at": (540, 1000),
}  # the arguments a builder may need and any part can take


def auto(entry: registry.Entry) -> Recipe | None:
    """The recipe of a part that needs nothing but a place and a clock, so a new one shows with no entry here; ``None``
    when it needs data of its own."""
    needed = [
        p.name
        for p in list(inspect.signature(entry.builder).parameters.values())[2:]
        if p.default is p.empty and p.kind not in (p.VAR_KEYWORD, p.VAR_POSITIONAL)
    ]
    if not set(needed) <= set(FILLED):
        return None
    filled = {name: FILLED[name] for name in needed}
    return Recipe(lambda cv, g, e, ctx: e(cv, g, **filled))


_ROME = map_kit.Place("Rome", 41.89193, 12.51133)
_SPIN = ((0.0, -30.0), (SECONDS, -10.0))
_HOT = {"inside": map_kit.PIN}


def _maps(ctx: Context) -> bool:
    """Put the layers a map part reads beside its document."""
    map_kit.install(ctx.work)
    return True


def _on_flat(cv: Canvas, parent: Any, ctx: Context) -> Any:
    _maps(ctx)
    return map_kit.flat(cv, parent, 12.0, 42.0, 2.5, 0.0, SECONDS)


def _on_area(cv: Canvas, parent: Any, ctx: Context) -> Any:
    _maps(ctx)
    return map_kit.equal_area(cv, parent, 99.0, 21.0, 1.6, 0.0, SECONDS)


def part(*args, **kwargs) -> Draw:
    """A recipe that calls the builder with these arguments."""

    def draw(cv, g, e, ctx):
        return e(cv, g, *args, **kwargs)

    return draw


def lettered(*args, **kwargs) -> Draw:
    """A recipe whose builder measures its text in the style's font."""

    def draw(cv, g, e, ctx):
        return e(cv, g, *args, measure=ctx.measure, **kwargs)

    return draw


def typeset(*args, **kwargs) -> Draw:
    """A recipe whose builder wraps its text in the font's own bytes, on the recipe clock."""

    def draw(cv, g, e, ctx):
        return e(cv, g, *args, end=SECONDS, font=ctx.font, **kwargs)

    return draw


def _yard(cv, g, e, ctx):
    return e(cv, g, stick.load_plates(ctx.assets(TEAM) / "foliage.json"), 7)


def _cel_room(cv, g, e, ctx):
    assets = ctx.assets(MUSHROOM)
    camera, room = cel.load_camera(assets / "camera.json"), cel.load_camera(assets / "room-camera.json")
    return e(cv, g, camera, room, max(k.time for k in (*camera, *room)))


def _hook(cv, g, e, ctx):
    return e(cv, g, stick.load_lettering(ctx.assets(TEAM) / "lettering.json", ("hook",))["hook"], 0.0, SECONDS)


def _headline(cv, g, e, ctx):
    letters = stick.load_lettering(ctx.assets(TEAM) / "lettering.json", ("team_outline", "team_fill"))
    return e(cv, g, letters["team_outline"], letters["team_fill"], 0.0, SECONDS)


SHOW = (0.0, SECONDS)
BUBBLES = (ink_phone.Bubble("On my way."), ink_phone.Bubble("Agreed.", mine=False))
TAKE = Take("01", "speaker", "shot", "Hello.", 0.0, SECONDS)
PHONE_SCREENS = (toon_everyday.Screen(0.0, "notify", title="Mom", text="Are you eating?"),)


def _punched(cv: Canvas, g: object, e: registry.Entry, ctx: Context) -> None:
    shot = cv.group(g, cv.uid("g"))
    host_kit.lint(cv, shot, end=SECONDS)
    e(cv, shot, "close", SECONDS / 2, "lint")


def _plated(cv: Canvas, g: object, e: registry.Entry, ctx: Context) -> None:
    """A part that is one path-traced plate, on the stage (ADR 0068)."""
    plate = rafa_host.part_plates(e.name)[0]
    rafa_host.place(cv, g, plate, y=(rafa_host.HEIGHT - plate.height) / 2)


RECIPES: dict[str, Recipe] = {
    **dict.fromkeys((*rafa.ROOMS, *rafa.PROPS), Recipe(_plated)),
    # -- locations -------------------------------------------------------------------------------------------------
    "cel-room": Recipe(_cel_room),
    "stick-yard": Recipe(_yard),
    "stick-car": Recipe(part(SECONDS)),
    "stick-gym": Recipe(part(SECONDS)),
    "stick-windshield": Recipe(part(SECONDS)),
    "stick-entrance": Recipe(part(SECONDS)),
    "stick-street-lens": Recipe(part(SECONDS)),
    "stick-coffee-corner": Recipe(part()),
    "stick-home-street": Recipe(part()),
    "stick-road-plan": Recipe(part(scars=2)),
    "stick-road-ahead": Recipe(part()),
    "stick-kitchen": Recipe(part()),
    "stick-kitchen-plan": Recipe(part()),
    "ink-phone-shot": Recipe(part("Boss", BUBBLES)),
    "toon-lower-third": Recipe(lettered(((0.0, SECONDS, "UPDATE: SOMEONE IS 'HOME'"),))),
    # -- props ---------------------------------------------------------------------------------------------------
    "building": Recipe(part(300, 600, 480, 760)),
    "crumbs": Recipe(part(500, 900, 1100, toss=0.2, count=9)),
    "whiteboard": Recipe(part(300, 600, 480, 420, rising=False)),
    "blinds-window": Recipe(part(300, 600, 480, 420)),
    "slat-wall": Recipe(part(200, 500, 680, 700)),
    "reception-counter": Recipe(part(200, 880, 800, 1200)),
    "card-reader": Recipe(part(540, 960, readings=((0.0, "$3.00", "one coffee"),))),
    "pink-slip": Recipe(part(540, 960, name="ERIC")),
    "collage-phone-timer": Recipe(part(540, 960, start=0.0)),
    "collage-viewfinder": Recipe(part(start=0.0)),
    "collage-photo-print": Recipe(part(
        {"gary": collage_group.Place(230, 1800, 0.55), "kai": collage_group.Place(850, 1800, 0.5),
         "rosa": collage_group.Place(540, 1800, 0.58)},
        {"gary": ("wide", "o", "shrug"), "kai": ("closed", "grin", "face"), "rosa": ("closed", "grin", "hold")},
        x=90, y=600, width=900)),
    "collage-sign": Recipe(part("BOWLHEADS", 300, 800, 480, 160, size=64)),
    "collage-chart": Recipe(part(300, 700, 480, 360, (0.2, 0.5, 1.0))),
    "collage-food": Recipe(part("taco", 540, 960, 400)),
    "collage-phone": Recipe(part(380, 680, 320, 560)),
    "collage-bubble": Recipe(part("Dear Son.", 240, 860, 600, 200, size=64)),
    "collage-alarm-clock": Recipe(part(300, 840, 480, "11:40")),
    "collage-cereal-box": Recipe(part(370, 720, 340, 480)),
    "collage-duvet": Recipe(part()),
    "collage-tablecloth": Recipe(part()),
    "collage-salt-shaker": Recipe(part(540, 1080, 320)),
    "collage-thumb": Recipe(part(540, 1080, 420)),
    "collage-chip-bag": Recipe(part(540, 960, 460, 620, "FAMILY SIZE")),
    "collage-chip": Recipe(part(540, 960)),
    "collage-certificate": Recipe(part("AUTHENTIC", 260, 760, 560, 400, size=64)),
    "collage-snapshot": Recipe(part(360, 760, 360)),
    "collage-gust": Recipe(part((200, 1200), (800, 700), 0.0, SECONDS)),
    "collage-bill": Recipe(part("RENT", 540, 960)),
    "collage-handset": Recipe(part(540, 960)),
    "collage-desk-phone": Recipe(part(540, 1300, 460, "PARIS", size=56)),
    "collage-resume": Recipe(part(540, 960, 520)),
    "collage-fork": Recipe(part(540, 960, tilt=20.0)),
    "collage-gravy-boat": Recipe(part(540, 1200, 460)),
    "collage-tiny-cup": Recipe(part(540, 1100, 200)),
    "collage-wine-glass": Recipe(part(540, 1200, 420)),
    "collage-bank-card": Recipe(part(540, 960, 520, "GARY")),
    "collage-receipt": Recipe(part(540, 960, torn=True)),
    "collage-wallet": Recipe(part(540, 960)),
    "collage-counter": Recipe(part(1300)),
    "collage-till": Recipe(part(540, 1200, 420, "PAID", size=64)),
    "collage-stool": Recipe(part(540, 1000, 480)),
    "collage-towel": Recipe(part(540, 700)),
    "collage-ring-corner": Recipe(part()),
    "collage-eye-twitch": Recipe(part("brent", (0.2, 0.8))),
    "collage-confetti": Recipe(part(0.0, SECONDS)),
    "collage-arm": Recipe(part("deb", (760, 1500), (420, 900))),
    "collage-tv": Recipe(part(300, 700, 480)),
    "gloss-board": Recipe(typeset((gloss_sets.Card(0.0, "Joy Points", "Keep smiling."),))),
    "gloss-ticket": Recipe(part(at=(540, 1000), end=SECONDS, number="47")),
    "ink-hand": Recipe(part(540, 960, action="reach", at=0.5)),
    "ink-captcha": Recipe(part(
        prompt="Select all images with traffic lights.",
        tiles=("light", "car", "light", "tree", "light", "car", "tree", "car", "light"))),
    "ink-checkbox": Recipe(part("I'm not a robot")),
    "ink-phone": Recipe(part("Boss", BUBBLES)),
    "saga-holo": Recipe(typeset((saga_sets.Panel(0.0, "Ship's Log", "All systems nominal."),))),
    "soft-cake": Recipe(part("WE'LL MISS\nYOU", x=540, y=1000)),
    "soft-cane": Recipe(part(540, 1200)),
    "soft-parcels": Recipe(part(120, 1500)),
    "soft-whisk": Recipe(part(540, 1100, scale=4)),
    "soft-glare-lamp": Recipe(part(540, 1400)),
    "soft-briefcase": Recipe(part(540, 900)),
    "soft-hive": Recipe(part(540, 1200)),
    "soft-necktie": Recipe(part(540, 900)),
    "soft-shovel": Recipe(part(540, 960)),
    "soft-time-card": Recipe(part((soft_props.TimeState("2031", 0.0, SECONDS),), (380, 800, 320, 118))),
    "stick-cockpit": Recipe(part((stick.RigKey(0, "drive"),), SECONDS)),
    "stick-laptop": Recipe(part(540, 960, title="Sent", rows=("Re: budget", "Re: lunch"), badge="40")),
    "stick-phone": Recipe(part(sender="Boss", text="One more thing...")),
    "stick-bag-scale": Recipe(part(540, 1500, ((0.0, "23.4"), (2.0, "22.9")), SECONDS)),
    "stick-coat-ball": Recipe(part(540, 700, 320, layers=4, hats=3, scarves=3, trousers=True, shoes=True)),
    "stick-palm": Recipe(part(540, 1500)),
    "stick-bedroom": Recipe(part()),
    "stick-message-insert": Recipe(part(sender="MOM", text="We need to talk.")),
    "stick-chair": Recipe(part(540, 1500)),
    "stick-smoke-alarm": Recipe(part(540, 960, scale=2.0)),
    "stick-mound": Recipe(part(540, 1300, words="ALL 5")),
    "stick-shovel": Recipe(part(540, 1300)),
    "stick-murphy-bed": Recipe(part(SECONDS)),
    "stick-gym-counter": Recipe(part(sign="NO REFUNDS*", fine="*EVER")),
    "stick-kiosk": Recipe(part((stick_shop.Screen(0.0, "Place item in the bagging area"),), SECONDS)),
    "stick-name-badge": Recipe(part(540, 960, "DEV", "Employee of the month")),
    "stick-windshield-dash": Recipe(part(SECONDS)),
    "stick-glass-door": Recipe(part(SECONDS)),
    "stick-snow-cap": Recipe(part(540, 960, 2)),
    "stick-marathon": Recipe(part(SECONDS)),
    "stick-coffee-counter": Recipe(part()),
    "stick-side-car": Recipe(part()),
    "stick-suitcases": Recipe(part(540, 960)),
    "stick-top-car": Recipe(part()),
    "stick-stove-knob": Recipe(part()),
    "stick-door-lock": Recipe(part()),
    "stick-road-sign": Recipe(part(SECONDS, text="AIRPORT 2")),
    "stick-mug": Recipe(part(540, 960)),
    "stick-arm-cast": Recipe(part((480, 800), (640, 1000))),
    "stick-neck-brace": Recipe(part(540, 960)),
    "stick-parrot": Recipe(part(540, 960)),
    "stick-flames": Recipe(part(540, 960, SECONDS)),
    "stick-tombstone": Recipe(part(540, words="GOOD.")),
    "stick-meteor": Recipe(part(SECONDS, land=SECONDS / 2)),
    "stick-table": Recipe(part()),
    "stick-from-above": Recipe(part(SECONDS, hair="bun", phone="#e8558f")),
    "stick-fridge-open": Recipe(part()),
    "stick-safe-open": Recipe(part()),
    "stick-handset": Recipe(part(540, 960)),
    "stick-key": Recipe(part(540, 960, scale=3.0)),
    "stick-reply-screen": Recipe(part(name="Him", sent="just saying", answer="who is this")),
    "toon-dishes": Recipe(part((("salad", 380), ("water", 470), ("check", 540)))),
    "toon-card-reader": Recipe(part(((0.0, "TAP CARD", "idle"),))),
    "toon-phone": Recipe(lettered(PHONE_SCREENS)),
    "toon-speaker": Recipe(part(((0.0, "listen"),), SECONDS)),
    "mind-name-card": Recipe(lettered("A Long Name", 0.0, 0.2, SECONDS)),
    "mind-evidence-card": Recipe(
        lettered(
            mind_kit.Evidence("Lee & Ray", "2001", "Students wore a loud hat.", "Fewer saw it than guessed."),
            0.0,
            SECONDS,
        )
    ),
    "mind-captions": Recipe(
        lambda cv, g, e, ctx: e(cv, g, (toon.Line("1", "A caption.", 0.0, SECONDS, "narrator"),), ctx.measure, {})
    ),
    "mind-spotlight": Recipe(part((540.0, 1400.0), 0.0, SECONDS)),
    "mind-memory-shelf": Recipe(lettered(("One", "Two", "Three"))),
    "mind-two-lines": Recipe(lettered(("Guessed", 0.5, ""), ("Happened", 0.25, ""), 0.0, SECONDS)),
    "mind-lens": Recipe(part((540.0, 900.0), 0.0, SECONDS)),
    "map-globe": Recipe(lambda cv, g, e, ctx: e(cv, g, -20.0, 30.0, 0.0, SECONDS, spin=_SPIN) if _maps(ctx) else None),
    "map-flat": Recipe(lambda cv, g, e, ctx: e(cv, g, -30.0, 45.0, 1.6, 0.0, SECONDS) if _maps(ctx) else None),
    "map-equal-area": Recipe(lambda cv, g, e, ctx: e(cv, g, 99.0, 21.0, 1.6, 0.0, SECONDS) if _maps(ctx) else None),
    "map-pin": Recipe(
        lambda cv, g, e, ctx: e(cv, g, _on_flat(cv, g, ctx), _ROME, 0.0, SECONDS, ctx.measure)
    ),
    "map-parallel": Recipe(
        lambda cv, g, e, ctx: e(cv, g, _on_flat(cv, g, ctx), _ROME, 0.0, SECONDS, tag_from=0.0, measure=ctx.measure)
    ),
    "map-population": Recipe(
        lambda cv, g, e, ctx: e(cv, _on_area(cv, g, ctx), {"inside": (0.0, 0.5), "rest": (0.0, 0.5)}, _HOT)
    ),
    "map-ring": Recipe(part(map_kit.ring_px(3300.0, 1.6), 0.0, SECONDS)),
    "map-stamp": Recipe(lettered("A line of evidence. Source, 2026.", 0.0, SECONDS)),
    "map-captions": Recipe(
        lambda cv, g, e, ctx: e(cv, g, (toon.Line("1", "A caption.", 0.0, SECONDS, "narrator"),), ctx.measure, {})
    ),
    "news-captions": Recipe(
        lambda cv, g, e, ctx: e(cv, g, (toon.Line("1", "A caption.", 0.0, SECONDS, "vera"),), ctx.measure, {})
    ),
    "news-bug": Recipe(lettered(0.0, SECONDS)),
    "news-parody-tag": Recipe(lettered(0.0, SECONDS)),
    "news-source-card": Recipe(
        lettered(news_kit.Source("The Outlet", "Oct 30, 2026", "A headline, word for word"), 0.0, 1.8, SECONDS)
    ),
    "news-lower-third": Recipe(lettered("THE KICKER", "ONE LINE OF THE STORY", 0.0, SECONDS)),
    "news-missing-card": Recipe(lettered("ONE LID", 0.0, SECONDS)),
    "news-live-door": Recipe(lettered("KITCHEN", 0.0, SECONDS, shut=SECONDS / 2)),
    "news-money-app": Recipe(
        lettered("MY MONEY", "$11.00", "WITHDRAW", "SUSPENDED", 0.0, SECONDS, refused_at=SECONDS / 2)
    ),
    "news-oven-clock": Recipe(
        lettered("MY OVEN", "7:42", "1 HOUR OFF", "CORRECT", 0.0, SECONDS, right_at=SECONDS / 2)
    ),
    "news-banner": Recipe(lettered(0.0, SECONDS)),
    "news-ticker": Recipe(lettered(("ONE ITEM", "ANOTHER ITEM"), 0.0, SECONDS)),
    "news-phone": Recipe(lettered("The Chat", (news_kit.Bubble("7:15", "five minutes away"),), 0.0, SECONDS)),
    "news-route": Recipe(
        lettered(
            "The Map",
            ((80.0, 560.0), (300.0, 340.0), (560.0, 120.0)),
            (news_inked.Pin(560.0, 120.0, "HOME", news_kit.MINT),),
            0.0,
            SECONDS,
        )
    ),
    "host-label": Recipe(lettered("THE GROUP CHAT HAS RULES", 0.0, SECONDS)),
    "host-sign-off": Recipe(lettered("You know what you did.", 0.0, SECONDS)),
    "host-screen": Recipe(lettered("The Group Chat", (host_kit.Bubble("haha"),), 0.0, SECONDS)),
    "host-punch": Recipe(_punched),
    "toon-tee": Recipe(part((180, 660))),
    "toon-bow-tie": Recipe(part((180, 640))),
    "toon-stars": Recipe(part(5)),
    "toon-shower-water": Recipe(part(((0.0, SECONDS),))),
    "toon-suds": Recipe(part((540, 700))),
    "toon-towel": Recipe(part((540, 700))),
    "toon-open-book": Recipe(part({0: "#ffe14d", 1: "#ffe14d", 9: "#ff9ec4"})),
    "toon-shut-book": Recipe(part()),
    "toon-highlighter": Recipe(part((540.0, 960.0), "#c49a6c")),
    "toon-study-page": Recipe(
        lettered("Chapter 4", {0: "#ffe14d", 1: "#ff9ec4"}, (("#ffe14d", "important"), ("#ff9ec4", "very important")))
    ),
    "toon-quiz-sheet": Recipe(lettered(("What kind of", "learner?"), "Mostly A's:", "VISUAL")),
    "toon-receipt": Recipe(lettered((("Coffee", "3.00"), ("Cup fee", "0.75")), total=("TOTAL", "3.75"))),
    "toon-take-a-number": Recipe(lettered(((0.0, 47),))),
    "toon-clipboard": Recipe(
        lettered("Form 7", (toon_everyday.Field("Name", "Rex"), toon_everyday.Field("Date", "Today")))),
    "toon-key-line": Recipe(lettered("Say what you mean.", 0.0, SECONDS)),
    "toon-thermostat": Recipe(part(((0.0, "68"),))),
    "toon-day-card": Recipe(part(((0.0, 41),))),
    "toon-sink": Recipe(part(((0.0, "skin"), (0.1, "plant"), (0.2, "mail"), (0.3, "frog")))),
    "toon-bib-insert": Recipe(part(0.0, SECONDS)),
    "toon-clock": Recipe(part(((0.0, "09:00"),))),
    "toon-notes": Recipe(part(("REPORT!", "9 AM", "DO NOT", "FORGET"))),
    "toon-note-insert": Recipe(part("IT MOVED.", 0.0, SECONDS)),
    "toon-calendar": Recipe(part(((0.0, "OCT 27"),))),
    "toon-whirl": Recipe(part(), at=0.35),  # it is gone by 0.7 s
    "toon-sparkles": Recipe(part(), at=0.25),  # each glint twinkles for half a second
    "hair-fall": Recipe(part(), at=0.3),  # the sheet has crossed the frame by 0.6 s
    "water-splash": Recipe(part(), at=0.2),  # every bead has fallen back by 0.48 s
    # -- graphics -------------------------------------------------------------------------------------------------
    "signature-code": Recipe(part(540, 960, height=40)),
    "episode-slate": Recipe(part("08", "CAMERA OFF"), at=0.4),  # it fades out by one second
    "quiz-card": Recipe(part("QUICK MATH", "17 × 19 = ?", SHOW)),
    "answer-bubble": Recipe(part("42", SHOW)),
    "scorecard": Recipe(part("SCORE", (("SPEED", "10 / 10", "#AAD6BD"),), SHOW)),
    "dashboard": Recipe(part("MULTITASKING: ACTIVE", (("TABS", "47"), ("MEETINGS", "3")), SHOW)),
    "notification": Recipe(part(1, "BOSS", "Typing…", SHOW, x=300, y=800)),
    "password-card": Recipe(part("WI-FI", "secret", "NO SPACES", SHOW)),
    "location-slate": Recipe(part("LATER", SHOW)),
    "connected-card": Recipe(part("CONNECTED", "hunter2", SHOW)),
    "squeak-mark": Recipe(part("SQUEAK!", SHOW, x=540, y=960)),
    "gloss-hook": Recipe(typeset("What is really in the Joy Points?")),
    "gloss-notice": Recipe(typeset("Plaza Notice", "Smiling is mandatory.")),
    "ink-doorbell-view": Recipe(part(TAKE, tags=((0.0, "UNKNOWN"),))),
    "ink-app-screen": Recipe(part(
        TAKE, title="ParkPal", rows=(ink_meter.AppRow("A capital", 0.0), ink_meter.AppRow("A symbol", 0.0)))),
    "ink-floor-map": Recipe(part(TAKE)),
    "saga-hook": Recipe(typeset("Who approved the moon?")),
    "saga-entry": Recipe(typeset("The Handbook", "See page nine.")),
    "soft-status-badge": Recipe(part(
        (soft_props.BadgeState("a", "RELAX 15 MIN", "#2f7d57", 0.0, SECONDS),), (300, 800, 480, 92))),
    "soft-beach-call": Recipe(part(860, 500, name="BO · CEO")),
    "stick-card": Recipe(part("When the call runs over")),
    "stick-hook": Recipe(_hook),
    "stick-headline": Recipe(_headline),
    "stick-call": Recipe(part(
        (stick.Tile("Boss", stick.Look(hair="bald", glasses=True)), stick.Tile("Dev", stick.Look())),
        (stick.Mail("HR", "Re: Dev — concerns", unread=True), stick.Mail("IT", "Your password expires")),
        speaking="Boss")),
    "stick-essay": Recipe(part(
        ("My dad works from home.", "He wears a tie on top."), title="My Dad", by="Sam", shown=2)),
    "toon-toast": Recipe(part((toon_props.Toast(0.0, SECONDS, "Fern", "Are you free?"),))),
    "toon-board-text": Recipe(part("LOGO v1")),
    "toon-scribble": Recipe(part(((0.0, SECONDS),))),
    "toon-soup-tubs": Recipe(part(((0.0, 3),), end=SECONDS)),
    "toon-badge": Recipe(part("Fern calling", 0.0, SECONDS, lambda text: 16.0 * len(text))),
}  # fmt: skip
RECIPES.update(  # a kit's second version takes the same arguments, so it takes the same recipe
    {
        f"{name}@2": RECIPES[name]
        for name in (
            "news-captions",
            "news-bug",
            "news-parody-tag",
            "news-source-card",
            "news-lower-third",
            "news-banner",
            "news-ticker",
            "news-phone",
        )
    }
)

FIRST_POSE = Recipe(lambda cv, g, e, ctx: None, at=0.0)  # a character's drawing is srstudio.specimens' alone
REFUSED: dict[str, Refused] = {
    "captions": Refused(Reason.OVERLAY, "burned captions: lines of text timed over a shot"),
    "stick-captions": Refused(Reason.OVERLAY, "the Stick caption layer: lines of text timed over a shot"),
    "stick-words": Refused(Reason.OVERLAY, "word-by-word captions over a scrim that dims the shot under it"),
    "host-captions": Refused(Reason.OVERLAY, "the engine's caption track and its bands, timed over a shot"),
    "toon-captions": Refused(Reason.OVERLAY, "the white caption pills, timed over a shot"),
    "cel-lettering": Refused(Reason.OVERLAY, "one caption's lettering boxes, traced to sit over a Cel shot"),
    "woodgrain": Refused(Reason.OVERLAY, "faint grain strokes laid over a wood fill: too pale to see on their own"),
    "collage-flash": Refused(Reason.OVERLAY, "a white camera flash that covers the frame and fades"),
    "stick-ride": Refused(Reason.MOTION, "the bob of a car ride, keyed onto a node it is given"),
    "toon-headset": Refused(Reason.WORN, "returns a look with a headset: it is drawn only on a character"),
    "stick-figure": Refused(Reason.PLACEHOLDER, "a player of a project's traced poses; srstudio.specimens draws a "
                            "placeholder triangle for it, so its specimen would show no character"),
    "cel-traced": Refused(Reason.PLACEHOLDER, "a player of a project's traced drawings; srstudio.specimens draws "
                          "placeholder triangles for it, so its specimen would show no character"),
    **{n: Refused(Reason.CHARACTER_SHOT, f"the shot draws {who}, and the builder has no empty variant") for n, who in (
        ("office-wide", "the candidate's back"),
        ("ink-desk-shot", "the doodle"),
        ("ink-closeup", "the doodle"),
        ("ink-printer-shot", "the talking printer"),
        ("ink-wide", "the doodle and the printer"),
        ("ink-router-shot", "the talking router"),
        ("ink-router-wide", "the doodle and the router"),
        ("ink-doorstep", "the talking doorbell"),
        ("ink-kerb", "the talking meter"),
        ("ink-vacuum-shot", "the talking vacuum"),
    )},
}  # fmt: skip


def font_of(style: Style, episodes: Path) -> bytes | None:
    """The bytes of a style's font, as the first project that holds it has them; ``None`` for a style with no font."""
    if style.font is None:
        return None
    for found in sorted(Path(episodes).glob(f"*/{style.font.src}")):
        return found.read_bytes()
    raise SpecimenRenderError(f"no project in {episodes} holds {style.font.src}")


def style_of(entry: registry.Entry) -> Style:
    return STYLES[entry.style] if entry.style else CUTOUT


def _add_font(cv: Canvas, style: Style, id: str, data: bytes, work: Path) -> None:
    """Put the font file beside the document, under the name the document's asset gives it."""
    font = style.font
    assert font is not None
    target = work / font.src
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists() or target.stat().st_size != len(data):
        target.write_bytes(data)
    attrs = {"family": font.family, "weight": font.weight, "license": font.license or "see the font's project"}
    if font.style:
        attrs["fontStyle"] = font.style
    cv.assets.add_font(id=id, src=font.src, sha256=hashlib.sha256(data).hexdigest(), **attrs)


def _stage(style: Style, font: bytes | None, work: Path) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(
        width=style.width, height=style.height, fps=str(style.fps), duration=SECONDS, background=BACKGROUND
    )
    cv = Canvas(
        scene,
        style.palettes[0],
        font_asset=style.font.id if style.font else None,
        width=style.width,
        height=style.height,
        namer=style.namer() if style.namer else None,
        local_time=style.timing == "sequence",
        signature=Signature(),
    )
    if style.font and font is not None:
        _add_font(cv, style, style.font.id, font, work)
    return cv


def document(entry: registry.Entry, recipe: Recipe, font: bytes | None, episodes: Path, work: Path) -> bytes:
    """The scene document of one part. A character's comes from :data:`srstudio.specimens.SPECIMENS`, with its font
    added when it letters anything."""
    style = style_of(entry)
    if entry.kind == "character":
        cv = specimens.SPECIMENS[entry.name](entry)
        if b'fontAsset="caption"' in cv.scene.to_bytes() and font is not None:
            _add_font(cv, style, "caption", font, work)
        return cv.scene.to_bytes()
    cv = _stage(style, font, work)
    recipe.draw(cv, cv.comp, entry, Context(font or b"", episodes, work))
    return cv.scene.to_bytes()


def drawing_of(entry: registry.Entry, document: bytes) -> str:
    """What a part's file depends on. A character's digest is :func:`srstudio.specimens.fingerprint`, which holds the
    drawing and nothing around it; anything else takes its document, so a new font renders it again."""
    return hashlib.sha256(document).hexdigest() if entry.kind != "character" else specimens.fingerprint(document)


def digest(name: str, number: int, episodes: Path) -> str:
    """The digest of what version ``number`` of ``name`` draws: what ``parts.json`` records for it. A character needs
    nothing but its specimen; another part is drawn by its recipe, with its style's font and its project's data."""
    registered = parts.part_name(name, number)
    part = parts.get(name)
    if part.refused:
        raise SpecimenRenderError(f"{name} is refused ({part.refused.reason.value}), so it has no digest")
    if part.kind == "character":
        return specimens.digest(name, number)
    entry = registry.get(part.kind, registered)
    with tempfile.TemporaryDirectory() as work:
        built = document(entry, recipe_of(entry), font_of(style_of(entry), episodes), episodes, Path(work))
    return specimens.fingerprint(built)


def check(plan_: Plan) -> None:
    """Raises :class:`srstudio.specimens.DrawingChangedError` when an approved part no longer draws what it did."""
    name, _, number = plan_.entry.name.partition("@")
    version = parts.get(name).version(int(number or 1))
    if version.status == "approved" and specimens.fingerprint(plan_.document) != version.drawing:
        raise specimens.DrawingChangedError(
            f"{name} version {version.number} is approved and immutable, and it no longer draws what was approved. "
            f"Restore its drawing and add a version: an approved look is never revised in place"
        )


def key(entry: registry.Entry, drawing: str, at: float) -> str:
    """The name of a part's file."""
    return hashlib.sha256(f"{FRAMING}|{SIZE}|{at:g}|{entry.kind}|{drawing}".encode()).hexdigest()[:32]


def drawn_by_some_recipe(entry: registry.Entry) -> bool:
    """Whether :func:`recipe_of` has an answer for ``entry``."""
    return entry.name in RECIPES or entry.name in specimens.SPECIMENS or auto(entry) is not None


def recipe_of(entry: registry.Entry) -> Recipe:
    if entry.kind == "character":
        if entry.name not in specimens.SPECIMENS:
            raise SpecimenRenderError(f"character {entry.name} has no drawing in srstudio.specimens.SPECIMENS")
        return FIRST_POSE
    recipe = RECIPES.get(entry.name) or auto(entry)
    if recipe is None:
        raise SpecimenRenderError(f"{entry.kind} {entry.name} has no specimen recipe and no typed refusal")
    return recipe


def plan(episodes: Path, work: Path) -> tuple[list[Plan], dict[str, Refused]]:
    """What to render and what is refused, for every registered part."""
    specimens.load_parts()
    entries = registry.entries()
    refused = {e.name: REFUSED[e.name] for e in entries if e.name in REFUSED}
    drawn = [(e, recipe_of(e)) for e in entries if e.name not in refused]
    fonts: dict[str, bytes | None] = {}
    plans = []
    for entry, recipe in drawn:
        style = style_of(entry)
        if style.slug not in fonts:
            fonts[style.slug] = font_of(style, episodes)
        built = document(entry, recipe, fonts[style.slug], episodes, work / style.slug)
        plans.append(
            Plan(entry, built, recipe.at, key(entry, drawing_of(entry, built), recipe.at), entry.kind == "location")
        )
    return plans, refused


def bounds(pixels: np.ndarray, background: Sequence[int]) -> tuple[int, int, int, int] | None:
    """``(x0, y0, x1, y1)``, end exclusive, of the pixels that differ from ``background``; ``None`` when so few do
    that nothing was drawn."""
    drawn = (np.abs(pixels.astype(np.int16) - np.asarray(background, np.int16)) > THRESHOLD).any(axis=2)
    if drawn.sum() < BLANK:
        return None
    ys, xs = np.nonzero(drawn.any(axis=1))[0], np.nonzero(drawn.any(axis=0))[0]
    return int(xs[0]), int(ys[0]), int(xs[-1]) + 1, int(ys[-1]) + 1


def framed(document: bytes, *, background: str | None = None, x: float = 0, y: float = 0, scale: float = 1) -> bytes:
    """``document`` on ``background``, with its whole composition moved and scaled."""
    root = ET.fromstring(document)
    project, composition = root.find("project"), root.find("composition")
    if project is None or composition is None:
        raise SpecimenRenderError("a scene document with no project or no composition cannot be framed")
    if background:
        project.set("background", background)
    children = list(composition)
    group = ET.Element("group", {"id": "specimen-frame", "x": f"{x:g}", "y": f"{y:g}"})
    group.set("scaleX", f"{scale:g}")
    group.set("scaleY", f"{scale:g}")
    for child in children:
        composition.remove(child)
        group.append(child)
    composition.append(group)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def rgb(colour: str) -> tuple[int, int, int]:
    return int(colour[1:3], 16), int(colour[3:5], 16), int(colour[5:7], 16)


def _render(engine: Path, document: bytes, at: float, out: Path) -> None:
    source = out.with_suffix(".scene.xml")
    source.write_bytes(document)
    run = subprocess.run(
        [str(engine), "render", source.name, "-t", f"{at:g}", "-o", out.name],
        cwd=out.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        raise SpecimenRenderError(f"{out.stem}: scene-render failed: {run.stdout[-400:]} {run.stderr[-400:]}")
    source.unlink()


def pixels_of(png: Path, width: int, height: int) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(png), "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True,
        check=True,
    ).stdout
    return np.frombuffer(raw, np.uint8).reshape(height, width, 3)


def _resize(png: Path, out: Path, crop: str, scale: str) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(png), "-vf", f"{crop}scale={scale}:flags=lanczos", str(out)],
        check=True,
    )


def render_one(plan_: Plan, engine: Path, folder: Path) -> None:
    style = style_of(plan_.entry)
    project = ET.fromstring(plan_.document).find("project")
    assert project is not None  # framed() refuses a document without one before anything is rendered
    width, height = int(project.get("width", style.width)), int(project.get("height", style.height))
    name = plan_.entry.name
    work = folder / "work" / style.slug
    work.mkdir(parents=True, exist_ok=True)
    for plate in rafa_host.part_plates(name):
        plates.render(plate, engine=engine, cache=work / "plates", fonts=Path(os.environ.get("SRSTUDIO_FONTS", "")))
    trial = work / f"{plan_.key}.trial.png"
    final = folder / f"{plan_.key}.png"
    if plan_.set:
        document = framed(plan_.document, background=style.palettes[0].background)
        _render(engine, document, plan_.at, trial)
        stage = rgb(style.palettes[0].background)
        if bounds(pixels_of(trial, width, height), stage) is None:
            raise SpecimenRenderError(f"{name}: the set drew nothing at {plan_.at:g} s")
        _resize(trial, final.with_suffix(".tmp.png"), "", f"{SIZE}:-2")
        final.with_suffix(".tmp.png").replace(final)
        trial.unlink()
        return
    # half scale, centred: what a part draws past the edge of the frame is still measured
    _render(
        engine, framed(plan_.document, background=BACKGROUND, x=width / 4, y=height / 4, scale=0.5), plan_.at, trial
    )
    box = bounds(pixels_of(trial, width, height), rgb(BACKGROUND))
    if box is None:
        raise SpecimenRenderError(f"{name}: the recipe drew nothing at {plan_.at:g} s")
    x0, y0, x1, y1 = (
        (box[0] - width / 4) * 2,
        (box[1] - height / 4) * 2,
        (box[2] - width / 4) * 2,
        (box[3] - height / 4) * 2,
    )
    side = min(width, height)
    scale = side * (1 - 2 * MARGIN) / max(x1 - x0, y1 - y0)
    document = framed(
        plan_.document,
        background=BACKGROUND,
        x=width / 2 - scale * (x0 + x1) / 2,
        y=height / 2 - scale * (y0 + y1) / 2,
        scale=scale,
    )
    _render(engine, document, plan_.at, trial)
    _resize(trial, final.with_suffix(".tmp.png"), f"crop={side}:{side},", f"{SIZE}:{SIZE}")
    final.with_suffix(".tmp.png").replace(final)
    trial.unlink()


def _size(plan_: Plan) -> tuple[int, int]:
    if not plan_.set:
        return SIZE, SIZE
    style = style_of(plan_.entry)
    return SIZE, round(SIZE * style.height / style.width / 2) * 2


def render_all(engine: Path, cache: Path, episodes: Path) -> Shelf:
    """Every part's specimen and every refusal. Only a drawing with no file yet is rendered."""
    if not shutil.which("ffmpeg"):
        raise SpecimenRenderError("specimens need ffmpeg")
    folder = Path(cache).resolve() / "specimens"
    plans, refused = plan(episodes, folder / "work")
    missing = {p.key: p for p in plans if not (folder / f"{p.key}.png").exists()}
    with ThreadPoolExecutor(WORKERS) as pool:
        running = [(p, pool.submit(render_one, p, Path(engine).resolve(), folder)) for p in missing.values()]
    failed = [str(f.exception()) for _, f in running if f.exception() is not None]
    if failed:
        raise SpecimenRenderError(f"{len(failed)} specimens failed:\n" + "\n".join(failed))
    done = {p.entry.name: Specimen(p.entry.name, folder / f"{p.key}.png", *_size(p)) for p in plans}
    return Shelf(done, refused, len(missing))


def scene_of(packages: Path, slug: str) -> Path:
    """The scene spec of the newest version of a package, by the name its folder and ``project/`` give it."""
    versions = {}
    for folder in Path(packages).glob(f"{slug}-*"):
        if m := _VERSION.fullmatch(folder.name.removeprefix(f"{slug}-")):
            versions[tuple(map(int, m.groups()))] = folder
    if not versions:
        raise SpecimenRenderError(f"package {slug}: no {slug}-<version> folder in {packages}")
    project = versions[max(versions)] / "project"
    for scene in (project / "scene.xml", project / f"{slug}.scene.xml"):
        if scene.is_file():
            return scene
    raise SpecimenRenderError(f"package {slug}: no scene spec in {project}")


def poster_key(scene: Path, at: float) -> str:
    """Changes with the spec, the moment and the output, and with the package's version, whose assets it pins."""
    what = f"{FRAMING}|{POSTER_WIDTH}|{at:.3f}|{scene.parent.parent.name}".encode()
    return hashlib.sha256(what + scene.read_bytes()).hexdigest()[:32]


def poster(packages: Path, slug: str, engine: Path, cache: Path) -> Path:
    """A frame of a package's film, from its own spec through the engine. The package is only read: the engine runs
    in its project folder, where the spec's relative assets are, and writes to the cache."""
    scene = scene_of(packages, slug)
    try:
        project = ET.parse(scene).getroot().find("project")
        duration = float(project.get("duration", "")) if project is not None else 0.0
    except (ET.ParseError, ValueError) as exc:
        raise SpecimenRenderError(f"package {slug}: {scene.name}: {exc}") from None
    if duration <= 0:
        raise SpecimenRenderError(f"package {slug}: {scene.name} has no duration")
    at = round(duration * POSTER_AT, 3)
    folder = Path(cache).resolve() / "posters"
    out = folder / f"{slug}-{poster_key(scene, at)}.jpg"
    if out.exists():
        return out
    folder.mkdir(parents=True, exist_ok=True)
    frame = folder / f"{out.stem}.frame.png"
    run = subprocess.run(
        [str(Path(engine).resolve()), "render", scene.name, "-t", f"{at:g}", "-o", str(frame)],
        cwd=scene.parent,
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0 or not frame.exists():
        raise SpecimenRenderError(f"package {slug}: scene-render failed: {run.stdout[-400:]} {run.stderr[-400:]}")
    _resize(frame, folder / f"{out.stem}.tmp.jpg", "", f"{POSTER_WIDTH}:-2")
    (folder / f"{out.stem}.tmp.jpg").replace(out)
    frame.unlink()
    return out

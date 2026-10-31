"""No Thanks — the sketch as data: Brent blocks a shop door for her email. To refuse she must read his card aloud: no
thanks, I hate saving money. He flips it: yes, my family deserves less. He follows her to the till, and then home, to
the foot of her bed at night, the card lit from below: we miss you. She sits up. Unsubscribe. His face falls, he sits
down, he takes off one shoe. That takes ten business days.

Collage style (ADR 0026): a website's manners on a man who can actually stand in the way. The reel opens moving (the
sp-hook_motion test's arm b): Brent leaps into frame on frame one. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_everyday
from srstudio.collage_group import Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, events

SEED = 3106
SLUG = "no-thanks"
TITLE = "No Thanks — Priya and Brent (Collage)"
NAMES = ("brent", "priya")
SHOP = "supermarket"
BEDROOM = "bedroom"
DESCRIPTION = (
    "A Collage sketch: Brent blocks a shop door with ten percent off, makes Priya read out the card that insults her, "
    "and turns up at the end of her bed to say he misses her."
)
ACCESSIBILITY = (
    "Paper cut-out characters: a man leaps in front of a woman at a shop door, offering ten percent off. To refuse, "
    "she must read his card aloud, which says she hates saving money. He flips it and she reads that her family "
    "deserves less. At the till he says she left something in her cart. At night he stands at the end of her bed "
    "holding the card, lit from below. She says unsubscribe. He sits down, takes off one shoe, and says it takes ten "
    "business days. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesised whoosh and thud."
NOTE = "ElevenLabs premade voices Brian and Sarah at their natural pace; no reference-voice cloning."
BITRATE = 5_800_000  # two passes: a master under 20 MB

PRIYA, BRENT = Place(290.0, 1920.0, 0.8), Place(800.0, 1920.0, 0.8)
LEAP = (760.0, 120.0, 0.32)  # the opening: how far right and down he starts, and the seconds he lands in
CARD_FIRST = "NO THANKS, I HATE SAVING MONEY"
CARD_SECOND = "YES, MY FAMILY DESERVES LESS"
CARD = dict(x=540.0, y=1560.0, w=760.0, h=420.0, size=78.0)
SHORT = dict(x=540.0, y=1470.0, w=430.0, h=250.0, size=84.0)
SLIDE = 600.0  # how far Brent slides in at the till, or out at the door
LOWER = 170.0  # how far down Priya lies and Brent sits
DARK = "#141a3a"
SHOE_AT = (820.0, 1590.0)

LINES = (
    Line("brent", "Wait! Ten percent off for your email!"),
    Line("priya", "No thanks."),
    Line("brent", "Read the card."),
    Line("priya", "No thanks, I hate saving money."),
    Line("brent", "Are you sure?"),
    Line("priya", "Yes."),
    Line("priya", "Yes, my family deserves less."),
    Line("brent", "You left something in your cart."),
    Line("priya", "I didn't."),
    Line("brent", "We'll remind you."),
    Line("brent", "We miss you."),
    Line("priya", "Unsubscribe."),
    Line("brent", "That takes ten business days."),
)
BEATS, END = timed(
    LINES,
    (
        (2.1, "brent", 0, "wide", "grin", "shrug"),
        (0.9, "priya", 1, "half", "flat", "hold"),
        (0.85, "brent", 2, "open", "smile", "hold", "reveal:card"),
        (2.1, "priya", 3, "half", "flat", "hold"),
        (0.8, "brent", 4, "wide", "smile", "hold"),
        (0.65, "priya", 5, "angry", "flat", "hold"),
        (0.6, "brent", "", "half", "smug", "hold", "swat"),  # the flip
        (2.0, "priya", 6, "half", "frown", "hold"),
        (0.7, "brent", "", "open", "smile", "down", "reveal:aside"),
        (0.8, "priya", "", "half", "flat", "hold", "reveal:till"),  # one light bulb
        (1.45, "brent", 7, "open", "smile", "point"),
        (0.9, "priya", 8, "angry", "flat", "hold"),
        (0.95, "brent", 9, "open", "smug", "down"),
        (1.3, "priya", "", "open", "flat", "down", "reveal:bed"),  # awake
        (0.9, "brent", 10, "open", "smile", "hold", "reveal:foot"),
        (1.5, "brent", "", "open", "smile", "hold"),
        (1.25, "priya", 11, "angry", "flat", "down", "reveal:up"),
        (0.6, "brent", "", "sad", "frown", "down", "reveal:shoe"),  # he sits
        (0.4, "brent", "", "sad", "frown", "down", "thud"),  # one shoe
        (1.6, "brent", 12, "sad", "flat", "down"),
        (1.4, "priya", "", "half", "flat", "down"),
    ),
    tail=0.2,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _at(beats: Sequence[Beat], name: str) -> float:
    return next(t for t, what in events(beats, "reveal") if what == name)


def setting(beats: Sequence[Beat], app: Appearance) -> str:
    """The shop, until she gets home."""
    return BEDROOM if app.start >= _at(beats, "bed") else SHOP


def _drawn(cv, parent, who: str, app: Appearance, mouths: Mouths, place: Place, held: str = "hold"):
    """``who`` in ``place``, on its own group; the speaker on its poses, the other held in one of them."""
    x, y = place.transform()
    g = cv.group(parent, cv.uid(f"shop-{who}"), x=x, y=y, scaleX=place.scale, scaleY=place.scale)
    poses = app.poses if who == app.who else [{"start": 0.0, "eyes": "open", "mouth": "flat", "arms": held}]
    collage.DRAWERS[who](cv, g, collage.parse_poses(poses, f"{who} at {app.start}"), app.end, (), enter=app.start,
                         mouths=mouths.get(who, ()))  # fmt: skip
    return g


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """Brent's leap, the two of them at the door and the till, then each alone in the dark."""
    first = beats[1].start
    aside, till, bed, up, shoe = (_at(beats, n) for n in ("aside", "till", "bed", "up", "shoe"))
    slides = next(b.start for b in beats if b.start > till)

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if app.start < first:
            leapt = cv.group(parent, cv.uid("g"))
            cv.keys(leapt, "x", [(0.0, LEAP[0]), (LEAP[2], 0.0)], kind="cubic-out", local=False)
            cv.keys(leapt, "y", [(0.0, LEAP[1]), (LEAP[2], 0.0)], kind="cubic-out", local=False)
            collage.DRAWERS["brent"](cv, leapt, collage.parse_poses(app.poses, "the leap"), app.end, (),
                                     enter=app.start, mouths=mouths.get("brent", ()))  # fmt: skip
            return collage.face(collage.LOOKS["brent"])
        if app.start < bed:
            _drawn(cv, parent, "priya", app, mouths, PRIYA)
            if app.start != till:  # at the till she is alone at first
                brent = _drawn(cv, parent, "brent", app, mouths, BRENT, held="hold" if app.start < aside else "down")
                x = BRENT.transform()[0]
                if app.start == aside:
                    cv.keys(brent, "x", [(aside, x), (aside + 0.5, x + SLIDE)], kind="sine-in-out", local=False)
                if app.start == slides:
                    cv.keys(brent, "x", [(slides, x + SLIDE), (slides + 0.3, x)], kind="cubic-out", local=False)
            return PRIYA.x, 1200.0
        moved = cv.group(parent, cv.uid("g"))
        if app.who == "priya":
            if app.start >= up:
                cv.keys(moved, "y", [(up, LOWER), (up + 0.35, 0.0)], kind="cubic-out", local=False)
            else:
                moved = cv.group(parent, cv.uid("g"), y=LOWER)
        elif app.start >= shoe:
            cv.keys(moved, "y", [(shoe, 0.0), (shoe + 0.4, LOWER)], kind="sine-in-out", local=False)
        collage.DRAWERS[app.who](cv, moved, collage.parse_poses(app.poses, "the dark"), app.end, (), enter=app.start,
                                 mouths=mouths.get(app.who, ()))  # fmt: skip
        return collage.face(collage.LOOKS[app.who])

    return draw


def _bulb(cv, parent) -> None:
    """The one light bulb she came for, in her hands."""
    cv.ellipse(parent, 225.0, 1400.0, 130.0, 130.0, "#ffe066", collage.INK, 6.0)
    cv.rect(parent, 262.0, 1520.0, 56.0, 50.0, "#9a9aa6", collage.INK, 6.0, radius=6.0)


def _shoe(cv, parent, t: float) -> None:
    g = cv.group(parent, cv.uid("g"), x=SHOE_AT[0], y=SHOE_AT[1])
    cv.gate(g, [(t, 86400.0)])
    cv.rect(g, -90.0, -36.0, 180.0, 62.0, "#6b4226", collage.INK, 6.0, radius=26.0)
    cv.rect(g, -96.0, 22.0, 192.0, 16.0, "#2b2d42", collage.INK, 4.0, radius=6.0)


def dress(shot) -> None:
    """The card, the till, the duvet, the dark, the glow under the card, and one shoe."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    card, aside, till, bed, foot, shoe = (_at(beats, n) for n in ("card", "aside", "till", "bed", "foot", "shoe"))
    flip = events(beats, "swat")[0][0]
    if card <= app.start < aside:
        collage_everyday.flip_card(cv, shot.front, ((0.0, CARD_FIRST), (flip, CARD_SECOND)), **CARD)
    if till <= app.start < bed:
        cv.rect(shot.front, -20.0, 1620.0, 1120.0, 330.0, "#8d99ae", collage.INK, 7.0)
        _bulb(cv, shot.front)
    if app.start >= bed:
        collage_everyday.duvet(cv, shot.front)
        if app.who == "brent":
            _shoe(cv, shot.front, events(beats, "thud")[0][0])
        dark = cv.grad("collage-no-thanks-dark", [(0, DARK + "00"), (0.2, DARK + "aa"), (1, DARK + "cc")], (0, 0, 0, 1))
        cv.rect(shot.front, 0, 790, cv.width, 1130, dark)
        if app.who == "brent" and app.start >= foot:
            glow = cv.grad(
                "collage-no-thanks-glow", [(0, "#ffd16600"), (0.5, "#ffd16648"), (1, "#ffd16600")], (0, 0, 0, 1)
            )
            cv.rect(shot.front, 0, 1060, cv.width, 860, glow)
            if app.start < shoe:
                collage_everyday.flip_card(cv, shot.front, ((0.0, "10% OFF"),), **SHORT)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"brent": SHOP, "priya": SHOP},
    dress=dress,
    cast=casting,
    setting=setting,
    bitrate=BITRATE,
)

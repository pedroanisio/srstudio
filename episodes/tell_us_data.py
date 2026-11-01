"""Tell Us — the sketch as data: "tell us about yourself", and Gary starts at birth. His father wasn't there. Deb puts
her pen down and leans in, and by the end the interview is a session, with Brent crying into a tissue and nobody
mentioning the job.

Collage style (ADR 0026), the panel's two-shot of ADR 0036: Gary's chair tips back further each cut. The wall clock
says 9:00 on the hook's hour and 9:50 when Deb calls time. The reel moves from its first second (L7): the panel's pens
are tapping. ElevenLabs premade voices, lip-synced.
"""

from __future__ import annotations

from collections.abc import Sequence

from srstudio import collage, collage_home
from srstudio.collage_group import Lineup, Place
from srstudio.collage_sketch import TINTS, CastDrawer, Staging, make_sketch, solo, timed, voices_note
from srstudio.sketch import Appearance, Beat, Line, Mouths, appearances

SEED = 3307
SLUG = "tell-us"
TITLE = "Tell Us — Brent, Deb and Gary (Collage)"
NAMES = ("brent", "deb", "gary")
ROOM = "boardroom"
DESCRIPTION = (
    "A Collage sketch: 'tell us about yourself' is the easiest question in the world until you are asked it, and "
    "Gary starts at birth."
)
ACCESSIBILITY = (
    "Paper cut-out characters in a boardroom: a man and a woman on an interview panel hold pens. The candidate tips "
    "further back in his chair with each cut, eyes on the ceiling. The woman puts down her pen and leans in. A box "
    "of tissues appears. The man cries. A wall clock says ten to ten. Lines appear in tinted pills."
)
NARRATION = f"Voiced with ElevenLabs premade voices {voices_note(NAMES)}; a synthesized zoom and sting."
NOTE = "ElevenLabs premade voices Brian, Jessica and Chris at their natural pace; no reference-voice cloning."
BITRATE = 5_600_000  # two passes: a master under 20 MB; the grain, new every frame, is what costs the bits
HOOK = "INTERVIEW, 9:00"
HOOK_SECONDS = 3.0

PLACES = {"brent": Place(300.0, 1800.0, 0.7), "deb": Place(780.0, 1800.0, 0.7)}
TIPS = (0.0, -4.0, -9.0, -15.0, -22.0, -28.0)  # Gary's chair, further back each cut
PENS = {"brent": (300.0, 1700.0), "deb": (780.0, 1700.0)}
BOX = (530.0, 1760.0, 300.0)
CLOCK = (130.0, 760.0, 84.0)
TISSUE = (232.0, 1560.0)  # in Brent's hand

LINES = (
    Line("brent", "So. Tell us about yourself."),
    Line("gary", "Sure. I was born."),
    Line("deb", "Okay."),
    Line("gary", "In a hospital. My father wasn't there."),
    Line("brent", "We meant more recently."),
    Line("gary", "He's still not there."),
    Line("deb", "And how did that make you feel?"),
    Line("brent", "Deb, no."),
    Line("deb", "Shh."),
    Line("gary", "I've never told anyone this."),
    Line("brent", "Did he ever come to your games?"),
    Line("gary", "One."),
    Line("deb", "I'm afraid that's our time."),
    Line("gary", "So, do I have the job?"),
    Line("deb", "Same time next week?"),
)
BEATS, END = timed(
    LINES,
    (
        (1.9, "brent", 0, "open", "smile", "hold"),
        (1.4, "gary", 1, "open", "smile", "down"),
        (0.9, "deb", 2, "half", "flat", "hold"),
        (2.4, "gary", 3, "up", "flat", "down"),
        (1.5, "brent", 4, "half", "flat", "hold"),
        (1.5, "gary", 5, "up", "frown", "down"),
        (1.5, "deb", "", "sad", "flat", "hold"),  # the pen goes down; she leans in
        (1.8, "deb", 6, "sad", "flat", "hold", "zoom"),
        (0.9, "brent", 7, "wide", "flat", "shrug"),
        (0.9, "deb", 8, "half", "flat", "point"),
        (1.8, "gary", 9, "up", "frown", "down"),
        (2.0, "brent", 10, "sad", "frown", "hold"),  # he has a tissue
        (0.9, "gary", 11, "closed", "frown", "down"),
        (0.3, "brent", "", "sad", "frown", "hold"),  # his chin goes; Deb checks the clock
        (0.3, "brent", "", "sad", "flat", "hold"),
        (0.3, "brent", "", "sad", "frown", "hold"),
        (0.6, "brent", "", "closed", "frown", "hold"),
        (1.6, "deb", 12, "side", "flat", "hold", "sting"),
        (1.5, "gary", 13, "open", "smile", "shrug"),
        (1.6, "deb", 14, "half", "smile", "hold"),
    ),
    tail=2.0,
)
SKETCH = make_sketch(SLUG, TITLE, NAMES, LINES, BEATS, END)


def _pose(start: float, eyes: str, mouth: str, arms: str) -> dict:
    return {"start": round(max(start, 0.0), 6), "eyes": eyes, "mouth": mouth, "arms": arms}


def _said(beats: Sequence[Beat], line: int) -> float:
    return next(b.start for b in beats if b.line == line)


def lineup(beats: Sequence[Beat], end: float) -> Lineup:
    """The panel in one frame whenever Gary is not on screen, each listening on the project clock."""
    leans, tissue = _said(beats, 5) + 1.5, _said(beats, 10)
    reactions = {
        "brent": [_pose(0, "open", "smile", "hold"), _pose(_said(beats, 6), "side", "flat", "hold"),
                  _pose(tissue, "sad", "frown", "hold")],
        "deb": [_pose(0, "half", "flat", "hold"), _pose(leans, "sad", "flat", "hold"),
                _pose(_said(beats, 12) - 1.5, "side", "flat", "hold")],
    }  # fmt: skip
    return Lineup(PLACES, reactions, tuple((a.start, a.end) for a in appearances(beats, end) if a.who != "gary"))


def casting(beats: Sequence[Beat], end: float) -> CastDrawer:
    """The panel, or Gary alone in his chair, tipped further back each time we come to him."""
    group = lineup(beats, end)
    gary = [a.start for a in appearances(beats, end) if a.who == "gary"]

    def tip(app: Appearance) -> float:
        return TIPS[min(len(TIPS) - 1, gary.index(app.start))]

    def draw(cv, parent, app: Appearance, mouths: Mouths) -> collage.Point:
        if group.staged(app):
            return group(cv, parent, app, mouths)
        tilted = cv.group(parent, cv.uid("g"), x=collage.CX, y=1920.0, rotation=tip(app))
        moved = cv.group(tilted, cv.uid("g"), x=-collage.CX, y=-1920.0)
        collage_home.chair_back(cv, moved, collage.CX, 860, 560, 1200)
        return solo(cv, moved, app, mouths)

    return draw


def _pens(cv, front, app: Appearance, beats: Sequence[Beat]) -> None:
    """The panel's pens: tapping from the first frame; Deb's goes down when she leans in, Brent's stays up."""
    down = _said(beats, 5) + 1.5
    for name, (x, y) in PENS.items():
        hand = cv.group(front, cv.uid("g"))
        tap = [(i * 0.25, 0.0 if i % 2 else -16.0) for i in range(5)]
        cv.keys(hand, "y", tap, hold=False, local=False)
        if name == "deb":
            lay = cv.group(hand, cv.uid("g"), x=x, y=y)
            cv.keys(lay, "y", [(down, y), (down + 0.35, y + 90.0)], kind="cubic-out", local=False)
            cv.keys(lay, "rotation", [(down, 10.0), (down + 0.35, 84.0)], kind="cubic-out", local=False)
            collage_home.pen(cv, lay, 0, 0, 230)
        else:
            collage_home.pen(cv, hand, x, y, 230, -10.0)


def dress(shot) -> None:
    """The table's props in the panel's shots, the clock over the shelf side, the hook while it is up."""
    cv, app, beats = shot.cv, shot.app, shot.beats
    if app.who != "gary":
        _pens(cv, shot.front, app, beats)
        tissue = _said(beats, 10)
        if app.end > tissue - 0.01:
            shown = cv.group(shot.front, cv.uid("g"))
            cv.gate(shown, [(tissue, shot.end)])
            collage_home.tissue_box(cv, shown, *BOX)
            cv.ellipse(shown, TISSUE[0] - 48, TISSUE[1] - 40, 96, 80, "#ffffff", collage.INK, 3)
        over = _said(beats, 12) - 1.5
        early = cv.group(shot.back, cv.uid("g"))
        cv.gate(early, [(0.0, over)])
        collage_home.wall_clock(cv, early, *CLOCK, "9:00")
        late = cv.group(shot.back, cv.uid("g"))
        cv.gate(late, [(over, shot.end)])
        collage_home.wall_clock(cv, late, *CLOCK, "9:50")
    if app.start < HOOK_SECONDS:
        collage_home.hook_card(cv, shot.front, HOOK, ROOM, shot.measure, start=0.0, seconds=HOOK_SECONDS)


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    sets={"brent": ROOM, "deb": ROOM, "gary": ROOM},
    dress=dress,
    cast=casting,
    bleed=True,
    bitrate=BITRATE,
    keep_signature=True,
    loudness="-14",
)

#!/usr/bin/env python3
"""Out of Cyan, built with srstudio: Rosa wants one black page, and the printer has taken it hostage.

    srstudio record out-of-cyan PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build out-of-cyan PROJECT    # → PROJECT/out-of-cyan.scene.xml

Held frame: Rosa and the printer, eye to display: LOW ON CYAN. "It's black and white." It prints a page anyway, in
cut-out letters: WE HAVE YOUR DOCUMENT. BRING CYAN. COME ALONE. Sixty-four dollars at the card reader. NOT OUR CYAN.
The official one, more money. NOW THE MAGENTA, with a photo of her document tied to a chair. "Don't hurt it." She pays
again. The display says THANK YOU, and the page comes out perfectly, in cyan. Stop on her face.

The first second is still (arm A of the ``sp-hook_motion`` test): one held frame, no camera move, the error beep at
its end. Like *Neighbor Names* it declares no engine safe area: the close-up reframes the desk's lettering out of frame
and the pages stand in for it, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from out_of_cyan_audio import INTERVIEW
from srstudio import OFFICE, Episode, EpisodeSpec, cast, cutout_home, locations, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="out-of-cyan",
        title="Out of Cyan",
        description="Printer comedy: one black page, a printer that wants cyan, and a ransom note in cut-out letters. "
        "Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),
        seed=26052,
        background="#A5B9AF",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
PAGES = [float(p) for p in t.meta["pages"]]
WHIRS = [(float(a), float(b)) for a, b in t.meta["whirs"]]
REACTION, DURATION = t.reaction, t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
ROSA_AT = (540, 640, 1.75)
PRINTER_FOOT = (540, 1310)
CYAN = "#14B4DA"
EPS = 1 / 120

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))

rosa = cast.Rosa(cv)


def at_desk(g):
    """She looks down at the display, up at nothing when a page lands, and into the lens at the end."""
    ep.perform(
        rosa,
        g,
        *ROSA_AT,
        mouth=ep.mouth("rosa"),
        blinks=[
            (L[0].end + 0.10, L[0].end + 0.24),
            (L[1].end + 0.05, L[1].end + 0.19),
            (L[2].end + 0.30, L[2].end + 0.44),
            (REACTION + 1.05, REACTION + 1.45),  # one slow blink, the only thing she does
        ],
        nods=[
            (0, 0),
            (L[0].start, 0),
            (L[0].start + 0.22, 3),  # "It's black and white.": patient
            (L[1].start - 0.15, 3),
            (L[1].start + 0.20, -7),  # "I beg your pardon?": the chin up
            (L[1].end + 0.2, -7),
            (L[1].end + 0.5, 2),
            (L[3].start, 2),
            (L[3].start + 0.2, 8),  # "It's blue, dear.": a firm little nod
            (L[3].end, 8),
            (L[3].end + 0.3, 0),
            (REACTION, 0),
        ],
    )
    down, lens = 6, -3  # the eyes carry her glasses, so they move little
    cv.keys(rosa.eyes, "y", [(0, down), (L[1].start - 0.15, down), (L[1].start - 0.05, lens), (L[1].end, lens),
                             (L[1].end + 0.15, down), (L[3].start - 0.1, down), (L[3].start, lens), (L[3].end, lens),
                             (L[3].end + 0.1, down), (REACTION - 0.05, down), (REACTION, lens)],
            hold=False)  # fmt: skip


def on_desk(g):
    ink = "#1B1B1F"
    cutout_home.desk_printer(
        cv,
        g,
        *PRINTER_FOOT,
        lcd=((0.0, "LOW ON CYAN"), (WHIRS[4][0], "THANK YOU")),
        whirs=WHIRS,
        sheets=tuple((a, b - a, CYAN if k == 4 else ink) for k, (a, b) in enumerate(WHIRS)),
    )
    bag = cv.group(g, "bag-on-desk")
    cv.gate(bag, [(spans["reader-1"][0][1], DURATION)])  # the little bag stays on the desk from the first purchase
    cutout_home.paper_bag(cv, bag, 150, 1330, scale=1.15, id="desk-paper-bag")


finish = locations.finish(cv, ep.comp)
study = cutout_home.home_study(cv, finish, behind_desk=at_desk, on_desk=on_desk)


def framing(at, scale, to):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


FRAMES = {"two": (1.0, 0.0, 0.0), "rosa": framing(ROSA_AT[:2], 1.75, (540, 560))}
rows = [(c.time, *FRAMES[c.angle]) for c in cuts if c.angle in FRAMES]
PUSH = framing(ROSA_AT[:2], 1.95, (540, 560))  # the last shot creeps in on her face
for prop, column in [("scaleX", 1), ("scaleY", 1), ("x", 2), ("y", 3)]:
    values = [(0.0, rows[0][column])]
    for prev, row in zip(rows, rows[1:], strict=False):
        values += [(row[0] - EPS, prev[column]), (row[0], row[column])]
    values.append((DURATION, PUSH[column - 1]))
    cv.keys(study, prop, values, hold=False)


def page_insert(n: int, draw):
    """A page on the desk, seen from above, for as long as its cut lasts."""
    shot = cv.group(finish, f"insert-page-{n}")
    cv.gate(shot, spans[f"page-{n}"])
    cutout_home.desk_top(cv, shot, id=f"desk-top-{n}")
    draw(shot)


def reader_insert(n: int, amount: str, label: str):
    shot = cv.group(finish, f"insert-reader-{n}")
    cv.gate(shot, spans[f"reader-{n}"])

    def counter(g):
        props.card_reader(cv, g, 400, 1260, readings=((0, amount, label),), scale=2.1)
        cutout_home.paper_bag(cv, g, 830, 1240, scale=1.5, id=f"till-bag-{n}")

    cutout_home.shop_till(cv, shot, on_counter=counter, id=f"till-{n}")


page_insert(1, lambda g: cutout_home.ransom_note(cv, g, 120, 240, lines=("WE HAVE", "YOUR", "DOCUMENT"), size=150))
page_insert(2, lambda g: cutout_home.ransom_note(cv, g, 120, 240, lines=("BRING", "CYAN.", "COME", "ALONE."), size=150,
                                                 seed=12, id="ransom-note-2"))  # fmt: skip
page_insert(3, lambda g: cutout_home.ransom_note(cv, g, 120, 240, lines=("NOT", "OUR", "CYAN."), size=170, seed=13,
                                                 id="ransom-note-3"))  # fmt: skip


def magenta(g):
    cutout_home.ransom_note(cv, g, 120, 170, lines=("NOW THE", "MAGENTA"), height=620, size=124, seed=14,
                            id="ransom-note-4")  # fmt: skip
    cutout_home.hostage_photo(cv, g, 290, 740, scale=0.98)


page_insert(4, magenta)


def finished_page(g):
    """The document she asked for, in the one colour it never needed."""
    cv.rect(g, 164, 266, 800, 1040, "#2A2018", opacity=0.35)
    cv.rect(g, 140, 240, 800, 1040, cutout_home.PAGE, "#1B1B1F", 3)
    cv.rect(g, 210, 320, 420, 44, CYAN)
    for k in range(13):
        cv.line(g, 210, 430 + k * 58, 870 if k % 5 != 4 else 610, 430 + k * 58, CYAN, 14)


page_insert(5, finished_page)
reader_insert(1, "$64.00", "CYAN, 4 ML")
reader_insert(2, "$89.00", "OFFICIAL CYAN")
reader_insert(3, "$98.00", "MAGENTA")

specs = [(0.0, L[0].start - 0.05, "Printing one black page.", "hook")]
for i, p in enumerate(t.phrases):
    specs.append((p.start - 0.05, p.end + 0.25, p.caption, f"dialogue-{i + 1}"))
spoken = ep.captions(specs, x=80, y=1335, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-note", PAGES[0], "The first demand"), ("marker-photo", PAGES[3], "The photo")])
ep.instagram(POSTS["out-of-cyan"])
ep.finish()

#!/usr/bin/env python3
"""Just a Trim, built with srstudio: there is a lawnmower in the barber's, and she says she loves it.

    srstudio record just-a-trim PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build just-a-trim PROJECT    # → PROJECT/just-a-trim.scene.xml

Held frame: Rosa in the mirror, a lawnmower parked behind her, a hedge trimmer on the shelf. "Just a trim, please."
"Sure." The cape covers the mirror. A hedge trimmer, heard. A lawnmower, heard. The barber blocks the glass: "Bit off
the sides?" Hair falls past the lens in sheets. "...Sure." The engine stops. The cloth drops. A different head, two
seconds of nothing. "How's that?" The face wobbles. "Love it." The card reader: the cut, then the tip. It stops there.

The first second is still (arm A of the ``sp-hook_motion`` test). Nobody's hair is redrawn: the head in the mirror
afterwards is another approved character speaking with Rosa's voice. It declares no engine safe area, so captions are
placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from just_a_trim_audio import INTERVIEW
from srstudio import OFFICE, Episode, EpisodeSpec, cast, cutout_shop, locations, look, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="just-a-trim",
        title="Just a Trim",
        description="Service comedy: a customer asks for a trim, sits through a hedge trimmer and a lawnmower, and is "
        "too polite to say anything but thank you. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),
        seed=26171,
        background="#E9D7BC",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
CAPE, BLOCK, UNCOVER = float(t.meta["cape"]), float(t.meta["block"]), float(t.meta["uncover"])
WOBBLE = tuple(float(x) for x in t.meta["wobble"])
KEYS, PAID = float(t.meta["keys"]), float(t.meta["paid"])
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
EPS = 1 / 120
HEAD = (430, 600, 2.6)
MX, MY, MW, MH = cutout_shop.BARBER_MIRROR
cuts = list(t.cuts)
TILL = next(c.time for c in cuts if c.angle == "till")


def before(g):
    rosa = cast.Rosa(cv, tag="rosa-character")
    cv.gate(g, [(0.0, CAPE + 0.3)])
    ep.perform(rosa, g, *HEAD, mouth=ep.mouth("rosa"), stitch=None, blinks=[(L[1].end + 0.05, L[1].end + 0.2)])


def after(g):
    cv.gate(g, [(UNCOVER - 0.1, DURATION)])
    jitter = [(0.0, 0.0), (WOBBLE[0], 0.0)]
    at, sign = WOBBLE[0] + 0.07, 1
    while at < WOBBLE[1]:
        jitter.append((at, 2.6 * sign))
        at += 0.07
        sign = -sign
    jitter += [(WOBBLE[1] + 0.05, 0.0), (L[5].start + 0.1, -4.0)]
    ep.perform(
        cast.Manager(cv, tag="after-character"),
        g,
        *HEAD,
        mouth=ep.mouth("rosa"),
        blinks=[(L[4].end - 0.1, L[4].end + 0.04)],
        nods=jitter,
    )
    cutout_shop.barber_cape(cv, g, HEAD[0], HEAD[1] + 267, width=700, height=420, id="after-cape")


def in_mirror(g):
    cutout_shop.lawnmower(cv, g, 830, 1170, scale=1.1, facing=-1, id="parked-mower")
    before(cv.group(g, "mirror-before"))
    after(cv.group(g, "mirror-after"))
    cloth = cv.group(g, "mirror-cloth")
    cv.gate(cloth, [(CAPE, UNCOVER + 0.3)])
    cv.keys(cloth, "y", [(CAPE, 1300.0), (CAPE + 0.26, 0.0), (UNCOVER, 0.0), (UNCOVER + 0.24, 1300.0)], hold=False)
    cutout_shop.barber_cape(
        cv, cloth, MX + MW / 2, MY - 20, width=MW + 40, height=MH + 40, spread=True, id="mirror-cape"
    )


def on_counter(g):
    cutout_shop.hedge_trimmer(cv, g, 300, 1312, scale=1.0, id="shelf-trimmer")


finish = locations.finish(cv, ep.comp)
cutout_shop.barbershop(cv, finish, in_mirror=in_mirror, on_counter=on_counter, shots=[(0.0, TILL)])

barber_at = cv.group(finish, "barber-in-the-way")
cv.gate(barber_at, [(BLOCK, UNCOVER)])
cv.keys(barber_at, "x", [(BLOCK, 900.0), (BLOCK + 0.2, 0.0), (UNCOVER - 0.26, 0.0), (UNCOVER, -900.0)], hold=False)
ep.perform(
    cast.Barista(cv, tag="barber-character"),
    barber_at,
    540,
    720,
    2.5,
    mouth=ep.mouth("barista"),
    blinks=[(L[2].end + 0.04, L[2].end + 0.18)],
    nods=[(0, 0), (L[2].start, 0), (L[2].start + 0.3, 4), (L[2].end, 0)],
    name=None,
)
cutout_shop.hair_fall(
    cv,
    finish,
    falls=[(BLOCK + 0.2, 0.6), (BLOCK + 0.75, 0.6), (BLOCK + 1.25, 0.55), (BLOCK + 1.7, 0.55), (BLOCK + 2.1, 0.5)],
)

till = cv.group(finish, "till")
cv.gate(till, [(TILL, DURATION)])
cv.rect(till, -10, -10, 1100, 1940, cv.grad("till-wall", [(0, "#E9D7BC"), (1, "#CFB997")], (0, 0, 0, 1)))
cv.rect(till, -10, 1160, 1100, 800, "#F4EFE0", cv.ink, 4)
look.pool(cv, till, "till-contact", "#2A2018CC", 170, 1190, 740, 60, opacity=0.5)
props.card_reader(cv, till, 540, 1230, scale=2.6, readings=((0, "$22.00", "TRIM"), (PAID, "$30.00", "TIP")))

specs = [(max(p.start - 0.05, 0.0), p.end + 0.2, p.caption, f"dialogue-{i + 1}") for i, p in enumerate(t.phrases)]
spoken = ep.captions(specs, x=80, y=1420, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-mirror", UNCOVER, "The mirror"), ("marker-tip", PAID, "The tip")])
ep.instagram(POSTS["just-a-trim"])
ep.finish()

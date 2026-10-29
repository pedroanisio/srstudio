#!/usr/bin/env python3
"""Episode 14 — Culture Fit, built with srstudio: Milo from episodes 05 and 09 meets the boss on a park bench.

    python3 culture_fit_audio.py PROJECT --key-stdin < key   # generated clips, resolved and pinned by the engine
    python3 culture_fit.py PROJECT                            # → PROJECT/culture-fit.scene.xml

Job hunt, day 200: "Two hundred applications. Not one reply." The boss sits down with his lunch, and a pigeon lands
at his feet. "So. Where do you see yourself in five years?" Coo. "Love that. Can you start Monday?" Coo; his phone
pings: offer accepted. "Sorry, are you hiring?" "Not anymore." "I have a master's degree." A long look, a handful of
crumbs: "He works for crumbs." "...I can do crumbs." "We'll keep you on file." Ping: Pigeon, team lead, wants to
connect.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import CAFE, Episode, EpisodeSpec, camera, cast, graphics, locations, props

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="culture-fit",
        number="14",
        title="Culture Fit — Comedy Cut 14",
        description="Park comedy: a job hunter, a boss on his lunch break, and the pigeon that gets the job. Native "
        "vector animation in the park; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=14041,
        background="#CFE3E6",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        # no engine safe area: the park sign's lettering sits right of x 920 and the close-ups push the bench out
        # of frame on purpose, which the text check (SA01) refuses; captions and cards are placed by hand instead
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
TOSS, OFFER, CONNECT = t.toss_start, t.offer_start, t.connect_start
REACTION, ENDING, DURATION = t.reaction, t.ending, t.duration
FX = {s.name: s for s in t.sound_effects}
LAND = FX["flutter"].start
SCALE = 1.25
MILO_AT = (370, locations.park_seat_y(300, SCALE), SCALE)  # the seated café rig ends its torso at 300
BOSS_AT = (720, locations.park_seat_y(cast.Manager.bottom, SCALE), SCALE)
BIRD = (540, 1547, 1.05)  # on the path between them, facing the boss
HAND = (BOSS_AT[0] - 82 * SCALE, BOSS_AT[1] + 300 * SCALE)  # the boss's left hand, on his knee


def nod(at: float, depth: float = 14, hold: float = 0.22) -> list[tuple[float, float]]:
    return [(at, 0), (at + 0.10, depth), (at + 0.10 + hold, depth), (at + 0.22 + hold, 0)]


def peck(at: float) -> list[tuple[float, float]]:
    return [(at, 0), (at + 0.08, 32), (at + 0.18, 4), (at + 0.26, 32), (at + 0.36, 4), (at + 0.44, 32), (at + 0.6, 0)]


def bird(g):
    """The pigeon drops in on the flutter, nods twice to the interview, and pecks at the crumbs."""
    x, y, s = BIRD
    drop = cv.group(g, "pigeon-landing", x=0, y=0)
    cv.gate(drop, [(LAND, DURATION)])
    cv.keys(drop, "y", [(LAND, -260), (LAND + 0.30, 8), (LAND + 0.40, 0)], hold=False)
    cv.keys(drop, "x", [(LAND, -120), (LAND + 0.30, 0)], hold=False)
    nods = [(0, 0)] + nod(FX["coo-1"].start) + nod(FX["coo-2"].start) + peck(FX["coo-3"].start)
    cast.pigeon(cv, drop, x, y, s, flip=False, nods=nods)
    props.crumbs(cv, g, *HAND, y + 50, toss=TOSS, count=7, seed=14)


milo = cast.Customer(cv, seated=True)
boss = cast.Manager(cv, tag="manager-park")
park = ep.setup(
    locations.park,
    [(0, DURATION)],
    on_bench=lambda g: (
        ep.perform(
            milo,
            g,
            *MILO_AT,
            mouth=ep.mouth("milo", smile=[(P(7).end + 0.1, P(8).start)]),  # the hopeful grin at his counter-offer
            blinks=[(1.9, 2.04), (P(4).end + 0.05, P(4).end + 0.25), (P(6).end + 0.4, P(6).end + 0.9)],
            nods=[
                (0, 6),
                (P(0).end, 6),
                (P(0).end + 0.3, 0),
                (P(3).start, 0),
                (P(3).start + 0.25, -4),
                (P(5).start, -4),
                (P(5).start + 0.2, -8),
                (P(5).end, 0),
                (P(6).end + 0.3, 0),
                (P(6).end + 0.6, 7),
                (P(7).start, 7),
                (P(7).start + 0.3, -3),
                (REACTION, -3),
                (REACTION + 0.25, 6),
            ],
        ),
        ep.perform(
            boss,
            g,
            *BOSS_AT,
            legs="seated",
            smile=[(P(2).start, P(2).end), (P(8).start, P(8).end)],
            blinks=[
                (P(1).start - 0.4, P(1).start - 0.26),
                (P(5).end + 0.35, P(5).end + 0.75),
                (REACTION + 0.4, REACTION + 0.54),
            ],
            nods=[
                (0, 0),
                (P(1).start, 0),
                (P(1).start + 0.3, 6),
                (P(2).start, 6),
                (P(2).start + 0.2, -4),
                (P(2).end, 0),
                (P(4).start, 0),
                (P(4).start + 0.2, -6),
                (P(4).end, 0),
                (P(6).start, 0),
                (P(6).start + 0.3, 5),
                (P(8).start, 5),
                (P(8).start + 0.3, -3),
            ],
            pupils=[
                (0, -31),
                (LAND, -31),
                (LAND + 0.3, -16),  # down at the pigeon
                (P(3).start + 0.2, -16),
                (P(3).start + 0.4, -31),  # up at Milo
                (P(6).end + 0.1, -31),
                (P(6).end + 0.3, -16),
                (P(8).start, -16),
                (P(8).start + 0.2, -31),
            ],
        ),
    ),
    beside_bench=bird,
)
cv.keys(milo.eyes, "x", [(0, -10), (P(0).end + 0.2, -10), (P(0).end + 0.4, 12)], hold=False)  # phone, then the boss


def close(at, scale, to=(540, 760)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


FRAMES = {  # angle -> scale, x, y
    "wide": (1.0, 0, 0),
    "end": (1.0, 0, 0),
    "boss": close(BOSS_AT[:2], 1.65),
    "milo": close(MILO_AT[:2], 1.65),
    "pigeon": close((BIRD[0] + 42, BIRD[1] - 42), 2.4, (540, 950)),  # the frame still ends on the path
}
camera.reframe(cv, park, [(c.time, *FRAMES[c.angle]) for c in t.cuts])


def phone_card(index: int, who: str, status: str, show: tuple[float, float]):
    """A push notification, at two and a quarter times the café card, high in the frame."""
    holder = cv.group(ep.comp, f"push-holder-{index}", x=215, y=330, scaleX=2.25, scaleY=2.25)
    graphics.notification(cv, holder, index, who, status, show, x=0, y=0, id_prefix="push")


phone_card(1, "Pigeon", "accepted your offer", (OFFER, P(3).start + 0.4))
phone_card(2, "Pigeon · Team Lead", "wants to connect", (CONNECT, ENDING))
hook = graphics.location_slate(cv, ep.comp, "JOB HUNT: DAY 200", show=(0, P(1).start - 0.1), x=90, y=235)
graphics.scorecard(
    cv,
    ep.comp,
    "JOB MARKET",
    [("APPLICATIONS", "201", "#E6AA92"), ("REPLIES", "1 (PIGEON)", "#E6AA92"), ("SALARY", "CRUMBS", "#AAD6BD")],
    show=(ENDING + 0.3, DURATION),
    x=90,
    y=235,
    w=820,
    value_w=380,
    label_w=360,
)
specs = []
for i, p in enumerate(t.phrases):
    until = t.phrases[i + 1].start - 0.02 if i + 1 < len(t.phrases) else REACTION + 0.6
    specs.append((max(0.0, p.start - 0.05), until, p.caption, f"dialogue-{i + 1}"))
spoken = ep.captions(
    specs,
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-7": [("He works for ", False), ("crumbs.", True)],
        "dialogue-8": [("I can do ", False), ("crumbs.", True)],
    },
)
ep.hide_on_cover(hook, *spoken)
ep.markers(extra=[("marker-toss", TOSS, "Crumbs tossed"), ("marker-connect", CONNECT, "Pigeon wants to connect")])
ep.instagram(POSTS["culture-fit"])
ep.finish()

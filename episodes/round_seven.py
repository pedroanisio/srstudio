#!/usr/bin/env python3
"""Round Seven, built with srstudio: the seventh round at a building that has already made him a fire warden.

    srstudio record round-seven PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build round-seven PROJECT    # → PROJECT/round-seven.scene.xml

He walks into reception and a coffee slides into his hand. "Morning! Round seven?" "Round seven." The office: "So. Tell
me about yourself." "We've met. Six times." "Great energy. One more round." Reception: a lanyard with his face on it.
"Your parking space came through." "I don't work here." "You're a fire warden." Streamers, the Boss, a cake: 5 YEARS
SHORTLISTED. "Surprise!" Nothing. "Do I have the job?" "It's between you and Dave." He turns to Ava, she nods at the
wall, and the plaque he has walked past every day comes up in a crash zoom. Then she leans in. "Dave has a pension."

The plaque hangs in every reception shot as scrawl and is lettered only for the zoom. No music: the foley is synthesized
here. It declares no engine safe area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from round_seven_audio import INTERVIEW
from srstudio import (
    OFFICE,
    Episode,
    EpisodeSpec,
    cast,
    cutout_arm,
    cutout_hiring,
    cutout_key,
    cutout_lobby,
    foley,
    locations,
    props,
    signature,
)
from srstudio import interview as iv_audio
from srstudio.rig import Performance

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="round-seven",
        title=INTERVIEW.title,
        description="Job-hunting comedy: the seventh interview round at a building that has already given the "
        "candidate a parking space and a fire warden's lanyard. Native vector animation; ElevenLabs dialogue, "
        "synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=3311,
        background="#EDE5D8",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        bleed=True,
    )
)
t, cv = ep.t, ep.cv
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
LANYARD, TURN, ZOOM = float(t.meta["lanyard"]), float(t.meta["turn"]), float(t.meta["zoom"])

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))
ARRIVE = spans["arrive"][0]
PARTY = spans["party"][0]
PLAQUE = spans["plaque"][0]
WHISPER = spans["whisper"][0]
LOBBY = spans["arrive"] + spans["lanyard"] + spans["party"] + spans["plaque"] + spans["whisper"]
THEN = spans["lanyard"][0][0]

CANDIDATE = (210, 830, 1.6)
AVA = (700, 790, 1.3)
AVA_PARTY = (840, 712, 1.3)
AVA_CLOSE = (610, 700, 1.3)
BOSS = (520, 690, 1.35)
TALL = (420, 470, 2.2)
SEEN_LOW = (540, 737, 2.07)
WALL = (300, 500)  # the plaque's middle: left of the logo, over his head
CUP_ROW = 1022
FLICK, CAUGHT = 0.22, 0.86
CUP_FROM, CUP_TO = 560.0, 450.0
YEARS = tuple(str(2014 + n) for n in range(12))

foley.write_bursts(ROOT / "assets" / "slide.wav", [FLICK + 0.03], DURATION, foley.SCRAPE, seed=3312)
foley.write_bursts(ROOT / "assets" / "catch.wav", [CAUGHT], DURATION, foley.KNOCK, seed=3313)
foley.write_whoosh(ROOT / "assets" / "zoom.wav", [ZOOM - 0.08], DURATION, seed=3314)
foley.write_bursts(ROOT / "assets" / "plaque.wav", [ZOOM + 0.22], DURATION, foley.KNOCK, seed=3315)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("slide", "assets/slide.wav", {"role": "effects", "gain": -8}),
        ("catch", "assets/catch.wav", {"role": "effects", "gain": -14}),
        ("zoom", "assets/zoom.wav", {"role": "effects", "gain": -8}),
        ("plaque", "assets/plaque.wav", {"role": "effects", "gain": -12}),
    ],
    loudness="-14",
)


def ava_at_counter(g):
    """Her left arm is drawn in the slot in front of the counter, where the cup and the lanyard are."""
    cv.gate(g, spans["arrive"] + spans["lanyard"])
    ep.perform(
        cast.Barista(cv, tag="ava-counter"),
        g,
        *AVA,
        mouth=ep.mouth("barista", smile=[(0.0, L[0].start), (L[0].end, L[5].start), (L[7].end, DURATION)]),
        blinks=[(L[1].start, L[1].start + 0.14), (L[6].end - 0.05, L[6].end + 0.09)],
        nods=[(0, 0), (L[0].start, 0), (L[0].start + 0.2, -3), (L[0].end, 0), (L[7].start, 0), (L[7].start + 0.2, 3)],
        free_arms=("left",),
    )


def ava_with_cake(g):
    cv.gate(g, spans["party"] + spans["plaque"])
    who = cast.Barista(cv, tag="ava-party")
    ep.perform(
        who,
        g,
        *AVA_PARTY,
        mouth=ep.mouth("barista", smile=[(0.0, L[8].start), (L[8].end, TURN)]),
        blinks=[(L[8].end + 0.7, L[8].end + 0.84)],
        nods=[(0, 0), (TURN, 0), (TURN + 0.12, -9), (TURN + 0.24, -3), (TURN + 0.36, -9)],
        name=None,
    )
    cv.keys(who.eyes, "x", [(0, 0), (TURN, 0), (TURN + 0.1, -9)], hold=False)
    cv.keys(who.eyes, "y", [(0, 0), (TURN, 0), (TURN + 0.1, -7)], hold=False)


def ava_close(g):
    cv.gate(g, spans["whisper"])
    who = cast.Barista(cv, tag="ava-close")
    ep.perform(who, g, *AVA_CLOSE, mouth=ep.mouth("barista"), blinks=[(L[11].end + 0.2, L[11].end + 0.34)],
               nods=[(0, -6), (L[11].start, -6), (L[11].start + 0.4, -8)], name=None)  # fmt: skip
    cv.keys(who.eyes, "x", [(0, -8)], hold=False)


def the_boss(g):
    cv.gate(g, spans["party"] + spans["plaque"])
    ep.perform(
        cast.Manager(cv, tag="boss-party"),
        g,
        *BOSS,
        mouth=ep.mouth("manager", smile=[(0.0, L[10].start), (L[10].end, DURATION)]),
        blinks=[(L[8].end + 0.3, L[8].end + 0.44)],
        nods=[(0, 0), (L[10].start, 0), (L[10].start + 0.3, 3)],
    )


def behind_counter(g):
    ava_at_counter(cv.group(g, "ava-at-the-counter"))
    ava_with_cake(cv.group(g, "ava-at-the-party"))
    ava_close(cv.group(g, "ava-leaning-in"))
    the_boss(cv.group(g, "boss-at-the-party"))


def on_counter(g):
    cake = cv.group(g, "party-cake")
    cv.gate(cake, spans["party"] + spans["plaque"] + spans["whisper"])
    cutout_lobby.sheet_cake(cv, cake, 690, locations.COUNTER_Y + 8, lines=("5 YEARS", "SHORTLISTED"), scale=1.45)


def the_candidate(g):
    cv.gate(g, LOBBY)
    who = cast.Candidate(cv, tag="candidate-lobby")
    x, y, size = CANDIDATE
    node = ep.perform(
        who,
        g,
        *CANDIDATE,
        mouth=ep.mouth("candidate"),
        blinks=[(L[8].end + 0.55, L[8].end + 0.69), (ZOOM - 0.2, ZOOM - 0.06), (L[11].end + 0.05, L[11].end + 0.2)],
        nods=[(0, 0), (L[6].start, 0), (L[6].start + 0.2, 3), (L[6].end, 0)],
        arms="articulated",
        legs="standing",
    )
    cv.keys(node, "x", [(0.0, -230.0), (0.72, float(x))], hold=False, kind="sine-out")
    cv.keys(node, "y", [(0.0, y), (0.16, y - 12), (0.32, y), (0.48, y - 12), (0.64, y), (0.8, y)], hold=False)
    cv.keys(who.eyes, "x", [(0, 7), (TURN, 7), (TURN + 0.14, 11), (WHISPER[0], 11)], hold=False)
    down = (120.0, 270.0)
    catch = ((CUP_TO + 26 - x) / size, (CUP_ROW + 6 - y) / size)
    done = ARRIVE[1]
    cv.gate(who.right_arm, [(done, DURATION)])
    track = [
        (0.0, *down),
        (CAUGHT - 0.2, catch[0] + 8, catch[1] + 16),
        (CAUGHT, *catch),
        (done, catch[0], catch[1] - 14),
    ]
    arm = cutout_arm.arm(cv, who.group, "candidate-catch", (67, 148), track, upper=96, fore=96, bend=-1)
    cv.gate(arm.group, [ARRIVE])
    cup = cv.group(arm.grip, "cup-in-hand", x=-26 / size)
    cv.gate(cup, [(CAUGHT, done)])
    props.coffee_cup(cv, cup, 0, 0, 1 / size)


def ava_arm(g):
    """In frame pixels, on the near side of the counter: the flick, then the lanyard held out."""
    shoulder = (AVA[0] - 66 * AVA[2], AVA[1] + 140 * AVA[2])
    rest = (CUP_FROM + 30, 1046.0)
    out = (420.0, 880.0)
    lift, lands = THEN + 0.05, LANYARD + 0.05
    back = spans["lanyard"][0][1] - 0.05
    track = [(0.0, *rest), (FLICK - 0.1, rest[0] + 24, rest[1]), (FLICK + 0.1, rest[0] - 60, rest[1]),
             (0.7, *rest), (lift, *rest), (lands, *out), (back, *out)]  # fmt: skip
    arm = cutout_arm.arm(
        cv, g, "ava-reach", shoulder, track, upper=150, fore=150, bend=1, width=6.5, hand=50, skin=cast.Barista.skin
    )
    cv.gate(arm.group, spans["arrive"] + spans["lanyard"])
    held = cv.group(arm.grip, "lanyard-held")
    cv.gate(held, [(lift, back + 0.05)])

    def photo(window):
        face = cast.Candidate(cv, tag="candidate-photo")
        face.build(window, 0, -4, 0.27, Performance(mouth=[(0.0, "smile")]))

    cutout_lobby.id_lanyard(cv, held, 0, 14, photo=photo, label="STAFF", scale=1.25)


def the_cup(g):
    moving = cv.group(g, "cup-sliding", y=CUP_ROW)
    cv.gate(moving, [(0.0, CAUGHT)])
    cv.keys(moving, "x", [(0.0, CUP_FROM), (FLICK, CUP_FROM), (CAUGHT, CUP_TO)], hold=False, kind="sine-out")
    props.coffee_cup(cv, moving, 0, 0, 1.0)


def at_counter(g):
    the_candidate(cv.group(g, "candidate-at-the-counter"))
    the_cup(g)
    ava_arm(cv.group(g, "ava-arm-in-front"))


def wall_shelf(g):
    """The cup and then the cake take the counter, so the cactus sits on a bracket shelf on the plain wall, clear of
    Ava, of the bug and of everyone's hands until the zoom."""
    cv.path(g, "M968 482 L968 512 L994 482Z", "#D8CCBB", cv.ink, 2.5)
    cv.path(g, "M1040 482 L1040 512 L1014 482Z", "#D8CCBB", cv.ink, 2.5)
    cv.rect(g, 948, 470, 112, 12, "#F4F0E9", cv.ink, 2.5, radius=2)
    signature.cactus(cv, g, 1004, 472, 0.6)


def the_room(g):
    """What hangs on the wall: the plaque always, the streamers from the party on."""
    cutout_lobby.wall_plaque(
        cv, g, *WALL, title="CANDIDATE OF THE YEAR", name="DAVE", years=YEARS, read=[PLAQUE], scale=1.08
    )


def manager_at_desk(g):
    cv.gate(g, spans["desk"])
    ep.perform(
        cast.Manager(cv, tag="boss-desk"),
        g,
        *TALL,
        mouth=ep.mouth("manager", smile=[(L[4].start, L[4].start + 0.9)]),
        blinks=[(L[2].end + 0.05, L[2].end + 0.19)],
        nods=[(0, 0), (L[2].start, 0), (L[2].start + 0.3, 3), (L[2].end, 0), (L[4].start, 0), (L[4].start + 0.3, -3)],
    )


def on_desk(g):
    props.papers(cv, g, 470, 1190, 1.1, 4)
    before = cv.group(g, "candidate-low", y=590, x=-110, scaleX=0.72, scaleY=0.72)
    props.candidate_back(cv, before)


def in_chair(g):
    ep.perform(
        cast.Candidate(cv, tag="candidate-chair"),
        g,
        *SEEN_LOW,
        mouth=ep.mouth("candidate"),
        blinks=[(L[3].start + 0.5, L[3].start + 0.64)],
    )


finish = locations.finish(cv, ep.comp)
lobby = locations.reception(cv, finish, behind_counter, on_counter, at_counter, shots=LOBBY, cactus=wall_shelf)
wall = cv.group(lobby, "wall-of-the-lobby")
# The wall's props sit over the set's own slat wall, and under nobody: the cast keeps clear of them.
the_room(wall)
streamers = cv.group(wall, "party-streamers")
cv.gate(streamers, spans["party"] + spans["plaque"] + spans["whisper"])
cutout_lobby.paper_streamers(cv, streamers, 170, 910, 196, swags=4, sag=62.0)

cutout_hiring.hiring_office(cv, finish, behind_desk=manager_at_desk, on_desk=on_desk, shots=spans["desk"])
locations.office_reverse(cv, finish, in_chair=in_chair, shots=spans["chair"], depth=6)

SIZE, AT = 3.0, (WALL[0], WALL[1] + 8)
CLOSE, CLOSE_AT = 1.36, (430.0, 830.0)
for prop, base, near, whisper in (
    ("scaleX", 1.0, SIZE, CLOSE),
    ("scaleY", 1.0, SIZE, CLOSE),
    ("x", 0.0, 540 - AT[0] * SIZE, 540 - CLOSE_AT[0] * CLOSE),
    ("y", 0.0, 680 - AT[1] * SIZE, 800 - CLOSE_AT[1] * CLOSE),
):
    cv.keys(
        lobby,
        prop,
        [(0.0, base), (ZOOM, base), (ZOOM + 0.2, near), (WHISPER[0] - 1 / 120, near), (WHISPER[0], whisper)],
        hold=False,
    )

hook = cutout_key.key_line(cv, ep.comp, "ANOTHER INTERVIEW", 0.0, 3.0, top=300, font=(ROOT / ep.spec.font).read_bytes())
spoken = ep.captions(ep.spoken_captions(min_seconds=0.84), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(hook, *spoken)
ep.markers(extra=[("marker-cake", PARTY[0], "The cake"), ("marker-plaque", ZOOM, "The plaque")])
ep.instagram(POSTS["round-seven"])
ep.finish()

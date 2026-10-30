#!/usr/bin/env python3
"""I'm Quitting, built with srstudio: forty years of quitting today, and one friend who has heard it all.

    srstudio record im-quitting PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build im-quitting PROJECT    # → PROJECT/im-quitting.scene.xml

At the coffee machine, already mid-rant: "That's it. I'm quitting. Today." His friend, eyes on his own mug: "Mm." The
same shot, a new mug, a bigger plant, and the wall board reads 2,190 days since "today". "This time I mean it." "Mm."
Twelve years in, his friend slaps a planner down. "You said Friday." "Which Friday?" Every Friday is circled.
"Twelve years of them." A party, a banner, a gold watch. "Forty years. Thank you." He taps the mic. "That's it. I'm
quitting." His friend, the same mug: "Mm."

The first frame already moves (arm B of the ``sp-hook_motion`` test): his arm is up and he is talking. Time passes on
the props, not on the people: the mug, the plant, the board. Like *Neighbor Names* it declares no engine safe area, so
captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from im_quitting_audio import INTERVIEW
from instagram_posts import POSTS
from srstudio import OFFICE, Episode, EpisodeSpec, cast, cutout_office, locations, props
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="im-quitting",
        title="I'm Quitting",
        description="Office comedy: a man who has been quitting today for forty years, and the friend who answers him "
        "the same way every time. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        **iv_audio.spec_font(INTERVIEW.font, project_root(__file__)),
        seed=26102,
        background="#E0BD73",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv = ep.t, ep.cv
SIX, TWELVE, SLAP, RIFFLE, TAP = (float(t.meta[k]) for k in ("day_six", "day_twelve", "slap", "riffle", "tap"))
CLAPS = tuple(float(x) for x in t.meta["applause"])
REACTION, DURATION = t.reaction, t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
QUIT_AT, FRIEND_AT = (290, 720, 1.6), (790, 720, 1.6)
MIC_AT, CLOSE_AT = (540, 790, 1.6), (540, 880, 2.4)
FRIEND_MUG = "#3F7F8C"
DOWN = [(0, -17)]  # his pupils, on his own mug
EPS = 1 / 120

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))


def rant(start: float, end: float, up: float, down: float, step: float = 0.2) -> list[tuple[float, float]]:
    """The forearm beating time between ``up`` and ``down`` degrees."""
    keys, at, high = [], start, True
    while at < end:
        keys.append((at, up if high else down))
        at, high = at + step, not high
    return keys


def people(g):
    quitter = cast.Candidate(cv, tag="quitter-character")
    friend = cast.Manager(cv, tag="friend-character")
    ep.perform(
        quitter,
        g,
        *QUIT_AT,
        arms="articulated",
        pointing=[(0.0, L[5].end + 0.2)],
        forearm=[
            *rant(0.0, L[0].end, -176, -140),  # the finger up from the first frame, beating time
            (L[0].end + 0.2, -10),
            *rant(L[2].start, L[2].end, -172, -146, 0.26),
            (L[2].end + 0.2, -10),
            (L[5].start, -10),
            (L[5].start + 0.15, -168),  # "Which Friday?"
            (L[5].end + 0.1, -168),
        ],
        mouth=ep.mouth("candidate"),
        blinks=[(L[1].start + 0.05, L[1].start + 0.19), (L[3].start + 0.05, L[3].start + 0.19)],
        nods=[(0, -5), (0.25, 5), (0.5, -6), (0.8, 4), (1.1, -6), (L[0].end, 2), (L[2].start, -3), (L[2].end, 3)],
    )
    ep.perform(
        friend,
        g,
        *FRIEND_AT,
        mouth=ep.mouth("manager"),
        pupils=DOWN,
        blinks=[(0.9, 1.04), (SIX + 1.3, SIX + 1.44)],
        nods=[(0, 2)],
    )


def on_counter(g):
    cutout_office.drip_machine(cv, g, 540, 1240, pours=((0.0, 3.4),), scale=0.78)
    cutout_office.office_mug(cv, g, 800, 1255, colour=FRIEND_MUG, scale=1.3, id="friend-mug")
    for name, colour, label, a, b in (
        ("mug-one", "#F2EDE0", None, 0.0, SIX),
        ("mug-six", "#E2574A", "6 YEARS", SIX, TWELVE),
        ("mug-twelve", "#2F7D4F", "12 YEARS", TWELVE, DURATION),
    ):
        held = cv.group(g, f"{name}-shot")
        cv.gate(held, [(a, b)])
        cutout_office.office_mug(cv, held, 200, 1262, colour=colour, label=label, scale=1.3, id=name)
    for name, scale, a, b in (
        ("plant-one", 0.13, 0.0, SIX),
        ("plant-six", 0.42, SIX, TWELVE),
        ("plant-twelve", 0.8, TWELVE, DURATION),
    ):
        grown = cv.group(g, f"{name}-shot", x=950, y=1250, scaleX=scale, scaleY=scale)
        cv.gate(grown, [(a, b)])
        props.plant(cv, cv.group(grown, f"{name}-at", x=-80, y=-1139), id=name)
    planner = cv.group(g, "slapped-planner")
    cv.gate(planner, [(SLAP - 0.2, DURATION)])
    cv.keys(planner, "y", [(0, 900), (SLAP - 0.2, 900), (SLAP, 0)], hold=False)
    cutout_office.wall_planner(cv, planner, 372, 1020, scale=0.37, id="counter-planner")


def on_wall(g):
    cutout_office.days_board(
        cv, g, 540, 96, heading='DAYS SINCE "TODAY"', counts=((0.0, "0"), (SIX, "2,190"), (TWELVE, "4,380"))
    )


finish = locations.finish(cv, ep.comp)
cutout_office.break_room(cv, finish, behind_counter=people, on_counter=on_counter, on_wall=on_wall, shots=spans["room"])

planner_shot = cv.group(finish, "planner-insert")
cv.gate(planner_shot, spans["planner"])
cv.rect(planner_shot, 0, 0, 1080, 1920, "#566A66")
PAGES = ("MARCH", "JUNE", "NOVEMBER", "JANUARY", "AUGUST", "MAY", "OCTOBER", "APRIL")
months = [(0.0, "MARCH")] + [(RIFFLE + k * 0.15 + 0.05, m) for k, m in enumerate(PAGES[1:])]
cutout_office.wall_planner(cv, planner_shot, 90, 260, months=months)


def mic_stage(g):
    speaker = cast.Candidate(cv, tag="speaker-character")
    ep.perform(
        speaker,
        g,
        *MIC_AT,
        legs="standing",
        arms="articulated",
        forearm=[
            (0, -140),
            (L[7].end + 0.3, -140),
            (L[7].end + 0.6, -20),  # the watch comes down for what he came to say
        ],
        mouth=ep.mouth("candidate"),
        blinks=[(TAP - 0.5, TAP - 0.36), (TAP + 0.3, TAP + 0.44)],
        nods=[
            (0, 0),
            (L[7].start, 0),
            (L[7].start + 0.3, 5),
            (L[7].end, 5),
            (TAP, 0),
            (L[8].start, 0),
            (L[8].start + 0.3, 4),
        ],
    )
    cutout_office.gold_watch(cv, speaker.forearm, -9, 140, gleam=L[7].start + 0.2, scale=0.55)
    cutout_office.stage_mic(cv, g, 500, 1900, height=900)


cutout_office.office_party(
    cv,
    finish,
    stage=mic_stage,
    front=lambda g: cutout_office.party_crowd(cv, g, 1490, claps=(CLAPS,)),
    banner="40 YEARS",
    shots=spans["mic"],
)


def friend_close(g):
    friend = cast.Manager(cv, tag="close-friend-character")
    ep.perform(
        friend,
        g,
        *CLOSE_AT,
        legs="standing",
        mouth=ep.mouth("manager"),
        pupils=DOWN,
        blinks=[(REACTION + 0.4, REACTION + 0.7)],
    )
    cutout_office.office_mug(cv, g, 760, 1650, colour=FRIEND_MUG, scale=2.2, id="close-mug")


cutout_office.office_party(
    cv, finish, stage=friend_close, banner="40 YEARS", id="location-office-party-close", shots=spans["friend"]
)

spoken = ep.captions(ep.spoken_captions(tail=0.25), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(*spoken)
ep.markers(extra=[("marker-board", SIX, "Day 2,190"), ("marker-mic", TAP, "He taps the mic")])
ep.instagram(POSTS["im-quitting"])
ep.finish()

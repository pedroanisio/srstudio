#!/usr/bin/env python3
"""Episode 09 — Upside Down, built with srstudio: the polished reception and conference room.

    python3 upside_down_audio.py PROJECT --key-stdin < key   # generated clips, resolved and pinned by the engine
    python3 upside_down.py PROJECT                            # → PROJECT/upside-down.scene.xml

Milo, the Wi-Fi guy from episode 05, turns up at reception for the quarterly review. The applicant from the
interviews now works the front desk: "Conference room. Bring tissues." Upstairs the boss shows a red chart going
down. The speakerphone beeps: "Sir? Your board is upside down." Flip: the chart goes up. "Record quarter! Bonuses
for everyone!" Beep: "Including reception?" A long stare at the speakerphone. Flip. "It's upside down again."
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import Episode, EpisodeSpec, camera, cast, graphics, layout, locations, props

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="upside-down",
        number="09",
        title="Upside Down — The Interview 07",
        description="Office comedy: a quarterly review saved, and unsaved, by flipping the whiteboard. Native "
        "vector animation in the polished reception and conference room; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=92028,
        background="#D5DFDF",
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # text and captions held inside x 80–920, y 220–1420 by the engine
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
FLIP, BACK, REACTION, ENDING, DURATION = t.flip_start, t.flip_back_start, t.reaction, t.ending, t.duration
FX = {s.name: s for s in t.sound_effects}
TURN = 0.12  # half a flip: the board is edge-on at FLIP + TURN, where the drawings swap
EDGE = 0.03  # the narrowest the board gets: never a zero-height (singular) transform

# -- reception: Milo at the counter, the applicant behind it ----------------------------------------------
clerk = cast.Candidate(cv, tag="candidate-reception")
milo = cast.Customer(cv, tag="milo-reception")
reception = ep.setup(
    locations.reception,
    t.shots({"reception", "clerk"}),
    behind_desk=lambda g: ep.perform(
        clerk,
        g,
        *locations.RECEPTION_CLERK,
        smile=[(P(1).end + 0.05, DURATION)],
        blinks=[(P(0).end - 0.2, P(0).end - 0.06), (P(1).start + 0.6, P(1).start + 0.74)],
        nods=[(0, 0), (P(1).start, 0), (P(1).start + 0.25, -4), (P(1).end, 2)],
    ),
    at_desk=lambda g: ep.perform(
        milo,
        g,
        *locations.RECEPTION_VISITOR,
        mouth=ep.mouth("milo", smile=[(0, P(0).start), (P(0).end, P(1).end)]),
        blinks=[(0.45, 0.59), (P(1).end - 0.3, P(1).end - 0.16)],
        nods=[(0, 0), (P(0).start, 0), (P(0).start + 0.3, 3), (P(0).end, 0), (P(1).end - 0.2, -5)],
    ),
)
cv.keys(clerk.eyes, "x", [(0, 0), (0.8, -9)], hold=False)  # the clerk watches Milo come in
cx, cy, _ = locations.RECEPTION_CLERK
camera.reframe(cv, reception, [(0, 1, 0, 0), (t.cuts[1].time, 1.45, 540 - cx * 1.45, 760 - cy * 1.45)])


# -- conference room: the boss, the board that flips, the speakerphone that talks ----------------------------
def board(g):
    bx, by, bw, bh = locations.CONFERENCE_BOARD
    flip = cv.group(g, "whiteboard-flip", x=bx + bw / 2, y=by + bh / 2)
    down = props.whiteboard(cv, flip, -bw / 2, -bh / 2, bw, bh, rising=False, id="board-down")
    up = props.whiteboard(cv, flip, -bw / 2, -bh / 2, bw, bh, rising=True, id="board-up")
    cv.gate(down, [(0, FLIP + TURN), (BACK + TURN, DURATION)])
    cv.gate(up, [(FLIP + TURN, BACK + TURN)])
    squash = [(0, 1)]
    wobble = [(0, 0)]
    for at in (FLIP, BACK):
        squash += [(at, 1), (at + TURN, EDGE), (at + 2 * TURN, 1.06), (at + 2 * TURN + 0.08, 1)]
        wobble += [(at + 2 * TURN, 0), (at + 2 * TURN + 0.06, -3), (at + 2 * TURN + 0.14, 2), (at + 2 * TURN + 0.22, 0)]
    cv.keys(flip, "scaleY", squash, hold=False)
    cv.keys(flip, "rotation", wobble, hold=False)


SPEAKS = [(FX["speaker-beep"].start, P(3).end + 0.1), (FX["speaker-beep-2"].start, P(5).end + 0.1)]


def speaking(g):
    """The speakerphone's ring lights up while reception is on the line."""
    lit = cv.group(g, "speaker-live", x=560, y=1323)
    cv.gate(lit, SPEAKS)
    cv.ellipse(lit, -70, -34, 140, 68, "#5FD1A0", opacity=0.22)
    ring = cv.ellipse(lit, -24, -9, 48, 18, "#B8F5D8", "#5FD1A0", 4)
    cv.expression(ring, "opacity", ".65+.35*Math.sin(time*18)")


boss = cast.Manager(cv, tag="manager-conference")
conference = ep.setup(
    locations.conference_room,
    t.shots({"conference", "speaker", "board", "manager", "end"}),
    rising=None,
    on_wall=board,
    on_table=speaking,
    behind_table=lambda g: ep.perform(
        boss,
        g,
        *locations.CONFERENCE_SEAT,
        smile=[(P(4).start - 0.1, P(5).start)],
        blinks=[
            (P(2).start - 0.3, P(2).start - 0.16),
            (P(3).end + 0.05, P(3).end + 0.19),
            (P(5).end + 0.25, P(5).end + 0.65),  # the long, slow blink at "Including reception?"
            (REACTION + 0.4, REACTION + 0.54),
        ],
        nods=[
            (0, 0),
            (P(2).start, 0),
            (P(2).start + 0.4, 3),
            (P(2).end, 3),
            (P(4).start, 3),
            (P(4).start + 0.2, -6),
            (P(4).start + 0.5, 4),
            (P(4).start + 0.8, -4),
            (P(4).end, 0),
            (P(5).end + 0.2, 0),
            (P(5).end + 0.5, -7),
        ],
        brows=(
            [(0, 0), (P(4).start - 0.1, 0), (P(4).start + 0.1, 10), (P(4).end, 10), (P(5).end, -6)],
            [(0, 0), (P(4).start - 0.1, 0), (P(4).start + 0.1, -10), (P(4).end, -10), (P(5).end, 6)],
        ),
        pupils=[(0, -31), (P(5).start, -31), (P(5).start + 0.2, -18), (BACK, -18), (BACK + 0.2, -31)],
    ),
)
mx, my, _ = locations.CONFERENCE_SEAT
bx, by, bw, bh = locations.CONFERENCE_BOARD
FRAMES = {  # angle -> scale, x, y: the conference group is reframed on every cut
    "conference": (1.0, 0, 0),
    "end": (1.0, 0, 0),
    "speaker": (2.6, 540 - 560 * 2.6, 250 - locations.CONFERENCE_TABLE_Y * 2.6),  # the table edge near the top
    "board": (1.8, 540 - (bx + bw / 2) * 1.8, 800 - (by + bh / 2) * 1.8),
    "manager": (1.5, 540 - mx * 1.5, 780 - my * 1.5),
}
camera.reframe(cv, conference, [(c.time, *FRAMES[c.angle]) for c in t.cuts if c.angle in FRAMES])

for name, text, at, rot in (("flip-mark", "FLIP!", FLIP, -9), ("flop-mark", "FLOP.", BACK, 8)):
    graphics.squeak_mark(
        cv, ep.comp, text, show=(at + TURN, at + 0.9), x=540, y=1150, w=300, h=100, size=62, rotation=rot, id=name
    )

graphics.episode_slate(cv, ep.comp, "09", "UPSIDE DOWN", x=90, y=235)
graphics.scorecard(
    cv,
    ep.comp,
    "Q3 REVIEW",
    [
        ("SALES", "UPSIDE DOWN", "#E6AA92"),
        ("BONUSES", "ALSO DOWN", "#E6AA92"),
        ("RECEPTION", "TAKING NOTES", "#AAD6BD"),
    ],
    show=(ENDING + 0.3, DURATION),
    x=90,
    y=235,
    w=820,
    value_w=380,
    label_w=320,
    prefix="q3",
)
specs = []
for i, p in enumerate(t.phrases):
    until = t.phrases[i + 1].start - 0.02 if i + 1 < len(t.phrases) else REACTION + 0.6
    specs.append((max(0.0, p.start - 0.05), until, p.caption, f"dialogue-{i + 1}"))
ep.captions(
    specs,
    x=80,
    y=1240,
    width=840,
    highlights={
        "dialogue-2": [("Conference room.\n", False), ("Bring tissues.", True)],
        "dialogue-4": [("SPEAKER: Sir? Your board\n", False), ("is upside down.", True)],
        "dialogue-7": [("It's upside down\n", False), ("again.", True)],
    },
)
ep.markers(extra=[("marker-flip", FLIP, "Board flipped"), ("marker-flip-back", BACK, "Board flipped back")])
ep.instagram(POSTS["upside-down"])
out = ep.finish()
ep.check_overlays(out, ["episode-slate", "flip-mark", "flop-mark", "final-scorecard"])

#!/usr/bin/env python3
"""Episode 16 — Market Rate, built with srstudio: the candidate from the interview series asks for a raise.

    python3 market_rate_audio.py PROJECT --key-stdin < key   # generated clips, resolved and pinned by the engine
    python3 market_rate.py PROJECT                            # → PROJECT/market-rate.scene.xml

The candidate got the job. Alone in the conference room, he asks the boss on the speakerphone about his salary.
"Look at the chart. Record year!" "So, a raise?" "Better. A title. You're Senior now." "Does Senior pay more?"
"It's longer." Ping: his own job, posted online, paying more. "That's for external talent." "So if I quit and
reapply?" "Hold, please." Hold music. "Your interview is Thursday." Ping: the boss endorsed him for loyalty.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import OFFICE, Episode, EpisodeSpec, camera, cast, graphics, layout, locations

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ep = Episode(
    EpisodeSpec(
        slug="market-rate",
        number="16",
        title="Market Rate — Comedy Cut 16",
        description="Office comedy: an employee asks for a raise over the conference-room speakerphone and finds his "
        "own job posted online, paying more. Native vector animation; ElevenLabs dialogue and sound effects.",
        root=project_root(__file__),
        seed=16041,
        background="#D5DFDF",
        palette=OFFICE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        safe_area=layout.VERTICAL,  # text and captions held inside x 80–920, y 220–1420 by the engine
    )
)
ep.audio(extra=[("room-tone", "assets/room-tone.wav", {"role": "ambience"})])
t, cv, P = ep.t, ep.cv, ep.P
POSTING, HOLD, ENDORSE = t.posting_start, t.hold_start, t.endorse_start
REACTION, ENDING, DURATION = t.reaction, t.ending, t.duration
FX = {s.name: s for s in t.sound_effects}
BOSS = [p for p in t.phrases if p.role == "manager"]
HOLD_END = HOLD + FX["hold-music"].duration
# the ring lights while the boss talks and while his hold music plays
TALK = sorted([(p.start, p.end) for p in BOSS] + [(HOLD, HOLD_END)])
SEAT = locations.CONFERENCE_SEAT
PHONE = (560, 1310)  # the speakerphone on the conference table
BOARD = (830, 510)  # the whiteboard's centre


def listening(spans, depth: float) -> list[tuple[float, float]]:
    """Eye keys: down at the speakerphone by ``depth`` in each span, back up between them."""
    keys: list[tuple[float, float]] = [(0, 0)]
    for start, end in spans:
        keys += [(start, 0), (start + 0.15, depth), (end, depth), (end + 0.2, 0)]
    return keys


candidate = cast.Candidate(cv)
room = ep.setup(
    locations.conference_room,
    [(0, DURATION)],
    speaker_talk=TALK,
    behind_table=lambda g: ep.perform(
        candidate,
        g,
        *SEAT,
        mouth=ep.mouth("candidate", smile=[(P(2).start - 0.1, P(3).start + 0.4), (P(8).end + 0.1, P(9).start)]),
        blinks=[
            (1.6, 1.74),
            (P(3).end + 0.2, P(3).end + 0.34),
            (P(5).end + 0.3, P(5).end + 0.7),  # "It's longer.": a slow blink
            (P(7).end + 0.1, P(7).end + 0.24),
            (REACTION + 0.3, REACTION + 0.8),
        ],
        nods=[
            (0, 0),
            (P(1).start, 0),
            (P(1).start + 0.3, 5),
            (P(2).start, 5),
            (P(2).start + 0.2, -5),  # leans in, hopeful
            (P(3).end, -5),
            (P(3).end + 0.3, 0),
            (P(6).start, 0),
            (P(6).start + 0.25, -7),
            (P(7).end, 0),
            (P(8).start, 0),
            (P(8).start + 0.3, -6),
            (REACTION, -6),
            (REACTION + 0.3, 8),
        ],
    ),
)
cv.keys(candidate.eyes, "y", listening(TALK, 9), hold=False)


def close(at, scale, to=(540, 760)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


FRAMES = {  # angle -> scale, x, y
    "wide": (1.0, 0, 0),
    "end": (1.0, 0, 0),
    "candidate": close((SEAT[0], SEAT[1] - 40), 1.55, (540, 900)),
    "phone": close(PHONE, 1.25, (540, 1110)),  # the ring above the captions, his face above it
    "board": close(BOARD, 1.9, (540, 860)),
}
camera.reframe(cv, room, [(c.time, *FRAMES[c.angle]) for c in t.cuts])

hook = graphics.location_slate(cv, ep.comp, "ASKING FOR A RAISE", show=(0, P(2).start - 0.1), x=90, y=235)
posting_holder = cv.group(ep.comp, "posting-holder", x=82, y=240, scaleX=1.16, scaleY=1.16)
posting = graphics.password_card(
    cv,
    posting_holder,
    "NOW HIRING: YOUR JOB",
    "Pays more.",
    "External candidates only. Apply today!",
    show=(POSTING, P(7).start + 0.3),
    x=0,
    y=0,
    id="job-posting",
    prefix="posting",
)
holder = cv.group(ep.comp, "endorse-holder", x=215, y=330, scaleX=2.25, scaleY=2.25)
graphics.notification(
    cv, holder, 1, "Your boss", "endorsed you for Loyalty", (ENDORSE, ENDING), x=0, y=0, id_prefix="push"
)
graphics.scorecard(
    cv,
    ep.comp,
    "SALARY REVIEW",
    [("RAISE", "NONE", "#E6AA92"), ("TITLE", "SENIOR", "#AAD6BD"), ("STATUS", "APPLICANT", "#E6AA92")],
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
        "dialogue-6": [("It's ", False), ("longer.", True)],
        "dialogue-11": [("Your interview is ", False), ("Thursday.", True)],
    },
)
ep.hide_on_cover(hook, posting, *spoken)
ep.markers(
    extra=[
        ("marker-posting", POSTING, "His job, posted"),
        ("marker-hold", HOLD, "Hold music"),
        ("marker-endorse", ENDORSE, "Endorsed for loyalty"),
    ]
)
ep.instagram(POSTS["market-rate"])
ep.finish()

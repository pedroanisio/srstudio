#!/usr/bin/env python3
"""Stick 08 — Group 9, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 group_nine_audio.py PROJECT --font DIR   # voices, bed, timeline.json
    python3 group_nine.py PROJECT                                         # → PROJECT/group-nine.scene.xml

At the gate, Sam asks if Group 9 is boarding: after the luggage, and his bag is Group 4. Group 8 costs extra. The
plane can't leave without him? Everyone says that. He puts on his cap: he's the pilot. Pilots are Group 9. The
button is the cabin: the captain speaks from the middle seat, both armrests taken.

The gate is ``stick_airport``: the terminal with its window and boarding sign (calling ``NOW`` per take), the
carry-on with its tag beside Sam at the left, the agent mirrored at ``AGENT_AT`` behind the podium. Each take is a
shot: the wide gate, Sam's close-up, the agent's, the bag's tag, and the cabin row with Sam in the middle seat
between two passengers in ``spread`` poses. The hook card stays up through the first take; the words come one at a
time as spoken.
"""

import os

from _common import project_root
from group_nine_audio import AGENT, BAG_TAG, BAG_X, CAPPED, GATE, NEIGHBOURS, NOW, PILOT, ROW, SAM, SEATS
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, STICK, Episode, EpisodeSpec, fonts, stick, stick_airport, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
HOOK = "Why is there\na Group 9?"
F = stick.Face
SAM_AT = (-260.0, 0.0)  # a STANDING pose here stands at x 280, facing the podium
AT_AGENT = (1.0, 0.0)
# take: [(seconds into the take, pose, face)] for Sam and for the agent at the gate
SAM_PART: dict[str, list[tuple[float, str, stick.Face]]] = {
    "01": [(0, "stand", F("open", "raised", "smile", AT_AGENT))],
    "03": [(0, "shrug", F("wide", "raised", "frown", AT_AGENT))],
    "05": [(0, "stand", F("open", "raised", "smile", AT_AGENT))],
    "07": [(0, "point", F("open", "angry", "flat", AT_AGENT))],
    "09": [(0, "hands-hips", F("half", "flat", "smirk", (0.4, 0.0)))],
    "10": [(0, "hands-hips", F("wide", "worried", "frown", AT_AGENT))],
}
AGENT_PART: dict[str, list[tuple[float, str, stick.Face]]] = {
    "01": [(0, "stand", F("half", "flat", "smile", (1.0, 0.1)))],
    "06": [(0, "shrug", F("happy", "raised", "smile", (1.0, 0.1)))],
    "08": [(0, "hands-hips", F("half", "flat", "flat", (1.0, 0.1)))],
    "10": [(0, "point", F("half", "raised", "smirk", (1.0, 0.1)))],
}
# the cabin: Sam in the middle seat, the window seat asleep, the aisle seat staring at him
CABIN = (
    (stick_airport.SEATS[0], "spread", NEIGHBOURS[0], F("closed", "flat", "flat", (0.0, 0.0))),
    (stick_airport.SEATS[2], "spread", NEIGHBOURS[1], F("open", "flat", "frown", (-1.0, 0.0))),
)
SAM_SEATED = {"11": F("half", "worried", "flat", (0.0, 0.2)), "12": F("open", "flat", "flat", (0.0, 0.0))}
SAM_ZOOM, SAM_FOCUS, SAM_TO = 1.8, (320, 880), (540, 900)
AGENT_ZOOM, AGENT_FOCUS, AGENT_TO = 1.8, (840, 880), (540, 900)
BAG_ZOOM, BAG_FOCUS, BAG_TO = 2.2, (530, stick_airport.FLOOR_FEET - 350), (540, 1000)
DUCK = -7.0
SCRIM = 0.9
WORDS_Y = 1610
WORD_SIZE, WORD_LINGER, WORD_MIN = 80, 0.9, 1.0  # smaller than 88 so each take splits into cues of 0.85 s or more


def rig_keys(rows) -> list[stick.RigKey]:
    return [stick.RigKey(t, pose, face) for t, pose, face in rows]


def last_before(part: dict[str, list], ids: list[str], take_id: str) -> list:
    """A figure's rows in a take: its own, or its last pose before, held still."""
    i = ids.index(take_id)
    for prior in reversed(ids[: i + 1]):
        if prior in part:
            rows = part[prior]
            return rows if prior == take_id else [(0, *rows[-1][1:])]
    raise ValueError(f"no performance for take {take_id} or before it")


def now_at(ids: list[str], take_id: str) -> str:
    """What the sign calls in a take: its own entry or the last one before it."""
    i = ids.index(take_id)
    return next(NOW[p] for p in reversed(ids[: i + 1]) if p in NOW)


ep = Episode(
    EpisodeSpec(
        slug="group-nine",
        number="R8",
        title="Group 9 — Stick 08",
        description="Portrait stick-figure cartoon: at the boarding gate a passenger in Group 9 argues with the gate "
        "agent until he puts on his cap. Native vector animation; ElevenLabs voices, effect and music bed.",
        root=ROOT,
        seed=1120,
        style=STICK,
        dialogue="timeline.json",
        local_time=True,
        language="en-US",
        output_options=dict(
            codec="h264",
            container="mp4",
            fps="24",
            crf="18",
            preset="medium",
            pixelFormat="yuv420p",
            audioBitrate="192000",
            faststart=True,
            report="qa/render-report.json",
        ),
        poster=dict(time=1.0, path="group-nine-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in word captions and an external SRT."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
ids = [take.id for take in t.takes]
capped = set(ids[ids.index(CAPPED) :])
for take in t.takes:
    g = ep.shot(shots, take)
    end = take.duration
    speaks = {take.actor: dict(phones=take.phones, mood=take.mood)} if not take.is_effect else {}
    blinks = (0.9,) if end > 1.6 else ()
    look = PILOT if take.id in capped else SAM
    if take.shot == "cabin":
        frame = stick.camera(cv, g, (540, 960), to=(540, 960))
        stick_airport.cabin(cv, frame, row=ROW, seats=SEATS)
        for seat, pose, who, face in CABIN:
            stick.rig(cv, frame, [stick.RigKey(0, pose, face)], end, look=who, poses=stick_airport.SQUEEZED,
                      at=(seat - 540, 0), blinks=blinks)  # fmt: skip
        stick.rig(cv, frame, [stick.RigKey(0, "tucked", SAM_SEATED[take.id])], end, look=look,
                  poses=stick_airport.SQUEEZED, blinks=blinks, mouth=SPEECH_MOUTH,
                  **speaks.get("sam", {}))  # fmt: skip
        stick_airport.armrests(cv, frame)
        continue
    if take.shot == "sam":
        frame = stick.camera(cv, g, SAM_FOCUS, zoom=SAM_ZOOM, to=SAM_TO)
    elif take.shot == "agent":
        frame = stick.camera(cv, g, AGENT_FOCUS, zoom=AGENT_ZOOM, to=AGENT_TO)
    elif take.shot == "bag":
        frame = stick.camera(cv, g, BAG_FOCUS, zoom=BAG_ZOOM, to=BAG_TO)
    else:
        frame = stick.camera(cv, g, (540, 960), to=(540, 960))  # the whole gate, one to one
    stick_airport.gate(cv, frame, gate=GATE, now=now_at(ids, take.id))
    close = take.shot in ("sam", "agent")  # the caption band crosses the plate and the tag: leave them unlettered
    stick_airport.carry_on(cv, frame, BAG_X, stick_airport.FLOOR_FEET, tag=None if close else BAG_TAG)
    stick.rig(cv, frame, rig_keys(last_before(SAM_PART, ids, take.id)), end, look=look, poses=stick.STANDING,
              at=SAM_AT, blinks=blinks, mouth=SPEECH_MOUTH, **speaks.get("sam", {}))  # fmt: skip
    stick.rig(cv, frame, rig_keys(last_before(AGENT_PART, ids, take.id)), end, look=AGENT, poses=stick.STANDING,
              at=stick_airport.AGENT_AT, flip=True, blinks=blinks, mouth=SPEECH_MOUTH,
              **speaks.get("agent", {}))  # fmt: skip
    stick_airport.podium(cv, frame, gate=GATE, plate=not close)

# The card and the words sit above the shots, on the episode clock, so a close-up never scales them.
hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[1].start)])
spoken = cv.group(cv.comp, "spoken-words")
caption_font = (ROOT / STICK.font.src).read_bytes()
cues = stick.word_cues(
    t.takes,
    min_seconds=WORD_MIN,
    linger=WORD_LINGER,
    width=lambda text: fonts.text_width(caption_font, text, WORD_SIZE),
    size=WORD_SIZE,
    borrow=True,
    balance=True,
)
stick.words(cv, spoken, cues, y=WORDS_Y, scrim=SCRIM)
ep.hide_on_cover(hook, spoken)

music = t.meta["music"]
ep.audio(
    take=lambda take: dict(fadeIn=".003", fadeOut=".008"),
    extra=[("music", music["file"], dict(role="music", gain=str(music["gain_db"])))],
    duck=DUCK,
)
srt = [(x.start, x.end, x.text) for x in t.takes if not x.is_effect]
subtitles.write_srt(ROOT / "group-nine.srt", srt)
ep.instagram(POSTS["group-nine"])
ep.finish(ROOT / "group-nine.scene.xml", ROOT / "qa" / "sdk-validation.json")

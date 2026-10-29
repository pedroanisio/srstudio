#!/usr/bin/env python3
"""Stick 05 — The Viewing, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_viewing_audio.py PROJECT --font DIR   # voices, effect, bed, timeline.json
    python3 the_viewing.py PROJECT                                         # → PROJECT/the-viewing.scene.xml

Day 41 of the flat hunt. The kitchen has a toilet in it (open plan: cook and multitask), the window is painted on
(the view never changes: stability), and the bed folds down out of the wall with Gary asleep in it; Gary comes with
the lease. Two grand a month, each. Dev takes it, and he is applicant forty-seven. Gary, asleep, is forty-six.

The set is ``stick_flat`` (the studio and the fold-down bed); the figures are ``stick.rig`` in ``STANDING`` poses,
Dev at ``VIEWER_AT`` by the stove and the agent mirrored at ``AGENT_AT``. Each take is a shot: the wide room, the
window close, Dev's or the agent's close-up, or the bed, a turn of the camera to the right. The hook card stays up
until Gary answers; the words come one at a time as spoken.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, STICK, Episode, EpisodeSpec, fonts, stick, stick_flat, subtitles
from the_viewing_audio import AGENT, DEV, DROP, GARY, GARY_TALKS

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
HOOK = "Flat hunting, day 41."
F = stick.Face
AT_ROOM = F("open", "raised", "flat", (0.9, -0.2))
DOUBT = F("half", "worried", "flat", (0.9, 0))
AT_WINDOW = F("open", "raised", "flat", (0.4, -0.9))
AT_BED = F("wide", "worried", "flat", (1, 0))
DEADPAN = F("half", "flat", "flat", (0, 0))
SELLING = F("happy", "raised", "smile", (-0.8, 0))  # mirrored: toward Dev
BEAMING = F("happy", "raised", "smile", (0, 0))
# take: [(seconds into the take, pose, face)]
DEV_PART: dict[str, list[tuple[float, str, stick.Face]]] = {
    "01": [(0, "point", AT_ROOM)],
    "02": [(0, "stand", DOUBT)],
    "03": [(0, "point", AT_WINDOW)],
    "04": [(0, "stand", DOUBT)],
    "05": [(0, "shrug", DOUBT)],
    "06": [(0, "shrug", AT_BED)],
    "07": [(0, "stand", AT_BED)],
    "08": [(0, "stand", AT_BED)],
    "09": [(0, "stand", DOUBT)],
    "10": [(0, "stand", DOUBT), (1.6, "stand", DEADPAN)],
    "11": [(0, "stand", DEADPAN)],
    "12": [(0, "stand", DEADPAN)],
    "13": [(0, "stand", AT_BED)],
}
AGENT_PART: dict[str, list[tuple[float, str, stick.Face]]] = {
    "01": [(0, "hands-hips", SELLING)],
    "02": [(0, "wave", SELLING)],
    "03": [(0, "hands-hips", SELLING)],
    "04": [(0, "wave", BEAMING)],
    "05": [(0, "hands-hips", SELLING)],
    "06": [(0, "point", F("happy", "raised", "smile", (1, 0)))],
    "07": [(0, "point", F("happy", "raised", "smile", (1, 0)))],
    "08": [(0, "point", SELLING)],
    "09": [(0, "hands-hips", SELLING)],
    "10": [(0, "shrug", BEAMING)],
    "11": [(0, "hands-hips", SELLING)],
    "12": [(0, "wave", BEAMING)],
    "13": [(0, "hands-hips", F("open", "raised", "flat", (1, 0.2)))],
}
WIDE_FOCUS, WIDE_TO = (620, 1150), (540, 1180)
KITCHEN_FOCUS, KITCHEN_TO, KITCHEN_ZOOM = (600, 1300), (540, 900), 1.4  # the stove and the toilet
# between the card and the words, the faces above the card
CLOSE_ZOOM, WINDOW_ZOOM, BED_ZOOM, WIDE_ZOOM = 2.0, 2.1, 1.6, 1.08
HEAD_TO, WINDOW_TO, BED_TO = (540, 820), (540, 900), (540, 960)  # Gary's head above the words
DUCK = -7.0
WORD_SIZE, WORD_LINGER, SCRIM = 88, 0.6, 0.88  # smaller words join into readable phrases; a darker band
# keeps white legible over the bright window and the bed
WORD_MIN = 0.85  # the engine's legibility check: a cue drawn for 20 frames at 24 fps; short words join a phrase


def rig_keys(rows) -> list[stick.RigKey]:
    return [stick.RigKey(t, pose, face) for t, pose, face in rows]


def head(rows, at, flip: bool) -> tuple[float, float]:
    hx, hy = stick.STANDING[rows[0][1]].head
    return (at[0] - hx if flip else at[0] + hx, hy + 40)


ep = Episode(
    EpisodeSpec(
        slug="the-viewing",
        number="R5",
        title="The Viewing — Stick 05",
        description="Portrait stick-figure cartoon: a flat viewing with a toilet in the kitchen, a painted window and "
        "a bed that comes with Gary. Native vector animation; ElevenLabs voices, effect and music bed.",
        root=ROOT,
        seed=1055,
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
        poster=dict(time=1.0, path="the-viewing-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in word captions and an external SRT."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
gary_at = t.duration
dropped = False
for take in t.takes:
    g = ep.shot(shots, take)
    end = take.duration
    if take.id == GARY_TALKS:
        gary_at = take.start
    if take.shot == "window":
        frame = stick.camera(cv, g, stick_flat.WINDOW_FOCUS, zoom=WINDOW_ZOOM, to=WINDOW_TO)
    elif take.shot == "dev":
        frame = stick.camera(cv, g, head(DEV_PART[take.id], stick_flat.VIEWER_AT, False), zoom=CLOSE_ZOOM, to=HEAD_TO)
    elif take.shot == "agent":
        frame = stick.camera(cv, g, head(AGENT_PART[take.id], stick_flat.AGENT_AT, True), zoom=CLOSE_ZOOM,
                             to=HEAD_TO)  # fmt: skip
    elif take.shot == "kitchen":
        frame = stick.camera(cv, g, KITCHEN_FOCUS, zoom=KITCHEN_ZOOM, to=KITCHEN_TO)
    elif take.shot == "bed":
        frame = stick.camera(cv, g, stick_flat.BED_FOCUS, zoom=BED_ZOOM, to=BED_TO)
    else:
        frame = stick.camera(cv, g, WIDE_FOCUS, zoom=WIDE_ZOOM, to=WIDE_TO)
    stick_flat.studio(cv, frame)
    drop_at = DROP[1] if take.id == DROP[0] else (0.0 if dropped else None)
    talk = ((0.0, round(take.speech_duration, 3)),) if take.id == GARY_TALKS else ()
    stick_flat.murphy_bed(cv, frame, end, drop_at=drop_at, sleeper=GARY, talk=talk)
    dropped = dropped or take.id == DROP[0]
    speaks = {take.actor: dict(phones=take.phones, mood=take.mood)} if not take.is_effect else {}
    blinks = (0.9,) if end > 1.6 else ()
    stick.rig(cv, frame, rig_keys(DEV_PART[take.id]), end, look=DEV, poses=stick.STANDING, at=stick_flat.VIEWER_AT,
              blinks=blinks, mouth=SPEECH_MOUTH, **speaks.get("dev", {}))  # fmt: skip
    stick.rig(cv, frame, rig_keys(AGENT_PART[take.id]), end, look=AGENT, poses=stick.STANDING,
              at=stick_flat.AGENT_AT, flip=True, blinks=blinks, mouth=SPEECH_MOUTH,
              **speaks.get("agent", {}))  # fmt: skip

# The card and the words sit above the shots, on the episode clock, so a close-up never scales them.
hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, gary_at)])
spoken = cv.group(cv.comp, "spoken-words")
caption_font = (ROOT / STICK.font.src).read_bytes()
cues = stick.word_cues(
    t.takes,
    min_seconds=WORD_MIN,
    linger=WORD_LINGER,
    width=lambda text: fonts.text_width(caption_font, text, WORD_SIZE),
    size=WORD_SIZE,
    borrow=True,
)
stick.words(cv, spoken, cues, scrim=SCRIM)
ep.hide_on_cover(hook, spoken)

music = t.meta["music"]
ep.audio(
    take=lambda take: dict(fadeIn=".003", fadeOut=".008"),
    extra=[("music", music["file"], dict(role="music", gain=str(music["gain_db"])))],
    duck=DUCK,
)
srt = [(x.start, x.end, x.text) for x in t.takes if not x.is_effect]
subtitles.write_srt(ROOT / "the-viewing.srt", srt)
ep.instagram(POSTS["the-viewing"])
ep.finish(ROOT / "the-viewing.scene.xml", ROOT / "qa" / "sdk-validation.json")

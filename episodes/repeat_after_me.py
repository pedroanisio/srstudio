#!/usr/bin/env python3
"""Stick 03 — Repeat After Me, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 repeat_after_me_audio.py PROJECT --font DIR   # voices, effect, bed, timeline.json
    python3 repeat_after_me.py PROJECT                                         # → PROJECT/repeat-after-me.scene.xml

Dev drives home and makes the viewer repeat two vows after him, twice each, firmer the second time: no email on
the drive home, work stays at work. A phone buzzes; the camera cuts to the passenger seat, where an open laptop
says otherwise, and Dev beams through the confession. Then he starts over: "Now repeat after me." The car is
``stick_car`` (the interior, the driving poses, the passenger seat, the laptop and the phone); Dev is
``stick.rig``, riding the suspension under the wheel and the belt of ``stick_car.cockpit``. The POV card stays up
for the whole reel, and the words come one at a time (``stick.words``), each as it is spoken, from the take
timings, a word too quick to read joined by the next. The music bed plays under everything, ducked under the voice.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, STICK, Episode, EpisodeSpec, fonts, stick, stick_car, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
HOOK = "POV: you swore you'd stop working after hours"
F = stick.Face
DEV = stick.Look()
TO_YOU = F(look=(0, 0))  # eyes on the viewer
ROAD = F(look=(1, 0.05))  # eyes on the road
FIRM = F("open", "angry", "flat", (0.2, 0))
EARNEST = F("wide", "raised", "flat", (0, 0))
GRITTED = F("half", "angry", "frown", (0, 0))
CAUGHT = F("wide", "worried", "flat", (0.6, 0.6))  # toward the phone on the seat
BEAMING = F("happy", "raised", "smile", (0, 0))
PERFORMANCE: dict[str, list[tuple[float, str, stick.Face]]] = {  # take: (seconds into the take, pose, face)
    "01": [(0, "drive", TO_YOU)],
    "02": [(0, "drive", ROAD)],
    "03": [(0, "grip", FIRM)],
    "04": [(0, "grip", EARNEST)],
    "05": [(0, "grip", GRITTED)],
    "06": [(0, "turn", CAUGHT)],
    "07": [(0, "one-hand", BEAMING)],
    "08": [(0, "drive", TO_YOU)],
}
CLOSE, PUSH = 2.0, 1.7  # the close-up's zoom; the push-in's end zoom
CLOSE_DEFOCUS = 8.0  # the close-up focuses on the face: the country behind the glass goes soft
HEAD_FRAMING = (60, 40)  # a close-up centres a little right of and below the head, toward the wheel
SPEED = 520  # px/s past the window; each shot starts the country where the last one's clock would have it
PASSING = {"02": (1.3,), "08": (0.9,)}  # takes in which an oncoming car passes, seconds into the take
LAPTOP = dict(title="Sent", rows=("Re: quick question", "Re: Re: urgent", "Re: tomorrow?"), badge="40", scale=1.35)
LAPTOP_AT = (450, stick_car.CUSHION)
PHONE = dict(sender="Boss", text="One more thing...")
DUCK = -6.0  # the bed under the voice
WORD_MIN = 0.3  # a spoken word shown for less joins the next: quicker swaps are unreadable, and flash


def keys(take) -> list[stick.RigKey]:
    return [stick.RigKey(t, pose, face) for t, pose, face in PERFORMANCE[take.id]]


ep = Episode(
    EpisodeSpec(
        slug="repeat-after-me",
        number="R3",
        title="Repeat After Me — Stick 03",
        description="Portrait stick-figure cartoon: on the drive home Dev makes you repeat his vows to stop working "
        "after hours, until the passenger seat gives him away. Native vector animation; ElevenLabs voice, effect "
        "and music bed.",
        root=ROOT,
        seed=1031,
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
        poster=dict(time=1.0, path="repeat-after-me-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in word captions and an external SRT."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
for take in t.takes:
    g = ep.shot(shots, take)
    performance = keys(take)
    hx, hy = stick_car.DRIVING[performance[0].pose].head
    focus = (hx + HEAD_FRAMING[0], hy + HEAD_FRAMING[1])
    zoom, defocus = 1.0, 0.0
    if take.shot in ("drive", "seat"):
        frame = g
    elif take.shot == "close":
        frame = stick.camera(cv, g, focus, zoom=CLOSE, to=(540, 820))
        zoom, defocus = CLOSE, CLOSE_DEFOCUS
    else:
        frame = stick.camera(cv, g, focus, zoom=PUSH, push=take.duration * 0.8, to=(540, 860))
        zoom = PUSH
    # a zoom magnifies the country's speed with the face: slowed by it, the trees pass the screen as fast as in
    # the wide shot (twice as fast, dark against the bright horizon, they flash)
    scroll = stick_car.Scroll(speed=SPEED / zoom, offset=take.start * SPEED)
    stick_car.car(cv, frame, take.duration, scroll=scroll, passing=PASSING.get(take.id, ()), defocus=defocus)
    blinks = (0.9,) if take.duration > 1.6 else ()
    driver = cv.group(frame, cv.uid("driver"))
    stick_car.ride(cv, driver, take.duration, amplitude=1.5)
    stick.rig(cv, driver, performance, take.duration, phones=take.phones, mood=take.mood, blinks=blinks,
              poses=stick_car.DRIVING, look=DEV, mouth=SPEECH_MOUTH)  # fmt: skip
    stick_car.cockpit(cv, frame, performance, take.duration, scroll=scroll)
    stick_car.phone(cv, frame, **PHONE, buzz=(0.0, 0.4) if take.is_effect else ())
    if take.shot == "seat":
        stick_car.seat(cv, frame)
        stick_car.laptop(cv, frame, *LAPTOP_AT, **LAPTOP)

# The hook card and the words sit above the shots, on the episode clock, so a close-up never scales them.
hook = stick.card(cv, cv.comp, HOOK, size=58)
spoken = cv.group(cv.comp, "spoken-words")
caption_font = (ROOT / STICK.font.src).read_bytes()
cues = stick.word_cues(
    t.takes, min_seconds=WORD_MIN, width=lambda text: fonts.text_width(caption_font, text, stick.WORD_SIZE)
)
stick.words(cv, spoken, cues)
ep.hide_on_cover(hook, spoken)  # the cover's own headline replaces them

music = t.meta["music"]
ep.audio(
    take=lambda take: dict(fadeIn=".003", fadeOut=".008"),
    extra=[("music", music["file"], dict(role="music", gain=str(music["gain_db"])))],
    duck=DUCK,
)
srt = [(x.start, x.end, x.text) for x in t.takes if not x.is_effect]
subtitles.write_srt(ROOT / "repeat-after-me.srt", srt)
ep.instagram(POSTS["repeat-after-me"])
ep.finish(ROOT / "repeat-after-me.scene.xml", ROOT / "qa" / "sdk-validation.json")

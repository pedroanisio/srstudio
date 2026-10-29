#!/usr/bin/env python3
"""Stick 09 — The Exit, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 the_exit_audio.py PROJECT --font DIR   # voices, effects, bed, timeline.json
    python3 the_exit.py PROJECT                                         # → PROJECT/the-exit.scene.xml

Dev has missed the exit, and the couple run their oldest argument in shorthand: the sister's wedding, the mum's
birthday, the tent, both at once. Dead air, the radio hushed. Sorry, sorry. Then it dawns on them that they are not
going to her sister's, and they smile at the road. Her sister texts; Noor puts the phone face down.

The car is ``stick_windshield``: the camera on the hood looking in, Noor in the passenger seat on the left, Dev
driving on the right, the phone in its mount between them. The two-shot is framed at 1.25× on the windshield, the
shorthand in 1.7× singles, the phone in an insert (``stick_car`` under a close camera) and the face-down in a 1.5×
punch-in on Noor's hand that cuts back to the two-shot for the held ending. The hook card is Noor's first line, up
through the first take; the words come one at a time from the second take, over the hood.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, STICK, Episode, EpisodeSpec, fonts, gloss_reel, stick, stick_car, subtitles
from srstudio import stick_windshield as ws
from the_exit_audio import CAMERAS, CUT, DOWN, HOOK, SETTLE, WORDS_Y, part

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
AT = {"noor": ws.PASSENGER_AT, "dev": ws.DRIVER_AT}
PHONE_CAMERA = ((stick_car.MOUNT[0] + 102, stick_car.MOUNT[1] + 150), 2.6, (540, 760))  # the screen, from the seat
TEXT = dict(sender="Sis", text="where are you??")
DUCK = -6.0
SCRIM = 0.9
WORD_SIZE, WORD_LINGER, WORD_MIN = 76, 0.9, 0.85  # a word shown for less than 0.833 s is unreadable


def keys(who: str, take) -> list[stick.RigKey]:
    rows = [stick.RigKey(t, pose, face) for t, pose, face in part(who, ids, take.id)]
    if take.id in SETTLE:
        delay, settled = SETTLE[take.id]
        rows.append(stick.RigKey(round(take.speech_duration + delay, 6), *settled[who]))
    return rows


def car(frame, take, end: float, *, buzz=(), down=None) -> None:
    """The couple through the windshield, each in their seat; the speaker's mouth follows the take."""
    ws.windshield(cv, frame, end)
    blinks = (0.9,) if end > 1.6 else ()
    for who in ("noor", "dev"):
        speaks = dict(phones=take.phones, mood=take.mood) if take.actor == who else {}
        stick.rig(cv, frame, keys(who, take), end, poses=ws.FRONT, look=ws.COUPLE[who], at=AT[who],
                  blinks=blinks, mouth=SPEECH_MOUTH, **speaks)  # fmt: skip
    ws.dashboard(cv, frame, end, buzz=buzz, down=down)


def camera(parent, name: str, frame=None):
    focus, zoom, to = frame or CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


ep = Episode(
    EpisodeSpec(
        slug="the-exit",
        number="R9",
        title="The Exit — Stick 09",
        description="Portrait stick-figure cartoon: a couple who have had the same argument forty times run it in "
        "shorthand after a missed exit, until they realise where they are no longer going. Native vector animation; "
        "ElevenLabs voices, effects and music bed.",
        root=ROOT,
        seed=1209,
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
        poster=dict(time=1.0, path="the-exit-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in word captions and an external SRT."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
ids = [take.id for take in t.takes]
for take in t.takes:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "phone":
        frame = camera(g, "phone", PHONE_CAMERA)
        stick_car.car(cv, frame, end, defocus=6.0)
        stick_car.phone(cv, frame, **TEXT, buzz=(0.0, 0.4))
    elif take.shot == "down":
        close = cv.group(g, cv.uid("punch-in"))
        cv.gate(close, [(0.0, CUT)])
        car(camera(close, "down"), take, end, down=DOWN)
        wide = cv.group(g, cv.uid("held"))
        cv.gate(wide, [(CUT, end)])
        car(camera(wide, "two"), take, end, down=DOWN)
    else:
        car(camera(g, take.shot), take, end)

# The card and the words sit above the shots, on the episode clock, so a close-up never scales them.
hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, t.takes[1].start)])
spoken = cv.group(cv.comp, "spoken-words")
caption_font = (ROOT / STICK.font.src).read_bytes()
cues = stick.word_cues(
    t.takes[1:],  # the first line is the card
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
down_take = t.takes[-1]
mix = ep.audio(
    # the thunk is heard when the phone lies down, not when the take starts
    take=lambda take: dict(
        fadeIn=".003", fadeOut=".008", **({"start": take.start + DOWN} if take is down_take else {})
    ),
    extra=[("music", music["file"], dict(role="music", gain=str(music["gain_db"])))],
    duck=DUCK,
)
(bed,) = [x for x in mix.find_all("audioTrack") if x.role == "music"]
said = [(x.start, x.start + x.speech_duration) for x in t.takes if not x.is_effect]
gloss_reel.hush(cv, bed, said, float(music["gain_db"]))  # the radio drops into the dead air
srt = [(x.start, x.end, x.text) for x in t.takes if not x.is_effect]
subtitles.write_srt(ROOT / "the-exit.srt", srt)
ep.instagram(POSTS["the-exit"])
ep.finish(ROOT / "the-exit.scene.xml", ROOT / "qa" / "sdk-validation.json")

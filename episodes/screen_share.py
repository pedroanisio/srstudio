#!/usr/bin/env python3
"""Stick 02 — Screen Share, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 screen_share_audio.py PROJECT --font DIR   # voices, effect, timeline.json
    python3 screen_share.py PROJECT                                          # → PROJECT/screen-share.scene.xml

Three beats of a remote workday, each under its hook card: the boss shares a screen (and an inbox), a
meeting that runs over meets a sudden bad connection, and a Friday "got a sec?" gets a stare. Dev is the
Stick style's drawn rig (``stick.rig``) at the desk of the library's study (``stick.room``). The call is
``stick.call``: the boss shares his inbox, and the camera pushes in on the row that concerns Dev. On Friday
the boss is in the room, a standing rig with his own look. Nine takes cut as a shot sequence of wide shots,
close-ups, the call and pushes; captions follow the words of each take and are also written to an external
SRT.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import STICK, Episode, EpisodeSpec, fonts, stick, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
HOOKS = {
    "screen": "When the meeting starts with “can everyone see my screen?”",
    "wrap-up": "Me when the meeting runs over",
    "friday": "Friday, 4:59 PM",
}
F = stick.Face
LAPTOP = F()  # eyes open, on the laptop
FLAT = F("half", "flat", "flat")
DREAD = F("half", "worried", "frown")
FAKE = F("wide", "worried", "flat")
SMUG = F("happy", "flat", "smile", (0, 0))
BLISS = F("closed", "flat", "smile", (0, 0.2))
CAUGHT = F("wide", "raised", "frown")
STARE = F("half", "angry", "flat", (0, 0))
DEV = stick.Look()
BOSS = stick.Look(hair="bald", glasses=True, tie="#b8433a")
TILES = {  # the call's tiles per take: the boss presents in 01, Dev answers in 03
    "01": (F(look=(0, 0.1)), F("half", "flat", "flat", (0, 0.1))),
    "03": (F("wide", "raised", "frown", (0, 0.1)), F("half", "raised", "smirk", (0, 0))),
}
INBOX = (
    stick.Mail("HR", "Re: Dev — concerns", unread=True),
    stick.Mail("Calendar", "Moved: Friday 4:59 PM sync", unread=True),
    stick.Mail("Store", "Your order: World's Best Boss mug"),
    stick.Mail("IT", "Your password expires today"),
    stick.Mail("Me", "Reminder: be more approachable"),
    stick.Mail("Mom", "Call me back please"),
)
SHARED = (540, 950)  # the middle of the shared screen, which the camera pushes in on in 03
CALL_ZOOM = 1.15  # enough to read the rows, little enough to keep the screen above the captions
CAPTION_SIZE, MIN_PAGE, PAGE, MARGIN = 60, 0.85, 24, 60  # pages of 24 characters, kept 60 px off each edge
CLOSE, PUSH = 2.05, 2.5  # close-up zoom; the push-in's end zoom
FRAMING = 100  # a close-up centres right of Dev's head, so the laptop he looks at stays in the frame
POSTER = 4.9  # the inbox, pushed in, its row about Dev marked


def typing(start: float, end: float, face: stick.Face, step: float = 1 / 6) -> list[stick.RigKey]:
    """Hands on the keys, two poses swapped every other frame at 12 fps."""
    n = max(1, int((end - start) / step))
    return [stick.RigKey(round(start + i * step, 4), ("type-a", "type-b")[i % 2], face) for i in range(n)]


def word_at(take, prefix: str) -> float:
    return next(w["start"] for w in take.words if w["text"].lower().startswith(prefix))


def performance(take, boss_words) -> list[stick.RigKey]:
    """What Dev does in each take, on the take's clock."""
    if take.id == "02":
        return [stick.RigKey(0, "type-a", FLAT)]
    if take.id == "04":
        wrap = word_at(take, "wrap")
        return typing(0, wrap, LAPTOP) + [stick.RigKey(round(wrap, 4), "type-a", DREAD)]
    if take.id == "05":
        return [stick.RigKey(0, "lean", FAKE)]
    if take.id in ("06", "07"):
        return [stick.RigKey(0, "back", SMUG)]
    if take.id == "08":
        sec = word_at(boss_words, "sec")
        return [stick.RigKey(0, "stretch", BLISS), stick.RigKey(round(sec, 4), "stretch", CAUGHT)]
    if take.id == "09":
        return [stick.RigKey(0, "turn", STARE)]
    raise ValueError(f"take {take.id} has no performance")


def boss_in_room(take) -> list[stick.RigKey] | None:
    """The boss, standing in front of the desk on Friday: leaning in to ask, then waiting, hands on hips."""
    if take.id == "08":
        return [stick.RigKey(0, "lean-in", F("open", "raised", "smile", (1, 0.2)))]
    if take.id == "09":
        return [stick.RigKey(0, "hands-hips", F("open", "raised", "smile", (1, 0.1)))]
    return None


def call_screen(frame, take) -> None:
    boss_face, dev_face = TILES[take.id]
    tiles = (
        stick.Tile("Boss", BOSS, boss_face),
        stick.Tile("Dev", DEV, dev_face),
        stick.Tile("Kim", stick.Look(hair="bun"), F("half", "worried", "flat", (0, 0.1))),
        stick.Tile("Raj", stick.Look(hair="spiky"), F("wide", "raised", "flat", (0, 0.1))),
    )
    speaker = "Boss" if take.actor == "boss" else "Dev"
    concerns = 0 if take.id == "03" else None  # Dev has read the first row
    stick.call(cv, frame, tiles, INBOX, speaking=speaker, title="Inbox (1,204)", highlight=concerns)


ep = Episode(
    EpisodeSpec(
        slug="screen-share",
        number="R2",
        title="Screen Share — Stick 02",
        description="Portrait stick-figure cartoon in three beats of a remote workday: a shared screen, a meeting "
        "that runs over and a Friday 'got a sec?'. Native vector animation; ElevenLabs dialogue and effect.",
        root=ROOT,
        seed=1028,
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
        poster=dict(time=POSTER, path="screen-share-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in captions and an external SRT."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
for take in t.takes:
    g = ep.shot(shots, take)
    if take.id in TILES:
        frame = g if take.id == "01" else stick.camera(cv, g, SHARED, zoom=CALL_ZOOM, push=1.0, to=(540, 960))
        call_screen(frame, take)
        continue
    keys = performance(take, take)
    hx, hy = stick.SEATED[keys[0].pose].head
    if take.shot == "wide":
        frame = g
    elif take.shot == "close":
        frame = stick.camera(cv, g, (hx + FRAMING, hy), zoom=CLOSE, to=(540, 860))
    else:
        frame = stick.camera(cv, g, (hx, hy), zoom=PUSH, push=min(1.4, take.duration * 0.6), to=(540, 860))
    stick.room(cv, frame)
    blinks = (0.9,) if take.duration > 1.6 else ()
    speaks = take.actor == "dev"
    boss = boss_in_room(take)
    if boss is not None:  # mirrored to face Dev; his x 540 centre lands at 860
        stick.rig(cv, frame, boss, take.duration, phones=() if speaks else take.phones, mood=take.mood,
                  poses=stick.STANDING, look=BOSS, at=(860 + 540 * 0.95, -40), scale=0.95, flip=True)  # fmt: skip
    stick.rig(cv, frame, keys, take.duration, phones=take.phones if speaks else (), mood=take.mood, blinks=blinks,
              look=DEV)  # fmt: skip

# The hook cards and the captions sit above the shots, on the episode clock, so a close-up never scales them.
for beat, hook in HOOKS.items():
    takes = [x for x in t.takes if x.extra.get("beat") == beat]
    card = stick.card(cv, cv.comp, hook, size=62)
    cv.gate(card, [(takes[0].start, takes[-1].end)])
on_call: list[stick.Line] = []  # cues over the call's dark screen
lines: list[stick.Line] = []
srt = []
font = (ROOT / ep.spec.font).read_bytes()
for take in t.takes:
    cues = (
        [(0.0, take.duration, take.text)]
        if take.is_effect
        else subtitles.chunk_words(take.words, take.duration, max_chars=PAGE, upper=False, min_seconds=MIN_PAGE)
    )
    for i, (start, end, text) in enumerate(cues):
        shown = f"BOSS: {text}" if take.actor == "boss" and i == 0 else text
        if fonts.text_width(font, shown, CAPTION_SIZE) > cv.width - 2 * MARGIN:  # captions do not wrap
            raise ValueError(f"take {take.id}: caption {shown!r} is wider than the frame at {CAPTION_SIZE} px")
        cue = stick.Line(round(take.start + start, 3), round(take.start + end, 3), shown, CAPTION_SIZE)
        (on_call if take.id in TILES else lines).append(cue)
        srt.append((take.start + start, take.start + end, shown))
stick.captions(cv, cv.comp, on_call, outline="none")  # white alone: an ink outline cannot contrast with the call
stick.captions(cv, cv.comp, lines, outline="layer")

ep.audio(take=lambda take: dict(pan=-0.06 if take.actor == "boss" else 0.04, fadeIn=".003", fadeOut=".008"))
subtitles.write_srt(ROOT / "screen-share.srt", srt)
ep.instagram(POSTS["screen-share"])
ep.finish(ROOT / "screen-share.scene.xml", ROOT / "qa" / "sdk-validation.json")

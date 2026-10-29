#!/usr/bin/env python3
"""Stick 07 — What My Dad Does, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 what_my_dad_does_audio.py PROJECT --font DIR   # voices, bed, timeline.json
    python3 what_my_dad_does.py PROJECT                                         # → PROJECT/what-my-dad-does.scene.xml

Parent-teacher night. Dev perches on a child's chair, knees above his hip, while Ms. Reyes reads his son's essay:
he works from home in a tie and no pants, his job is saying "I think you're on mute", Focus Time snores. Dev has an
answer for each. Dad says he works from home; Mom says he's just home. What did he get? An A. His mom helped.

The set is ``stick_school``: the classroom, the tiny chair under Dev in a ``PERCHED`` pose, the teacher mirrored at
``TEACHER_AT`` holding the page in a ``READING`` pose, and her desk in front of her. Each take is a shot: the wide
room, Dev's close-up, the teacher's, and the essay on the desk, its lines coming up as she reads them, the line
being read highlighted from its first spoken word, and on the button the grade and the margin note. The hook card
stays up until the page is first shown; the words come one at a time as spoken.
"""

import os
import re

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, STICK, Episode, EpisodeSpec, fonts, stick, stick_school, subtitles
from what_my_dad_does_audio import BY, DEV, GRADE, GRADED, LINES, NOTE, NOTE_WORD, PAGES, TEACHER, TITLE

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
HOOK = "What did your kid\nwrite about you?"
F = stick.Face
UP = (0.7, -0.6)  # Dev on the tiny chair looks up at the teacher
FOND = F("happy", "raised", "smile", UP)
SURE = F("open", "flat", "smirk", UP)
PROUD = F("half", "raised", "smirk", UP)
HIT = F("wide", "worried", "frown", UP)
SMALL = F("half", "worried", "flat", (0.6, -0.3))
READS = F("open", "raised", "flat", (0.5, 0.7))  # at the page in her hands
OVER = F("half", "raised", "flat", (0.9, 0.3))  # over the page, at him
# take: [(seconds into the take, pose, face)] for Dev and for the teacher
DEV_PART: dict[str, list[tuple[float, str, stick.Face]]] = {
    "01": [(0, "perch", F("open", "raised", "smile", UP))],
    "02": [(0, "perch-lean", FOND)],
    "04": [(0, "perch-point", SURE)],
    "06": [(0, "perch-shrug", SURE)],
    "08": [(0, "perch-point", PROUD)],
    "09": [(0, "perch", F("open", "raised", "smile", UP))],
    "12": [(0, "perch", HIT)],
    "13": [(0, "perch-face", SMALL)],
}
TEACHER_PART: dict[str, list[tuple[float, str, stick.Face]]] = {
    "01": [(0, "read", OVER)],
    "02": [(0, "read", READS)],
    "08": [(0, "read", OVER)],
    "09": [(0, "read", OVER)],
    "12": [(0, "lower", F("half", "flat", "flat", (0.9, 0.3)))],
}
DEV_ZOOM, DEV_TO = 1.9, (540, 860)
TEACHER_FOCUS, TEACHER_ZOOM, TEACHER_TO = (880, 900), 1.7, (540, 900)
DUCK = -7.0
SCRIM = 0.9
WORDS_Y = 1610  # under the page in the essay shot, under Dev's knees in the room
WORD_SIZE, WORD_LINGER, WORD_MIN = 88, 0.9, 1.0
HELD = 0.2  # the page in her hands, at this scale


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


def page_before(ids: list[str], take_id: str) -> int:
    """How many lines are up on the page by this take: the last essay take's, or none before the first."""
    i = ids.index(take_id)
    return next((PAGES[p][0] for p in reversed(ids[: i + 1]) if p in PAGES), 0)


def word_at(take, word: str) -> float:
    """When ``word`` starts in a take, from its timestamps: the highlighter and the note wait for it."""
    for w in take.words:
        if re.sub(r"[^\w']", "", w["text"]).lower() == word.lower():
            return float(w["start"])
    raise ValueError(f"take {take.id} never says {word!r}")


ep = Episode(
    EpisodeSpec(
        slug="what-my-dad-does",
        number="R7",
        title="What My Dad Does — Stick 07",
        description="Portrait stick-figure cartoon: at parent-teacher night Dev perches on a child's chair while the "
        "teacher reads his son's essay about his work from home. Native vector animation; ElevenLabs voices, effect "
        "and music bed.",
        root=ROOT,
        seed=1119,
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
        poster=dict(time=1.0, path="what-my-dad-does-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in word captions and an external SRT."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
ids = [take.id for take in t.takes]
page_at = t.duration
for take in t.takes:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "essay":
        page_at = min(page_at, take.start)
        shown, mark, word = PAGES[take.id]
        frame = stick.camera(cv, g, (540, 960))
        stick.box(cv, frame, 0, 0, 1080, 1920, stick_school.DESK)
        for yy in (420, 980, 1540):  # the desk's grain
            stick.shape(cv, frame, f"M 0 {yy} Q 540 {yy - 30} 1080 {yy}", sw=5, stroke=stick_school.DESK_FRONT)
        graded = take.id == GRADED
        stick_school.essay(cv, frame, LINES, title=TITLE, by=BY, shown=shown, mark=mark,
                           mark_at=word_at(take, word) if mark is not None else 0.0,
                           grade=GRADE if graded else None, note=NOTE if graded else None,
                           note_at=word_at(take, NOTE_WORD) if graded else 0.0)  # fmt: skip
        continue
    if take.shot == "dev":
        hx, hy = stick_school.PERCHED[last_before(DEV_PART, ids, take.id)[0][1]].head
        frame = stick.camera(cv, g, (hx + 60, hy + 80), zoom=DEV_ZOOM, to=DEV_TO)
    elif take.shot == "teacher":
        frame = stick.camera(cv, g, TEACHER_FOCUS, zoom=TEACHER_ZOOM, to=TEACHER_TO)
    else:
        frame = stick.camera(cv, g, (540, 960), to=(540, 960))  # the whole room, one to one
    stick_school.classroom(cv, frame)
    speaks = {take.actor: dict(phones=take.phones, mood=take.mood)} if not take.is_effect else {}
    blinks = (0.9,) if end > 1.6 else ()
    teacher = last_before(TEACHER_PART, ids, take.id)
    stick.rig(cv, frame, rig_keys(teacher), end, look=TEACHER, poses=stick_school.TEACHER_POSES,
              at=stick_school.TEACHER_AT, flip=True, blinks=blinks, mouth=SPEECH_MOUTH,
              **speaks.get("teacher", {}))  # fmt: skip
    if teacher[-1][1] in stick_school.READING:
        shown = max(page_before(ids, take.id), 1)
        stick_school.essay(cv, frame, LINES, title=TITLE, by=BY, shown=shown,
                           at=stick_school.held(teacher[-1][1]), scale=HELD)  # fmt: skip
    stick_school.teacher_desk(cv, frame)
    stick_school.tiny_chair(cv, frame)
    stick.rig(cv, frame, rig_keys(last_before(DEV_PART, ids, take.id)), end, look=DEV, poses=stick_school.PERCHED,
              blinks=blinks, mouth=SPEECH_MOUTH, **speaks.get("dev", {}))  # fmt: skip

# The card and the words sit above the shots, on the episode clock, so a close-up never scales them.
hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, page_at)])
spoken = cv.group(cv.comp, "spoken-words")
caption_font = (ROOT / STICK.font.src).read_bytes()
cues = stick.word_cues(
    t.takes,
    min_seconds=WORD_MIN,
    linger=WORD_LINGER,
    width=lambda text: fonts.text_width(caption_font, text, WORD_SIZE),
    size=WORD_SIZE,
    borrow=True,
    tail=True,
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
subtitles.write_srt(ROOT / "what-my-dad-does.srt", srt)
ep.instagram(POSTS["what-my-dad-does"])
ep.finish(ROOT / "what-my-dad-does.scene.xml", ROOT / "qa" / "sdk-validation.json")

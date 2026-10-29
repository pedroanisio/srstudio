#!/usr/bin/env python3
"""Stick 04 — Unexpected Item, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 unexpected_item_audio.py PROJECT --font DIR   # voices, effect, bed, timeline.json
    python3 unexpected_item.py PROJECT                                         # → PROJECT/unexpected-item.scene.xml

Dev buys one avocado at the self-checkout. The kiosk asks for it in the bagging area, then calls it unexpected,
asks for it out, asks for it back, and calls for help. The clerk reads his month off the screen: two hundred items
scanned, bagged, three jams fixed. He is employee of the month. He asks whether he gets paid, and the kiosk calls
that an unexpected item too. Saturday: Dev in the store's apron, saying the kiosk's line to the next shopper.

The set is ``stick_shop`` (the checkout, the kiosk and its screens, the avocado, the name badges); the figures are
``stick.rig`` in ``STANDING`` poses, Dev and the customer at ``SHOPPER_AT``, the clerk (and Dev on Saturday)
mirrored at ``CLERK_AT``. Each take is a shot: the wide set, the screen close, Dev's close-up, the clerk at the
screen. The hook card stays up until Saturday's card replaces it; the words come one at a time as spoken.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, STICK, Episode, EpisodeSpec, fonts, stick, stick_shop, subtitles
from unexpected_item_audio import ALARM, CLERK, CUSTOMER, DEV, DEV_HIRED, SCREENS

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
HOOK = "Who actually works the self-checkout?"
BUTTON = "Saturday."
F = stick.Face
AT_KIOSK = F(look=(0.9, -0.1))
SMUG = F("happy", "raised", "smile", (0.6, 0))
FIRM = F("open", "angry", "flat", (0.8, -0.1))
WORRIED = F("open", "worried", "flat", (0.8, -0.2))
DEADPAN = F("half", "flat", "flat", (0, 0))
TO_CLERK = F("wide", "worried", "flat", (1, 0))
HOPEFUL = F("wide", "raised", "smile", (0.3, 0))
BRISK = F("open", "flat", "flat", (-0.4, 0))  # mirrored: toward the kiosk
READING = F("half", "raised", "flat", (-0.8, -0.2))
PROUD = F("happy", "raised", "smile", (0, 0))
# take: [(seconds into the take, pose, face, where the avocado is: "hand" or "bag")]
PERFORMANCE: dict[str, list[tuple[float, str, stick.Face, str]]] = {
    "01": [(0, "stand", AT_KIOSK, "hand")],
    "02": [(0, "lean-in", AT_KIOSK, "hand")],
    "03": [(0, "lean-in", AT_KIOSK, "bag"), (0.6, "stand", SMUG, "bag")],
    "04": [(0, "stand", SMUG, "bag")],
    "05": [(0, "point", FIRM, "bag")],
    "06": [(0, "stand", WORRIED, "bag"), (0.9, "wave", WORRIED, "hand")],
    "07": [(0, "wave", WORRIED, "hand"), (2.0, "wave", DEADPAN, "hand")],
    "08": [(0, "stand", DEADPAN, "bag")],
    "10": [(0, "shrug", TO_CLERK, "bag")],
    "11": [(0, "stand", TO_CLERK, "bag")],
    "12": [(0, "stand", FIRM, "bag"), (0.9, "stand", DEADPAN, "bag")],
    "13": [(0, "stand", HOPEFUL, "bag")],
    "14": [(0, "stand", HOPEFUL, "bag")],
    "15": [(0, "stand", DEADPAN, "bag")],
}
CLERK_PART: dict[str, list[tuple[float, str, stick.Face]]] = {  # the clerk, who walks up in take 10
    "10": [(0, "hands-hips", BRISK)],
    "11": [(0, "point", READING)],
    "12": [(0, "hands-hips", BRISK)],
    "13": [(0, "hands-hips", PROUD)],
    "14": [(0, "hands-hips", F("half", "raised", "flat", (-0.6, 0)))],
    "15": [(0, "hands-hips", F("closed", "flat", "flat", (0, 0)))],
}
SATURDAY_DEV = [(0, "hands-hips", F("happy", "raised", "smile", (-0.5, 0)))]
SATURDAY_CUSTOMER = [(0, "lean-in", F("open", "worried", "flat", (0.9, -0.1)))]
SCREEN_ZOOM, DEV_ZOOM, CLERK_ZOOM, WIDE_ZOOM = 2.4, 2.0, 1.45, 1.2
WIDE_FOCUS, WIDE_TO = (640, 1150), (540, 1180)  # the wide: the counter, both figures, a little floor
CLERK_FOCUS = (700, 860)  # the clerk at the screen: both in the frame
DEV_HEAD_TO = (540, 820)
DUCK = -7.0
WORD_SIZE, WORD_LINGER, SCRIM = 88, 0.9, 0.9  # smaller words join into readable phrases over a darker band
WORD_MIN = 1.0  # the engine's legibility check: a cue drawn for 20 frames at 24 fps, after its 0.12 s pop-in
BADGE = (stick_shop.CLERK_AT[0] - 540 - 105, 930)  # a mirrored STANDING figure's chest at CLERK_AT


def rig_keys(rows) -> list[stick.RigKey]:
    return [stick.RigKey(t, pose, face) for t, pose, face, *_ in rows]


ep = Episode(
    EpisodeSpec(
        slug="unexpected-item",
        number="R4",
        title="Unexpected Item — Stick 04",
        description="Portrait stick-figure cartoon: Dev buys one avocado at the self-checkout and ends up employee "
        "of the month, unpaid. Native vector animation; ElevenLabs voices, effect and music bed.",
        root=ROOT,
        seed=1044,
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
        poster=dict(time=1.0, path="unexpected-item-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in word captions and an external SRT."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
saturday_at = 0.0
for take in t.takes:
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "button":
        saturday_at = take.start
    if take.shot in ("screen", "award"):
        frame = stick.camera(cv, g, stick_shop.SCREEN_CENTRE, zoom=SCREEN_ZOOM, to=(540, 860))
    elif take.shot == "dev":
        hx, hy = stick.STANDING[PERFORMANCE[take.id][0][1]].head
        focus = (hx + stick_shop.SHOPPER_AT[0], hy + 40)
        frame = stick.camera(cv, g, focus, zoom=DEV_ZOOM, to=DEV_HEAD_TO)
    elif take.shot == "clerk":
        frame = stick.camera(cv, g, CLERK_FOCUS, zoom=CLERK_ZOOM, to=(540, 860))
    else:
        frame = stick.camera(cv, g, WIDE_FOCUS, zoom=WIDE_ZOOM, to=WIDE_TO)
    stick_shop.checkout(cv, frame)
    stick_shop.kiosk(cv, frame, SCREENS[take.id], end, alarm=(0.0,) if take.id in ALARM else ())
    speaks = {take.actor: dict(phones=take.phones, mood=take.mood)} if not take.is_effect else {}
    blinks = (0.9,) if end > 1.6 else ()
    if take.shot == "button":
        stick.rig(cv, frame, rig_keys(SATURDAY_CUSTOMER), end, look=CUSTOMER, poses=stick.STANDING,
                  at=stick_shop.SHOPPER_AT, blinks=blinks)  # fmt: skip
        x, y = stick_shop.hand(stick.STANDING["lean-in"], at=stick_shop.SHOPPER_AT)
        stick_shop.avocado(cv, frame, x, y + 20)
        stick.rig(cv, frame, rig_keys(SATURDAY_DEV), end, look=DEV_HIRED, poses=stick.STANDING,
                  at=stick_shop.CLERK_AT, flip=True, blinks=blinks, mouth=SPEECH_MOUTH,
                  **speaks.get("dev", {}))  # fmt: skip
        stick_shop.name_badge(cv, frame, *BADGE, "DEV", "Employee of the month")
        continue
    rows = PERFORMANCE[take.id]
    stick.rig(cv, frame, rig_keys(rows), end, look=DEV, poses=stick.STANDING, at=stick_shop.SHOPPER_AT,
              blinks=blinks, mouth=SPEECH_MOUTH, **speaks.get("dev", {}))  # fmt: skip
    for i, (start, pose, _, where) in enumerate(rows):
        until = rows[i + 1][0] if i + 1 < len(rows) else end
        item = cv.group(frame, cv.uid("avocado"))
        if where == "hand":
            x, y = stick_shop.hand(stick.STANDING[pose], at=stick_shop.SHOPPER_AT)
            stick_shop.avocado(cv, item, x, y + 20)
        else:
            stick_shop.avocado(cv, item, *stick_shop.BAG_SPOT)
        if (start, until) != (0, end):
            cv.gate(item, [(start, until)])
    if take.id in CLERK_PART:
        stick.rig(cv, frame, rig_keys(CLERK_PART[take.id]), end, look=CLERK, poses=stick.STANDING,
                  at=stick_shop.CLERK_AT, flip=True, blinks=blinks, mouth=SPEECH_MOUTH,
                  **speaks.get("clerk", {}))  # fmt: skip
        if take.shot in ("wide", "clerk"):  # whole in these frames; a close shot would cut it
            stick_shop.name_badge(cv, frame, *BADGE, "MAYA", "Store supervisor")

# The cards and the words sit above the shots, on the episode clock, so a close-up never scales them.
hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, saturday_at)])
saturday = stick.card(cv, cv.comp, BUTTON, size=72)
cv.gate(saturday, [(saturday_at, t.duration)])
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
stick.words(cv, spoken, cues, scrim=SCRIM)
ep.hide_on_cover(hook, saturday, spoken)

music = t.meta["music"]
ep.audio(
    take=lambda take: dict(fadeIn=".003", fadeOut=".008"),
    extra=[("music", music["file"], dict(role="music", gain=str(music["gain_db"])))],
    duck=DUCK,
)
srt = [(x.start, x.end, x.text) for x in t.takes if not x.is_effect]
subtitles.write_srt(ROOT / "unexpected-item.srt", srt)
ep.instagram(POSTS["unexpected-item"])
ep.finish(ROOT / "unexpected-item.scene.xml", ROOT / "qa" / "sdk-validation.json")

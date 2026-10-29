#!/usr/bin/env python3
"""Stick 06 — Cancel Anytime, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 cancel_anytime_audio.py PROJECT --font DIR   # voices, bed, timeline.json
    python3 cancel_anytime.py PROJECT                                         # → PROJECT/cancel-anytime.scene.xml

Theo wants to cancel his gym membership before dawn. Brooke at the front desk names the rules: in person, on a
Tuesday, before sunrise; he meets each one. Then a note from his trainer, whom he has never met; the trainer has
met him. Any other way? A death certificate. Whose? They are flexible. Then the sun comes up in the window, and
the close-up on the desk's sign reads its fine print.

The set is ``stick_gym`` (the gym with its window keyed to dawn, the counter with the sign drawn over Brooke); the
figures are ``stick.rig`` in ``STANDING`` poses, Theo at ``MEMBER_AT`` and Brooke mirrored at ``STAFF_AT``. Each
take is a shot: the wide set, Theo's close-up, Brooke's (the sign beside her), the sign close. The hook card stays
up until the sign's close-up; the words come one at a time as spoken.
"""

import os

from _common import project_root
from cancel_anytime_audio import BROOKE, FINE, SIGN, SUNRISE, THEO
from instagram_posts import POSTS
from srstudio import SPEECH_MOUTH, STICK, Episode, EpisodeSpec, fonts, stick, stick_gym, stick_shop, subtitles

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
HOOK = "Cancel anytime. Right?"
F = stick.Face
AT_DESK = F(look=(0.9, -0.1))
FIRM = F("open", "angry", "flat", (0.8, -0.1))
DEADPAN = F("half", "flat", "flat", (0.6, 0))
WORRIED = F("open", "worried", "flat", (0.8, -0.1))
LOST = F("wide", "raised", "flat", (0.8, 0))
CHIPPER = F("happy", "raised", "smile", (-0.5, 0))  # mirrored: toward Theo
SORRY = F("half", "worried", "flat", (-0.5, 0))
TO_WINDOW = F("wide", "raised", "flat", (-1, -0.2))
# take: [(seconds into the take, pose, face)] for Theo and for Brooke
THEO_PART: dict[str, list[tuple[float, str, stick.Face]]] = {
    "01": [(0, "lean-in", AT_DESK)],
    "02": [(0, "stand", AT_DESK)],
    "03": [(0, "shrug", FIRM)],
    "04": [(0, "stand", FIRM)],
    "05": [(0, "point", FIRM)],
    "06": [(0, "stand", DEADPAN)],
    "07": [(0, "point", F("open", "angry", "flat", (-1, -0.3)))],  # at the dark window behind him
    "08": [(0, "stand", DEADPAN)],
    "09": [(0, "shrug", WORRIED)],
    "10": [(0, "stand", WORRIED)],
    "11": [(0, "stand", F("half", "worried", "flat", (0.8, 0)))],
    "12": [(0, "stand", LOST)],
    "13": [(0, "stand", LOST)],
    "14": [(0, "stand", F("closed", "worried", "flat", (0, 0)))],
    "15": [(0, "stand", F("wide", "worried", "flat", (-1, -0.2)))],
    "16": [(0, "stand", DEADPAN)],
}
BROOKE_PART: dict[str, list[tuple[float, str, stick.Face]]] = {
    "01": [(0, "hands-hips", CHIPPER)],
    "02": [(0, "wave", CHIPPER)],
    "04": [(0, "point", CHIPPER)],
    "06": [(0, "point", CHIPPER)],
    "07": [(0, "hands-hips", CHIPPER)],
    "08": [(0, "point", CHIPPER)],
    "10": [(0, "hands-hips", SORRY)],
    "12": [(0, "hands-hips", CHIPPER)],
    "14": [(0, "shrug", CHIPPER)],
    "15": [(0, "hands-hips", TO_WINDOW), (1.0, "wave", CHIPPER)],
    "16": [(0, "wave", CHIPPER)],
}
WIDE_FOCUS, WIDE_ZOOM, WIDE_TO = (540, 1000), 1.0, (540, 1000)  # the whole set: brand, window, desk
THEO_ZOOM, THEO_TO = 2.0, (540, 820)
BROOKE_FOCUS, BROOKE_ZOOM, BROOKE_TO = (860, 900), 1.6, (540, 1000)  # her head clear of the hook card
SIGN_ZOOM, SIGN_TO = 3.0, (540, 900)
DUCK = -7.0
SCRIM = 0.9  # a darker band: the words sit over the bright desk in Brooke's close-up
WORDS_Y = 1580  # under the desk's sign in every shot, so its fine print stays clear of the band
WORD_SIZE, WORD_LINGER = 88, 0.9  # smaller words join into phrases; a take's last word stays long enough to read
WORD_MIN = 1.0  # the legibility check wants 20 frames at 24 fps drawn, after the word's pop-in: short words join
BADGE = (stick_gym.STAFF_AT[0] - 540 - 105, 930)  # a mirrored STANDING figure's chest at STAFF_AT


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


ep = Episode(
    EpisodeSpec(
        slug="cancel-anytime",
        number="R6",
        title="Cancel Anytime — Stick 06",
        description="Portrait stick-figure cartoon: Theo tries to cancel his gym membership before dawn and meets "
        "every rule but the last. Native vector animation; ElevenLabs voices and music bed.",
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
        poster=dict(time=1.0, path="cancel-anytime-cover.jpg", format="jpeg", quality=".95"),
        accessibility=dict(description="Stick-figure cartoon with burned-in word captions and an external SRT."),
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
ids = [take.id for take in t.takes]
dawn = ids.index(SUNRISE)
sign_at = t.duration
for k, take in enumerate(t.takes):
    g = ep.shot(shots, take)
    end = take.duration
    if take.shot == "theo":
        hx, hy = stick.STANDING[last_before(THEO_PART, ids, take.id)[0][1]].head
        frame = stick.camera(cv, g, (hx + stick_gym.MEMBER_AT[0], hy + 40), zoom=THEO_ZOOM, to=THEO_TO)
    elif take.shot == "brooke":
        frame = stick.camera(cv, g, BROOKE_FOCUS, zoom=BROOKE_ZOOM, to=BROOKE_TO)
    elif take.shot == "sign":
        sign_at = min(sign_at, take.start)
        frame = stick.camera(cv, g, stick_gym.SIGN_CENTRE, zoom=SIGN_ZOOM, to=SIGN_TO)
    else:
        frame = stick.camera(cv, g, WIDE_FOCUS, zoom=WIDE_ZOOM, to=WIDE_TO)
    sunrise = None if k < dawn else (0.1 if k == dawn else 0.0)
    stick_gym.gym(cv, frame, end, sunrise=sunrise)
    speaks = {take.actor: dict(phones=take.phones, mood=take.mood)} if not take.is_effect else {}
    blinks = (0.9,) if end > 1.6 else ()
    stick.rig(cv, frame, rig_keys(last_before(BROOKE_PART, ids, take.id)), end, look=BROOKE, poses=stick.STANDING,
              at=stick_gym.STAFF_AT, flip=True, blinks=blinks, mouth=SPEECH_MOUTH,
              **speaks.get("brooke", {}))  # fmt: skip
    stick_shop.name_badge(cv, frame, *BADGE, "BROOKE", "Member success")
    stick_gym.counter(cv, frame, sign=SIGN, fine=FINE)
    stick.rig(cv, frame, rig_keys(last_before(THEO_PART, ids, take.id)), end, look=THEO, poses=stick.STANDING,
              at=stick_gym.MEMBER_AT, blinks=blinks, mouth=SPEECH_MOUTH, **speaks.get("theo", {}))  # fmt: skip

# The card and the words sit above the shots, on the episode clock, so a close-up never scales them.
hook = stick.card(cv, cv.comp, HOOK, size=58)
cv.gate(hook, [(0, sign_at)])
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
subtitles.write_srt(ROOT / "cancel-anytime.srt", srt)
ep.instagram(POSTS["cancel-anytime"])
ep.finish(ROOT / "cancel-anytime.scene.xml", ROOT / "qa" / "sdk-validation.json")

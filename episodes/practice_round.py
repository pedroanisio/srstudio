#!/usr/bin/env python3
"""Stick — Practice Round, built with srstudio.

    SRSTUDIO_ALLOW_CLOUD=1 python3 practice_round_audio.py PROJECT --font DIR   # voices, timeline.json
    srstudio build practice-round PROJECT                                      # → PROJECT/practice-round.scene.xml

Dev asks Noor to practice interview questions with him and to be tough. The set is ``stick_table`` in the kitchen: the
planks, the drill and the empty brackets are in frame from the first frame, and the bedding comes along the table last.
The effects are ``foley`` bursts.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from practice_round_audio import (
    BEDDING_AT,
    BEDDING_FROM,
    BEDDING_RUN,
    BEDDING_TO,
    BRACKETS_AT,
    CAMERAS,
    DEV_ALONE,
    DEV_BEHIND,
    DEV_BRAVE,
    DEV_HANDS,
    DEV_KEEN,
    DEV_LOOK,
    DEV_READS,
    DEV_SMOOTH,
    DEV_THROWN,
    DRILL_AT,
    FACES,
    HOOK,
    LEFT,
    MARKS,
    MUG_AT,
    NOOR_ASKS,
    NOOR_DONE,
    NOOR_LOOK,
    NOOR_PAGE,
    NOOR_PLAIN,
    PEN,
    PEN_TILT,
    PLANKS_AT,
    POSES,
    RIGHT,
    SCRATCH_RATE,
    SETTLE,
    WHIP,
    WHIP_LOOK,
)
from srstudio import (
    SPEECH_MOUTH,
    Episode,
    foley,
    look,
    signature,
    stick,
    stick_home,
    stick_odds,
    stick_office,
    stick_reel,
)
from srstudio import stick_table as st

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    stick_reel.spec(
        ROOT,
        "practice-round",
        "196",
        "Practice Round — Stick",
        "Portrait stick-figure cartoon: Dev asks Noor to be tough in a practice interview, and every answer turns into "
        "evidence about the shelf. Native vector animation; ElevenLabs voices.",
        3404,
        bleed=True,
    )
)
cv, t = ep.cv, ep.t
shots = ep.sequence("shots")
said = {x.id: x for x in t.takes}
K = stick.RigKey
HOME, BOARD = K(0, "board", NOOR_PAGE), K(0, "rest", DEV_KEEN)


def camera(parent, name: str):
    focus, zoom, to = CAMERAS[name]
    return stick.camera(cv, parent, focus, zoom=zoom, to=to)


def speaks(take, who: str) -> dict:
    return dict(phones=take.phones, mood=take.mood) if take is not None and take.actor == who else {}


def noor(parent, keys, end: float, take=None) -> None:
    """Noor in her chair, the clipboard in her near hand, angled her way, or edge on while she guards it or carries it,
    and the pen in the far one."""
    place = dict(poses=POSES, at=RIGHT, flip=True)
    stick.rig(cv, parent, keys, end, look=NOOR_LOOK, mouth=SPEECH_MOUTH, **speaks(take, "noor"), **place)
    hand = stick.held(cv, parent, keys, end, **place)
    spans = [(k.start, keys[i + 1].start if i + 1 < len(keys) else end) for i, k in enumerate(keys)]
    shut = [span for span, k in zip(spans, keys, strict=True) if k.pose in ("guard", "up")]
    edge, page = cv.group(hand, cv.uid("board-edge")), cv.group(hand, cv.uid("board-page"))
    cv.gate(edge, shut or [(0, 0.0)])
    cv.gate(page, [span for span, k in zip(spans, keys, strict=True) if k.pose not in ("guard", "up")] or [(0, 0.0)])
    st.clipboard(cv, edge)
    st.clipboard(cv, page, quarter=True)
    pen = cv.group(stick.held(cv, parent, keys, end, far=True, **place), cv.uid("pen"))
    if len({PEN_TILT.get(k.pose, 0.0) for k in keys}) > 1:
        cv.keys(pen, "rotation", [(k.start, PEN_TILT.get(k.pose, 0.0)) for k in keys])
    else:
        pen.rotation = PEN_TILT.get(keys[0].pose, 0.0)
    stick.shape(cv, pen, "M -14 6 L 64 -14", sw=10, stroke=PEN)


def dev(parent, keys, end: float, take=None) -> None:
    stick.rig(cv, parent, keys, end, poses=POSES, look=DEV_LOOK, at=LEFT, mouth=SPEECH_MOUTH, **speaks(take, "dev"))


def scene(parent, end: float, dev_keys, noor_keys, *, take=None) -> None:
    """The kitchen out of focus, the job nobody has mentioned, the two of them, and the table over their knees."""
    far = look.depth(cv, parent, "practice-far", 5.0, overscan=True)
    stick_home.kitchen(cv, far, marks=False, safe=False)
    st.wall_brackets(cv, parent, *BRACKETS_AT)
    stick_odds.planks(cv, parent, *PLANKS_AT, scale=0.72)
    stick_odds.drill(cv, parent, *DRILL_AT, scale=0.7)
    st.seats(cv, parent)
    dev(parent, dev_keys, end, take)
    if noor_keys:
        noor(parent, noor_keys, end, take)
    st.table(cv, parent)
    stick_office.mug(cv, parent, *MUG_AT)
    signature.cactus(cv, parent, *MARKS["cactus"], scale=0.42)
    signature.code(cv, parent, *MARKS["code"], 9, color="#4a3520")


def stage(take) -> None:
    """Draw ``take``'s shot."""
    g = ep.shot(shots, take)
    end, line = take.duration, take.speech_duration
    if take.shot == "two" and take.id == "01":
        settle = [
            (0.0, "landing"),
            (0.2, "rest"),
            (0.42, "tug-a"),
            (0.62, "tug-b"),
            (0.82, "tug-a"),
            (SETTLE, "straight"),
        ]
        scene(camera(g, "two"), end, [K(a, p, DEV_KEEN) for a, p in settle], [K(0, "board", NOOR_PLAIN)], take=take)
    elif take.shot == "two" and take.id == "02":
        scene(camera(g, "two"), end, [K(0, "straight", DEV_KEEN)],
              [K(0, "click", NOOR_PAGE), K(0.25, "board", NOOR_ASKS)], take=take)  # fmt: skip
    elif take.shot == "two":
        scene(camera(g, "two"), end, [K(0, "lean", DEV_BRAVE), K(line, "sunk", DEV_THROWN)], [K(0, "guard", NOOR_PAGE)],
              take=take)  # fmt: skip
    elif take.shot == "dev":
        face = DEV_SMOOTH if take.id == "03" else DEV_THROWN
        scene(camera(g, "dev"), end, [K(0, "straight", face)], [K(0, "read", NOOR_PAGE)], take=take)
    elif take.shot == "noor":
        scene(camera(g, "noor"), end, [K(0, "straight", DEV_SMOOTH)], [K(0, "read", NOOR_PAGE)], take=take)
    elif take.shot == "whip":
        frame = stick.dolly(
            cv, g, CAMERAS["noor"], CAMERAS["planks"], WHIP, start=line + WHIP_LOOK - 0.05, kind="cubic-in-out"
        )
        scene(frame, end, [K(0, "straight", DEV_THROWN), K(line * 0.6, "back", DEV_BEHIND)],
              [K(0, "point", NOOR_PLAIN)], take=take)  # fmt: skip
    elif take.shot == "planks":
        scene(camera(g, "planks"), end, [K(0, "back", DEV_BRAVE)], [K(0, "point", NOOR_PLAIN)], take=take)
    elif take.shot == "close":
        if take.id == "08":
            keys = writing(end, NOOR_PAGE)
        else:
            keys = [K(0, "board", NOOR_ASKS)]
        scene(camera(g, "close"), end, [K(0, "straight", DEV_BRAVE)], keys, take=take)
    elif take.shot == "scratch":
        scratch(g, take, end, line)
    elif take.shot == "push":
        frame = stick.dolly(cv, g, CAMERAS["two"], CAMERAS["dev"], line + 0.2)
        looks = [K(0, "sunk", DEV_THROWN), K(line + 0.2, "back", DEV_BEHIND), K(line + 0.85, "sunk", DEV_KEEN),
                 K(line + 1.4, "sunk", DEV_HANDS)]  # fmt: skip
        scene(frame, end, looks, [K(0, "board", NOOR_ASKS)], take=take)
    elif take.shot == "with":
        written(g, take, end, line)
    else:  # end
        frame = camera(g, "end")
        scene(frame, end, [K(0, "sunk", DEV_THROWN), K(line + BEDDING_AT + BEDDING_RUN + 0.1, "sunk", DEV_ALONE)], None,
              take=take)  # fmt: skip
        arrive = line + BEDDING_AT
        st.folded_bedding(
            cv, frame, BEDDING_TO, st.TOP, slide=((arrive, BEDDING_FROM), (arrive + BEDDING_RUN, BEDDING_TO))
        )


def writing(end: float, face, *, start: float = 0.0) -> list:
    """Her far hand on the page in two frames, from ``start`` until ``end``."""
    keys = [K(0, "read", face)] if start else []
    step, i = 1 / SCRATCH_RATE, 0
    while start + i * step < end - 1e-6:
        keys.append(K(round(start + i * step, 4), "write-a" if i % 2 == 0 else "write-b", face))
        i += 1
    return keys


def scratch(g, take, end: float, line: float) -> None:
    """ "Really well." on Dev, then the two-shot: she writes for a long time, he leans in, she pulls the board away."""
    near = cv.group(g, cv.uid("dev-side"))
    cv.gate(near, [(0, line)])
    scene(camera(near, "dev"), end, [K(0, "straight", DEV_BRAVE)], [K(0, "read", NOOR_PLAIN)], take=take)
    wide = cv.group(g, cv.uid("write-wide"))
    cv.gate(wide, [(line, end)])
    guard = line + 1.0
    her = [k for k in writing(guard, NOOR_PAGE, start=line + 0.02)] + [K(guard, "guard", NOOR_PAGE)]
    scene(camera(wide, "two"), end, [K(0, "straight", DEV_BRAVE), K(line + 0.55, "lean", DEV_READS)], her)


def written(g, take, end: float, line: float) -> None:
    """ "With you?" held on Dev, then the two-shot: one word, the click, the board in, and she stands."""
    near = cv.group(g, cv.uid("dev-hope"))
    cv.gate(near, [(0, line + 0.15)])
    scene(camera(near, "dev"), end, [K(0, "sunk", DEV_BRAVE)], [K(0, "board", NOOR_PLAIN)], take=take)
    wide = cv.group(g, cv.uid("verdict"))
    cv.gate(wide, [(line + 0.15, end)])
    a = line + 0.15
    her = [*writing(a + 0.5, NOOR_PAGE, start=a), K(a + 0.5, "click", NOOR_PAGE), K(a + 0.9, "guard", NOOR_DONE),
           K(a + 1.25, "up", NOOR_DONE)]  # fmt: skip
    scene(camera(wide, "two"), end, [K(0, "sunk", DEV_BRAVE)], her)


def sound() -> list:
    """The chair, her pen's clicks and its scratches, the fridge through the long hold, and the bedding landing."""
    run = ROOT / "audio"
    click = foley.Burst(0.03, 3600.0, attack=0.001, decay=0.3, tone_hz=2400.0, tone_end_hz=1800.0, tone=0.2)
    scratchy = foley.Burst(0.09, 5200.0, attack=0.006, decay=0.7)
    write, ten, twelve, thirteen, fourteen = said["08"], said["10"], said["12"], said["13"], said["14"]
    scratch_from = ten.start + ten.speech_duration + 0.02
    verdict = thirteen.start + thirteen.speech_duration + 0.15
    scrapes = [write.start + 0.1 + i * 0.13 for i in range(6)]
    scrapes += [scratch_from + i * 0.13 for i in range(8)]
    scrapes += [verdict + i * 0.13 for i in range(4)]
    clicks = [said["02"].start, verdict + 0.5]
    foley.write_bursts(run / "chair.wav", [0.0, 0.05, 0.1], t.duration, foley.SCRAPE, seed=7)
    foley.write_bursts(run / "click.wav", clicks, t.duration, click)
    foley.write_bursts(run / "scratch.wav", scrapes, t.duration, scratchy, seed=11)
    hum = foley.Burst(STARE_SECONDS, 140.0, attack=0.25, decay=0.8, tone_hz=60.0, tone_end_hz=60.0, tone=0.6)
    foley.write_bursts(run / "hum.wav", [twelve.start + twelve.speech_duration], t.duration, hum)
    landing = fourteen.start + fourteen.speech_duration + BEDDING_AT + BEDDING_RUN
    foley.write_bursts(run / "land.wav", [landing - 0.04], t.duration, foley.THUD)
    foley.write_bursts(
        run / "slide.wav", [landing - BEDDING_RUN + i * 0.07 for i in range(6)], t.duration, foley.SCRAPE, seed=9
    )
    return [
        ("chair", "audio/chair.wav", {"role": "effects", "gain": -10}),
        ("click", "audio/click.wav", {"role": "effects", "gain": -9}),
        ("scratch", "audio/scratch.wav", {"role": "effects", "gain": -15}),
        ("hum", "audio/hum.wav", {"role": "ambience", "gain": -20}),
        ("slide", "audio/slide.wav", {"role": "effects", "gain": -16}),
        ("land", "audio/land.wav", {"role": "effects", "gain": -8}),
    ]


STARE_SECONDS = said["12"].end - said["12"].start - said["12"].speech_duration
for take in t.takes:
    stage(take)

for shot, faces in (("two", tuple(FACES.values())), ("dev", (FACES["dev"],)), ("noor", (FACES["noor"],)),
                    ("close", (FACES["noor"],)), ("planks", (FACES["dev"],)), ("end", (FACES["dev"],))):  # fmt: skip
    stick_reel.check_framing(CAMERAS[shot], faces=faces, marks=MARKS.values())
hook = stick.card(cv, cv.comp, HOOK, size=58, width=stick_reel.CARD_CLEAR)
cv.gate(hook, [(0, min(3.0, t.takes[1].start))])
spoken = stick_reel.words(ep, t.takes, sentences=True, hold=True, join=True, least=stick_reel.WORD_MIN)
ep.audio(take=stick_reel.placing({}), loudness="-14", extra=sound())
stick_reel.close(ep, POSTS["practice-round"], hook, spoken, first_word=True)

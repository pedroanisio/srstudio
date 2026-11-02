#!/usr/bin/env python3
"""Trial Shift, built with srstudio: a café where nobody has ever been hired.

    srstudio record trial-shift PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build trial-shift PROJECT    # → PROJECT/trial-shift.scene.xml

Ava ties an apron on Milo. "How long have you worked here?" "I don't. It's just a quick trial shift." "When did it
start?" "April." "That's not so bad." "2019." His smile stays where it is. Behind him the Candidate crosses with a tray,
in an apron, tagged TRIAL, and so is she. "They'll let us know Friday." "Which Friday?" "Has anyone ever been hired?"
"Of course!" "Who?" Her smile holds. A chime, and a hand comes in at the door with a CV folder. Milo looks down at his
apron, takes the spare off its hook and holds it out, smiling hers. "It's just a quick trial shift."

The holdout of its round: no recipient and no send line. No music: the foley is synthesized here. It declares no engine
safe area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from srstudio import (
    CAFE,
    Episode,
    EpisodeSpec,
    camera,
    cast,
    cutout_arm,
    cutout_counter,
    cutout_handed,
    cutout_key,
    cutout_trial,
    cutout_walk,
    foley,
    locations,
    props,
    signature,
)
from srstudio import interview as iv_audio
from trial_shift_audio import (
    ARM,
    AT_DOOR,
    AVA_APART,
    AVA_HAND,
    AVA_SHOULDER,
    AVA_SIZE,
    CAPTION_LEAD,
    CAPTION_MIN,
    CAPTION_TAIL,
    GONE,
    HELD_OUT,
    HOOK,
    INTERVIEW,
    LEAVES,
    MILO_RIGHT_HAND,
    MILO_RIGHT_SHOULDER,
    MILO_SIZE,
    MILO_X,
    MILO_Y,
    OUT_OF_SIGHT,
    REST,
    SHOULDER,
    TRAY_HAND,
    TRAY_SIZE,
    TURNS_FRAME,
    TWO,
    WALKS_ON,
)

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="trial-shift",
        title=INTERVIEW.title,
        description="Job-hunting comedy: a quick trial shift that started in April, 2019, and the only people who "
        "work at the café. Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=3607,
        background="#D4B390",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        bleed=True,
    )
)
t, cv = ep.t, ep.cv
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
BEHIND, TAG, CHIME, WIDE = (float(t.meta[k]) for k in ("behind", "tag", "chime", "wide"))
DOWN, CROSSES, ARRIVES = (float(t.meta[k]) for k in ("down", "crosses", "arrives"))
TAKEN = ARRIVES + 0.16
OUT = L[11].start + 0.1

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))


def seen(*angles: str) -> list[tuple[float, float]]:
    return sorted(s for a in angles for s in spans[a])


GREEN_INK = 3
APRON = "M-43 119 L-54 327 L57 327 L43 119 L24 119 L22 154 L-23 154 L-25 119Z"
TIE_UP = [0.15, 0.5, 0.85]  # she pulls the strings three times, and he rocks with it
AVA_Y = 1040.0
AVA_X, AVA_CLOSE, AVA_TAG = 880.0, 660.0, 620.0
STANDS = {"ava": AVA_CLOSE, "tag": AVA_TAG, "turns": AVA_APART, "wide": AVA_APART, "door": AVA_APART}  # by shot
TRAY_Y = 800.0
DOOR_X, DOOR_TOP, DOOR_H = -10.0, 430.0, 1270.0
FOLDER_HAND = (128.0, 1160.0)
LAST_LOOK = WIDE + 0.45  # all three, at the door


MILO_WALK = [(0.0, MILO_X), (CROSSES, MILO_X), (ARRIVES, AT_DOOR), (DURATION, AT_DOOR)]

for name, times, burst, seed in (
    ("strings", TIE_UP, foley.SWISH, 3608),
    ("cups", [BEHIND + 0.15, BEHIND + 0.5, BEHIND + 0.8, L[6].start + 0.3, L[7].end + 0.2], foley.CLACK, 3609),
    ("chime", [CHIME], foley.BELL, 3610),
    ("steps", cutout_walk.footfalls(MILO_WALK), foley.KNOCK, 3611),
    ("cloth", [ARRIVES + 0.05], foley.SWISH, 3612),
):
    foley.write_bursts(ROOT / "assets" / f"{name}.wav", list(times), DURATION, burst, seed=seed)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("strings", "assets/strings.wav", {"role": "effects", "gain": -14}),
        ("cups", "assets/cups.wav", {"role": "effects", "gain": -12}),
        ("chime", "assets/chime.wav", {"role": "effects", "gain": -10}),
        ("steps", "assets/steps.wav", {"role": "effects", "gain": -16}),
        ("cloth", "assets/cloth.wav", {"role": "effects", "gain": -14}),
    ],
    loudness="-14",
)


def milo_units(x: float, y: float) -> tuple[float, float]:
    """A point of the room in Milo's rig units, once he stands at the door."""
    return (x - AT_DOOR) / MILO_SIZE, (y - MILO_Y) / MILO_SIZE


def on_tray(g):
    tray = cv.group(g, "trial-tray", x=0, y=236)
    cv.rect(tray, -130, 0, 260, 14, "#8D949B", cv.ink, 3, radius=6)
    props.coffee_cup(cv, tray, -62, -56, 0.5)
    props.coffee_cup(cv, tray, 56, -56, 0.5)


def candidate(g):
    """Behind the counter, so the counter is his legs: he crosses and does not stop. Past Milo while they talk, in sight
    of the door when it chimes, and gone behind it before Milo crosses, so the last shot is Milo's."""
    group = cv.group(g, "candidate-shots")
    cv.gate(group, seen("behind", "friday", "turns", "wide"))
    who = cast.Candidate(cv, tag="candidate-tray")
    node = ep.perform(
        who,
        group,
        1010.0,
        TRAY_Y,
        TRAY_SIZE,
        mouth=ep.mouth("candidate"),
        blinks=[(L[6].end + 0.05, L[6].end + 0.19), (WIDE + 0.25, WIDE + 0.39)],
        nods=[(0, 3)],
        free_arms=("left", "right"),
    )
    cv.keys(
        who.eyes, "x", [(0, -8), (WIDE - 0.01, -8), (WIDE, 10), (LAST_LOOK, 10), (LAST_LOOK + 0.12, -14)], hold=False
    )
    cv.path(who.group, APRON, cutout_trial.GREEN, cv.ink, GREEN_INK)
    cutout_trial.trial_tag(cv, who.group, 0, 190, scale=0.78, id="candidate-tag")
    on_tray(who.group)
    for side, shoulder, hand in (("left", (-66, 148), (-TRAY_HAND, 240)), ("right", (67, 148), (TRAY_HAND, 240))):
        bend = 1 if side == "left" else -1
        cutout_arm.arm(cv, who.group, f"candidate-{side}", shoulder, [(0.0, *hand)], upper=80, fore=80, bend=bend,
                       width=5.0, hand=26.0, skin="#F1D0AA")  # fmt: skip
    friday, turns, wide = spans["friday"][0], spans["turns"][0], spans["wide"][0]
    rows = [
        (0.0, 1010.0),
        (BEHIND, 1010.0),
        (TAG, 800.0),
        (friday[0], 800.0),
        (friday[0], 850.0),
        (friday[1], 745.0),
        (turns[0], 745.0),
        (turns[0], WALKS_ON[0]),
        (turns[1], WALKS_ON[1]),
        (wide[0], WALKS_ON[1]),
        (wide[0], 272.0),  # clear of the board's code, and still in sight of the door
        (DOWN - LEAVES, 272.0),
        (CROSSES + GONE, OUT_OF_SIGHT),
        (DURATION, OUT_OF_SIGHT),
    ]
    cutout_walk.walk(cv, node, rows, TRAY_Y)


def door(parent):
    """The doorway, then the hand, then the leaf: it opens over the arm, and the street is plain light. Only the wide
    and the last shot see it: anywhere else its sign would hang out of the frame."""
    g = cv.group(parent, "the-door")
    cv.gate(g, seen("wide", "door"))
    cv.rect(g, DOOR_X - 18, DOOR_TOP - 18, 226, DOOR_H + 36, "#6E4B32", cv.ink, 5)
    cv.rect(g, DOOR_X, DOOR_TOP, 190, DOOR_H, "#E8F0EE")
    slide = cv.group(g, "hand-comes-in")  # the frame's left side is drawn again after it, over the sleeve
    cv.gate(slide, [(CHIME, DURATION)])
    cv.keys(slide, "x", [(0.0, -320.0), (CHIME + 0.1, -320.0), (CHIME + 0.5, 0.0)], kind="sine-out")
    cutout_counter.reaching_hand(
        cv,
        slide,
        *FOLDER_HAND,
        scale=0.8,
        rotation=90,
        grip=110,
        skin="#D9A87C",
        sleeve="#7D6A8C",
        holds=lambda h: cutout_handed.cv_folder(cv, cv.group(h, "cv-upright", rotation=-90), 0, -10, scale=0.5),
        id="the-next-hand",
    )
    cv.rect(g, DOOR_X - 18, DOOR_TOP - 18, 18, DOOR_H + 36, "#6E4B32", cv.ink, 5)
    leaf = cutout_handed.cafe_door(cv, g, DOOR_X, DOOR_TOP, width=190, height=DOOR_H, sign="OPEN", sign_size=22)
    cv.keys(leaf, "scaleX", [(0.0, 1.0), (CHIME, 1.0), (CHIME + 0.35, 0.4)], kind="sine-out")


def peg(g):
    """The spare on its hook, only in the shots that see the end of the counter whole."""
    g = cv.group(g, "the-peg")
    cv.gate(g, seen("wide", "door"))
    cv.rect(g, HOOK[0] - 26, HOOK[1] - 12, 52, 16, "#6E4B32", cv.ink, 3, radius=4)
    hung = cv.group(g, "spare-on-its-hook")
    cv.gate(hung, [(0.0, TAKEN)])
    cutout_trial.apron_spare(cv, hung, HOOK[0], HOOK[1] - 8, scale=0.56, id="spare-hung")


def ava(g):
    """Behind him at the opening, then her close and the tag, cheated along the room so the marks stay in frame."""
    group = cv.group(g, "ava-shots")
    cv.gate(group, seen("open", "ava", "tag", "turns", "wide", "door"))
    who = cast.Barista(cv, tag="ava-trial")
    smile = [(0.0, L[1].start), (L[1].end, L[3].start), (L[3].end, L[5].start), (L[5].end, L[9].start),
             (L[9].end, DURATION)]  # fmt: skip
    node = ep.perform(
        who,
        group,
        AVA_X,
        AVA_Y,
        AVA_SIZE,
        mouth=ep.mouth("ava", smile=smile),
        blinks=[(L[3].end + 0.05, L[3].end + 0.19), (L[9].end + 0.1, L[9].end + 0.24)],
        nods=[
            (0, 4),
            (L[1].start, 4),
            (L[1].start + 0.2, -2),
            (L[10].end, -2),
            (L[10].end + 0.2, -9),
            (WIDE, -9),
            (LAST_LOOK, -9),
            (LAST_LOOK + 0.15, 0),
        ],  # fmt: skip
        name=None,
        legs=True,
        free_arms=("left",),
    )
    eyes_x = [(0.0, -12.0), (L[1].start, -12.0), (L[1].start + 0.05, 0.0), (LAST_LOOK, 0.0), (LAST_LOOK + 0.12, -14.0)]
    cv.keys(who.eyes, "x", eyes_x, hold=False)
    eyes_y = [(0.0, 8.0), (L[1].start, 8.0), (L[1].start + 0.05, 0.0), (L[10].end, 0.0), (L[10].end + 0.2, -14.0),
              (LAST_LOOK, -14.0), (LAST_LOOK + 0.12, 0.0)]  # fmt: skip
    cv.keys(who.eyes, "y", eyes_y, hold=False)
    tied = [(0.0, -96.0, 168.0)]
    for at in TIE_UP:
        tied += [(at, -96.0, 168.0), (at + 0.12, -86.0, 192.0), (at + 0.3, -96.0, 168.0)]
    tied += [(L[1].start - 0.1, -96.0, 168.0), (L[1].start + 0.1, -92.0, 316.0)]
    turn = spans["turns"][0][0]
    tied += [(turn - 0.5, -92.0, 316.0), (turn - 0.1, *AVA_HAND)]  # off screen: she is not in Milo's close
    cutout_arm.arm(cv, who.group, "ava-tying", AVA_SHOULDER, tied, upper=96, fore=96, bend=-1, width=5.0, hand=26.0,
                   skin=who.skin)  # fmt: skip
    tag = cv.group(who.group, "ava-tag-from-here")
    cv.gate(tag, [(TAG, DURATION)])
    cutout_trial.trial_tag(cv, tag, 0, 188, scale=0.78, id="ava-tag")
    rows = [(0.0, AVA_X)]
    x = AVA_X
    for c in cuts[1:]:
        to = STANDS.get(c.angle, AVA_X)
        if to != x:
            rows += [(c.time, x), (c.time, to)]
            x = to
    rows.append((DURATION, x))
    cutout_walk.walk(cv, node, rows, AVA_Y)


def milo(g):
    """His smile, and the apron: he keeps both, and hands the look down the line at the end."""
    group = cv.group(g, "milo-shots")
    cv.gate(group, seen("open", "milo", "behind", "friday", "turns", "wide", "door"))
    who = cast.Customer(cv, tag="milo-trial")
    smile = [(0.0, L[0].start), (L[0].end, L[2].start), (L[4].end, L[7].start), (L[10].end - 0.02, DOWN),
             (ARRIVES, L[11].start), (L[11].end, DURATION)]  # fmt: skip
    nods = [(0, -2)]
    for at in TIE_UP:
        nods += [(at, -2), (at + 0.12, 3), (at + 0.3, -2)]
    nods += [(DOWN, -2), (DOWN + 0.14, 11), (CROSSES, 11), (CROSSES + 0.12, 0)]
    node = ep.perform(
        who,
        group,
        MILO_X,
        MILO_Y,
        MILO_SIZE,
        mouth=ep.mouth("milo", smile=smile),
        blinks=[(L[2].end + 0.05, L[2].end + 0.19), (L[7].end + 0.05, L[7].end + 0.19)],
        nods=nods,
        free_arms=("left", "right"),
    )
    cv.keys(who.eyes, "x", [(0.0, 0.0), (L[7].end, 0.0), (L[7].end + 0.1, 16.0), (WIDE, 16.0), (LAST_LOOK, 16.0),
                            (LAST_LOOK + 0.12, -14.0), (DOWN, -14.0), (DOWN + 0.1, 0.0)], hold=False)  # fmt: skip
    cv.keys(who.eyes, "y", [(0.0, 0.0), (DOWN, 0.0), (DOWN + 0.1, 12.0), (CROSSES, 12.0), (CROSSES + 0.1, 0.0)],
            hold=False)  # fmt: skip
    apron = cv.group(who.group, "milo-apron")
    cv.keys(
        apron, "y", [(0.0, 12.0), (TIE_UP[0] + 0.12, 8.0), (TIE_UP[1] + 0.12, 4.0), (TIE_UP[2] + 0.12, 0.0)], hold=False
    )
    cv.path(apron, APRON, cutout_trial.GREEN, cv.ink, GREEN_INK)
    turn = spans["turns"][0][0]
    hangs = [(0.0, 96.0, 326.0), (turn - 0.01, 96.0, 326.0), (turn, *MILO_RIGHT_HAND)]  # on the cut, off Ava's arm
    cutout_arm.arm(cv, who.group, "milo-right", MILO_RIGHT_SHOULDER, hangs, upper=96, fore=96, bend=1, width=5.0,
                   hand=26.0, skin=who.skin)  # fmt: skip
    hook = milo_units(HOOK[0], HOOK[1] - 8)
    held = milo_units(*HELD_OUT)
    track = [(0.0, *REST), (ARRIVES, *REST), (TAKEN, *hook), (OUT, *held)]
    arm = cutout_arm.arm(cv, who.group, "milo-left", SHOULDER, track, upper=ARM, fore=ARM, bend=-1, width=5.0,
                         hand=26.0, skin=who.skin)  # fmt: skip
    spare = cv.group(arm.grip, "spare-in-hand")
    cv.gate(spare, [(TAKEN, DURATION)])
    cutout_trial.apron_spare(cv, spare, 0, 0, scale=0.56 / MILO_SIZE, id="spare-held")
    return cutout_walk.walk(
        cv, node, [(0.0, MILO_X), (CROSSES, MILO_X), (ARRIVES, AT_DOOR), (DURATION, AT_DOOR)], MILO_Y
    )


def at_counter(g):
    door(g)
    peg(g)
    code = cv.group(g, "tag-shot-code")  # the shot is too close for the board's: the wall by her shoulder has it
    cv.gate(code, spans["tag"])
    signature.code(cv, code, 458, 1110, 9, color="#8C7A5A", align="end")
    ava(g)
    milo(g)


finish = locations.finish(cv, ep.comp)
room = locations.cafe(cv, finish, behind_counter=candidate, at_counter=at_counter)


def close(at, scale, to=(540, 775)):
    x, y = at
    return scale, to[0] - x * scale, to[1] - y * scale


FRAMES = {  # angle -> scale, x, y
    "open": TWO,
    "ava": close((AVA_CLOSE, AVA_Y), 1.7),
    "milo": close((MILO_X, MILO_Y), 1.6),
    "behind": close((MILO_X, MILO_Y), 1.2, (540, 900)),  # any tighter or higher, the head behind him reaches the bug
    "tag": close((AVA_TAG, AVA_Y + 188 * AVA_SIZE), 2.4, (540, 1000)),
    "friday": TWO,
    "turns": TURNS_FRAME,
    "wide": (1.0, 0.0, -140.0),
    "door": (1.2, 30.0, -320.0),
}
camera.reframe(cv, room, [(c.time, *FRAMES[c.angle]) for c in cuts])

hook = cutout_key.key_line(cv, ep.comp, "TRIAL SHIFT: 10 TO 11", 0.0, 3.0, font=(ROOT / ep.spec.font).read_bytes())
spoken = ep.spoken_captions(CAPTION_TAIL, CAPTION_LEAD, min_seconds=CAPTION_MIN)
spoken = ep.captions(spoken, x=80, y=1420, width=920, size=60)
ep.hide_on_cover(hook, *spoken)
ep.markers(extra=[("marker-tag", TAG, "The tag"), ("marker-door", CHIME, "The next one")])
ep.instagram(POSTS["trial-shift"])
ep.finish()

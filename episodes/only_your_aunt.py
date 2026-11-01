#!/usr/bin/env python3
"""Only Your Aunt, built with srstudio: one interview, one mother, and a town that already knows.

    srstudio record only-your-aunt PROJECT   # generated clips, resolved and pinned by the engine
    srstudio build only-your-aunt PROJECT    # → PROJECT/only-your-aunt.scene.xml

Milo walks into the cafe with the phone at his ear. "Mom, it's one interview. Don't tell anyone." "Who would I tell?" A
coffee comes down the counter into his hand, and he turns it round: GOOD LUCK AT THE BANK. "What a nice town." On a park
bench a stranger lays a crayon page on his knee, pats it twice and goes. "Is he a nice boy?" Reception: streamers, and
the Boss behind a cake with his name on it. Nobody speaks. "Mom. There's a cake." "Is it chocolate?" "Who did you tell?"
Rosa at home, a hand to her heart, wounded. "Nobody! Your aunt doesn't count." Cut on the last word to a slice held out.

Rosa is heard down the phone until her close-up. Ava, the man on the bench and the Boss are silent and unnamed. No
music: the foley is synthesized here. It declares no engine safe area, so captions are placed inside x 80–920 by hand.
"""

import os

from _common import project_root
from instagram_posts import POSTS
from only_your_aunt_audio import INTERVIEW
from srstudio import (
    CAFE,
    Episode,
    EpisodeSpec,
    cast,
    cutout_arm,
    cutout_counter,
    cutout_home,
    cutout_key,
    cutout_leak,
    cutout_lobby,
    cutout_locate,
    foley,
    locations,
    look,
    props,
    signature,
)
from srstudio import interview as iv_audio

os.umask(0o077)  # generated outputs are private: folders 700, files 600

ROOT = project_root(__file__)
ep = Episode(
    EpisodeSpec(
        slug="only-your-aunt",
        title=INTERVIEW.title,
        description="Job-hunting comedy: a mother asked to tell nobody, and a town that has read the cup by lunchtime. "
        "Native vector animation; ElevenLabs dialogue, synthesized foley.",
        root=ROOT,
        **iv_audio.spec_font(INTERVIEW.font, ROOT),
        seed=3401,
        background="#E4DBC4",
        palette=CAFE,
        audio=None,  # every clip is a pinned <generated> asset on its own track
        bleed=True,
    )
)
t, cv = ep.t, ep.cv
DURATION = t.duration
L = [ep.P(i) for i in range(len(t.phrases))]
FLICK, CAUGHT = float(t.meta["flick"]), float(t.meta["caught"])
SITS, PATS, LEAVES = float(t.meta["sits"]), float(t.meta["pats"]), float(t.meta["leaves"])
STOPS, CUTS = float(t.meta["stops"]), float(t.meta["cuts"])
TELL = iv_audio.said(ROOT, L[8], "tell")
COUNT = iv_audio.said(ROOT, L[9], "count")

cuts = list(t.cuts)
spans: dict[str, list[tuple[float, float]]] = {}
for i, c in enumerate(cuts):
    end = cuts[i + 1].time if i + 1 < len(cuts) else DURATION
    spans.setdefault(c.angle, []).append((c.time, end))
CAFE_SHOT, BACK = spans["cafe"]
CUP = spans["cup"][0]
PARK = spans["park"][0]
ROOM = spans["reception"][0]
HOME = (spans["home"][0][0], COUNT)
SLICE = (COUNT, DURATION)
ROOM_SHOTS = [ROOM, SLICE]

MILO = (270.0, 1035.0, 1.53)
MILO_SEATED = (720.0, locations.park_seat_y(300, 1.35), 1.35)
MILO_ROOM = (locations.RECEPTION_VISITOR[0], locations.RECEPTION_VISITOR[1], 1.5)
AVA = (800.0, 800.0, 1.4)
STRANGER = (300.0, locations.park_seat_y(330, 1.35), 1.35)
BOSS = (660.0, 690.0, 1.3)
ROSA = (480.0, 470.0, 2.6)
CUP_ROW = 1222.0
CUP_FROM, CUP_TO = 650.0, 460.0
KNEE = (690.0, 1322.0)
EAR = (-114.0, 6.0)  # the phone hand, in the rig's units
HIP = (112.0, 318.0)  # Milo's free hand at rest, in the rig's units
CHEST = (104.0, 196.0)  # and with a coffee in it
HOLDS = (118.0, 192.0)  # his hand on the short arm of the shots that open with the coffee already held
WHITE = "#F6F1E6"
LEAN = 26.0  # his arm comes up from the lower left
TILT = 48.0  # the Boss's arm comes in from the lower right; what it holds stays level
SHIRT = "#E9E5DC"

foley.write_bursts(ROOT / "assets" / "door.wav", [0.04], DURATION, foley.BELL, seed=3402)
foley.write_bursts(ROOT / "assets" / "slide.wav", [FLICK + 0.04], DURATION, foley.SCRAPE, seed=3403)
foley.write_bursts(ROOT / "assets" / "catch.wav", [CAUGHT, PARK[0] + 0.72], DURATION, foley.KNOCK, seed=3404)
foley.write_bursts(ROOT / "assets" / "pat.wav", [PATS, PATS + 0.2], DURATION, foley.CHEW, seed=3405)
foley.write_bursts(ROOT / "assets" / "rustle.wav", [ROOM[0] + 0.1, PARK[0] + 0.5], DURATION, foley.SWISH, seed=3406)
foley.write_bursts(ROOT / "assets" / "knife.wav", [CUTS + 0.02, CUTS + 0.72], DURATION, foley.KNOCK, seed=3407)
foley.write_whoosh(ROOT / "assets" / "zoom.wav", [TELL - 0.08], DURATION, seed=3408)
ep.audio(
    extra=[
        ("room-tone", "assets/room-tone.wav", {"role": "ambience"}),
        ("door", "assets/door.wav", {"role": "effects", "gain": -16}),
        ("slide", "assets/slide.wav", {"role": "effects", "gain": -8}),
        ("catch", "assets/catch.wav", {"role": "effects", "gain": -14}),
        ("pat", "assets/pat.wav", {"role": "effects", "gain": -8}),
        ("page-rustle", "assets/rustle.wav", {"role": "effects", "gain": -16}),
        ("knife", "assets/knife.wav", {"role": "effects", "gain": -12}),
        ("zoom", "assets/zoom.wav", {"role": "effects", "gain": -8}),
    ],
    loudness="-14",
)


def on_the_phone(who, tag):
    """His screen-left hand keeps the phone at his ear, in every shot he is in."""
    skin = getattr(who, "skin", None)
    arm = cutout_arm.arm(
        cv, who.group, f"{tag}-phone-arm", (-72, 143), [(0.0, *EAR)], upper=96, fore=96, bend=1, skin=skin
    )
    cutout_locate.held_phone(cv, arm.grip, 8, -18, scale=0.6, id=f"{tag}-phone")


def with_coffee(who, tag, size, track, shown, reach=96):
    """His screen-right hand on its own arm, the cup held in front of it, so the hand shows behind the cup."""
    arm = cutout_arm.arm(
        cv, who.group, f"{tag}-coffee-arm", (73, 144), track, upper=reach, fore=reach, bend=1, skin=who.skin
    )
    cup = cv.group(arm.grip, f"{tag}-cup-in-hand", x=-26 / size)
    cv.gate(cup, shown)
    props.coffee_cup(cv, cup, 0, 0, 1 / size, shadow=False)


def walks_in(node, x, y, start, end, start_x=-260.0):
    """In from off the left, the bob of a walk, and he stops."""
    cv.keys(node, "x", [(start, start_x), (end, x)], hold=False, kind="sine-out")
    steps = int((end - start) / 0.16)
    cv.keys(node, "y", [(start + k * 0.16, y - 12 if k % 2 else y) for k in range(steps)] + [(end, y)], hold=False)


def ava(g):
    ep.perform(
        cast.Barista(cv, tag="ava-cafe"),
        g,
        *AVA,
        mouth=[(0.0, "smile")],
        blinks=[(L[0].end, L[0].end + 0.14), (L[3].start, L[3].start + 0.14)],
        nods=[(0, 0), (BACK[0], 0), (BACK[0] + 0.2, 4), (BACK[0] + 0.6, 0)],
        free_arms=("left",),
        name=None,
    )


def milo_cafe(g):
    who = cast.Customer(cv, tag="milo-cafe")
    node = ep.perform(
        who,
        g,
        *MILO,
        mouth=ep.mouth("milo"),
        blinks=[(L[1].start, L[1].start + 0.14), (L[3].end, L[3].end + 0.14)],
        nods=[(0, 0), (L[0].start, 0), (L[0].start + 0.3, 3), (L[0].end, 0), (L[2].start, 0), (L[2].start + 0.2, -3)],
        free_arms=("left", "right"),
    )
    walks_in(node, MILO[0], MILO[1], 0.0, 0.84, start_x=-70.0)
    on_the_phone(who, "milo-cafe")
    size = MILO[2]
    catch = ((CUP_TO + 26 - MILO[0]) / size, (CUP_ROW + 6 - MILO[1]) / size)
    track = [(0.0, *HIP), (CAUGHT - 0.25, catch[0] - 6, catch[1] + 10), (CAUGHT, *catch), (CUP[1] - 0.1, *CHEST)]
    with_coffee(who, "milo-cafe", size, track, [(CAUGHT, DURATION)])


def ava_arm(g):
    """In frame pixels, in front of the counter: the flick along the wood. An arm bends to one side of its own line, so
    the salute is a second arm, its elbow out past her hair, swapped in on the cut back to the shot she is in."""
    shoulder = (AVA[0] - 66 * AVA[2], AVA[1] + 140 * AVA[2])
    rest = (CUP_FROM + 34, CUP_ROW + 4)
    track = [
        (0.0, *rest),
        (FLICK - 0.1, rest[0] + 22, rest[1]),
        (FLICK + 0.12, rest[0] - 50, rest[1]),
        (CAUGHT - 0.1, *rest),
    ]
    flick = cv.group(g, "ava-flicks")
    cv.gate(flick, [(0.0, BACK[0])])
    cutout_arm.arm(
        cv,
        flick,
        "ava-reach",
        shoulder,
        track,
        upper=128,
        fore=128,
        bend=-1,
        width=6.5,
        hand=50,
        skin=cast.Barista.skin,
    )
    salutes = cv.group(g, "ava-salutes")
    cv.gate(salutes, [BACK])
    brow = (AVA[0] - 180, AVA[1] - 48)
    up = [
        (BACK[0], brow[0] - 20, brow[1] + 110),
        (BACK[0] + 0.22, *brow),
        (BACK[1] - 0.4, *brow),
        (BACK[1], brow[0] - 26, brow[1] - 10),
    ]
    cutout_arm.arm(
        cv, salutes, "ava-salute", shoulder, up, upper=160, fore=160, bend=1, width=6.5, hand=50, skin=cast.Barista.skin
    )


def the_cup(g):
    moving = cv.group(g, "cup-sliding", y=CUP_ROW)
    cv.gate(moving, [(0.0, CAUGHT)])
    cv.keys(moving, "x", [(0.0, CUP_FROM), (FLICK, CUP_FROM), (CAUGHT, CUP_TO)], hold=False, kind="sine-out")
    props.coffee_cup(cv, moving, 0, 0, 1.0)


def at_counter(g):
    milo_cafe(cv.group(g, "milo-at-the-counter"))
    the_cup(g)
    ava_arm(cv.group(g, "ava-arm-in-front"))


def milo_bench(g):
    who = cast.Customer(cv, tag="milo-bench", seated=True)
    ep.perform(
        who,
        g,
        *MILO_SEATED,
        mouth=ep.mouth("milo"),
        blinks=[(SITS, SITS + 0.14), (L[5].start, L[5].start + 0.14)],
        nods=[(0, 0), (PATS, 0), (PATS + 0.2, 7), (L[4].start, 7), (L[4].start + 0.3, 3)],
        free_arms=("left", "right"),
    )
    cv.keys(who.eyes, "x", [(0, 0), (SITS, 0), (SITS + 0.1, -10)], hold=False)
    cv.keys(who.eyes, "y", [(0, 0), (PATS, 0), (PATS + 0.1, 8), (LEAVES + 0.3, 8), (LEAVES + 0.4, 0)], hold=False)
    on_the_phone(who, "milo-bench")
    with_coffee(who, "milo-bench", MILO_SEATED[2], [(0.0, *HOLDS)], [PARK], reach=46)


def stranger(g):
    """The man sits, lays a page on the knee, pats it twice and goes, without a word."""
    x, y, _ = STRANGER
    who = cast.Candidate(cv, tag="man-on-bench")
    node = ep.perform(
        who,
        g,
        *STRANGER,
        mouth=[(0.0, "rest")],
        blinks=[(PATS - 0.3, PATS - 0.16)],
        nods=[(0, 0), (PATS, 0), (PATS + 0.2, 6), (LEAVES, 6), (LEAVES + 0.1, 0)],
        legs="seated",
        free_arms=("right",),
    )
    cv.keys(who.eyes, "x", [(0, 12)], hold=False)
    cv.keys(who.eyes, "y", [(0, 6)], hold=False)
    start = PARK[0]
    cv.keys(node, "y", [(start, y - 90), (start + 0.22, y), (LEAVES, y), (LEAVES + 0.2, y - 90)], hold=False)
    cv.keys(node, "x", [(start, x), (LEAVES + 0.2, x), (LEAVES + 0.6, -300.0)], hold=False)
    return node


def bench_arm(g, node):
    """In frame pixels, in front of Milo: his hand carries the page over, then pats it."""
    shoulder = (STRANGER[0] + 67 * STRANGER[2], STRANGER[1] + 148 * STRANGER[2])
    lap = (KNEE[0], KNEE[1] - 46)
    rest = (shoulder[0] + 30, shoulder[1] + 240)
    start = PARK[0]
    track = [(start, *rest), (start + 0.25, rest[0], rest[1] - 24), (PATS - 0.2, *lap), (PATS, lap[0], lap[1] + 18),
             (PATS + 0.1, *lap), (PATS + 0.2, lap[0], lap[1] + 18), (PATS + 0.3, *lap), (LEAVES, *rest)]  # fmt: skip
    arm = cutout_arm.arm(cv, g, "man-reach", shoulder, track, upper=215, fore=215, bend=1, width=6.5, hand=50)
    cv.gate(arm.group, [(start, LEAVES + 0.2)])
    held = cv.group(arm.grip, "page-in-hand")
    cv.gate(held, [(start, PATS - 0.2)])
    cutout_leak.crayon_page(cv, held, 0, 40, scale=0.62, rotation=-8, id="page-carried")


def beside_bench(g):
    cast.pigeon(
        cv,
        g,
        55,
        1335,
        0.9,
        flip=False,
        nods=[(0, 0), (PATS, 0), (PATS + 0.2, 6), (PATS + 0.4, 0)],
        id="pigeon-watching",
    )
    laid = cv.group(g, "page-on-knee")
    cv.gate(laid, [(PATS - 0.2, DURATION)])
    cutout_leak.crayon_page(cv, laid, *KNEE, scale=0.62, rotation=-8)
    node = stranger(cv.group(g, "man-on-the-bench"))
    bench_arm(cv.group(g, "man-arm"), node)


def the_boss(g):
    ep.perform(
        cast.Manager(cv, tag="boss-reception"),
        g,
        *BOSS,
        mouth=[(0.0, "smile")],
        blinks=[(STOPS, STOPS + 0.14), (L[7].start, L[7].start + 0.14)],
        nods=[(0, 0), (CUTS, 0), (CUTS + 0.2, 4), (L[6].start, 4), (L[6].start + 0.2, 0)],
        free_arms=("right",),
    )


def on_counter(g):
    cutout_lobby.sheet_cake(cv, g, 700, locations.COUNTER_Y + 8, lines=("WELCOME", "MILO"), scale=1.15)
    shoulder = (BOSS[0] + 67 * BOSS[2], BOSS[1] + 148 * BOSS[2])
    above, into = (810.0, 790.0), (810.0, 880.0)
    track = [
        (0.0, *above),
        (CUTS - 0.4, *above),
        (CUTS, *into),
        (CUTS + 0.32, *above),
        (CUTS + 0.7, *into),
        (CUTS + 1.0, *above),
    ]
    arm = cutout_arm.arm(cv, g, "boss-cuts", shoulder, track, upper=130, fore=130, bend=-1, width=6.5, hand=48)
    cutout_leak.cake_knife(cv, arm.grip, 0, 0, scale=0.8)


def milo_room(g):
    who = cast.Customer(cv, tag="milo-room")
    node = ep.perform(
        who,
        g,
        *MILO_ROOM,
        mouth=ep.mouth("milo"),
        blinks=[(STOPS + 0.3, STOPS + 0.44), (L[7].end, L[7].end + 0.14)],
        nods=[(0, 0), (STOPS, 0), (STOPS + 0.2, -3), (L[8].start, -3), (L[8].start + 0.2, 4), (L[8].end, 0)],
        free_arms=("left", "right"),
    )
    cv.keys(who.eyes, "x", [(0, 12)], hold=False)
    walks_in(node, MILO_ROOM[0], MILO_ROOM[1], ROOM[0], STOPS)
    on_the_phone(who, "milo-room")
    with_coffee(who, "milo-room", MILO_ROOM[2], [(0.0, *HOLDS)], ROOM_SHOTS, reach=46)


def at_desk(g):
    milo_room(cv.group(g, "milo-at-reception"))
    hand = cv.group(g, "the-slice")
    cv.gate(hand, [SLICE])

    def plate(group):
        level = cv.group(group, "plate-level", rotation=TILT)
        cutout_leak.cake_slice(cv, level, 0, -40, scale=0.95)

    cv.keys(hand, "x", [(SLICE[0], 90.0), (SLICE[0] + 0.3, 0.0)], hold=False, kind="sine-out")
    cutout_counter.reaching_hand(
        cv, hand, 590, 1105, scale=1.0, rotation=-TILT, grip=120, skin=WHITE, sleeve=SHIRT, holds=plate
    )


def counter_cactus(g):
    """The cake takes the counter's middle, so the cactus stands at its near end, in frame in all three framings."""
    signature.cactus(cv, g, 430, locations.COUNTER_Y + 6, 0.5)


def rosa(g):
    who = cast.Rosa(cv, tag="rosa-home")
    ep.perform(
        who,
        g,
        *ROSA,
        mouth=ep.mouth("rosa"),
        blinks=[(HOME[0] + 0.35, HOME[0] + 0.5), (L[9].start - 0.12, L[9].start + 0.02)],
        nods=[(0, 0), (HOME[0], 0), (HOME[0] + 0.5, -4), (L[9].start, -4), (L[9].start + 0.25, 3)],
        free_arms=("left", "right"),
        stitch=None,
    )
    on_the_phone(who, "rosa")
    a = HOME[0] + 0.15
    track = [(0.0, 112.0, 216.0), (a, 112.0, 216.0), (a + 0.5, 30.0, 168.0)]
    cutout_arm.arm(cv, who.group, "rosa-heart", (67, 148), track, upper=96, fore=96, bend=1)


def cup_insert(g):
    """Full frame, his cup turned to the lens against the cafe, far plane soft and the marks on the counter's edge."""
    cv.gate(g, [CUP])
    far = look.depth(cv, g, "cup-depth-9", 9, overscan=True)
    cv.rect(far, 0, 0, 1080, 1240, "#E4DBC4")
    for yy in range(65, 1240, 130):
        cv.line(far, 0, yy, 1080, yy, "#C9C6AC", 3)
    for xx in range(110, 1080, 220):
        cv.line(far, xx, 0, xx, 1240, "#C9C6AC", 3)
    cv.rect(g, 0, 1240, 1080, 680, "#B27F51", cv.ink, 5)
    signature.cactus(cv, g, 930, 1240, 0.9)
    signature.code(cv, g, 1030, 1262, 12, color="#F3DCA4", align="end")

    def cup(group):
        level = cv.group(group, "cup-level", rotation=-LEAN)
        turning = cv.group(level, "cup-turning")
        cv.keys(turning, "scaleX", [(CUP[0], 0.45), (CUP[0] + 0.32, 1.0)], hold=False, kind="sine-out")
        cutout_leak.lettered_cup(cv, turning, 0, -60, lines=("GOOD LUCK", "AT THE", "BANK"), scale=0.98)

    rising = cv.group(g, "cup-rising")
    cv.keys(rising, "y", [(CUP[0], 150.0), (CUP[0] + 0.25, 0.0)], hold=False, kind="sine-out")
    cutout_counter.reaching_hand(
        cv, rising, 560, 800, scale=1.1, rotation=LEAN, grip=190, holds=cup, id="milo-holds-the-cup"
    )


finish = locations.finish(cv, ep.comp)
cafe = locations.cafe(
    cv, finish, behind_counter=ava, at_counter=at_counter, shots=[CAFE_SHOT, BACK], code_on_shelf=True
)
park = locations.park(cv, finish, on_bench=milo_bench, beside_bench=beside_bench, shots=[PARK], sign_lettering=False)
lobby = locations.reception(
    cv, finish, the_boss, on_counter, at_desk, shots=ROOM_SHOTS, cactus=counter_cactus, code_at=(560, 1376)
)
streamers = cv.group(lobby, "party-streamers")
cutout_lobby.paper_streamers(cv, streamers, 170, 910, 196, swags=4, sag=62.0)
home = cutout_home.home_study(cv, finish, behind_desk=rosa, shots=[HOME])
cup_insert(cv.group(finish, "cup-insert"))


def key(group, moves):
    """Hard cuts and pushes of a set, each frame (scale, x, y); the caller keeps every edge of the set out of frame."""
    for i, prop in enumerate(("scaleX", "x", "y")):
        cv.keys(group, prop, [(at, frame[i]) for at, frame in moves], hold=False)
    cv.keys(group, "scaleY", [(at, frame[0]) for at, frame in moves], hold=False)


WIDE = (1.0, 0.0, 0.0)
EPS = 1 / 120
ON_MILO = (1.12, 0.0, -320.0)  # Ava stays below the bug
key(cafe, [(0.0, WIDE), (BACK[0] - EPS, WIDE), (BACK[0], ON_MILO), (BACK[1], ON_MILO)])
MEDIUM = (1.1, 0.0, -192.0)
CRASH = (1.55, 0.0, -470.0)  # the Boss's head stays under the bug through the whole move, Milo's chin over the caption
key(
    lobby,
    [
        (0.0, WIDE),
        (L[6].start - 0.3 - EPS, WIDE),
        (L[6].start - 0.3, MEDIUM),
        (TELL - 0.02, MEDIUM),
        (TELL + 0.14, CRASH),
        (COUNT - EPS, CRASH),
        (COUNT, MEDIUM),
        (DURATION, MEDIUM),
    ],
)
CLOSE, CLOSER = (1.12, -24.0, 0.0), (1.18, -36.0, 0.0)
key(home, [(0.0, CLOSE), (HOME[0], CLOSE), (L[9].start, CLOSER), (DURATION, CLOSER)])

hook = cutout_key.key_line(cv, ep.comp, "TOP SECRET", 0.0, 3.0, top=250, font=(ROOT / ep.spec.font).read_bytes())
spoken = ep.captions(ep.spoken_captions(min_seconds=0.84), x=80, y=1420, width=920, size=60)
ep.hide_on_cover(hook, *spoken)
ep.markers(extra=[("marker-cake", ROOM[0], "The cake"), ("marker-count", COUNT, "Doesn't count")])
ep.instagram(POSTS["only-your-aunt"])
ep.finish()

"""The sloth, the goat and the hamster: three brush-drawn Toon characters with drawings of their own (pressed ink,
asymmetric dense contours, open inner strokes, a tilted head, a shade tone), the whole Toon contract, and the
signature expressions they bring to every brush character: a sleepy eye, a yawn, a scream and puffed cheeks."""

import hashlib
import math
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, brush, flat_counter, registry, sketch, toon, toon_cast, toon_critters, toon_wear
from srstudio.sketch import Beat, Line, Sketch, Speaker
from srstudio.toon import Pose, ToonDataError
from srstudio.voice import Voice, VoiceSettings
from support.toon_contour import bends, inside, points, sharpest
from support.toon_thumbnail import apart, lab, silhouette_rest, thumbnail

CRITTERS = toon_critters.CRITTERS
NEW = ("sloth", "goat", "hamster")
NEW_EYES = ("sleepy",)
NEW_MOUTHS = ("yawn", "scream", "puff")
BRUSH = {**toon_cast.LOOKS, **CRITTERS}  # every brush-drawn character


def canvas(duration: float) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


def runs_of(cv: Canvas):
    root = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    return [g for g in root.find("composition").iter("group") if g.get("start") is not None]


def width(layers) -> float:
    boxes = [brush.bounds(s) for s, _ in layers]
    return max(b[2] for b in boxes) - min(b[0] for b in boxes)


def height(layers) -> float:
    boxes = [brush.bounds(s) for s, _ in layers]
    return max(b[3] for b in boxes) - min(b[1] for b in boxes)


# -- every existing drawing is unchanged -------------------------------------------------------------------------------
OLD_EYES = (
    "wide",
    "half",
    "left",
    "up",
    "down",
    "side",
    "closed",
    "narrow",
    "shock",
    "roll",
    "teary",
    "wince",
    "hearts",
)
OLD_MOUTHS = (
    "flat",
    "open",
    "round",
    "o",
    "drop",
    "grin",
    "wave",
    "smirk",
    "none",
    "grimace",
    "frown",
    "tongue",
    "kiss",
)
OLD_LOOKS = ("dog", "frog", "bear", "rabbit", "fox", "raccoon", "hedgehog")


def test_every_existing_kind_on_every_existing_character_draws_byte_identically():
    """Digests taken at c857d72, before the critters: every part of every older brush character in every older kind
    (foundation, lids, headset, both eyes, mouths, visemes, both typing frames of every arms) and a sample of whole
    figures with wear."""
    h = hashlib.sha256()
    for name in OLD_LOOKS:
        look = toon_cast.LOOKS[name]
        parts = [toon_cast._foundation(look), toon_cast._lids(look), toon_cast.headset(look)]
        parts += [toon_cast._eye(look, look.eyes[k], e, s) for e in OLD_EYES for k, s in ((0, 1.0), (1, -1.0))]
        parts += [toon_cast._mouth(look, m) for m in OLD_MOUTHS]
        parts += [toon_cast._viseme(look, v) for v in toon_cast.VISEMES[1:]]
        parts += [toon_cast._arms(look, a, f) for a in toon.ARMS for f in (0, 1)]
        parts += [
            toon_cast.figure_layers(look, e, m, toon.ARMS[i % 7], i % 2, wear=toon.WEAR[: i % 4])
            for i, (e, m) in enumerate(zip(OLD_EYES, OLD_MOUTHS, strict=True))
        ]
        h.update(repr(parts).encode())
    assert h.hexdigest() == "f00cb004a87d14d7e6d81014229f85b33008950532a125ade725fb758150de0d"


def test_every_existing_character_draws_the_same_scene():
    h = hashlib.sha256()
    for name in OLD_LOOKS:
        cv = canvas(26.0)
        poses = [
            toon.Pose(2.0 * i, e, m, a)
            for i, (e, m, a) in enumerate(zip(OLD_EYES, OLD_MOUTHS, toon.ARMS * 2, strict=False))
        ]
        track = [(0.3, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed"), (14.1, "open"), (14.5, "closed")]
        getattr(toon_cast, name)(cv, cv.comp, poses, 26.0, taps=(8.2, 8.4, 8.6), mouths=track)
        h.update(cv.scene.to_bytes(layout="pretty"))
    assert h.hexdigest() == "7837d169258ffe66ce4218d3e7ba02377a8c972d464feee4ab0166d90dbc0f4c"


def test_the_traced_cat_draws_the_same_scene():
    cv = canvas(20.0)
    poses = [
        toon.Pose(2.0 * i, e, m, toon.ARMS[i % 7], toon.WEAR[: i % 4])
        for i, (e, m) in enumerate(zip(toon.TRACED_EYES, toon.TRACED_MOUTHS, strict=True))
    ]
    toon.cat(cv, cv.comp, poses, 20.0, taps=(2.2, 2.4))
    digest = hashlib.sha256(cv.scene.to_bytes(layout="pretty")).hexdigest()
    assert digest == "1975851a3cb6d271bcc4f1491d5382c04464ee62c20ead295a22ddced694df76"


# -- the new kinds -----------------------------------------------------------------------------------------------------
def test_the_vocabulary_gains_a_sleepy_eye_and_three_mouths():
    assert toon.EYES[-1:] == NEW_EYES and toon.MOUTHS[-3:] == NEW_MOUTHS
    assert not set(NEW_EYES) & set(toon.TRACED_EYES) and not set(NEW_MOUTHS) & set(toon.TRACED_MOUTHS)
    assert sketch.TOON_CAST.eyes == toon.EYES and sketch.TOON_CAST.mouths == toon.MOUTHS
    poses = toon.parse_poses([{"start": 0, "eyes": "sleepy", "mouth": "yawn", "arms": "sigh"}])
    assert (poses[0].eyes, poses[0].mouth) == ("sleepy", "yawn")


@pytest.mark.parametrize("name", list(BRUSH))
def test_every_brush_character_draws_the_new_mouths_unlike_any_older_one(name):
    look = BRUSH[name]
    older = [toon_cast.figure_layers(look, "wide", kind, "desk")[1] for kind in OLD_MOUTHS]
    for kind in NEW_MOUTHS:
        mine = toon_cast.figure_layers(look, "wide", kind, "desk")[1]
        assert mine and all(mine != theirs for theirs in older), f"{name}'s {kind} repeats an older mouth"


@pytest.mark.parametrize("name", list(BRUSH))
def test_every_brush_character_draws_a_sleepy_eye_unlike_any_older_one(name):
    look = BRUSH[name]
    older = [toon_cast.figure_layers(look, kind, "flat", "desk")[0] for kind in OLD_EYES]
    mine = toon_cast.figure_layers(look, "sleepy", "flat", "desk")[0]
    assert all(mine != theirs for theirs in older), f"{name}'s sleepy eyes repeat an older pair"


@pytest.mark.parametrize("name", list(BRUSH))
def test_a_yawn_is_a_tall_open_mouth_with_a_throat_and_a_tongue(name):
    look = BRUSH[name]
    yawn = toon_cast._mouth(look, "yawn")
    colours = [c for _, c in yawn]
    assert toon_critters.THROAT in colours and toon_cast.TONGUE in colours
    assert height(yawn) > height(toon_cast._mouth(look, "round")) + 10  # taller than any older open mouth
    assert height(yawn) > height(toon_cast._mouth(look, "open")) + 10


@pytest.mark.parametrize("name", list(BRUSH))
def test_a_scream_is_wider_than_a_shock_with_teeth_and_a_tongue(name):
    look = BRUSH[name]
    scream = toon_cast._mouth(look, "scream")
    colours = [c for _, c in scream]
    assert "white" in colours and toon_cast.TONGUE in colours and toon_critters.THROAT in colours
    for shocked in ("o", "round", "open"):
        assert width(scream) > width(toon_cast._mouth(look, shocked)) + 4, f"{name}: no wider than {shocked}"
    assert height(scream) > height(toon_cast._mouth(look, "open"))


@pytest.mark.parametrize("name", list(BRUSH))
def test_puffed_cheeks_are_a_closed_smile_between_two_bulges(name):
    look = BRUSH[name]
    puff = toon_cast._mouth(look, "puff")
    colours = [c for _, c in puff]
    assert toon.LIPS not in colours and toon_critters.THROAT not in colours  # the lips are closed
    assert width(puff) > look.mouth_w + 20  # the cheeks bulge out past the mouth's corners
    mx = look.mouth[0]
    left = [brush.bounds(s) for s, c in puff if c == "ink" and brush.bounds(s)[2] < mx]
    right = [brush.bounds(s) for s, c in puff if c == "ink" and brush.bounds(s)[0] > mx]
    assert left and right


def test_sleepy_eyes_hang_heavy_lids_over_low_pupils():
    look = toon_cast.FOX
    (_, ey), r = look.eyes[0], look.eye_r
    layers = toon_cast._eye(look, look.eyes[0], "sleepy", 1.0)
    lid = [brush.bounds(s) for s, c in layers if c == look.coat]
    assert lid and lid[0][3] > ey + 0.15 * r  # the lid comes down past the middle of the eye
    half = [brush.bounds(s) for s, c in toon_cast._eye(look, look.eyes[0], "half", 1.0) if c == look.coat]
    assert lid[0][3] > half[0][3] + 0.2 * r  # heavier than half-lidded
    pupils = [b for b in (brush.bounds(s) for s, c in layers if c == "ink") if b[2] - b[0] < r * 0.8]
    assert pupils and min((b[1] + b[3]) / 2 for b in pupils) > ey + 0.2 * r


def blinks_of(run) -> list[tuple[float, int]]:
    shut = [g for g in run.findall("group") if g.find("animate") is not None]
    assert len(shut) == 1
    return [(float(k.get("time")), int(k.get("value"))) for k in shut[0].find("animate").findall("key")]


@pytest.mark.parametrize("name", ["fox", "sloth", "hamster"])
def test_sleepy_eyes_blink_slower_and_longer(name):
    look = BRUSH[name]
    keys = {}
    for eyes in ("wide", "sleepy"):
        cv = canvas(20.0)
        toon_cast.figure(cv, cv.comp, look, [toon.Pose(0.0, eyes, "flat", "desk")], 20.0)
        keys[eyes] = blinks_of(runs_of(cv)[0])
    downs = {e: [t for t, v in k if v == 1] for e, k in keys.items()}
    holds = {
        e: [round(b - a, 6) for (a, va), (b, _) in zip(k, k[1:], strict=False) if va == 1] for e, k in keys.items()
    }
    assert downs["wide"][1] - downs["wide"][0] == pytest.approx(look.blink)
    assert downs["sleepy"][1] - downs["sleepy"][0] == pytest.approx(look.blink * toon_cast.SLEEPY_PACE)
    assert set(holds["wide"]) == {toon_cast.BLINK_HOLD} and set(holds["sleepy"]) == {toon_cast.SLEEPY_HOLD}
    assert toon_cast.SLEEPY_PACE > 1 and toon_cast.SLEEPY_HOLD > toon_cast.BLINK_HOLD


def test_blink_times_takes_a_hold_and_keeps_its_default():
    assert toon_cast.blink_times(0.0, 10.0, 3.0) == toon_cast.blink_times(0.0, 10.0, 3.0, toon_cast.BLINK_HOLD)
    assert toon_cast.blink_times(0.0, 2.0, 1.0, hold=0.5) == [0.55]
    with pytest.raises(ToonDataError, match="hold"):
        toon_cast.blink_times(0.0, 2.0, 1.0, hold=0.0)


@pytest.mark.parametrize(
    ("eyes", "mouth", "named"), [("sleepy", "flat", "sleepy")] + [("wide", m, m) for m in NEW_MOUTHS]
)
def test_the_traced_cat_refuses_the_new_kinds_by_name_drawing_nothing(eyes, mouth, named):
    cv = canvas(4.0)
    poses = [toon.Pose(0.0, "wide", "flat", "desk"), toon.Pose(2.0, eyes, mouth, "desk")]
    with pytest.raises(ToonDataError, match=f"traced cat has no {named!r}"):
        toon.cat(cv, cv.comp, poses, 4.0)
    assert runs_of(cv) == []


@pytest.mark.parametrize(("mouth", "teeth"), [("scream", False), ("yawn", True), ("puff", True)])
def test_the_rabbit_s_front_teeth_stay_out_of_a_scream(mouth, teeth):
    over = toon_cast.figure_layers(toon_cast.RABBIT, "wide", mouth, "desk")[2]
    assert (over[: len(toon_cast._teeth(toon_cast.RABBIT))] == toon_cast._teeth(toon_cast.RABBIT)) == teeth


# -- the three join the cast -------------------------------------------------------------------------------------------
def test_the_three_join_the_cast_by_name():
    names = {e["name"]: e for e in registry.catalog(style="toon")}
    for name in NEW:
        look = CRITTERS[name]
        assert look.name == name and getattr(toon_critters, name.upper()) is look
        assert isinstance(look.drawing, toon_critters.Critter)
        assert sketch.DRAWERS[name] is getattr(toon_critters, name)
        assert name in sketch.CHARACTERS and name in sketch.LIP_SYNCED and name in sketch.TOON_CAST.characters
        assert names[f"toon-{name}"]["kind"] == "character"
    assert all(look.drawing is None for look in toon_cast.LOOKS.values())  # the older cast draws from its fields


def covering_sample() -> list[tuple[str, str, str]]:
    """Every eyes kind with every mouth kind, the arms turning through ARMS so each meets every eyes and mouth."""
    return [
        (eyes, mouth, toon.ARMS[(e + m) % len(toon.ARMS)])
        for e, eyes in enumerate(toon.EYES)
        for m, mouth in enumerate(toon.MOUTHS)
    ]


SAMPLE = covering_sample()


def test_the_sample_covers_every_pair_of_kinds():
    assert {(e, m) for e, m, _ in SAMPLE} == {(e, m) for e in toon.EYES for m in toon.MOUTHS}
    assert {(e, a) for e, _, a in SAMPLE} == {(e, a) for e in toon.EYES for a in toon.ARMS}
    assert {(m, a) for _, m, a in SAMPLE} == {(m, a) for m in toon.MOUTHS for a in toon.ARMS}


def _crown(shape) -> tuple[float, float]:
    """The topmost on-curve point of a brush shape."""
    return min(zip(shape[0::6], shape[1::6], strict=False), key=lambda p: p[1])


@pytest.mark.parametrize("name", NEW)
def test_every_expression_is_drawn_inside_the_character_s_corner(name):
    look = CRITTERS[name]
    for eyes, mouth, arms in SAMPLE:
        for frame in (0, 1) if arms == "type" else (0,):
            layers = toon_cast.figure_shapes(look, eyes, mouth, arms, frame)
            assert layers and all(len(s) >= 8 and (len(s) - 2) % 6 == 0 for s, _ in layers)
            boxes = [brush.bounds(s) for s, _ in layers]
            where = f"{name} {eyes}/{mouth}/{arms}/{frame}"
            assert min(b[0] for b in boxes) > -40 and max(b[2] for b in boxes) < 440, where
            assert min(b[1] for b in boxes) > 360 and max(b[3] for b in boxes) < 860, where
            colours = [c for _, c in layers]
            assert colours[0] == "ink" and look.coat in colours and look.drawing.shade in colours, where
            rest = toon_cast.figure_shapes(look, eyes, mouth, "desk")
            if arms in ("face", "face2"):  # the paws over the mouth come last
                assert colours[-1] in ("ink", look.paw or look.coat), where
            if arms == "sigh":
                drop = brush.bounds(layers[0][0])[1] - brush.bounds(rest[0][0])[1]
                assert drop == pytest.approx(toon_cast.SIGH_DROP, abs=0.01), where
            if arms == "lean":  # clockwise about the seat: the crown swings toward the laptop, the base stays put
                assert _crown(layers[0][0])[0] > _crown(rest[0][0])[0] + 30.0, where
    assert toon_cast.figure_shapes(look, "wide", "scream", "face") == toon_cast.figure_shapes(
        look, "wide", "scream", "face"
    )  # the same drawing every build


@pytest.mark.parametrize("name", NEW)
def test_the_two_typing_frames_differ_only_in_the_arms(name):
    look = CRITTERS[name]
    a = toon_cast.figure_shapes(look, "half", "flat", "type", 0)
    b = toon_cast.figure_shapes(look, "half", "flat", "type", 1)
    assert len(a) == len(b) and a != b
    found = len(toon_cast._foundation(look))
    assert a[:found] == b[:found] and a[-1] == b[-1]  # the body and the mouth hold; the arms move


@pytest.mark.parametrize("name", NEW)
def test_a_new_character_types_speaks_and_blinks(name):
    look = CRITTERS[name]
    assert look.blink > 0
    cv = canvas(8.0)
    poses = toon.parse_poses(
        [
            {"start": 0.0, "eyes": "wide", "mouth": "flat", "arms": "desk"},
            {"start": 4.0, "eyes": "half", "mouth": "smirk", "arms": "type"},
        ]
    )
    track = [(0.3, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed")]
    getattr(toon_critters, name)(cv, cv.comp, poses, 8.0, taps=(4.5, 4.7), mouths=track)
    first, second = runs_of(cv)
    lips, shut = first.findall("group")
    assert len(lips.findall("group")) == 4  # closed, open, round, teeth
    assert shut.find("animate").get("property") == "opacity"
    assert len(second.findall("group")) == 3  # the two typing frames and the blink lids
    for viseme in toon_cast.VISEMES[1:]:
        assert toon_cast._viseme(look, viseme)
    with pytest.raises(ToonDataError, match="no viseme"):
        toon_cast._viseme(look, "shout")


@pytest.mark.parametrize("name", NEW)
def test_the_new_three_wear_glasses_a_sweat_drop_and_a_flush(name):
    look = CRITTERS[name]
    bare = toon_cast.figure_layers(look, "wide", "flat", "desk")
    worn = toon_cast.figure_layers(look, "wide", "flat", "desk", wear=toon.WEAR)
    assert len(worn[0]) > len(bare[0]) and len(worn[2]) > len(bare[2])
    face = toon_wear.face_of(look)
    assert face.eyes == look.eyes and face.mouth == look.mouth
    assert toon_wear.FLUSH in [c for _, c in worn[0]] and toon_wear.SWEAT in [c for _, c in worn[2]]


@pytest.mark.parametrize("name", NEW)
def test_a_headset_fits_the_new_heads(name):
    look = CRITTERS[name]
    band = brush.bounds(toon_cast.headset(look)[0][0])
    top = min(y for _, y in look.silhouette)
    assert top - 16 < band[1] < top


@pytest.mark.parametrize("name", NEW)
def test_what_the_new_three_wear_turns_with_their_tilted_heads(name):
    look = CRITTERS[name]
    face = toon_wear.face_of(look)
    assert face.tilt == look.drawing.tilt != 0.0
    layers = toon_wear.wear_layers(face, ("glasses",))[1]
    for k, eye in enumerate(look.eyes):  # the lenses stay on the eyes
        x0, y0, x1, y1 = brush.bounds(layers[k][0])
        assert math.dist(((x0 + x1) / 2, (y0 + y1) / 2), eye) < 1.5
    (lx, ly), (rx, ry) = look.eyes
    centre = (lx + rx) / 2, (ly + ry) / 2
    temples = [brush.bounds(brush.rotate(layers[k][0], *centre, -face.tilt)) for k in (3, 4)]
    assert abs(temples[0][1] - temples[1][1]) < 4.0  # the arms run level on the head, so they turn with it
    assert abs(brush.bounds(layers[3][0])[1] - brush.bounds(layers[4][0])[1]) > 4.0


def test_a_sketch_plays_the_new_three_by_name_with_their_signatures():
    lines = (Line("a", "Monday again."), Line("b", "WHAT."), Line("c", "Free snacks!"))

    def speaker(name, who):
        return Speaker(name, Voice(role=name, id=f"id-{name}", name=name), VoiceSettings(0.5, 0.75, 0.2), who)

    beats = (
        Beat(0.0, "sloth", lines[0].text, "sleepy", "yawn", "sigh", 0, 0),
        Beat(2.0, "goat", lines[1].text, "shock", "scream", "desk", 1, 0),
        Beat(4.0, "hamster", lines[2].text, "closed", "puff", "face2", 2, 0, wear=("flush",)),
    )
    sk = Sketch(
        "critters",
        "Critters",
        (speaker("a", "sloth"), speaker("b", "goat"), speaker("c", "hamster")),
        lines,
        beats,
        6.0,
    )
    sketch.check(sk)
    cv = canvas(6.0)
    groups = sketch.draw_cast(cv, cv.comp, sk.beats, sk.end, mouths={"goat": [(2.2, "open"), (2.5, "closed")]})
    assert len(groups) == 3
    assert [(g.get("start"), g.get("end")) for g in runs_of(cv)] == [("0", "2"), ("2", "4"), ("4", "6")]


# -- told apart --------------------------------------------------------------------------------------------------------
def head(name: str) -> frozenset[tuple[int, int]]:
    """The head and ears at thumbnail size: ADR 0041's measure for the older cast, every foundation shape (the
    contours, horns and ears; inner marks sit inside them) for a critter."""
    if name in CRITTERS:
        return thumbnail([s for s, _ in toon_cast._foundation(CRITTERS[name])])
    return silhouette_rest(name)


@pytest.mark.parametrize("name", NEW)
def test_each_new_head_reads_apart_from_every_other_character_at_thumbnail_size(name):
    older = ("cat", "dog", "frog", "bear", "rabbit")
    floor = min(apart(head(a), head(b)) for i, a in enumerate(older) for b in older[i + 1 :])
    assert floor > 0.2
    mine = head(name)
    for other in ("cat", *toon_cast.LOOKS, *NEW):
        if other != name:
            assert apart(mine, head(other)) >= floor, f"{name} reads too close to {other}"


@pytest.mark.parametrize("name", NEW)
def test_each_new_coat_is_far_from_every_other_coat(name):
    coats = {n: look.coat for n, look in BRUSH.items()}
    coats["cat"] = PEACH.shade
    for other, colour in coats.items():
        if other != name:
            assert math.dist(lab(coats[name]), lab(colour)) > 20, f"{name}'s coat is too near {other}'s"


def test_the_builds_differ_droopy_wiry_and_round():
    sloth, goat, hamster = (CRITTERS[n] for n in NEW)

    def span(look, top, bottom):
        xs = [x for x, y in look.silhouette if top <= y <= bottom]
        return max(xs) - min(xs)

    crown = {n: min(y for _, y in CRITTERS[n].silhouette) for n in NEW}
    assert span(goat, 0.0, goat.mouth[1]) < span(hamster, 0.0, hamster.mouth[1]) - 60  # a narrow, long face
    assert goat.mouth[1] - goat.eyes[0][1] > max(n.mouth[1] - n.eyes[0][1] for n in (sloth, hamster)) + 25
    assert sloth.limb > hamster.limb and goat.limb < sloth.limb  # long sloth arms, wiry goat, tiny hamster paws
    assert crown["hamster"] > crown["sloth"]  # the hamster is a small round ball


# -- polish ------------------------------------------------------------------------------------------------------------
def test_a_pressed_rim_is_heavier_at_the_bottom_and_back_than_at_the_top():
    ring = [(100 + 50 * math.cos(2 * math.pi * k / 16), 100 + 50 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    rim = toon_critters.pressed(ring, 6.0)
    x0, y0, x1, y1 = brush.bounds(rim)
    below, above = y1 - 150, 50 - y0
    assert below > 2 * above > 0
    assert x1 - 150 > 50 - x0  # the back (right, away from the light) is heavier than the front
    assert toon_critters.pressed(ring, 6.0) == rim
    with pytest.raises(brush.BrushError):
        toon_critters.pressed(ring[:2], 6.0)
    with pytest.raises(brush.BrushError):
        toon_critters.pressed(ring, 0.0)


@pytest.mark.parametrize("name", NEW)
def test_the_new_three_are_drawn_with_polish(name):
    look = CRITTERS[name]
    critter = look.drawing
    (lx, ly), (rx, ry) = look.eyes
    assert abs(math.degrees(math.atan2(ry - ly, rx - lx))) >= 3  # the head is tilted
    assert len(look.silhouette) >= 40  # a dense contour
    mirrored = thumbnail([brush.flip(brush.outline(look.silhouette), toon_cast.CENTRE)])
    assert apart(thumbnail([brush.outline(look.silhouette)]), mirrored) > 0.04  # and not a mirrored one
    base = toon_cast._foundation(look)
    colours = [c for _, c in base]
    assert critter.shade in colours and critter.shade != look.coat
    assert len(critter.details()) >= 8  # open, tapered inner strokes: fur, creases, the cheek line
    assert all(layer in base for layer in critter.details())


@pytest.mark.parametrize(("name", "kind"), [("sloth", "yawn"), ("goat", "scream"), ("hamster", "puff")])
def test_each_signature_is_its_own_drawing_not_the_shared_one(name, kind):
    look = CRITTERS[name]
    own = toon_cast._mouth(look, kind)
    shared = toon_critters.shared_mouth(look, kind)
    assert own != shared and len(own) >= len(shared)
    assert height(own) >= height(shared) or width(own) >= width(shared)


def test_the_sloth_s_eyes_sit_in_dark_stripes_running_down_and_out():
    look = toon_critters.SLOTH
    stripes = [brush.bounds(s) for s, c in toon_cast._foundation(look) if c == toon_critters.SLOTH_STRIPE]
    assert len(stripes) == 2
    for (ex, ey), (x0, y0, x1, y1), outward in zip(look.eyes, sorted(stripes), (-1, 1), strict=True):
        assert x0 < ex < x1 and y0 < ey < y1
        assert y1 > ey + 2.5 * look.eye_r  # running down
        assert x0 < ex - 1.5 * look.eye_r if outward < 0 else x1 > ex + 1.5 * look.eye_r  # and out


def test_the_goat_has_bar_pupils_horns_and_a_beard():
    look = toon_critters.GOAT
    r = look.eye_r
    pupils = [brush.bounds(s) for s, c in toon_cast._eye(look, look.eyes[0], "wide", 1.0) if c == "ink"]
    bars = [b for b in pupils if b[2] - b[0] < 2 * r and b[2] - b[0] > 1.5 * (b[3] - b[1])]
    assert bars  # a pupil wider than tall
    base = toon_cast._foundation(look)
    colours = [c for _, c in base]
    assert colours.count(toon_critters.GOAT_HORN) == 2
    horns = [brush.bounds(s) for s, c in base if c == toon_critters.GOAT_HORN]
    assert all(b[1] < min(y for _, y in look.silhouette) - 30 for b in horns)  # rising over the crown
    beard = [brush.bounds(s) for s, c in base if c == look.light]
    assert max(b[3] for b in beard) > look.mouth[1] + 40  # hanging below the chin


def test_the_hamster_s_puff_swells_its_cheeks_past_its_head():
    look = toon_critters.HAMSTER
    puff = toon_cast._mouth(look, "puff")
    xs = [x for x, y in look.silhouette if look.eyes[0][1] < y < look.mouth[1] + 30]
    assert width(puff) > (max(xs) - min(xs)) * 0.9


@pytest.mark.parametrize("name", NEW)
def test_a_pose_draws_a_reasonable_number_of_shapes(name):
    look = CRITTERS[name]
    count = len(toon_cast.figure_shapes(look, "wide", "flat", "desk"))
    assert 50 <= count <= 90


# -- the shoulders: one smooth body with the arms inside it (ADR 0049) -------------------------------------------------
def _body_rim(look):
    inks = [s for s, c in toon_cast._foundation(look) if c == "ink"]
    return max(
        inks, key=lambda s: (brush.bounds(s)[2] - brush.bounds(s)[0]) * (brush.bounds(s)[3] - brush.bounds(s)[1])
    )


@pytest.mark.parametrize("name", NEW)
def test_the_arms_sit_inside_the_body_with_nothing_above_or_outside_the_shoulders(name):
    look = CRITTERS[name]
    torso = look.drawing.torso
    body = brush.outline(look.silhouette, steps=3)
    level = max(y for _, y in torso.shoulders)
    (left, _), (right, _) = torso.shoulders
    for arms in toon.ARMS:
        for frame in (0, 1) if arms == "type" else (0,):
            under, over = toon_cast._arms(look, arms, frame)
            assert under + over, arms
            for shape, _ in under + over:
                for x, y in points(shape):
                    in_front = bool(over) and left < x < right  # a paw raised to the mouth crosses the neck
                    assert inside(body, x, y) or y > level or in_front, f"{name} {arms}/{frame} at {(x, y)}"


@pytest.mark.parametrize("name", NEW)
def test_the_body_runs_from_neck_to_flank_with_no_corner_sharper_than_a_gentle_curve(name):
    look = CRITTERS[name]
    torso = look.drawing.torso
    top = max(torso.head[0][1], torso.head[-1][1]) + 2.0
    for shape in (_body_rim(look), brush.outline(look.silhouette, steps=3)):  # the ink band and the coat
        out, inward = sharpest(shape, top, torso.base - 15.0)
        assert out <= 10.0 and inward <= 15.0, (name, out, inward)  # degrees per 8 px: radii of 46 and 31 px
        for run in bends(shape, top, torso.base - 15.0).values():  # no lumps: in at the neck, out at the shoulder
            signs = [b > 0 for b in run if abs(b) > 3.5]  # the pressed ink breathes a little under that
            assert sum(1 for a, b in zip(signs, signs[1:], strict=False) if a != b) <= 1, name


@pytest.mark.parametrize("look", toon_critters.CRITTERS.values(), ids=toon_critters.CRITTERS)
def test_the_two_shoulders_sit_at_about_the_same_height(look):
    (_, left), (_, right) = look.drawing.torso.shoulders
    assert abs(left - right) <= 10.0  # a head tilted about the neck must not drop one shoulder and lift the other


@pytest.mark.parametrize("name", NEW)
def test_typing_still_reaches_the_laptop_and_resting_paws_the_desk(name):
    look = CRITTERS[name]
    for frame, lift in ((0, 0.0), (1, 9.0)):
        under, _ = toon_cast._arms(look, "type", frame)
        boxes = [brush.bounds(s) for s, _ in under]
        for px, py in ((376.0, 789.0 - lift), (404.0, 764.0 + lift)):
            assert any(b[0] <= px <= b[2] and b[1] <= py <= b[3] for b in boxes), (name, frame, px, py)
    under, _ = toon_cast._arms(look, "desk", 0)
    assert max(brush.bounds(s)[3] for s, _ in under) >= 794.0


APPROVED = {  # scene digests of the drawing the operator approved on 2026-10-30, ADR 0049: wedge arms, band shade
    "sloth": "6714deb01199165da68327abceece793f2e9de6158d25d9af121362c3648ffc4",
    "goat": "9536f085a35b64e23fae091d41af7abbf51df69268674bcc89e1db39bf565c32",
    "hamster": "5309b9315bb91993dde800d61b3c7a1a113818bd2a0186ba1431b69b73f3461a",
}


@pytest.mark.parametrize("name", sorted(APPROVED))
def test_the_three_are_drawn_as_the_operator_approved_them(name):
    poses = [
        Pose(0.0, "sleepy", "flat", "desk"),
        Pose(1.0, "half", "smirk", "type"),
        Pose(2.0, "wide", "yawn", "sigh"),
        Pose(3.0, "shock", "scream", "lean"),
        Pose(4.0, "wince", "puff", "face"),
        Pose(5.0, "hearts", "kiss", "face2"),
    ]
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=6.0, background=PEACH.background)
    cv = Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))
    toon_cast.figure(cv, cv.comp, toon_critters.CRITTERS[name], poses, 6.0, (1.2, 1.4, 1.9))
    assert hashlib.sha256(scene.to_bytes(layout="pretty")).hexdigest() == APPROVED[name]


def test_drifted_is_a_wobble_rounded_for_the_control_points_and_refuses_the_wrong_weights():
    ring = [(100 + 50 * math.cos(2 * math.pi * k / 16), 100 + 50 * math.sin(2 * math.pi * k / 16)) for k in range(16)]
    assert toon_critters.drifted(ring, 1.3, 1.0) == toon_critters.drifted(ring, 1.3, 1.0, (1.0,) * 16)
    assert toon_critters.drifted(ring, 1.3, 1.0, (0.0,) * 16) == tuple((round(x, 2), round(y, 2)) for x, y in ring)
    with pytest.raises(brush.BrushError):
        toon_critters.drifted(ring, 1.3, 1.0, (1.0,) * 15)
    with pytest.raises(brush.BrushError):
        toon_critters.drifted(ring, 1.3, 1.0, (1.0,) * 15 + (-1.0,))

"""Version 2 of the older brush cast (ADR 0052): the dog, the frog, the bear, the rabbit, the raccoon and the hedgehog
drawn again with a smooth torso and the critters' polish, each kept recognisably itself, each approved by the operator:
a new reel draws them by default, and a pin at version 1 stays where it is."""

import math

import pytest
from sr_core.scene import Scene

from srstudio import (
    PEACH,
    Canvas,
    brush,
    flat_counter,
    head_motion,
    parts,
    registry,
    sketch,
    specimens,
    toon,
    toon_cast,
    toon_critters,
    toon_head,
    toon_redrawn,
    toon_rigs,
)
from srstudio.toon import ToonDataError
from srstudio.toon_torso import depth_in
from support.spring_curve import sample
from support.toon_contour import bends, inside, points, sharpest
from support.toon_thumbnail import _inside, _polygon, apart, silhouette_rest, thumbnail

specimens.load_parts()
REDRAWN = toon_redrawn.REDRAWN
NAMES = ("dog", "frog", "bear", "rabbit", "raccoon", "hedgehog")
EVERY_EYES = toon.EYES
EVERY_MOUTHS = toon.MOUTHS


def canvas(duration: float) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=duration, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


# -- proposed, never drawn by default ----------------------------------------------------------------------------------
def test_the_six_are_exactly_the_older_cast_but_the_fox():
    assert tuple(REDRAWN) == NAMES
    assert set(NAMES) == set(toon_cast.LOOKS) - {"fox"}


@pytest.mark.parametrize("name", NAMES)
def test_each_is_version_2_approved_in_the_operator_s_words_with_its_proof(name):
    part = sketch.part_of(name)
    character = parts.get(part)
    assert [v.number for v in character.versions] == [1, 2]
    v = character.version(2)
    assert v.status == "approved"
    assert v.approval == parts.Approval("2026-10-30", "all the old-cast approved on v2")
    assert v.proof == "generated/character-proofs/older-cast/index.html"
    assert character.version(1).status == "approved"


@pytest.mark.parametrize("name", NAMES)
def test_a_new_reel_draws_version_2_and_a_pin_keeps_version_1(name):
    part = sketch.part_of(name)
    assert parts.latest(part).number == 2
    assert parts.resolved(part) == 2
    assert parts.resolved(part, {part: 1}) == 1
    assert sketch.drawer(name, {}) is getattr(toon_redrawn, name)
    assert sketch.drawer(name, {part: 2}) is getattr(toon_redrawn, name)


@pytest.mark.parametrize("name", NAMES)
def test_version_1_still_draws_the_old_look(name):
    part = sketch.part_of(name)
    assert sketch.drawer(name, {part: 1}) is registry.get("character", part).builder
    assert toon_cast.LOOKS[name].drawing is None


@pytest.mark.parametrize("name", NAMES)
def test_the_version_is_registered_as_a_part_of_its_own(name):
    part = sketch.part_of(name)
    entry = parts.drawing(part, 2)
    assert entry.name == f"{part}@2" and entry.builder is getattr(toon_redrawn, name)


@pytest.mark.parametrize("name", NAMES)
def test_its_recorded_digest_is_what_it_draws(name):
    part = sketch.part_of(name)
    assert parts.get(part).version(2).drawing == specimens.digest(part, 2)
    assert specimens.SPECIMENS[f"{part}@2"] is specimens.SPECIMENS["toon-sloth"]  # the newer kinds are part of it


# -- each stays itself -------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
def test_it_keeps_its_colours_its_build_and_the_face_it_had(name):
    old, new = toon_cast.LOOKS[name], REDRAWN[name]
    assert (new.coat, new.dark, new.light) == (old.coat, old.dark, old.light)
    assert (new.eye_r, new.mouth_w, new.lid, new.brows, new.teeth) == (
        old.eye_r,
        old.mouth_w,
        old.lid,
        old.brows,
        old.teeth,
    )
    for (ox, oy), (nx, ny) in zip(old.eyes, new.eyes, strict=True):
        assert math.dist((ox, oy), (nx, ny)) < 30.0  # the eyes sit where they did, turned with the head
    assert math.dist(old.mouth, new.mouth) < 22.0


def test_each_head_reads_apart_from_every_other_at_thumbnail_size():
    def head(name):
        return thumbnail([s for s, _ in toon_cast._foundation(REDRAWN[name])])

    for name in NAMES:
        for other in NAMES:
            if other != name:
                assert apart(head(name), head(other)) > 0.2, (name, other)
        assert apart(head(name), silhouette_rest("cat")) > 0.2, name


def test_what_makes_each_one_stays():
    dog, frog, bear, rabbit, raccoon, hedgehog = (REDRAWN[n] for n in NAMES)

    def top(look):
        return min(brush.bounds(s)[1] for s, _ in toon_cast._foundation(look))

    assert top(rabbit) < top(dog) - 50.0  # the tall ears
    assert frog.eyes[0][1] < dog.eyes[0][1] - 50.0  # the frog's eyes sit on top of its head
    assert frog.mouth_w > 2 * dog.mouth_w  # and it has the wide mouth
    assert raccoon.lid == toon_cast.RACCOON_MASK  # the bandit's mask
    assert raccoon.drawing.face.paw == toon_cast.RACCOON.paw  # and the gloves
    colours = [c for _, c in toon_cast._foundation(hedgehog)]
    assert colours.index(hedgehog.dark) < colours.index(hedgehog.coat)  # the spines behind the coat
    assert top(hedgehog) < min(y for _, y in hedgehog.silhouette) - 60.0  # and well over the crown
    assert not toon_redrawn.BEAR_CRITTER.face.teeth and rabbit.teeth


@pytest.mark.parametrize("name", NAMES)
def test_every_one_blinks(name):
    assert REDRAWN[name].blink > 0  # the dog and the frog never did


# -- the polish --------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
def test_it_is_drawn_with_polish(name):
    look = REDRAWN[name]
    critter = look.drawing
    (lx, ly), (rx, ry) = look.eyes
    assert abs(math.degrees(math.atan2(ry - ly, rx - lx))) >= 3  # the head is tilted
    assert len(look.silhouette) >= 40  # a dense contour
    head = critter.torso.head
    assert any(math.hypot(ax + bx - 2 * toon_cast.CENTRE, ay - by) > 3 for (ax, ay), (bx, by) in
               zip(head, head[::-1], strict=True))  # fmt: skip # placed by hand, not mirrored
    assert len(critter.details()) >= 8  # open inner strokes
    assert critter.shade in [c for _, c in toon_cast._foundation(look)]  # one shade tone
    assert critter.shade not in (look.coat, look.dark, look.light)


@pytest.mark.parametrize("name", NAMES)
def test_its_own_pupils_and_paws(name):
    critter = REDRAWN[name].drawing
    assert critter.pupil is not toon_critters._round_pupil
    plain = toon_critters._pressed_paw(critter.face, (100.0, 100.0), 20.0, 18.0, critter.face.coat, 1.0)
    assert len(critter.paw(critter.face, (100.0, 100.0), (1.0, 0.0), True)) > len(plain)


@pytest.mark.parametrize("kind", ["half", "down", "side", "narrow", "roll", "sleepy"])
def test_the_frog_s_lids_stay_on_its_eye_domes(kind):
    look = REDRAWN["frog"]
    for centre, inner in zip(look.eyes, (1.0, -1.0), strict=True):
        lids = [s for s, c in toon_cast._eye(look, centre, kind, inner) if c == look.coat]
        assert lids
        reach = look.eye_r + toon_cast.INK + 2.0
        assert all(math.dist(centre, p) <= reach for s in lids for p in points(s)), kind


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("kind", ["half", "down", "side", "narrow", "roll", "sleepy", "blink"])
def test_a_lid_stays_inside_the_outline(name, kind):
    """A lid is painted in the coat, so past the edge of the fill it would erase the ink of the head."""
    look = REDRAWN[name]
    critter = look.drawing
    lid = look.lid or look.coat
    fills = [_polygon(s) for s, c in critter.foundation(look) if c == look.coat]
    fill = max(fills, key=lambda p: max(y for _, y in p) - min(y for _, y in p))  # the body, not an ear
    if kind == "blink":
        layers = critter.lids(look)
    else:
        layers = [
            layer
            for centre, inner in zip(look.eyes, (1.0, -1.0), strict=True)
            for layer in critter.eye(look, centre, kind, inner)
        ]
    lids = [s for s, c in layers if c == lid]
    assert lids
    assert all(_inside(fill, *p) for s in lids for p in points(s)), (name, kind)


# -- the whole contract ------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("arms", toon.ARMS)
def test_every_kind_is_drawn_inside_the_character_s_corner(name, arms):
    look = REDRAWN[name]
    for k, eyes in enumerate(EVERY_EYES):
        mouth = EVERY_MOUTHS[k % len(EVERY_MOUTHS)]
        for frame in (0, 1) if arms == "type" else (0,):
            layers = toon_cast.figure_shapes(look, eyes, mouth, arms, frame)
            assert layers and all(len(s) >= 8 and (len(s) - 2) % 6 == 0 for s, _ in layers)
            boxes = [brush.bounds(s) for s, _ in layers]
            where = f"{name} {eyes}/{mouth}/{arms}/{frame}"
            assert min(b[0] for b in boxes) > -40 and max(b[2] for b in boxes) < 440, where
            assert min(b[1] for b in boxes) > 340 and max(b[3] for b in boxes) < 860, where
            assert toon_cast.figure_shapes(look, eyes, mouth, arms, frame) == layers  # the same every build


@pytest.mark.parametrize("name", NAMES)
@pytest.mark.parametrize("kind", EVERY_MOUTHS)
def test_every_mouth_and_viseme_draws(name, kind):
    look = REDRAWN[name]
    assert toon_cast._mouth(look, kind) or kind == "none"
    for viseme in toon_cast.VISEMES[1:]:
        assert toon_cast._viseme(look, viseme)
    with pytest.raises(ToonDataError, match="no viseme"):
        toon_cast._viseme(look, "shout")


@pytest.mark.parametrize("name", NAMES)
def test_it_types_speaks_and_blinks_on_a_canvas(name):
    cv = canvas(8.0)
    poses = [toon.Pose(0.0, "wide", "flat", "desk"), toon.Pose(4.0, "half", "smirk", "type")]
    track = [(0.3, "open"), (0.6, "round"), (0.9, "teeth"), (1.2, "closed")]
    getattr(toon_redrawn, name)(cv, cv.comp, poses, 8.0, taps=(4.5, 4.7), mouths=track)
    root = cv.scene.to_bytes(layout="pretty").decode()
    assert 'property="opacity"' in root


@pytest.mark.parametrize("name", NAMES)
def test_what_it_wears_turns_with_its_tilted_head(name):
    look = REDRAWN[name]
    bare = toon_cast.figure_layers(look, "wide", "flat", "desk")
    worn = toon_cast.figure_layers(look, "wide", "flat", "desk", wear=("glasses", "sweat", "flush"))
    assert sum(map(len, worn)) > sum(map(len, bare))
    assert toon_cast.headset(look)


# -- one smooth body ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", NAMES)
def test_the_body_runs_from_neck_to_flank_with_no_corner_sharper_than_a_gentle_curve(name):
    look = REDRAWN[name]
    torso = look.drawing.torso
    top = max(torso.head[0][1], torso.head[-1][1]) + 2.0
    rim = next(s for s, c in toon_cast._foundation(look) if c == "ink" and brush.bounds(s)[3] > torso.base)
    for shape in (rim, brush.outline(look.silhouette, steps=3)):  # the ink band and the coat
        out, inward = sharpest(shape, top, torso.base - 15.0)
        assert out <= 10.0 and inward <= 15.0, (name, out, inward)
        for run in bends(shape, top, torso.base - 15.0).values():  # no lumps: in at the neck, out at the shoulder
            signs = [b > 0 for b in run if abs(b) > 3.5]
            assert sum(1 for a, b in zip(signs, signs[1:], strict=False) if a != b) <= 1, name


@pytest.mark.parametrize("name", NAMES)
def test_the_two_shoulders_sit_at_about_the_same_height(name):
    (_, left), (_, right) = REDRAWN[name].drawing.torso.shoulders
    assert abs(left - right) <= 10.0


@pytest.mark.parametrize("name", NAMES)
def test_the_arms_sit_inside_the_body_with_nothing_above_or_outside_the_shoulders(name):
    look = REDRAWN[name]
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


@pytest.mark.parametrize("name", NAMES)
def test_typing_still_reaches_the_laptop_and_resting_paws_the_desk(name):
    look = REDRAWN[name]
    for frame, lift in ((0, 0.0), (1, 9.0)):
        under, _ = toon_cast._arms(look, "type", frame)
        boxes = [brush.bounds(s) for s, _ in under]
        for px, py in ((376.0, 789.0 - lift), (404.0, 764.0 + lift)):
            assert any(b[0] <= px <= b[2] and b[1] <= py <= b[3] for b in boxes), (name, frame, px, py)
    under, _ = toon_cast._arms(look, "desk", 0)
    assert max(brush.bounds(s)[3] for s, _ in under) >= 794.0


# -- the head rigs (ADR 0059) ------------------------------------------------------------------------------------------
def rig_of(name: str) -> toon_head.HeadRig:
    return toon_rigs.RIGS[f"toon-{name}@2"]


def shut(rig: toon_head.HeadRig, name: str, x: float) -> float:
    """The reference height of the chin at ``x``: the lowest the head's contour reaches there."""
    edge = [p for p in brush.spline(rig.head, True, 6) if abs(p[0] - x) < 6.0]
    assert edge, (name, x)
    return max(y for _, y in edge)


@pytest.mark.parametrize("name", NAMES)
def test_each_has_a_rig_at_version_2_and_none_at_version_1(name):
    assert f"toon-{name}@2" in toon_rigs.RIGS
    assert f"toon-{name}" not in toon_rigs.RIGS


@pytest.mark.parametrize("name", NAMES)
def test_a_rig_stays_proposed_until_the_operator_judges_the_clips(name):
    held = parts.get(f"toon-{name}").version(2).rig
    assert held is not None and held.status == "proposed" and held.approval is None
    assert held.proof == "generated/character-proofs/older-rigs/index.html"


@pytest.mark.parametrize("name", NAMES)
def test_the_record_holds_the_drawing_the_proof_shows(name):
    assert parts.get(f"toon-{name}").version(2).rig.drawing == specimens.rig_digest(f"toon-{name}", 2)


@pytest.mark.parametrize("name", NAMES)
def test_a_proposed_rig_moves_no_reel(name):
    with pytest.raises(ToonDataError, match=f"toon-{name} version 2's head rig is not approved"):
        toon_rigs.rig_of(f"toon-{name}")


@pytest.mark.parametrize("name", NAMES)
def test_version_1_is_still_refused_by_name(name):
    with pytest.raises(ToonDataError, match=f"toon-{name} version 1 has no head rig"):
        toon_rigs.rig_of(f"toon-{name}", {f"toon-{name}": 1})


@pytest.mark.parametrize("name", NAMES)
def test_the_head_turns_about_the_neck_the_drawing_uses_and_keeps_its_tilt(name):
    critter, rig = REDRAWN[name].drawing, rig_of(name)
    assert (rig.neck, rig.tilt, rig.head[: len(critter.torso.head)]) == (critter.neck, critter.tilt, critter.torso.head)
    assert rig.head_over


@pytest.mark.parametrize("name", NAMES)
def test_no_line_crosses_the_neck_the_approved_drawing_runs_on_through_it(name):
    """Version 2 has no chin line: the head and the body read as one contour, and the rig has to keep that at rest."""
    rig = rig_of(name)
    for x in (150.0, 185.0, 220.0):
        chin = shut(rig, name, x)
        for y in (chin - 6.0, chin - 3.0, chin, chin + 3.0):
            assert _top(rig.skull(), x, y) != "ink", (name, x, y)


def _top(layers, x: float, y: float) -> str | None:
    """The colour on top at a reference point: the last layer whose polygon holds it."""
    for shape, colour in reversed(list(layers)):
        if _inside(_polygon(shape), x, y):
            return colour
    return None


@pytest.mark.parametrize("name", NAMES)
def test_at_rest_what_the_flat_drawing_shows_under_the_chin_the_rig_shows_too(name):
    """The throat and belly of the drawing run up past the neck: the head over the body must not cut them off."""
    look, rig = REDRAWN[name], rig_of(name)
    flat = list(look.drawing.parts())
    for x in (150.0, 185.0, 220.0):
        y = shut(rig, name, x) - 2.0
        seen = _top([layer for layer, _ in flat], x, y)
        if seen in (look.coat, look.drawing.shade):
            continue
        assert _top([*rig.skull(), *rig.face()], x, y) == seen, (name, x, y)


def _take() -> head_motion.Alignment:
    text = "Everyone knows I rested and nobody asked why"
    spans = ((i * 0.08, (i + 1) * 0.08) for i in range(len(text)))
    return head_motion.Alignment(tuple(text), *zip(*spans, strict=True))


def _slides(rig: toon_head.HeadRig) -> tuple[float, float, float]:
    """How far a loud line slides the face over the skull: across, down and up, in reference pixels."""
    speech = head_motion.Speech(1.0, head_motion.words_of(_take(), 1.0), (-20.0,) * 300)
    nod = head_motion.plan(rig.style, [speech], 8.0).nod
    seen = [sample(nod, k / 100.0) * toon_head.FACE_SLIDE for k in range(800)]
    return head_motion.limit(rig.style, "face_x"), max(seen), min(seen)


@pytest.mark.parametrize("name", NAMES)
def test_the_eyes_stay_on_the_head_however_far_the_face_slides(name):
    """An eye slides over the skull with the face; past the outline it would paint over the ink."""
    rig = rig_of(name)
    across, down, up = _slides(rig)
    reach = rig.look.eye_r + toon_cast.INK + 1.0
    for ex, ey in rig.look.eyes:
        for dx in (-across, across):
            for dy in (up, down):
                for k in range(16):
                    a = 2.0 * math.pi * k / 16
                    edge = (ex + dx + reach * math.cos(a), ey + dy + reach * math.sin(a))
                    assert depth_in(rig.head, edge)[0] >= 0.0, (name, dx, dy, edge)


@pytest.mark.parametrize("name", NAMES)
def test_what_slides_with_the_face_stays_inside_the_head(name):
    rig = rig_of(name)
    across, down, up = _slides(rig)
    for shape, _ in rig.face():
        for x, y in points(shape):
            for dx in (-across, across):
                assert depth_in(rig.head, (x + dx, y + up))[0] >= 0.0, (name, x + dx, y + up)
                assert depth_in(rig.head, (x + dx, y))[0] >= 0.0, (name, x + dx, y)


def test_each_of_the_six_moves_its_own_way():
    dog, frog, bear, rabbit, raccoon, hedgehog = (rig_of(name).style for name in NAMES)
    assert frog.idle_roll == min(s.idle_roll for s in (dog, bear, rabbit, raccoon, hedgehog, frog))  # it sits still
    # and then it jerks
    assert frog.head.frequency == max(s.head.frequency for s in (dog, bear, rabbit, raccoon, hedgehog, frog))
    assert bear.head.frequency == min(s.head.frequency for s in (dog, frog, rabbit, raccoon, hedgehog, bear))  # heavy
    assert bear.nod_px == max(s.nod_px for s in (dog, frog, rabbit, raccoon, hedgehog, bear))
    assert bear.breath_period == max(s.breath_period for s in (dog, frog, rabbit, raccoon, hedgehog, bear))
    assert dog.signature == "~" and dog.head.damping < 0.6  # it bounces
    assert rabbit.glance_every == min(s.glance_every for s in (dog, frog, bear, raccoon, hedgehog, rabbit))  # alert
    assert raccoon.avert > dog.avert and raccoon.glance_turn >= max(s.glance_turn for s in (dog, frog, bear, hedgehog))
    assert hedgehog.signature == "/" and hedgehog.head.anticipation >= 0.12  # it flinches first


@pytest.mark.parametrize("name", NAMES)
def test_a_rig_changes_nothing_of_the_approved_drawing(name):
    assert rig_of(name).look != REDRAWN[name]
    specimens.check(f"toon-{name}", 2)

"""Leo and Sam as two young men inked the News way (ADR 0231): both approved at version 1 by arc4d3 on 4 Nov (Slack
1793837712.509019), each with looks of his own that differ from one another, hands that are one drawing and its
mirror, a face kept alive by breath, blinks and drift, and the screen's light kept to the people by a track matte."""

import re
import subprocess
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, anatomy, anatomy_parts, flat_counter, parts, registry, specimens, styles
from srstudio import inked_friends as f
from srstudio.anatomy import Facing, Side
from srstudio.inked_friends import Beat, FriendsError, Hold, Look, Moves

NAMES = ("friends-leo", "friends-sam")
EACH = pytest.mark.parametrize("name", NAMES)
WHO = pytest.mark.parametrize("who", ("leo", "sam"))


def stage(seconds: float = 8.0) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=seconds, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("f"))


def xml(cv: Canvas) -> str:
    return cv.scene.to_bytes(layout="pretty").decode()


def draw(who: str, beats, end: float = 6.0, moves: Moves = f.STILL, mouths=()) -> str:
    cv = stage(end)
    f.perform(cv, cv.comp, who, beats, end, moves=moves, mouths=mouths)
    return xml(cv)


# -- the record --------------------------------------------------------------------------------------------------------
@EACH
def test_each_is_a_toon_character_approved_at_version_one_on_arc4d3s_words(name):
    specimens.load_parts()
    assert registry.get("character", name).style == "toon"
    record = parts.get(name)
    assert record.kind == "character" and record.style == "toon"
    version = record.version(1)
    assert version.status == "approved" and version.approval is not None
    assert version.approval.date == "2026-11-04" and "1793837712.509019" in version.approval.words
    assert version.proof == "generated/character-proofs/between-friends/index.html"


@EACH
def test_the_digest_on_record_is_the_one_drawn(name):
    assert specimens.digest(name) == parts.get(name).version(1).drawing


@EACH
def test_the_approved_drawing_verifies_against_its_record(name):
    specimens.check(name)  # raises when the drawing is not the approved one on record


def test_the_style_lists_the_module():
    assert "inked_friends" in styles.STYLES["toon"].parts


@EACH
def test_each_declares_a_seated_body_and_a_pair_of_hands_seen_from_the_back(name):
    hands = anatomy_parts.CHARACTERS[name]
    assert hands.kind is anatomy_parts.Kind.PAIRED
    assert hands.drawing == f.GRIP
    assert anatomy_parts.BODIES[name] is anatomy_parts.BODIES["news-vera"]


# -- the faces ---------------------------------------------------------------------------------------------------------
@WHO
def test_no_two_looks_of_one_friend_are_the_same(who):
    looks = [look for name, look in f.FRIENDS[who].looks.items() if name != "shut"]
    assert len(set(looks)) == len(looks)


def test_leo_hurt_lifts_the_inner_brows_and_looks_down_never_a_cross_brow():
    hurt = f.LEO_LOOKS["hurt"]
    assert hurt.inner >= 15 and hurt.outer < 0 and hurt.gaze[1] > 0.3
    assert all(look.inner > -5 for look in f.LEO_LOOKS.values())


def test_leo_neutral_is_at_ease_and_his_smile_reaches_the_eyes():
    level, soft, horror = f.LEO_LOOKS["level"], f.LEO_LOOKS["soft"], f.LEO_LOOKS["horror"]
    assert level.lid >= 0.3 and level.wide == 1.0  # lids part way down: not the startled stare of the first proof
    assert soft.under >= level.under + 0.2  # the lower lids rise into a smile
    assert horror.wide > 1.2 and horror.lid == 0.0


def test_sam_easy_and_deadpan_differ_in_the_lids_and_the_dry_look_lifts_one_brow():
    easy, deadpan, dry = f.SAM_LOOKS["easy"], f.SAM_LOOKS["deadpan"], f.SAM_LOOKS["dry"]
    assert deadpan.lid - easy.lid >= 0.3
    assert dry.near > 0 and dry.gaze[0] > 0
    assert f.SAM_LOOKS["concern"].inner > 0


def test_the_allergies_stare_and_the_horror_do_not_blink():
    assert not f.LEO_LOOKS["set"].blinks and not f.LEO_LOOKS["horror"].blinks
    assert not f.SAM_LOOKS["deadpan"].blinks


@WHO
@pytest.mark.parametrize("mouth", f.MOUTHS)
def test_every_mouth_draws_and_draws_unlike_the_rest(who, mouth):
    rest = draw(who, [Beat(0.0, next(iter(f.FRIENDS[who].looks)), "rest")])
    shown = draw(who, [Beat(0.0, next(iter(f.FRIENDS[who].looks)), mouth)])
    assert (shown == rest) == (mouth in ("rest", "closed"))  # a closed viseme is the mouth at rest


@WHO
def test_every_look_draws_something_of_its_own(who):
    friend = f.FRIENDS[who]
    drawn = {name: draw(who, [Beat(0.0, name)]) for name in friend.looks if name != "shut"}
    assert len(set(drawn.values())) == len(drawn)


# -- the timeline ------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("beats", "end", "match"),
    [
        ([], 4.0, "first beat"),
        ([Beat(0.5, "level")], 4.0, "first beat"),
        ([Beat(0.0, "level"), Beat(2.0, "level"), Beat(1.0, "level")], 4.0, "forward"),
        ([Beat(0.0, "level"), Beat(4.0, "level")], 4.0, "before the end"),
        ([Beat(0.0, "dry")], 4.0, "no look 'dry'"),  # Sam's look, not Leo's
        ([Beat(0.0, "level")], 0.0, "ends after 0"),
        ([Beat(0.0, "level")], float("nan"), "ends after 0"),
    ],
)
def test_a_timeline_leo_cannot_play_is_refused(beats, end, match):
    with pytest.raises(FriendsError, match=match):
        f.perform(stage(), None, "leo", beats, end)


def test_the_phone_is_held_by_the_friend_on_the_left_only():
    with pytest.raises(FriendsError, match="held by the friend on the left"):
        f.perform(stage(), None, "sam", [Beat(0.0, "easy", hands="phone")], 4.0)
    assert "phone" not in {b.hands for b in f.specimen_beats("sam", 8.0)}
    assert "phone" in {b.hands for b in f.specimen_beats("leo", 8.0)}


def test_an_unknown_friend_is_refused():
    with pytest.raises(FriendsError, match="seats"):
        f.perform(stage(), None, "gus", [Beat(0.0, "level")], 4.0)


@pytest.mark.parametrize(
    ("make", "match"),
    [
        (lambda: Beat(-1.0, "level"), "second >= 0"),
        (lambda: Beat(float("inf"), "level"), "second >= 0"),
        (lambda: Beat(0.0, "level", "whistle"), "a mouth is"),
        (lambda: Beat(0.0, "level", hands="wave"), "hands are"),
        (lambda: Beat(0.0, "level", tilt=20.0), "tilts at most"),
        (lambda: Beat(0.0, "level", turn=1.5), "tilts at most"),
        (lambda: Look(0.9), "lid is"),
        (lambda: Look(0.3, gaze=(0.8, 0.0)), "inside the eye"),
        (lambda: Look(0.3, wide=2.0), "eye scale"),
        (lambda: Hold((0.0, 0.0), ("stick",)), "each thumb"),
        (lambda: Hold((0.0, 0.0), ("stick", "trigger")), "each thumb"),
        (lambda: Hold((0.0, 0.0), (None, "stick")), "always holds"),
        (lambda: Moves(nods=((1.0, 40.0),)), "dips 2..16"),
        (lambda: Moves(shrugs=(-1.0,)), "shrug or a swallow"),
        (lambda: Moves(flush=((2.0, 1.0),)), "a blush is a span"),
    ],
)
def test_malformed_parts_of_a_performance_are_refused(make, match):
    with pytest.raises(FriendsError, match=match):
        make()


def test_a_nod_that_starts_inside_another_is_refused():
    with pytest.raises(FriendsError, match="before the one before it is over"):
        cv = stage()
        f.perform(cv, cv.comp, "sam", [Beat(0.0, "easy")], 6.0, moves=Moves(nods=((1.0, 8.0), (1.2, 8.0))))


def test_a_viseme_outside_the_set_is_refused():
    with pytest.raises(FriendsError, match="a viseme is one of"):
        draw("leo", [Beat(0.0, "level", "talk")], mouths=[(0.5, "shout")])


# -- life in a held shot -----------------------------------------------------------------------------------------------
@WHO
def test_blinks_come_every_few_seconds_on_a_fixed_rhythm(who):
    friend = f.FRIENDS[who]
    first = next(iter(friend.looks))
    rows = f._blinks(friend, [Beat(0.0, first)], 30.0)
    shut = [t for t, state in rows if state == "shut"]
    assert len(shut) >= 5 and all(b - a <= 6.0 for a, b in zip(shut, shut[1:], strict=False))
    assert rows == f._blinks(friend, [Beat(0.0, first)], 30.0)


def test_no_blink_falls_inside_a_look_that_holds_its_stare():
    beats = [Beat(0.0, "level"), Beat(2.0, "set"), Beat(12.0, "level")]
    rows = f._blinks(f.LEO_FRIEND, beats, 20.0)
    assert not [t for t, state in rows if state == "shut" and 2.0 <= t < 12.0]
    assert [t for t, state in rows if state == "shut" and t >= 12.0]


@WHO
def test_breath_and_drift_move_a_friend_who_holds_one_beat(who):
    out = draw(who, [Beat(0.0, next(iter(f.FRIENDS[who].looks)))], 10.0)
    assert out.count('property="y"') >= 1 and out.count('property="rotation"') >= 1
    breath = f._breath(10.0, f.FRIENDS[who].seed)
    assert min(v for _, v in breath) <= -f.BREATH_PX + 0.1 and max(v for _, v in breath) == 0.0


def test_a_nod_dips_the_head_and_brings_it_back():
    keys = f._nods(((2.0, 10.0),), ())
    assert keys[0] == (0.0, 0.0) and keys[-1][1] == 0.0
    assert max(v for _, v in keys) == 10.0
    with_nod = draw("sam", [Beat(0.0, "easy")], 6.0, Moves(nods=((2.0, 10.0),)))
    assert with_nod != draw("sam", [Beat(0.0, "easy")], 6.0)


def test_a_shrug_a_swallow_and_a_blush_each_change_the_drawing():
    still = draw("leo", [Beat(0.0, "level")])
    for moves in (Moves(shrugs=(1.0,)), Moves(swallows=(1.0,)), Moves(flush=((1.0, 2.0),))):
        assert draw("leo", [Beat(0.0, "level")], moves=moves) != still


# -- the hands ---------------------------------------------------------------------------------------------------------
def test_the_grip_is_the_left_hand_seen_from_the_back_and_the_right_is_its_mirror():
    left = anatomy.Arm(Side.LEFT).hand(Facing.BACK)
    right = anatomy.Arm(Side.RIGHT).hand(Facing.BACK)
    assert not f.GRIP.mirrored(left) and f.GRIP.mirrored(right)


def test_the_thumbs_point_in_at_their_sticks():
    for thumb, (x, y) in f._TIPS.items():
        assert x < 0 and y < -15, thumb  # the left hand's thumb tip lies right of its grip, over the top edge
    root_x = -50.0
    assert f._TIPS["stick"][0] > root_x and f._TIPS["menu"][0] > f._TIPS["stick"][0]


@WHO
def test_both_grips_are_drawn_once_mirrored_and_once_not(who):
    out = draw(who, [Beat(0.0, next(iter(f.FRIENDS[who].looks)))])
    assert out.count('scaleX="-1"') >= 1


@pytest.mark.parametrize(
    ("who", "hands"), [(w, h) for w in ("leo", "sam") for h in f.HANDS if (w, h) != ("sam", "phone")]
)
def test_every_hold_reaches_and_changes_the_drawing(who, hands):
    look = next(iter(f.FRIENDS[who].looks))
    shown = draw(who, [Beat(0.0, look, hands=hands)])
    assert (shown == draw(who, [Beat(0.0, look)])) == (hands == "pad")


def test_the_phone_hold_lets_go_with_the_right_hand_only():
    assert f.HOLDS["phone"].thumbs == ("rest", None)
    assert all(None not in hold.thumbs for name, hold in f.HOLDS.items() if name != "phone")


# -- the light ---------------------------------------------------------------------------------------------------------
def test_the_screen_lights_only_the_people_through_a_matte_and_multiplies():
    cv = stage(6.0)
    people = cv.group(cv.comp, "people")
    f.perform(cv, people, "leo", [Beat(0.0, "level")], 6.0)
    cues = ((0.0, "on", "blue"), (2.0, "on", "red"), (3.0, "dim", "blue"), (5.0, "on", "green"))
    parsed = f.screen_light(cv, cv.comp, "people", cues, 6.0, ((540.0, 700.0),))
    assert [c.colour for c in parsed] == ["blue", "red", "blue", "green"]
    out = xml(cv)
    assert out.count('matte="people"') == 2
    assert 'blend="multiply"' in out and 'blend="screen"' in out
    assert 'matteVisible="false"' not in out  # the people stay drawn under their light


def test_a_light_with_no_face_or_bad_cues_is_refused():
    cv = stage()
    with pytest.raises(FriendsError, match="at least one face"):
        f.screen_light(cv, cv.comp, "people", ((0.0, "on", "blue"),), 4.0, ())
    with pytest.raises(Exception, match="state"):
        f.screen_light(cv, cv.comp, "people", ((0.0, "blaze", "blue"),), 4.0, ((540.0, 700.0),))


# -- each face reads in every light: a measured floor per figure (rendered) --------------------------------------------
LIT = {"pause": ((0.0, "dim", "blue"),), "play": ((0.0, "on", "blue"),), "red": ((0.0, "on", "red"),)}
AT = {"leo": 278.0, "sam": 802.0}
SCALE, GROUND = 1.5, 1090.0
KEPT = 0.6  # the least share of a face's own drawn contrast (skin against features) it keeps in any light
PARITY = 0.03  # how far below Leo's share Sam's may fall: his face reads as clearly as Leo's


def lightness(rgb: np.ndarray) -> np.ndarray:
    """CIE L* of sRGB pixels: a perceptual scale, so a difference near black counts as the eye counts it."""
    c = rgb / 255.0
    linear = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    y = linear @ np.array([0.2126, 0.7152, 0.0722])
    return np.where(y > 0.008856, 116.0 * np.cbrt(y) - 16.0, 903.3 * y)


def hue(rgb: np.ndarray) -> float:
    """The hue angle in degrees of a patch's mean colour (opponent axes), enough to tell light from colour."""
    r, g, b = (rgb / 255.0).mean(axis=0)
    return float(np.degrees(np.arctan2(np.sqrt(3) * (g - b), 2 * r - g - b)))


def lit_frame(tmp_path: Path, scene_render: Path, state: str | None, keyed: bool = True) -> np.ndarray:
    """Both friends at the proof's places, under one state of the screen (``None``: unlit, as drawn)."""
    cv = stage(1.0)
    people = cv.group(cv.comp, "people")
    for who, look in (("leo", "level"), ("sam", "easy")):
        f.perform(cv, people, who, [Beat(0.0, look)], 1.0, x=AT[who], y=GROUND, scale=SCALE)
    if state is not None:
        faces = [f.face_at(AT[who], GROUND, SCALE) for who in AT]
        keys = [f.key(who, AT[who], GROUND, SCALE) for who in AT] if keyed else ()
        f.screen_light(cv, cv.comp, "people", LIT[state], 1.0, faces, keys)
    doc = tmp_path / f"{state}-{keyed}.scene.xml"
    doc.write_bytes(cv.scene.to_bytes())
    png = tmp_path / f"{state}-{keyed}.png"
    subprocess.run([str(scene_render), "render", str(doc), "-f", "0", "-o", str(png)], check=True, capture_output=True)
    return np.asarray(Image.open(png).convert("RGB"), dtype=float)


def face_of(img: np.ndarray, who: str) -> np.ndarray:
    """The face from the forehead to the top lip, cheek to cheek: mostly skin, with the brows, eyes and nose."""
    x, y = f.face_at(AT[who], GROUND, SCALE)
    box = img[int(y - 60 * SCALE) : int(y + 80 * SCALE), int(x - 95 * SCALE) : int(x + 95 * SCALE)]
    return box.reshape(-1, 3)


def skin(img: np.ndarray, who: str) -> float:
    return float(np.percentile(lightness(face_of(img, who)), 60))


def contrast(img: np.ndarray, who: str) -> float:
    """The face's skin (most of the box) against its darkest features (the brows, lids, lines), in L*."""
    shade = lightness(face_of(img, who))
    return float(np.percentile(shade, 60) - np.percentile(shade, 5))


@pytest.fixture(scope="module")
def lit(tmp_path_factory, scene_render):
    where = tmp_path_factory.mktemp("lit")
    frames = {state: lit_frame(where, scene_render, state) for state in LIT}
    frames["bare-pause"] = lit_frame(where, scene_render, "pause", keyed=False)
    frames["drawn"] = lit_frame(where, scene_render, None)
    return frames


@pytest.mark.parametrize("state", LIT)
@WHO
def test_every_face_keeps_its_features_in_every_light(lit, state, who):
    """Sam went dark against the dark room from the pause to the deadpan: his features sank into his skin. Every face
    keeps a floor share of the contrast its drawing has, in the dimmest light as in the brightest."""
    kept = contrast(lit[state], who) / contrast(lit["drawn"], who)
    assert kept >= KEPT, (state, who, kept)


@pytest.mark.parametrize("state", LIT)
def test_sams_face_reads_as_clearly_as_leos(lit, state):
    share = {who: contrast(lit[state], who) / contrast(lit["drawn"], who) for who in AT}
    assert share["sam"] >= share["leo"] - PARITY, (state, share)


def test_without_his_key_sams_face_sinks_under_the_pause(lit):
    """The floor is the one the unkeyed light broke: it is not met by a face the screen alone lights."""
    assert contrast(lit["bare-pause"], "sam") / contrast(lit["drawn"], "sam") < KEPT


def test_the_key_adds_light_not_colour(lit):
    """Sam keeps his skin: under the key his face is lighter, his hue no further from his own drawn skin than the
    screen alone puts it, his skin under the pause near his skin as drawn, and he stays darker than Leo."""
    bare, keyed, drawn = lit["bare-pause"], lit["pause"], lit["drawn"]
    assert skin(keyed, "sam") > skin(bare, "sam") + 5.0
    own = hue(face_of(drawn, "sam"))
    assert abs(hue(face_of(keyed, "sam")) - own) <= abs(hue(face_of(bare, "sam")) - own)
    assert abs(skin(keyed, "sam") - skin(drawn, "sam")) <= 4.0
    for state in LIT:
        assert skin(lit[state], "sam") <= skin(lit[state], "leo") - 10.0, state


def test_a_key_is_neutral_and_dodges_only_the_people():
    cv = stage(6.0)
    people = cv.group(cv.comp, "people")
    f.perform(cv, people, "sam", [Beat(0.0, "easy")], 6.0)
    key = f.key("sam", 540.0, 1120.0)
    assert key.at == f.face_at(540.0, 1120.0) and 0.0 < key.lift <= 0.75
    f.screen_light(cv, cv.comp, "people", ((0.0, "on", "blue"), (3.0, "dim", "blue")), 6.0, (key.at,), (key,))
    out = xml(cv)
    assert 'blend="color-dodge"' in out and out.count('matte="people"') == 3
    stops = re.findall(r'<radialGradient id="friends-key[^"]*"[^>]*>\s*<stop offset="0" color="(#[0-9a-f]{6})', out)
    assert stops and all(c[1:3] == c[3:5] == c[5:7] for c in stops)  # a grey: the same gain on every channel


def test_leo_needs_no_key_and_a_key_out_of_range_is_refused():
    assert f.key("leo", 540.0, 1120.0).lift == 0.0
    cv = stage()
    f.screen_light(cv, cv.comp, "people", ((0.0, "on", "blue"),), 4.0, ((540.0, 700.0),), (f.key("leo", 540, 1120),))
    assert 'blend="color-dodge"' not in xml(cv)
    for lift in (-0.1, 0.8):
        with pytest.raises(FriendsError, match="lift"):
            f.Key((540.0, 700.0), lift)
    with pytest.raises(FriendsError, match="radius"):
        f.Key((540.0, 700.0), 0.2, 0.0)
    with pytest.raises(FriendsError, match="unknown friend"):
        f.key("gus", 540.0, 1120.0)


def test_a_beat_copy_keeps_its_checks():
    with pytest.raises(FriendsError):
        replace(Beat(0.0, "level"), mouth="whistle")

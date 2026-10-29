"""The Gloss style (ADR 0030): its cast, sets and props, the staging checks and a reel built end to end."""

from __future__ import annotations

import inspect
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import (
    GLOSS,
    PLASTIC,
    STYLES,
    VERTICAL,
    Canvas,
    Episode,
    EpisodeSpec,
    craft,
    flat_counter,
    gloss,
    native,
    registry,
)
from srstudio.canvas import Signature
from srstudio.gloss import GlossError
from srstudio.sample import SYSTEM_FONTS
from srstudio.timeline import Take

FONT_FILE = next((f for f in SYSTEM_FONTS if f.exists()), None)
needs_font = pytest.mark.skipif(FONT_FILE is None, reason="DejaVu Sans Bold is required")
D = 4.0


def font() -> bytes:
    assert FONT_FILE is not None
    return FONT_FILE.read_bytes()


def canvas(signed: bool = True) -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=PLASTIC.background)
    cv = Canvas(scene, PLASTIC, font_asset="f", namer=flat_counter("g"), signature=Signature() if signed else None)
    cv.assets.add_font(id="f", src="f.ttf", family="DejaVu Sans", weight="700")
    return cv


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes())


def phones(text: str, start: float = 0.1, step: float = 0.07) -> tuple[dict, ...]:
    return tuple(
        {"c": c, "start": round(start + i * step, 3), "end": round(start + (i + 1) * step, 3)}
        for i, c in enumerate(text)
    )


def take(id="01", actor="nadia", text="Where is the exit?", start=0.0, duration=1.5, **kw) -> Take:
    words = tuple({"text": w, "start": 0.1 + i * 0.3, "end": 0.35 + i * 0.3} for i, w in enumerate(text.split()))
    return Take(id, actor, "", text, start, duration, words=words, phones=phones(text.lower()), **kw)


def opacity_at(node: ET.Element, t: float) -> float:
    """The hold-keyed opacity of ``node`` at second ``t`` (its static opacity when it has no keys)."""
    for a in node.findall("animate"):
        if a.get("property") == "opacity":
            value = None
            for k in a.iter("key"):
                if float(k.get("time")) <= t + 1e-9:
                    value = float(k.get("value"))
            return 0.0 if value is None else value
    return float(node.get("opacity", 1))


def pivots_stay_put(cv: Canvas) -> None:
    for g in tree(cv).iter("group"):
        if g.get("anchorX") is not None or g.get("anchorY") is not None:
            assert (float(g.get("x", 0)), float(g.get("y", 0))) == (
                float(g.get("anchorX", 0)),
                float(g.get("anchorY", 0)),
            ), g.attrib


# -- the style and its registration -----------------------------------------------------------------------------------
def test_gloss_is_a_registered_portrait_sequence_style_with_its_own_palette_mouth_and_rounded_font():
    assert STYLES["gloss"] is GLOSS
    assert (GLOSS.width, GLOSS.height, GLOSS.fps, GLOSS.timing) == (1080, 1920, 24, "sequence")
    assert GLOSS.default_palette is PLASTIC and GLOSS.mouth() is gloss.GLOSS_MOUTH
    assert GLOSS.parts == ("gloss", "gloss_sets")
    assert GLOSS.font is not None and GLOSS.font.google is not None
    assert (GLOSS.font.family, GLOSS.font.weight, GLOSS.font.src) == ("Fredoka", "600", "assets/fredoka-600.ttf")


def test_every_gloss_part_is_registered_under_the_style():
    entries = {e.name: e for e in registry.entries() if e.style == "gloss"}
    want = {
        "character": {"gloss-sunny", "gloss-nadia", "gloss-gus", "gloss-tamsin"},
        "location": {"gloss-plaza", "gloss-activity", "gloss-waiting"},
        "prop": {"gloss-board", "gloss-door", "gloss-ticket"},
        "graphic": {"gloss-hook", "gloss-notice"},
    }
    for kind, names in want.items():
        assert names <= {n for n, e in entries.items() if e.kind == kind}, kind
    assert all(e.summary for e in entries.values())


# -- speech and tracks ------------------------------------------------------------------------------------------------
def test_talk_reads_the_take_into_rising_visemes_that_end_closed():
    states = gloss.talk(take())
    assert states and states[-1][1] == "closed"
    assert all(b[0] > a[0] for a, b in zip(states, states[1:], strict=False))
    assert gloss.talk(Take("02", "sfx", "", "[BONK]", 0, 1.0)) == []


@pytest.mark.parametrize(
    "bad", [[(0.5, "open"), (0.2, "closed")], [(-1, "open")], [(0.1, "yodel")], [(float("nan"), "open")]]
)
def test_talk_states_out_of_order_or_unknown_are_refused(bad):
    with pytest.raises(GlossError):
        gloss.check_talk(bad)


@pytest.mark.parametrize(
    ("track", "names", "message"),
    [
        ([(0.5, "open"), (0.4, "flat")], gloss.FACES, "rise"),
        ([(0.2, "smug")], gloss.FACES, "not one of"),
        ([(0.2, "cartwheel")], gloss.POSES, "not one of"),
        ([(9.0, "up")], gloss.POSES, "inside"),
    ],
)
def test_a_face_or_pose_track_must_rise_inside_the_shot_and_name_known_states(track, names, message):
    with pytest.raises(GlossError, match=message):
        gloss.check_track(track, names, "track", D)


# -- the cast ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("who", gloss.CAST)
def test_every_cast_member_draws_breathes_blinks_and_keys_its_speech(who):
    cv = canvas()
    states = [(0.0, "closed"), (0.2, "open"), (0.5, "round"), (0.8, "closed")]
    gloss.draw(cv, cv.comp, who, at=(540, 1270), talk=states, end=D)
    animated = {a.get("property") for a in tree(cv).iter("animate")}
    assert {"y", "opacity", "scaleY"} <= animated  # breath or hover, the mouth, the blinks


@pytest.mark.parametrize("who", gloss.CAST)
def test_every_pivoted_group_stays_where_it_was_drawn_so_blinks_happen_on_the_face(who):
    cv = canvas()
    gloss.draw(cv, cv.comp, who, at=(540, 1270), end=D)
    pivots_stay_put(cv)


def switched(cv: Canvas, ids: set[str]) -> list[ET.Element]:
    return [n for n in tree(cv).iter() if n.get("id") in ids]


@pytest.mark.parametrize("who", gloss.CAST)
def test_one_mouth_one_face_and_one_pose_show_at_a_time(who):
    cv = canvas()
    faces = gloss.HOST_FACES if who == gloss.HOST else gloss.FACES
    face = [(0.5, faces[1]), (1.5, faces[2])]
    kw = {} if who == gloss.HOST else {"pose": [(0.4, "up"), (1.2, "shrug"), (2.0, "point")]}
    states = [(0.0, "closed"), (0.2, "open"), (0.5, "teeth"), (0.9, "shout"), (1.3, "closed")]
    made = gloss.draw(cv, cv.comp, who, at=(540, 1270), talk=states, face=face, end=D, **kw)
    for part, names in (("mouth", gloss.VISEMES), ("face", faces), ("pose", gloss.POSES)):
        nodes = made.parts.get(part, {})
        if not nodes:
            assert part == "pose" and who == gloss.HOST
            continue
        drawn = switched(cv, {n.id for n in nodes.values()})
        for t in (0.0, 0.3, 0.6, 1.0, 1.4, 1.7, 2.5, 3.9):
            assert sum(opacity_at(n, t) for n in drawn) == 1, (part, t)
        assert set(nodes) <= set(names)


def test_a_cast_member_needs_a_size_a_length_and_known_traits():
    cv = canvas()
    with pytest.raises(GlossError, match="scale"):
        gloss.nadia(cv, cv.comp, at=(0, 0), scale=0, end=D)
    with pytest.raises(GlossError, match="0 s"):
        gloss.sunny(cv, cv.comp, at=(0, 0), end=0)
    with pytest.raises(GlossError, match="cast"):
        gloss.draw(cv, cv.comp, "jester", at=(0, 0), end=D)
    with pytest.raises(GlossError, match="unwound"):
        gloss.gus(cv, cv.comp, at=(0, 0), end=D, unwound=D + 1)
    with pytest.raises(GlossError, match="bounce"):
        gloss.tamsin(cv, cv.comp, at=(0, 0), end=D, bounce=[(3.0, 1.0)])
    with pytest.raises(GlossError, match="peel"):
        gloss.nadia(cv, cv.comp, at=(0, 0), end=D, peel=[D])
    with pytest.raises(GlossError, match="walk"):
        gloss.nadia(cv, cv.comp, at=(0, 0), end=D, walk=(2.0, 1.0, 300))
    with pytest.raises(GlossError, match="fall"):
        gloss.gus(cv, cv.comp, at=(0, 0), end=D, fall=D)
    with pytest.raises(GlossError, match="scan"):
        gloss.sunny(cv, cv.comp, at=(0, 0), end=D, scan=[(1.0, 9.0)])


def test_the_traits_each_name_options_their_drawer_takes():
    for who, traits in gloss.TRAITS.items():
        assert who in gloss.CAST
        assert set(traits) <= set(gloss.DRAWERS[who].__kwdefaults__ or {}), who


def keys_of(cv: Canvas, prop: str) -> list[list[tuple[float, float]]]:
    return [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == prop
    ]


def test_the_wind_up_key_turns_until_it_unwinds_and_then_stays_still():
    cv = canvas()
    gloss.gus(cv, cv.comp, at=(540, 1270), end=D, unwound=2.0)
    (turn,) = [k for k in keys_of(cv, "scaleX") if len(k) > 4]
    assert turn[-1][0] <= 2.0 + 1e-6 and turn[0][0] == 0
    steps = [b[0] - a[0] for a, b in zip(turn, turn[1:], strict=False)]
    assert steps[-1] > steps[0]  # it slows before it stops


def test_a_fall_tips_the_doll_over_its_feet_and_it_stays_down():
    cv = canvas()
    gloss.nadia(cv, cv.comp, at=(540, 1270), end=D, fall=1.0)
    (fall,) = keys_of(cv, "rotation")
    assert fall[0] == (0.0, 0.0) and (1.0, 0.0) in fall and abs(fall[-1][1]) >= 80 and fall[-1][0] < D


def test_a_walk_moves_the_doll_to_its_mark_and_hops_on_the_way():
    cv = canvas()
    gloss.tamsin(cv, cv.comp, at=(300, 1270), end=D, walk=(0.5, 1.5, 700))
    xs = [k for k in keys_of(cv, "x") if k[-1] == (1.5, 700.0)]
    assert xs and xs[0][0] == (0.0, 300.0)


def test_sunny_wears_a_tie_only_when_asked_and_scans_only_inside_its_spans():
    plain, tied = canvas(), canvas()
    gloss.sunny(plain, plain.comp, at=(540, 600), end=D)
    gloss.sunny(tied, tied.comp, at=(540, 600), end=D, tie=True, scan=[(1.0, 2.0)])
    assert len(list(tree(tied).iter("shape"))) > len(list(tree(plain).iter("shape")))
    gates = [k for k in keys_of(tied, "opacity") if (1.0, 1.0) in k and (2.0, 0.0) in k]
    assert gates


# -- the sets ---------------------------------------------------------------------------------------------------------
from srstudio import gloss_reel as reel  # noqa: E402
from srstudio import gloss_sets as sets  # noqa: E402
from srstudio.gloss_reel import Move, Notice, Place, Prop, Stage  # noqa: E402
from srstudio.gloss_sets import Card  # noqa: E402

LOCATIONS = [
    (sets.plaza, {"sign": True}),
    (sets.activity, {"number": "12"}),
    (sets.waiting, {"serving": [(0, "3"), (2.0, "4")]}),
]


@pytest.mark.parametrize(("location", "options"), LOCATIONS)
def test_locations_draw_both_signature_marks_only_when_signed(location, options):
    signed, unsigned = canvas(), canvas(signed=False)
    location(signed, signed.comp, end=D, **options)
    location(unsigned, unsigned.comp, end=D, **options)
    ids = [g.get("id") or "" for g in tree(signed).iter("group")]
    assert any(i.startswith("sig-cactus") for i in ids) and any(i.startswith("sig-code") for i in ids)
    assert not any(g.get("id", "").startswith("sig-") for g in tree(unsigned).iter("group"))


def test_location_events_must_fall_inside_the_shot():
    cv = canvas()
    with pytest.raises(GlossError, match="NOW SERVING"):
        sets.waiting(cv, cv.comp, end=D, serving=[(0, "3"), (D + 1, "4")])
    with pytest.raises(GlossError, match="first number"):
        sets.waiting(cv, cv.comp, end=D, serving=[(1.0, "3")])
    with pytest.raises(GlossError, match="at least one"):
        sets.waiting(cv, cv.comp, end=D, serving=[])
    with pytest.raises(GlossError, match="0 s"):
        sets.plaza(cv, cv.comp, end=0)


def test_the_display_shows_one_number_at_a_time():
    cv = canvas()
    sets.waiting(cv, cv.comp, end=D, serving=[(0, "3"), (1.0, "4"), (2.0, "3")])
    gated = [g for g in tree(cv).iter("group") if any(a.get("property") == "opacity" for a in g.findall("animate"))]
    assert len(gated) == 3
    for t in (0.0, 0.5, 1.2, 2.5, 3.9):
        assert sum(opacity_at(g, t) for g in gated) == 1


def test_seven_segment_numbers_are_digits_only():
    cv = canvas()
    with pytest.raises(GlossError, match="digits only"):
        sets.digits(cv, cv.comp, "4,8", 0, 0, 100, "#000000")
    with pytest.raises(GlossError, match="digits only"):
        sets.ticket(cv, cv.comp, at=(0, 0), end=D, number="")
    lit = canvas()
    sets.digits(lit, lit.comp, "8", 0, 0, 100, "#000000")
    one = canvas()
    sets.digits(one, one.comp, "1", 0, 0, 100, "#000000", ghost="#222222")
    assert len(list(tree(lit).iter("shape"))) == len(list(tree(one).iter("shape"))) == 7


def test_a_nested_door_opens_one_leaf_per_opening_and_the_last_reveals_the_dispenser():
    for opens in ((), (0.5,), (0.5, 1.0, 1.5)):
        cv = canvas()
        sets.door(cv, cv.comp, at=(540, 1200), end=D, opens=opens)
        swings = keys_of(cv, "scaleX")
        assert sorted(k[1][0] for k in swings) == list(opens)
        pivots_stay_put(cv)


@pytest.mark.parametrize(
    ("kw", "message"),
    [
        ({"opens": (0.5,), "painted": True}, "painted door"),
        ({"opens": (0.5, 1.0, 1.5, 2.0)}, "at most"),
        ({"opened": 1, "painted": True}, "painted door"),
        ({"opens": (1.0, 0.5)}, "rise"),
        ({"scale": 0}, "scale"),
    ],
)
def test_a_door_refuses_what_it_cannot_do(kw, message):
    cv = canvas()
    with pytest.raises(GlossError, match=message):
        sets.door(cv, cv.comp, at=(540, 1200), end=D, **kw)


@needs_font
def test_wrap_measures_every_line_and_refuses_what_does_not_fit():
    assert sets.wrap(font(), "one two three four", 48, 2000, 1) == ["one two three four"]
    assert len(sets.wrap(font(), "one two three four", 48, 200, 4)) > 1
    with pytest.raises(GlossError, match="wider"):
        sets.wrap(font(), "Supercalifragilistic", 48, 100, 3)
    with pytest.raises(GlossError, match="lines"):
        sets.wrap(font(), "a b c d e f g h i j k l m n o p", 48, 60, 2)


@needs_font
def test_the_board_switches_cards_in_order_and_refuses_bad_ones():
    cv = canvas()
    cards = [Card(0, "Held a door", points=2), Card(1.0, "Exhaled audibly", points=-40), Card(2.0, "Survey", "1 2 3")]
    made = sets.board(cv, cv.comp, cards, end=D, font=font())
    nodes = switched(cv, {g.id for g in made})
    for t in (0.0, 1.5, 3.0):
        assert sum(opacity_at(n, t) for n in nodes) == 1
    texts = [t.get("text") for t in tree(cv).iter("text")]
    assert "+2" in texts and "−40" in texts and "JOY POINTS" in texts
    for bad, message in (
        ([], "at least one"),
        ([Card(1.0, "b"), Card(0.5, "a")], "rise"),
        ([Card(0, "a", tone="neon")], "tone"),
    ):
        with pytest.raises(GlossError, match=message):
            sets.board(cv, cv.comp, bad, end=D, font=font())
    with pytest.raises(GlossError, match="safe region"):
        sets.board(cv, cv.comp, cards, end=D, font=font(), box=(0, 100, 900, 300))
    with pytest.raises(GlossError, match="at least"):
        sets.board(cv, cv.comp, cards, end=D, font=font(), box=(100, 300, 300, 300))


def contrast(a: str, b: str) -> float:
    def lum(hex_: str) -> float:
        c = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b_ = (x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_every_tone_reads_at_4_5_to_1_on_the_opaque_board_and_white_reads_on_every_badge():
    for colour in sets.TONES.values():
        assert contrast(colour, sets.PAPER) >= 7, colour  # antialiased glyphs measure about a quarter lower
        assert contrast("#ffffff", colour) >= 4.5, colour
    assert contrast(sets.TEXT, sets.PAPER) >= 7


@needs_font
def test_the_hook_and_the_notice_are_lettered_and_have_sunny_speak():
    cv = canvas()
    talk = [(0.0, "closed"), (0.3, "open"), (0.9, "closed")]
    sets.hook(cv, cv.comp, "Where is the exit?", end=D, font=font(), talk=talk)
    sets.notice(cv, cv.comp, "Orientation", "Day one of forever.", end=D, font=font(), talk=talk)
    texts = [t.get("text") for t in tree(cv).iter("text")]
    assert {"Where is the exit?", "Orientation", "Day one of forever.", "PLAZA NOTICE"} <= set(texts)
    assert any(a.get("preset") == "typewriter" for a in tree(cv).iter("textAnimator"))


def test_every_text_layer_of_the_sets_stays_inside_the_safe_region():
    if FONT_FILE is None:
        pytest.skip("DejaVu Sans Bold is required")
    cv = canvas()
    for location, options in LOCATIONS:
        location(cv, cv.comp, end=D, **options)
    sets.board(cv, cv.comp, [Card(0, "Held a door", "And smiled", points=2)], end=D, font=font())
    sets.hook(cv, cv.comp, "Have you ever woken up inside a mandatory team building exercise?", end=D, font=font())
    sets.notice(cv, cv.comp, "Orientation", "Day one of forever. The exit is in a future update.", end=D, font=font())
    root = tree(cv)
    sizes = {t.get("id"): (float(t.get("width")), float(t.get("height"))) for t in root.iter("text")}
    x0, y0, x1, y1 = sets.SAFE
    for layer in root.iter("layer"):
        if layer.get("asset") in sizes:
            w, h = sizes[layer.get("asset")]
            x, y = float(layer.get("x")), float(layer.get("y"))
            assert x0 <= x and x + w <= x1 + 1 and y0 <= y and y + h <= y1, (layer.get("asset"), x, y, w, h)


# -- staging ----------------------------------------------------------------------------------------------------------
def staging_takes() -> list[Take]:
    return [
        take("01", "sunny", "Where is the exit?", 0, 1.5),
        take("02", "nadia", "I know.", 1.5, 1.5),
        Take("03", "sfx", "", "[BONK]", 3.0, 1.0),
        take("04", "sunny", "Day one.", 4.0, 1.5),
    ]


GOOD = {
    "01": Stage("plaza", cast=(Place("nadia", 540),)),
    "02": Stage("plaza", cast=(Place("nadia", 540), Place("sunny", 800))),
    "03": Stage("activity", props=(Prop("door", 540, 1200, {"painted": True}),)),
    "04": Stage(notice=Notice("Orientation", "Day one of forever.")),
}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"04": None}, "without a stage"),
        ({"02": Stage("moon", cast=(Place("nadia", 540),))}, "unknown location"),
        ({"02": Stage("plaza", cast=(Place("jester", 540),))}, "not in the cast"),
        ({"02": Stage("plaza", cast=(Place("gus", 540),))}, "nadia speaks but is not on screen"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540), Place("nadia", 200)))}, "two places"),
        ({"03": Stage("plaza", props=(Prop("trapdoor", 0, 0),))}, "unknown prop"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540),), cards=(Card(9, "late"),))}, "outside"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540),), move=Move("crash", 1.45, 1.4, 540, 600))}, "inside"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540),), move=Move("dolly", 0.1, 1.4, 540, 600))}, "crash or"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540),), dark=((1.0, 3.0),))}, "outside"),
        ({"04": Stage("plaza", notice=Notice("a", "b"))}, "alone"),
        ({"02": Stage(notice=Notice("a", "b"))}, "only the host"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540, traits={"tie": True}),))}, "no trait"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540, traits={"fall": 9.0}),))}, "inside"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540, face=((0.2, "smug"),)),))}, "not one of"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540, walk=(1.0, 4.0, 300)),))}, "walk"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540), Place("sunny", 800, pose=((0, "up"),))))}, "floats"),
        ({"02": Stage("plaza", cast=(Place("nadia", 540), Place("sunny", 800, traits={"tie": "yes"})))}, "on or off"),
    ],
)
def test_staging_that_does_not_fit_the_recording_is_refused(change, message):
    stages = {**GOOD, **change}
    stages = {k: v for k, v in stages.items() if v is not None}
    with pytest.raises(GlossError, match=message):
        reel.check(staging_takes(), stages)


def test_the_host_may_speak_from_off_screen():
    reel.check(staging_takes(), {**GOOD, "01": Stage("plaza")})


# -- a reel, built and checked by the engine --------------------------------------------------------------------------
def write_project(root: Path, takes: list[Take] | None = None) -> None:
    takes = takes or staging_takes()
    items = []
    for t in takes:
        item = {
            "id": t.id,
            "actor": t.actor,
            "shot": "",
            "text": t.text,
            "start": t.start,
            "duration": t.duration,
            "audio": f"audio/take-{t.id}.wav",
        }
        if not t.is_effect:
            item.update(speech_duration=t.duration - 0.2, words=list(t.words), phones=list(t.phones), mood="calm")
        items.append(item)
    (root / "audio").mkdir(parents=True)
    for t in takes:
        subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=330:duration={t.duration}",
             "-ar", "48000", "-ac", "1", str(root / f"audio/take-{t.id}.wav")],
            check=True,
        )  # fmt: skip
    total = round(takes[-1].start + takes[-1].duration, 3)
    (root / "timeline.json").write_text(json.dumps({"duration": total, "tempo_adjustment": 1.0, "items": items}))
    (root / "assets").mkdir(parents=True, exist_ok=True)
    assert FONT_FILE is not None
    shutil.copy(FONT_FILE, root / "assets" / "fredoka-600.ttf")


def episode(root: Path) -> Episode:
    return Episode(
        EpisodeSpec(
            slug="gloss-test",
            title="Gloss test",
            description="A Gloss reel in the test suite.",
            root=root,
            seed=1,
            style=GLOSS,
            language="en-US",
            font_family="DejaVu Sans",
            safe_area=VERTICAL,
        )
    )


@needs_font
def test_a_reel_builds_with_the_hook_the_board_the_notice_crossfade_captions_and_mix(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    write_project(tmp_path)
    ep = episode(tmp_path)
    stages = {
        **GOOD,
        "01": Stage("plaza", cast=(Place("nadia", 540, walk=(0.2, 1.0, 400)),)),
        "02": Stage(
            "waiting",
            options={"serving": ((0, "3"), (1.0, "4"))},
            cast=(Place("nadia", 540, face=((0.5, "wide"),), pose=((0.2, "shrug"),)), Place("gus", 200)),
            cards=(Card(0, "Held a door", points=2),),
            props=(Prop("ticket", 760, 1080, {"number": "4812006"}, front=True),),
            move=Move("crash", 0.5, 1.3, 540, 900),
            shake=((0.2, 0.6),),
            dark=((1.2, 1.4),),
        ),
    }
    made = reel.build(ep, stages, hook="Where is the exit?", font=font())
    out = ep.finish(tmp_path / "gloss-test.scene.xml", tmp_path / "qa" / "sdk.json", strict=False)
    root = ET.fromstring(out.read_bytes())
    assert [t.get("type") for t in root.iter("transition")] == ["crossfade"]
    assert root.find(".//captionTrack") is not None and made["captions"] is not None
    assert len(list(root.iter("audioTrack"))) == 4
    texts = [t.get("text") for t in root.iter("text")]
    assert "Where is the exit?" in texts and "+2" in texts and "Orientation" in texts
    cut = round(ep.takes[0].duration, 3)  # the camera, named as one, crashes in on the episode's clock
    assert craft.Move("crash", "gloss-02-angle", round(cut + 0.5, 3), round(cut + 0.65, 3), 1.3, True) in craft.moves(
        out.read_bytes()
    )
    found = shutil.which("scene-render") or __import__("os").environ.get("SRSTUDIO_ENGINE")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    check = subprocess.run([str(Path(found).resolve()), "validate", str(out)], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr


def test_reel_captions_leave_no_lone_last_word_and_stay_up_long_enough_to_read():
    assert inspect.signature(reel.build).parameters["look"].default is native.CAPTION_LOOK  # shipped reels rebuild
    assert reel.LOOK.min_last == 2 and reel.LOOK.min_seconds >= 0.8334  # the engine's legibility minimum
    words, at = [], 0.0
    for w in "By continuing to exist, you agree to continue existing.".split():
        words.append({"text": w, "start": at, "end": at + 0.3})
        at += 0.35
    line = Take("10", "sunny", "", " ".join(w["text"] for w in words), 20.0, at + 1.2, words=tuple(words))
    cues = native.cues_from_takes([line], look=reel.LOOK)
    assert [len(c.text.split()) > 1 for c in cues] == [True] * len(cues) and len(cues) > 1
    assert all(c.end - c.start >= reel.LOOK.min_seconds for c in cues)


@needs_font
def test_the_music_hushes_through_every_pause_between_lines_and_comes_back_for_the_next(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    write_project(tmp_path)  # lines at 0-1.3, 1.5-2.8 and 4.0-5.3: one pause, over the [BONK]
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=5.5",
                    "-ar", "48000", "-ac", "2", str(tmp_path / "audio/music.wav")], check=True)  # fmt: skip
    timeline = json.loads((tmp_path / "timeline.json").read_text())
    timeline["music"] = {"file": "audio/music.wav", "gain_db": -17.0}
    (tmp_path / "timeline.json").write_text(json.dumps(timeline))
    ep = episode(tmp_path)
    reel.build(ep, GOOD, hook="Where is the exit?", font=font())
    out = ep.finish(tmp_path / "gloss-test.scene.xml", tmp_path / "qa" / "sdk.json", strict=False)
    (music,) = [t for t in ET.fromstring(out.read_bytes()).iter("audioTrack") if t.get("role") == "music"]
    (gain,) = [a for a in music.findall("animate") if a.get("property") == "gain"]
    keys = [(float(k.get("time")), float(k.get("value"))) for k in gain.iter("key")]
    low = -17.0 + reel.HUSH
    want = [(0.0, -17.0), (2.8, -17.0), (2.8 + reel.HUSH_RAMP, low), (4.0 - reel.HUSH_RAMP, low), (4.0, -17.0)]
    assert keys == [(round(t, 6), round(v, 6)) for t, v in want]
    assert gain.get("timeBase") is None  # on the episode's clock


@needs_font
def test_the_board_stays_out_of_the_camera_so_a_zoom_never_pushes_its_text_out_of_the_safe_area(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    write_project(tmp_path)
    ep = episode(tmp_path)
    zoomed = Stage("plaza", cast=(Place("nadia", 540),), cards=(Card(0, "Ran into decor", "Seems bad?", points=-3),),
                   move=Move("crash", 0.2, 1.3, 540, 900))  # fmt: skip
    reel.build(ep, {**GOOD, "02": zoomed}, hook="Why?", font=font())
    out = ep.finish(tmp_path / "gloss-test.scene.xml", tmp_path / "qa" / "sdk.json", strict=False)
    parents = {c: p for p in ET.fromstring(out.read_bytes()).iter() for c in p}

    def moved(node) -> bool:
        while node in parents:
            node = parents[node]
            if node.get("id", "").startswith("shot-"):
                return False
            for a in node.findall("animate"):
                if (
                    a.get("property", "").startswith("scale")
                    and max(float(k.get("value")) for k in a.iter("key")) > 1.2
                ):
                    return True
        return False

    (body,) = [t.get("id") for t in parents if t.tag == "text" and t.get("text") == "Seems bad?"]
    layers = [n for n in parents if n.tag == "layer" and n.get("asset") == body]
    assert layers and not any(moved(n) for n in layers)


@needs_font
def test_the_host_speaking_off_screen_appears_in_the_corner(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    write_project(tmp_path)
    alone, shown = episode(tmp_path), None
    reel.build(alone, {**GOOD, "02": Stage("plaza", cast=(Place("nadia", 540),))}, hook="Why?", font=font())
    takes = [take("01", "nadia", "I know.", 0, 1.5), take("02", "sunny", "Day one.", 1.5, 1.5),
             take("03", "sunny", "Day two.", 3.0, 1.5), Take("04", "sfx", "", "[BONK]", 4.5, 1.0)]  # fmt: skip
    root = tmp_path / "two"
    write_project(root, takes)
    shown = episode(root)
    stages = {"01": Stage("plaza", cast=(Place("nadia", 540),)), "02": Stage("plaza"),
              "03": Stage("plaza", cast=(Place("sunny", 800),)), "04": Stage("plaza")}  # fmt: skip
    reel.build(shown, stages, hook="Why?", font=font())
    xml = ET.fromstring(shown.cv.scene.to_bytes())
    corner = [g for g in xml.iter("group") if (g.get("x"), g.get("y")) == (str(reel.BADGE[0]), str(reel.BADGE[1]))]
    assert len(corner) == 1  # take 02 only: in 03 Sunny is in the shot


def test_stroked_lettering_scales_with_its_height_and_refuses_what_it_cannot_draw():
    cv = canvas()
    gloss.letters(cv, cv.comp, "NOW SERVING", 0, 0, 40, "#000000")
    assert gloss.letters_width("NOW SERVING", 40) == 9 * 32 + 20 + 24
    assert gloss.letters_width("EXIT", 20) == gloss.letters_width("EXIT", 40) / 2
    for bad in ("exit", "4 EVER", "", "  "):
        with pytest.raises(GlossError, match="stroked lettering"):
            gloss.letters(cv, cv.comp, bad, 0, 0, 40, "#000000")


def test_the_sets_need_no_font_so_no_scenery_text_can_leave_the_safe_area_under_a_zoom():
    cv = canvas()
    for location, options in LOCATIONS:
        location(cv, cv.comp, end=D, **options)
    sets.door(cv, cv.comp, at=(540, 1200), end=D, opens=(0.5,))
    sets.ticket(cv, cv.comp, at=(540, 1000), end=D, number="4812006")
    assert not list(tree(cv).iter("text"))


def test_a_fall_at_the_first_frame_is_a_doll_already_lying_down():
    cv = canvas()
    gloss.gus(cv, cv.comp, at=(540, 1270), end=D, fall=0.0)
    (fall,) = keys_of(cv, "rotation")
    assert fall == [(0.0, -88.0)]


def test_the_vinyl_finish_lights_every_part_and_keeps_its_outline_crisp():
    assert gloss.mix("#000000", "#ffffff", 0.5) == "#808080" and gloss.mix("#ff5fa2", "#000000", 0) == "#ff5fa2"
    cv = canvas()
    gloss.nadia(cv, cv.comp, at=(540, 1270), end=D)
    root = tree(cv)
    effects = {e.get("id"): e.get("type") for e in root.iter("effect")}
    assert effects["gloss-form"] == effects["gloss-rim"] == "inner-shadow"
    finished = [g for g in root.iter("group") if "gloss-form" in (g.get("effects") or "")]
    assert len(finished) >= 3  # body, head and sleeves
    for g in finished:  # the fill is finished; its outline is drawn after it, outside the effect
        assert all(s.get("strokeWidth") in (None, "0", "0.0") for s in g.iter("shape") if s.get("shape") != "path")
    assert any(p.get("id", "").startswith("gloss-vinyl-") for p in root.iter("linearGradient"))


def test_every_reel_shot_is_graded_by_the_style():
    cv = canvas()
    shot = cv.group(cv.comp, "shot")
    sets.finish(cv, shot)
    assert tree(cv).find(".//group[@id='shot']").get("effects").split() == [f"gloss-{k}" for k in sets.GRADE]


def test_a_nested_door_carries_its_state_across_shots_with_depth_and_opened():
    cv = canvas()  # shot two of three: the first leaf is already open, the second swings, the third stays shut
    sets.door(cv, cv.comp, at=(540, 1200), end=D, depth=3, opened=1, opens=(0.5,))
    swings = keys_of(cv, "scaleX")
    assert sorted(k[-1][1] for k in swings) == [0.08, 0.08] and sorted(k[0][1] for k in swings) == [0.08, 1]
    assert len([g for g in tree(cv).iter("group") if g.get("anchorX") is not None]) == 3  # three leaves drawn
    for kw in ({"depth": 2, "opened": 2, "opens": (0.5,)}, {"depth": 4}, {"depth": 0}, {"opened": -1}):
        with pytest.raises(GlossError, match="door"):
            sets.door(cv, cv.comp, at=(540, 1200), end=D, **kw)


@pytest.mark.parametrize("flip", [False, True])
def test_the_new_sticker_reads_the_right_way_round_on_a_flipped_doll(flip):
    cv = canvas()
    gloss.draw(cv, cv.comp, "nadia", at=(540, 1500), flip=flip, end=D)
    root = tree(cv)
    parents = {child: node for node in root.iter() for child in node}
    n = next(p for p in root.iter() if p.get("path") == gloss._GLYPHS["N"])
    sign, node = 1.0, n
    while node in parents:
        node = parents[node]
        sign *= 1 if float(node.get("scaleX", 1)) > 0 else -1
    assert sign > 0


@needs_font
def test_the_first_card_shows_its_words_only_once_the_pop_has_opened():
    cv = canvas()
    sets.board(cv, cv.comp, [Card(1.0, "Stay: permanent", "Fun: mandatory.", label="WELCOME")], end=D, font=font())
    root = tree(cv)
    parents = {c: p for p in root.iter() for c in p}
    words = {t.get("id"): t.get("text") for t in root.iter("text")}
    layers = [layer for layer in root.iter("layer") if layer.get("asset") in words]
    assert len(layers) == 3
    for layer in layers:
        node, seen = layer, 1.0
        while node in parents:
            node = parents[node]
            seen = min(seen, opacity_at(node, 1.0 + sets.POP_OPEN - 0.01))
        assert seen == 0, words[layer.get("asset")]


@needs_font
@pytest.mark.parametrize("where", ["plaza", "activity", "waiting", "notice"])
def test_every_location_shades_the_floor_under_the_caption_band(where):
    cv = canvas()
    if where == "notice":
        sets.notice(cv, cv.comp, "Orientation", "Day one of forever.", end=D, font=font())
    else:
        sets.SETS[where](cv, cv.comp, end=D)
    root = tree(cv)
    assert any(g.get("id") == "gloss-caption-shade" for g in root.iter("linearGradient"))
    assert any(node.get("fill") == "url(#gloss-caption-shade)" for node in root.iter())


@needs_font
def test_the_grade_lights_every_world_and_leaves_the_board_and_the_notice_card_crisp(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    write_project(tmp_path)
    ep = episode(tmp_path)
    scored = Stage("plaza", cast=(Place("nadia", 540),), cards=(Card(0, "Ran into decor", "Seems bad?", points=-3),))
    reel.build(ep, {**GOOD, "02": scored}, hook="Why?", font=font())
    out = ep.finish(tmp_path / "gloss-test.scene.xml", tmp_path / "qa" / "sdk.json", strict=False)
    root = ET.fromstring(out.read_bytes())
    parents = {c: p for p in root.iter() for c in p}
    graded = {g for g in root.iter("group") if "gloss-vignette" in (g.get("effects") or "").split()}

    def under_grade(node) -> bool:
        while node in parents:
            node = parents[node]
            if node in graded:
                return True
        return False

    shots = [g for g in root.iter("group") if g.get("id", "").startswith("shot-")]
    assert len(shots) == 4 and all(any(d in graded for d in s.iter("group")) for s in shots)
    words = {t.get("id") for t in root.iter("text")}
    layers = [n for n in root.iter("layer") if n.get("asset") in words]
    assert layers and not any(under_grade(n) for n in layers)


@needs_font
def test_the_notice_card_shows_its_words_once_the_crossfade_into_it_has_settled():
    cv = canvas()
    sets.notice(cv, cv.comp, "Orientation", "Day one of forever.", end=D, font=font(), settle=0.3)
    root = tree(cv)
    parents = {c: p for p in root.iter() for c in p}
    words = {t.get("id") for t in root.iter("text")}
    layers = [n for n in root.iter("layer") if n.get("asset") in words]
    assert len(layers) == 4
    for layer in layers:
        node, seen = layer, 1.0
        while node in parents:
            node = parents[node]
            seen = min(seen, opacity_at(node, 0.29))
        assert seen == 0
    with pytest.raises(GlossError, match="settle"):
        sets.notice(cv, cv.comp, "Orientation", "Day one of forever.", end=D, font=font(), settle=D)


@needs_font
def test_a_card_carried_over_from_the_last_shot_is_on_at_the_cut_without_popping_again():
    cv = canvas()
    sets.board(cv, cv.comp, [Card(0, "Held a door", points=2, carried=True), Card(1.0, "Said thank you", points=1)],
               end=D, font=font())  # fmt: skip
    root = tree(cv)
    scaled = [a for a in root.iter("animate") if a.get("property", "").startswith("scale")]
    starts = sorted({float(next(a.iter("key")).get("value")) for a in scaled})
    assert len(scaled) == 2 and starts == [0.2]  # only the second card's badge pops; nothing on the carried one
    with pytest.raises(GlossError, match="carried"):
        sets.board(cv, cv.comp, [Card(0.5, "Held a door", carried=True)], end=D, font=font())


@pytest.mark.parametrize("at", [0.0, 1.0])
def test_a_fallen_doll_lies_on_the_floor_not_half_through_it(at):
    cv = canvas()
    gloss.nadia(cv, cv.comp, at=(540, 1270), end=D, fall=at)
    (lift,) = [k for k in keys_of(cv, "y") if k[-1][1] == -gloss.LIE]
    assert lift[0] == ((0.0, -gloss.LIE) if at == 0 else (0.0, 0.0))
    assert gloss.LIE >= 105  # half the body's width: the side it lands on rests on the floor line


@pytest.mark.parametrize(
    ("who", "traits", "match"),
    [
        ("tamsin", {"bounce": [(True, 1.0)]}, "bounce span True..1.0 must rise inside the shot"),
        ("tamsin", {"bounce": [(0.5, 9.0)]}, "bounce span 0.5..9.0 must rise inside the shot"),
        ("nadia", {"fall": True}, "fall at True must fall inside the shot"),
        ("gus", {"unwound": float("nan")}, "unwound at nan must fall inside the shot"),
    ],
)
def test_a_trait_second_or_span_is_a_number_inside_the_shot(who, traits, match):
    with pytest.raises(GlossError, match=match):
        gloss.check_traits(who, traits, 4.0)

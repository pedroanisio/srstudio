"""The Saga style (ADR 0025): its cast, sets and props, the staging checks and a reel built end to end."""

from __future__ import annotations

import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import SAGA, STYLES, VERTICAL, VOID, Canvas, Episode, EpisodeSpec, flat_counter, registry, saga
from srstudio import saga_reel as reel
from srstudio import saga_sets as sets
from srstudio.canvas import Signature
from srstudio.saga import SagaError
from srstudio.saga_reel import Entry, Move, Place, Prop, Stage
from srstudio.saga_sets import Panel
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
    scene.add_project(width=1080, height=1920, fps="24", duration=D, background=VOID.background)
    cv = Canvas(scene, VOID, font_asset="f", namer=flat_counter("s"), signature=Signature() if signed else None)
    cv.assets.add_font(id="f", src="f.ttf", family="DejaVu Sans", weight="700")
    return cv


def tree(cv: Canvas) -> ET.Element:
    return ET.fromstring(cv.scene.to_bytes())


def phones(text: str, start: float = 0.1, step: float = 0.07) -> tuple[dict, ...]:
    return tuple(
        {"c": c, "start": round(start + i * step, 3), "end": round(start + (i + 1) * step, 3)}
        for i, c in enumerate(text)
    )


def take(id="01", actor="juno", text="I know.", start=0.0, duration=1.5, **kw) -> Take:
    words = tuple({"text": w, "start": 0.1 + i * 0.3, "end": 0.35 + i * 0.3} for i, w in enumerate(text.split()))
    phone_step = min(0.07, (duration - 0.2) / max(1, len(text)))
    return Take(id, actor, "", text, start, duration, words=words, phones=phones(text.lower(), step=phone_step), **kw)


# -- the style and its registration -----------------------------------------------------------------------------------
def test_saga_is_a_registered_portrait_sequence_style_with_its_own_palette_and_mouth():
    assert STYLES["saga"] is SAGA
    assert (SAGA.width, SAGA.height, SAGA.fps, SAGA.timing) == (1080, 1920, 24, "sequence")
    assert SAGA.default_palette is VOID and SAGA.mouth() is saga.SAGA_MOUTH
    assert SAGA.parts == ("saga", "saga_sets")
    assert SAGA.font is not None and SAGA.font.google is not None and SAGA.font.family == "Space Grotesk"


def test_every_saga_part_is_registered_under_the_style():
    entries = {e.name: e for e in registry.entries() if e.style == "saga"}
    want = {
        "character": {"saga-gloom", "saga-enforcer", "saga-droid", "saga-juno", "saga-rook", "saga-mabel"},
        "location": {
            "saga-space",
            "saga-bridge",
            "saga-cantina",
            "saga-cantina-bar",
            "saga-desert",
            "saga-cockpit",
            "saga-cockpit-console",
            "saga-compactor",
        },
        "prop": {"saga-handbook", "saga-holo", "saga-cube", "saga-freighter", "saga-fighter", "saga-pebble"},
        "graphic": {"saga-hook", "saga-entry"},
    }
    for kind, names in want.items():
        assert {n for n, e in entries.items() if e.kind == kind} == names
    assert all(e.summary for e in entries.values())


# -- speech -----------------------------------------------------------------------------------------------------------
def test_talk_reads_the_take_into_rising_visemes_that_end_closed():
    states = saga.talk(take(text="Open your mouth."))
    assert states[0][0] == 0 and states[-1][1] == "closed"
    assert {p for _, p in states} <= set(saga.VISEMES) and {"open", "closed"} <= {p for _, p in states}
    assert all(b[0] > a[0] for a, b in zip(states, states[1:], strict=False))
    assert saga.talk(Take("02", "sfx", "", "[BOOM]", 0, 1.0)) == []


@pytest.mark.parametrize("bad", [[(0.5, "open"), (0.2, "closed")], [(0, "grin")], [(-1, "open")]])
def test_talk_states_out_of_order_or_unknown_are_refused(bad):
    with pytest.raises(SagaError):
        saga.check_talk(bad)


# -- the cast ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("who", saga.CAST)
def test_every_cast_member_draws_and_keys_its_speech(who):
    cv = canvas()
    states = [(0.0, "closed"), (0.2, "open"), (0.5, "round"), (0.8, "closed")]
    saga.draw(cv, cv.comp, who, at=(540, 1500), talk=states, end=D)
    animated = {a.get("property") for a in tree(cv).iter("animate")}
    assert {"y", "opacity"} <= animated  # the breath, and the mouth or the visor
    if who not in saga.MASKED:
        assert "scaleY" in animated  # blinks


def effect_types(root: ET.Element, node: ET.Element) -> set[str]:
    declared = {e.get("id"): e.get("type") for e in root.iter("effect")}
    return {declared[e] for e in (node.get("effects") or "").split()}


def ancestry(root: ET.Element, node: ET.Element) -> list[ET.Element]:
    parents = {c: p for p in root.iter() for c in p}
    chain = [node]
    while chain[-1] in parents:
        chain.append(parents[chain[-1]])
    return chain


@pytest.mark.parametrize("who", saga.CAST)
def test_every_cast_member_is_lit_with_form_shading_and_a_lift_off_the_set(who):
    cv = canvas()
    saga.draw(cv, cv.comp, who, at=(540, 1500), end=D)
    root = tree(cv)
    (figure,) = [g for g in root.find(".//composition") if g.tag == "group"]
    assert {"inner-shadow", "drop-shadow"} <= effect_types(root, figure)


def pivots_stay_put(cv: Canvas) -> None:
    for g in tree(cv).iter("group"):
        if g.get("anchorX") is not None or g.get("anchorY") is not None:
            assert (float(g.get("x", 0)), float(g.get("y", 0))) == (
                float(g.get("anchorX", 0)),
                float(g.get("anchorY", 0)),
            ), g.attrib


@pytest.mark.parametrize("who", saga.CAST)
def test_every_pivoted_group_stays_where_it_was_drawn_so_eyes_blink_on_the_face_not_at_the_feet(who):
    cv = canvas()
    saga.draw(cv, cv.comp, who, at=(540, 1280), end=D)
    pivots_stay_put(cv)


def test_the_fireball_grows_from_the_cube_not_from_the_frame_corner():
    cv = canvas()
    sets.cube_station(cv, cv.comp, at=(540, 800), end=D, boom=0.5)
    pivots_stay_put(cv)


def test_an_unmasked_mouth_shows_exactly_one_pose_at_a_time():
    cv = canvas()
    states = [(0.0, "closed"), (0.2, "open"), (0.5, "teeth"), (0.8, "closed")]
    saga.juno(cv, cv.comp, at=(540, 1500), talk=states, end=D)
    tracks = [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == "opacity"
    ]
    assert len(tracks) == 3  # closed, open, teeth
    for t in (0.1, 0.3, 0.6, 0.9):
        assert sum(next(v for tt, v in reversed(k) if tt <= t) for k in tracks) == 1


def test_a_visor_lights_while_its_character_speaks():
    cv = canvas()
    saga.gloom(cv, cv.comp, at=(540, 1500), talk=[(0.0, "closed"), (0.3, "open"), (0.9, "closed")], end=D)
    (visor,) = [a for a in tree(cv).iter("animate") if a.get("property") == "opacity"]
    assert [(float(k.get("time")), float(k.get("value"))) for k in visor.iter("key")] == [
        (0.0, 0.35),
        (0.3, 1.0),
        (0.9, 0.35),
    ]


def test_a_cast_member_needs_a_size_a_length_and_a_named_look():
    cv = canvas()
    with pytest.raises(SagaError, match="scale"):
        saga.rook(cv, cv.comp, at=(0, 0), scale=0, end=D)
    with pytest.raises(SagaError, match="0 s"):
        saga.droid(cv, cv.comp, at=(0, 0), end=0)
    with pytest.raises(SagaError, match="cast"):
        saga.draw(cv, cv.comp, "wizard", at=(0, 0), end=D)


# -- the sets ---------------------------------------------------------------------------------------------------------
LOCATIONS = [
    (sets.space, {}),
    (sets.bridge, {}),
    (sets.cantina, {"stare": [(1.0, 2.0)]}),
    (sets.desert, {}),
    (sets.cockpit_front, {}),
    (sets.compactor, {"walls": (0.5, 2.0), "door": 2.5}),
]


@pytest.mark.parametrize(("location", "options"), LOCATIONS)
def test_locations_draw_both_signature_marks_only_when_signed(location, options):
    signed, unsigned = canvas(), canvas(signed=False)
    location(signed, signed.comp, end=D, **options)
    location(unsigned, unsigned.comp, end=D, **options)
    ids = [g.get("id") or "" for g in tree(signed).iter("group")]
    assert any(i.startswith("sig-cactus") for i in ids) and any(i.startswith("sig-code") for i in ids)
    assert not any(g.get("id", "").startswith("sig-") for g in tree(unsigned).iter("group"))


@pytest.mark.parametrize("name", sorted(sets.SETS))
def test_every_location_throws_its_far_plane_out_of_focus_and_keeps_the_signature_marks_sharp(name):
    cv = canvas()
    sets.SETS[name](cv, cv.comp, end=D)
    if name in sets.FRONTS:
        sets.FRONTS[name](cv, cv.comp, end=D)
    root = tree(cv)
    assert any("blur" in effect_types(root, g) for g in root.iter("group"))
    marks = [g for g in root.iter("group") if (g.get("id") or "").startswith("sig-")]
    assert len(marks) == 2
    for mark in marks:
        assert not any("blur" in effect_types(root, n) for n in ancestry(root, mark))


def test_location_events_must_fall_inside_the_shot():
    cv = canvas()
    with pytest.raises(SagaError):
        sets.cantina(cv, cv.comp, end=D, stare=[(2.0, 1.0)])
    with pytest.raises(SagaError):
        sets.compactor(cv, cv.comp, end=D, door=D + 1)
    with pytest.raises(SagaError):
        sets.compactor(cv, cv.comp, end=D, walls=(0, 1), travel=-5)
    with pytest.raises(SagaError):
        sets.cube_station(cv, cv.comp, at=(540, 800), end=D, boom=-1)


def test_the_cube_bursts_without_a_full_frame_flash():
    cv = canvas()
    sets.cube_station(cv, cv.comp, at=(540, 800), end=D, boom=1.0)
    big_white = [
        s
        for s in tree(cv).iter("shape")
        if s.get("fill", "").lower() in ("#ffffff", "#fff4dc") and float(s.get("width") or 0) >= 1080
    ]
    assert not big_white


# -- text and the hologram --------------------------------------------------------------------------------------------
@needs_font
def test_wrap_measures_every_line_and_refuses_what_does_not_fit():
    from srstudio import fonts

    lines = sets.wrap(font(), "Small hole. Goes straight to the reactor. Seems bad?", 44, 600, 4)
    assert len(lines) > 1 and all(fonts.text_width(font(), line, 44) <= 600 for line in lines)
    with pytest.raises(SagaError, match="lines"):
        sets.wrap(font(), "word " * 60, 44, 600, 3)
    with pytest.raises(SagaError, match="wider"):
        sets.wrap(font(), "Supercalifragilisticexpialidocious", 80, 300, 3)


@needs_font
def test_the_hologram_switches_panels_in_order_and_refuses_bad_ones():
    cv = canvas()
    panels = (Panel(0, "TICKET #4471", "Small hole."), Panel(1.5, "PRIORITY: LOW", tone="alert", face="seven"))
    groups = sets.holo(cv, cv.comp, panels, end=D, font=font())
    assert len(groups) == 2
    texts = [t.get("text") for t in tree(cv).iter("text")]
    assert "TICKET #4471" in texts and "PRIORITY: LOW" in texts
    for bad in (
        (Panel(1.0, "A"), Panel(0.5, "B")),
        (Panel(0, "A", tone="pink"),),
        (Panel(0, "A", face="wizard"),),
        (Panel(D + 1, "A"),),
        (),
    ):
        with pytest.raises(SagaError):
            sets.holo(canvas(), canvas().comp, bad, end=D, font=font())


def panel_rect(cv: Canvas) -> tuple[float, float]:
    """(top, bottom) of the first hologram panel drawn on ``cv``."""
    (r, *_) = [r for r in tree(cv).iter("shape") if r.get("fill") == sets.HOLO_FILL]
    return float(r.get("y")), float(r.get("y")) + float(r.get("height"))


@needs_font
def test_the_handbook_entry_is_as_tall_as_its_words_and_sits_above_the_caption_band():
    def case(body: str) -> tuple[float, float]:
        cv = canvas()
        sets.entry(cv, cv.comp, "Holes", body, end=D, font=font())
        (r,) = [r for r in tree(cv).iter("shape") if r.get("fill") == sets.ENTRY_CASE]
        return float(r.get("y")), float(r.get("y")) + float(r.get("height"))

    short, long = case("They are bad."), case("A custom older than the galaxy and twice as hard to leave. " * 3)
    assert short[1] - short[0] < 560 < long[1] - long[0]
    for top, bottom in (short, long):
        assert sets.SAFE[1] <= top and bottom <= sets.FLOOR


@needs_font
def test_the_hologram_is_as_tall_as_what_it_says_and_ends_above_the_cast_heads():
    def height(*panels: Panel) -> float:
        cv = canvas()
        sets.holo(cv, cv.comp, panels, end=D, font=font())
        top, bottom = panel_rect(cv)
        assert bottom <= sets.FLOOR - saga.HEIGHT - 20  # clear of a standing head
        return bottom - top

    short = height(Panel(0, "SKIP?", "No."))
    long = height(Panel(0, "INSTALLING UPDATE 1 OF 47", "Do not turn off your ship. Do not turn off your ship either."))
    assert short < long and short <= 200


@needs_font
def test_the_hologram_pops_in_about_its_own_centre_and_draws_nothing_below_itself():
    cv = canvas()
    sets.holo(cv, cv.comp, (Panel(0, "SKIP?", "No."),), end=D, font=font())
    pivots_stay_put(cv)
    _, bottom = panel_rect(cv)
    for shape in tree(cv).iter("shape"):
        assert float(shape.get("y", 0)) < bottom, shape.attrib
    pops = [a for a in tree(cv).iter("animate") if a.get("property") == "scaleY"]
    assert pops and float(next(pops[0].iter("key")).get("value")) < 0.2


# -- staging ----------------------------------------------------------------------------------------------------------
def staging_takes() -> list[Take]:
    return [
        take("01", "narrator", "Why is it?", 0, 1.5),
        take("02", "juno", "I know.", 1.5, 1.5),
        Take("03", "sfx", "", "[BOOM]", 3.0, 1.0),
    ]


GOOD = {
    "01": Stage("space", props=(Prop("cube", 540, 800),)),
    "02": Stage("desert", cast=(Place("juno", 540),)),
    "03": Stage(entry=Entry("Holes", "They are bad.")),
}


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"03": None}, "without a stage"),
        ({"02": Stage("moon", cast=(Place("juno", 540),))}, "unknown location"),
        ({"02": Stage("desert", cast=(Place("wizard", 540),))}, "not in the cast"),
        ({"02": Stage("desert", cast=(Place("rook", 540),))}, "juno speaks but is not on screen"),
        ({"02": Stage("desert", cast=(Place("juno", 540, behind=True),))}, "no front layer"),
        ({"02": Stage("desert", cast=(Place("juno", 540), Place("juno", 200)))}, "two places"),
        ({"01": Stage("space", props=(Prop("deathray", 0, 0),))}, "unknown prop"),
        ({"02": Stage("desert", cast=(Place("juno", 540),), panels=(Panel(9, "late"),))}, "outside"),
        ({"02": Stage("desert", cast=(Place("juno", 540),), move=Move("crash", 1.45, 1.4, 540, 600))}, "inside"),
        ({"02": Stage("desert", cast=(Place("juno", 540),), move=Move("dolly", 0.1, 1.4, 540, 600))}, "crash or"),
        ({"02": Stage("desert", cast=(Place("juno", 540),), dark=((1.0, 3.0),))}, "outside"),
        ({"03": Stage("desert", entry=Entry("a", "b"))}, "alone"),
    ],
)
def test_staging_that_does_not_fit_the_recording_is_refused(change, message):
    stages = {**GOOD, **change}
    stages = {k: v for k, v in stages.items() if v is not None}
    with pytest.raises(SagaError, match=message):
        reel.check(staging_takes(), stages)


def test_a_speaker_on_a_hologram_face_counts_as_seen():
    stages = {**GOOD, "02": Stage("compactor", panels=(Panel(0, "Facilities", face="juno"),))}
    reel.check(staging_takes(), stages)


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
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=330:duration={t.duration}",
                "-ar",
                "48000",
                "-ac",
                "1",
                str(root / f"audio/take-{t.id}.wav"),
            ],
            check=True,
        )
    total = round(takes[-1].start + takes[-1].duration, 3)
    (root / "timeline.json").write_text(json.dumps({"duration": total, "tempo_adjustment": 1.0, "items": items}))
    (root / "assets").mkdir(parents=True, exist_ok=True)
    assert FONT_FILE is not None
    shutil.copy(FONT_FILE, root / "assets" / "space-grotesk-700.ttf")


def episode(root: Path) -> Episode:
    return Episode(
        EpisodeSpec(
            slug="saga-test",
            title="Saga test",
            description="A Saga reel in the test suite.",
            root=root,
            seed=1,
            style=SAGA,
            language="en-US",
            font_family="DejaVu Sans",
            safe_area=VERTICAL,
        )
    )


@needs_font
def test_a_reel_builds_with_the_hook_the_entry_crossfade_captions_and_mix(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    write_project(tmp_path)
    ep = episode(tmp_path)
    stages = {
        **GOOD,
        "02": Stage("desert", cast=(Place("juno", 540),), move=Move("crash", 0.5, 1.3, 540, 900), shake=((0.2, 0.6),)),
    }
    made = reel.build(ep, stages, hook="Why is there a hole?", font=font())
    out = ep.finish(tmp_path / "saga-test.scene.xml", tmp_path / "qa" / "sdk.json", strict=False)
    root = ET.fromstring(out.read_bytes())
    assert [t.get("type") for t in root.iter("transition")] == ["crossfade"]
    assert root.find(".//captionTrack") is not None and made["captions"] is not None
    assert len(list(root.iter("audioTrack"))) == 3
    assert "Why is there a hole?" in [t.get("text") for t in root.iter("text")]
    shots = [g for g in root.iter("group") if (g.get("id") or "").startswith("shot-")]
    assert shots and all({"bloom", "vignette", "film-grain"} <= effect_types(root, g) for g in shots)
    found = shutil.which("scene-render") or __import__("os").environ.get("SRSTUDIO_ENGINE")
    if not found or not Path(found).exists():
        pytest.skip("set SRSTUDIO_ENGINE to a scene-render binary")
    check = subprocess.run([str(Path(found).resolve()), "validate", str(out)], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr


@needs_font
def test_the_narrator_badge_gives_way_to_a_hologram_so_the_two_never_overlap(tmp_path, monkeypatch):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    said = [take(i, "narrator", "It is bad.", k * 1.5, 1.5) for k, i in enumerate(("01", "02", "03"))]
    write_project(tmp_path, said)
    drawn: list[object] = []
    real = saga.handbook
    monkeypatch.setattr(saga, "handbook", lambda *a, **k: drawn.append(k["at"]) or real(*a, **k))
    stages = {"01": Stage("space"), "02": Stage("space", panels=(Panel(0, "TICKET"),)), "03": Stage("space")}
    reel.build(episode(tmp_path), stages, hook="Why?", font=font())
    assert len(drawn) == 2  # the hook's own and take 03's: 01 carries the hook, 02 the hologram


@needs_font
def test_a_narrated_line_too_long_for_one_caption_is_split_at_words_into_captions_that_fit(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    long = "Why are the walls of this trash compactor closing in on us today?"
    takes = [take("01", "narrator", long, 0, 4.2), take("02", "juno", "I know.", 4.2, 1.5),
             Take("03", "sfx", "", "[BOOM]", 5.7, 1.0)]  # fmt: skip
    write_project(tmp_path, takes)
    ep = episode(tmp_path)
    reel.build(ep, GOOD, hook="Why is there a hole?", font=font())
    texts = [text for _, _, text, _ in ep.caption_specs]
    assert len(texts) > 2 and " ".join(texts[:-1]) == long and texts[-1] == "I know."


@needs_font
def test_the_hologram_stays_out_of_the_camera_so_a_zoom_never_pushes_its_text_out_of_the_safe_area(tmp_path):
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg writes the test takes")
    write_project(tmp_path)
    ep = episode(tmp_path)
    zoomed = Stage("desert", cast=(Place("juno", 540),), panels=(Panel(0, "PRIORITY: NICE TO HAVE", "Seems bad?"),),
                   move=Move("crash", 0.2, 1.3, 540, 900))  # fmt: skip
    reel.build(ep, {**GOOD, "02": zoomed}, hook="Why?", font=font())
    out = ep.finish(tmp_path / "saga-test.scene.xml", tmp_path / "qa" / "sdk.json", strict=False)
    parents = {c: p for p in ET.fromstring(out.read_bytes()).iter() for c in p}

    def moved(node) -> bool:
        while node in parents:
            node = parents[node]
            for a in node.findall("animate"):  # a zoom in; the panel's own pop-in never passes 1
                if a.get("property", "").startswith("scale") and max(float(k.get("value")) for k in a.iter("key")) > 1:
                    return True
        return False

    (body,) = [t.get("id") for t in parents if t.tag == "text" and t.get("text") == "Seems bad?"]
    layers = [n for n in parents if n.tag == "layer" and n.get("asset") == body]
    assert layers and not any(moved(n) for n in layers)


def contrast(a: str, b: str) -> float:
    def lum(hex_: str) -> float:
        c = [int(hex_[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        r, g, b_ = (x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b_

    hi, lo = sorted((lum(a), lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_the_cast_stands_above_the_caption_band_and_every_front_layer_has_a_line_to_stand_behind():
    from srstudio import native

    band_top = sets.SAFE[3] - native.CAPTION_LOOK.block
    assert sets.FLOOR <= band_top
    assert set(sets.BEHIND) == set(sets.FRONTS)


def test_hologram_text_reads_at_4_5_to_1_on_an_opaque_panel_whatever_is_behind_it():
    assert all(contrast(tone, sets.HOLO_FILL) >= 4.5 for tone in sets.TONES.values())
    assert contrast("#fff4dc", sets.HOLO_FILL) >= 4.5
    cv = canvas()
    sets.holo(cv, cv.comp, (Panel(0, "SKIP?", "No."),), end=D, font=font())
    panels = [r for r in tree(cv).iter("shape") if r.get("fill") == sets.HOLO_FILL]
    assert panels and all(float(r.get("opacity", "1")) == 1.0 for r in panels)


def test_the_pebble_floats_up_from_its_lift_and_must_lift_inside_the_shot():
    cv = canvas()
    sets.pebble(cv, cv.comp, at=(700, 1480), end=D, lift=1.0)
    (y,) = [a for a in tree(cv).iter("animate") if a.get("property") == "y"]
    keys = [(float(k.get("time")), float(k.get("value"))) for k in y.iter("key")]
    assert keys[0][1] == keys[1][1] == 1480 and keys[1][0] == 1.0 and keys[-1][1] < 1480
    with pytest.raises(SagaError):
        sets.pebble(cv, cv.comp, at=(700, 1480), end=D, lift=D)


def test_the_compactor_walls_resume_where_the_last_shot_left_them():
    cv = canvas()
    sets.compactor(cv, cv.comp, end=D, walls=(0.0, 2.0), travel=60, start_px=40)
    xs = [
        [(float(k.get("time")), float(k.get("value"))) for k in a.iter("key")]
        for a in tree(cv).iter("animate")
        if a.get("property") == "x"
    ]
    assert sorted(x[-1][1] for x in xs) == [-100.0, 100.0] and sorted(x[0][1] for x in xs) == [-40.0, 40.0]
    with pytest.raises(SagaError):
        sets.compactor(cv, cv.comp, end=D, walls=(0.0, 1.0), travel=200, start_px=200)


@needs_font
@pytest.mark.parametrize("start", [-0.5, True, float("nan")])
def test_a_hologram_panel_starts_at_a_number_of_seconds_from_zero(start):
    with pytest.raises(SagaError, match="must rise inside the shot"):
        sets.holo(canvas(), canvas().comp, (Panel(start, "A"),), end=D, font=font())


@pytest.mark.parametrize("end", [True, float("nan"), 0, -1])
def test_a_set_is_drawn_for_a_number_of_seconds_above_zero(end):
    cv = canvas()
    with pytest.raises(SagaError, match="more than 0 s"):
        sets.space(cv, cv.comp, end=end)


def test_a_set_span_past_the_end_is_cut_at_it_and_a_bool_is_no_second():
    cv = canvas()
    sets.cantina(cv, cv.comp, end=2.0, stare=[(1.0, 9.0)])
    with pytest.raises(SagaError, match="must rise from a second >= 0"):
        sets.cantina(canvas(), canvas().comp, end=2.0, stare=[(True, 1.5)])

"""The staged-reel toolkit every sequence style shares (srstudio.staging): the stage checks, the camera rig, the
blackout, the crossfade into a closing card, and the captions and mix that close a reel."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from types import SimpleNamespace

import pytest
from sr_core.scene import Scene

from srstudio import VOID, Canvas, flat_counter, native, staging
from srstudio.staging import Move, StagingError


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=4.0, background=VOID.background)
    return Canvas(scene, VOID, font_asset="f", namer=flat_counter("s"))


def take(id: str, duration: float = 2.0, actor: str = "juno", effect: bool = False):
    return SimpleNamespace(id=id, duration=duration, actor=actor, is_effect=effect)


class StyleError(ValueError):
    pass


# -- checks -----------------------------------------------------------------------------------------------------------
def test_every_take_needs_a_stage_and_every_stage_a_take():
    staging.check_cover([take("01"), take("02")], {"01": 0, "02": 0})
    with pytest.raises(StyleError, match=r"without a stage \['02'\], stages without a take \['03'\]"):
        staging.check_cover([take("01"), take("02")], {"01": 0, "03": 0}, StyleError)


@pytest.mark.parametrize(
    "move",
    [
        Move("crash", 0.5, 1.4, 540, 900),
        Move("crash", 0.5, 1.4, 540, 900, back=1.5),
        Move("push", 0.0, 1.1, 540, 900, until=2.0),
    ],
)
def test_a_crash_or_a_push_that_ends_inside_the_take_is_accepted(move):
    staging.check_move(move, 2.0, "take 01")


@pytest.mark.parametrize(
    "move, message",
    [
        (Move("spin", 0.5, 1.4, 540, 900), "crash or a push, not 'spin'"),
        (Move("push", 0.5, 1.4, 540, 900), "must end inside"),
        (Move("push", 0.5, 1.4, 540, 900, until=2.5), "must end inside"),
        (Move("crash", 1.95, 1.4, 540, 900), "must end inside"),
        (Move("crash", float("nan"), 1.4, 540, 900), "must end inside"),
        (Move("crash", 0.5, float("nan"), 540, 900), "scale"),
        (Move("crash", 0.5, -2, 540, 900), "scale"),
        (Move("push", 0.0, 0, 540, 900, until=2.0), "scale"),
        (Move("crash", 0.5, 1.4, float("inf"), 900), "aims"),
        (Move("crash", 0.5, 1.4, 540, float("nan")), "aims"),
    ],
)
def test_a_move_that_is_unknown_or_overruns_its_take_is_refused_with_the_styles_error(move, message):
    with pytest.raises(StyleError, match=message):
        staging.check_move(move, 2.0, "take 01", StyleError)


def test_spans_fall_inside_the_take():
    staging.check_spans([(0.0, 1.0), (1.5, 2.0)], 2.0, "take 01")
    for bad in [(1.0, 1.0), (-0.1, 1.0), (1.0, 2.5), (float("inf"), 3.0)]:
        with pytest.raises(StagingError, match="falls outside the take"):
            staging.check_spans([bad], 2.0, "take 01")


def test_ordered_spans_refuse_one_that_starts_before_the_last_ends():
    staging.check_spans([(0.0, 1.0), (1.0, 2.0)], 2.0, "take 01", ordered=True)
    for spans in [[(0.0, 1.0), (0.5, 1.5)], [(1.0, 2.0), (0.0, 0.5)]]:
        staging.check_spans(spans, 2.0, "take 01")  # a blackout may overlap itself
        with pytest.raises(StagingError, match="take 01: span .* overlaps the one before"):
            staging.check_spans(spans, 2.0, "take 01", ordered=True)


def test_the_default_error_is_a_value_error():
    assert issubclass(StagingError, ValueError)


# -- drawing ----------------------------------------------------------------------------------------------------------
def node(root: ET.Element, id: str) -> ET.Element:
    return next(n for n in root.iter() if n.get("id") == id)


def keys(element: ET.Element, prop: str) -> list[tuple[float, float]]:
    return [
        (float(k.get("time")), float(k.get("value")))
        for a in element.findall("animate")
        if a.get("property") == prop
        for k in a.iter("key")
    ]


def test_a_still_rig_is_two_plain_groups():
    cv = canvas()
    shaken = staging.rig(cv, cv.comp, None, ())
    root = ET.fromstring(cv.scene.to_bytes())
    frame = next(n for n in root.iter("group") if any(c.get("id") == shaken.id for c in n))
    assert not list(root.iter("animate"))
    assert frame.get("id") != shaken.id


def test_a_named_rig_frame_takes_its_name_and_no_serial_id():
    cv = canvas()
    shaken = staging.rig(cv, cv.comp, Move("push", 0.5, 1.2, 540, 900, until=1.5), (), name="gloss-01-angle")
    root = ET.fromstring(cv.scene.to_bytes())
    frame = next(n for n in root.iter("group") if any(c.get("id") == shaken.id for c in n))
    assert frame.get("id") == "gloss-01-angle"
    assert keys(frame, "scaleX")[-1] == (1.5, 1.2)
    named, plain = canvas(), canvas()
    staging.rig(named, named.comp, None, (), name="still")
    staging.rig(plain, plain.comp, None, ())
    fresh = canvas()
    serials = [fresh.uid("g") for _ in range(3)]
    assert (named.uid("g"), plain.uid("g")) == (serials[1], serials[2])  # the name took no serial: later ids stay put
    with pytest.raises(TypeError):
        staging.rig(named, named.comp, None, (), "positional")  # type: ignore[misc]


def test_the_rig_moves_its_frame_and_shakes_its_inner_group():
    cv = canvas()
    shaken = staging.rig(cv, cv.comp, Move("push", 0.5, 1.2, 540, 900, until=1.5), ((0.2, 0.6),))
    root = ET.fromstring(cv.scene.to_bytes())
    frame = next(n for n in root.iter("group") if any(c.get("id") == shaken.id for c in n))
    assert keys(frame, "scaleX")[-1] == (1.5, 1.2)
    assert keys(node(root, shaken.id), "x")[-1] == (0.6, 0.0)


def test_a_crash_rig_snaps_in():
    cv = canvas()
    shaken = staging.rig(cv, cv.comp, Move("crash", 0.5, 1.4, 540, 900, back=1.5), ())
    root = ET.fromstring(cv.scene.to_bytes())
    frame = next(n for n in root.iter("group") if any(c.get("id") == shaken.id for c in n))
    assert max(v for _, v in keys(frame, "scaleX")) == pytest.approx(1.4)


def test_the_shake_settles_to_rest_at_the_end_of_each_span():
    cv = canvas()
    g = cv.group(cv.comp, "g")
    staging.shake(cv, g, ((0.5, 1.0), (1.5, 1.75)))
    xs = keys(node(ET.fromstring(cv.scene.to_bytes()), "g"), "x")
    assert xs[0] == (0.0, 0.0)
    assert (1.0, 0.0) in xs and (1.75, 0.0) in xs
    assert max(abs(v) for _, v in xs) == staging.SHAKE_PX


@pytest.mark.parametrize("span", [(1.0, 1.05), (1.0, 1.0 + staging.SHAKE_STEP), (1.0, 1.1)])
def test_a_shake_shorter_than_its_swings_still_settles_at_its_end(span):
    cv = canvas()
    g = cv.group(cv.comp, "g")
    staging.shake(cv, g, (span,))
    xs = keys(node(ET.fromstring(cv.scene.to_bytes()), "g"), "x")
    times = [t for t, _ in xs]
    assert times == sorted(set(times)) and xs[-1] == (round(span[1], 4), 0.0)
    assert all(t < span[1] for t, v in xs if v)


@pytest.mark.parametrize("spans", [((0.0, 0.5), (0.25, 0.6)), ((1.0, 1.5), (0.0, 0.5))])
def test_shakes_that_overlap_or_run_backwards_are_refused(spans):
    cv = canvas()
    with pytest.raises(StagingError, match="overlaps the one before"):
        staging.shake(cv, cv.group(cv.comp, "g"), spans)


def test_a_blackout_covers_the_frame_only_in_its_spans_and_is_absent_without_spans():
    cv = canvas()
    g = cv.group(cv.comp, "g")
    assert staging.blackout(cv, g, ()) is None
    black = staging.blackout(cv, g, ((0.4, 1.0),))
    assert black is not None
    assert (black.x, black.y, black.width, black.height) == (-200, -200, 1480, 2320)


# -- freezing ---------------------------------------------------------------------------------------------------------
def test_a_frozen_shot_holds_every_animated_property_at_its_value_at_the_shot_start():
    cv = canvas()
    shot = cv.group(cv.comp, "shot")
    breath = cv.group(shot, "breath")
    cv.keys(breath, "y", [(0, 0), (1.2, -5), (2.4, 0)], kind="sine-in-out")
    late = cv.group(shot, "late")
    cv.keys(late, "opacity", [(0.6, 0.2), (1.4, 1)])  # before its first key, a property holds that key's value
    gated = cv.group(shot, "gated")
    cv.gate(gated, [(0.5, 1.0)])
    staging.freeze(shot)
    root = ET.fromstring(cv.scene.to_bytes())
    assert not list(root.iter("animate"))
    found = {n.get("id"): n for n in root.iter() if n.get("id") in ("breath", "late", "gated")}
    assert float(found["breath"].get("y")) == 0 and float(found["late"].get("opacity")) == 0.2
    assert float(found["gated"].get("opacity")) == 0  # a gate shut at the start keeps it hidden


def test_a_shot_with_a_text_animator_or_an_expression_cannot_be_frozen():
    cv = canvas()
    shot = cv.group(cv.comp, "shot")
    cv.animate_text(cv.text(shot, "t", "Typed", 0, 0, 200, 60, 40), "typewriter", presetStart=0.2)
    with pytest.raises(StagingError, match="textAnimator"):
        staging.freeze(shot)
    cv = canvas()
    shot = cv.group(cv.comp, "shot")
    cv.expression(cv.group(shot, "g"), "x", "time * 10")
    with pytest.raises(StagingError, match="expression"):
        staging.freeze(shot)


# -- closing ----------------------------------------------------------------------------------------------------------
def test_the_closing_card_is_crossfaded_into_at_most_half_of_either_shot():
    takes = [take("01", 2.0), take("02", 0.4), take("03", 3.0), take("04", 2.0)]
    closing = {"03", "04"}
    assert staging.crossfades(takes, lambda id: id in closing) == {"03": 0.2}
    assert staging.crossfades([take("01", 2.0), take("02", 2.0)], lambda id: id == "02") == {"02": 0.3}
    assert staging.crossfades(takes, lambda id: False) == {}


def test_close_captions_the_takes_and_mixes_them_with_the_bed_ducked_under_speech():
    calls = {}

    class FakeEpisode:
        t = SimpleNamespace(meta={"music": {"file": "audio/bed.wav", "gain_db": -16.0}})

        def native_captions(self, cues, look):
            calls["captions"] = (cues, look)
            return "captions-node"

        def audio(self, *, take, extra, duck):
            calls["audio"] = ([take(t) for t in recorded], extra, duck)
            return "mix-node"

    recorded = [take("01", actor="juno"), take("02", actor="gloom")]
    look = native.CaptionLook(min_last=2)
    out = staging.close(FakeEpisode(), None, [], fades={}, look=look, pans={"gloom": -0.06}, duck=-9.0)
    assert out == {"captions": "captions-node", "mix": "mix-node"}
    assert calls["captions"] == ([], look)
    params, extra, duck = calls["audio"]
    assert [p["pan"] for p in params] == [0.0, -0.06]
    assert extra == [("music", "audio/bed.wav", {"role": "music", "gain": "-16.0"})]
    assert duck == -9.0


def test_close_without_a_bed_mixes_no_music_and_ducks_nothing():
    class FakeEpisode:
        t = SimpleNamespace(meta={})

        def native_captions(self, cues, look):
            return "c"

        def audio(self, *, take, extra, duck):
            return (extra, duck)

    out = staging.close(FakeEpisode(), None, [], fades={}, look=native.CAPTION_LOOK, pans={}, duck=-9.0)
    assert out["mix"] == ([], None)

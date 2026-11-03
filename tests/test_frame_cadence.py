"""Every held key shows on the frame it was keyed for: none held over by a 6-decimal write, none skipped."""

from __future__ import annotations

import pytest

from srstudio import frame_cadence as fc
from srstudio.errors import SrstudioError
from srstudio.frame_cadence import HELD_OVER, SKIPPED, CadenceError, check, read

FPS = 30


def scene(body: str, *, frames: int = 12, fps: int = FPS) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n<scene version="1.1">'
        f'<project width="100" height="100" fps="{fps}" duration="{frames / fps}"/>'
        f"<composition>{body}</composition></scene>"
    )


def track(times: list[float], *, prop: str = "x", interp: str = "hold", node: str = "dev-arm", extra: str = "") -> str:
    keys = "".join(f'<key time="{t:.6f}" value="{i}"/>' for i, t in enumerate(times))
    return (
        f'<group id="{node}">{extra}<animate property="{prop}" defaultInterpolation="{interp}">{keys}</animate></group>'
    )


def on_frames(n: int) -> list[float]:
    """One key per frame at f / 30, as a driver keying ``begin + i / FPS`` from 0 writes it."""
    return [round(f / FPS, 6) for f in range(n)]


def centres(n: int) -> list[float]:
    """One key per frame at the frame's centre, (f - 0.5) / 30."""
    return [(f - 0.5) / FPS for f in range(n)]


def test_keys_at_frame_centres_are_clean():
    report = check(scene(track(centres(12))))
    assert report.clean
    assert report.findings == ()
    assert report.frames == 12
    assert report.tracks == 1


def test_a_key_written_past_its_frame_is_held_over_and_skipped():
    report = check(scene(track(on_frames(12))))
    assert not report.clean
    # f / 30 rounds up past the frame's own time when f mod 3 = 2 (2/30 = 0.0666666... is written 0.066667)
    assert report.frames_flagged() == (2, 5, 8, 11)
    held = [f for f in report.findings if f.kind == HELD_OVER]
    assert [(f.frame, f.shown, f.intended) for f in held] == [(2, 1, 2), (5, 4, 5), (8, 7, 8), (11, 10, 11)]
    skipped = [f for f in report.findings if f.kind == SKIPPED]
    assert [(f.frame, f.intended) for f in skipped] == [(2, 2), (5, 5), (8, 8), (11, 11)]
    assert {f.owner for f in report.findings} == {"dev-arm"}
    assert {f.prop for f in report.findings} == {"x"}


def test_an_interpolated_track_is_not_judged():
    report = check(scene(track(on_frames(12), interp="linear")))
    assert report.clean
    assert report.tracks == 0


def test_a_key_that_interpolates_out_is_not_judged_inside_a_held_track():
    keys = "".join(
        f'<key time="{t:.6f}" value="{i}"' + (' interpolation="linear"/>' if i == 1 else "/>")
        for i, t in enumerate(on_frames(4))
    )
    body = f'<group id="g"><animate property="x" defaultInterpolation="hold">{keys}</animate></group>'
    report = check(scene(body, frames=4))
    # frame 2 still shows key 1, but key 1 eases into key 2, so the frame is within a write's rounding of key 2
    assert report.clean


def test_a_held_key_that_does_not_change_the_value_is_not_a_finding():
    keys = "".join(f'<key time="{t:.6f}" value="7"/>' for t in on_frames(6))
    body = f'<group id="g"><animate property="x" defaultInterpolation="hold">{keys}</animate></group>'
    assert check(scene(body, frames=6)).clean


def test_a_hidden_node_is_not_judged():
    gate = '<animate property="opacity" defaultInterpolation="hold"><key time="0" value="0"/></animate>'
    report = check(scene(f'<group id="gate">{gate}{track(on_frames(12))}</group>'))
    assert report.clean


def test_a_gate_that_opens_shows_only_its_visible_frames():
    gate = (
        '<animate property="opacity" defaultInterpolation="hold">'
        '<key time="0" value="0"/><key time="0.2" value="1"/></animate>'
    )
    report = check(scene(f'<group id="gate">{gate}{track(on_frames(12))}</group>'))
    # frames 0-5 are hidden (0.2 s is frame 6): frame 2 and 5 are not judged, 8 and 11 are
    assert report.frames_flagged() == (8, 11)


def test_static_opacity_zero_and_visible_false_hide_a_node():
    for attr in ('opacity="0"', 'visible="false"'):
        body = f'<group id="outer" {attr}>{track(on_frames(12))}</group>'
        assert check(scene(body)).clean, attr


def test_an_interpolated_opacity_counts_as_visible_while_either_end_is():
    fade = (
        '<animate property="opacity" defaultInterpolation="linear">'
        '<key time="0" value="0"/><key time="0.4" value="1"/></animate>'
    )
    report = check(scene(f'<group id="fade">{fade}{track(on_frames(12))}</group>'))
    # frame 0 is exactly at the 0 key: hidden; every frame after it is mid-fade or past it
    assert report.frames_flagged() == (2, 5, 8, 11)


def test_owner_is_the_nearest_named_node():
    body = '<group id="noor-join-5"><group id="n42">' + track(on_frames(3), node="n43") + "</group></group>"
    report = check(scene(body, frames=3))
    assert {f.owner for f in report.findings} == {"noor-join-5"}
    assert {f.node for f in report.findings} == {"n43"}


def test_owner_of_an_unnamed_root_track():
    body = '<group id="n1">' + track(on_frames(3), node="n2") + "</group>"
    report = check(scene(body, frames=3))
    assert {f.owner for f in report.findings} == {""}


def test_frames_before_the_first_key_hold_the_first_key():
    report = check(scene(track([0.1 + (f - 0.5) / FPS for f in range(6)]), frames=9))
    assert report.clean


def test_frames_flagged_by_owner():
    body = track(on_frames(6), node="dev") + track(centres(6), node="noor")
    report = check(scene(body, frames=6))
    assert report.frames_flagged("dev") == (2, 5)
    assert report.frames_flagged("noor") == ()
    assert report.owners() == ("dev",)


def test_read_returns_the_held_tracks():
    parsed = read(scene(track(centres(3)) + track(centres(3), interp="linear", node="lin"), frames=3))
    assert parsed.fps == 30.0
    assert parsed.frames == 3
    assert [t.owner for t in parsed.tracks] == ["dev-arm"]
    assert all(k.held for k in parsed.tracks[0].keys)


def test_bytes_input_is_read():
    assert check(scene(track(centres(3)), frames=3).encode()).clean


@pytest.mark.parametrize(
    ("xml", "code"),
    [
        ("<scene", "cadence.xml"),
        ("<notascene/>", "cadence.root"),
        ('<scene version="1.1"><composition/></scene>', "cadence.project"),
        ('<scene version="1.1"><project fps="0" duration="1"/></scene>', "cadence.project"),
        ('<scene version="1.1"><project fps="30" duration="nan"/></scene>', "cadence.project"),
        ('<scene version="1.1"><project fps="30"/></scene>', "cadence.project"),
        (scene('<group id="g"><animate property="x" defaultInterpolation="hold"></animate></group>'), "cadence.keys"),
        (scene('<group id="g"><animate property="x"><key time="x" value="1"/></animate></group>'), "cadence.time"),
        (scene('<group id="g"><animate property="x"><key time="inf" value="1"/></animate></group>'), "cadence.time"),
        (scene('<group id="g"><animate property="x"><key value="1"/></animate></group>'), "cadence.time"),
        (
            scene(
                '<group id="g"><animate property="x"><key time="0.2" value="1"/>'
                '<key time="0.1" value="2"/></animate></group>'
            ),
            "cadence.order",
        ),
        (
            scene('<group id="g"><animate property="x" timeBase="local"><key time="0" value="1"/></animate></group>'),
            "cadence.timebase",
        ),
        (
            scene('<group id="g"><animate property="opacity"><key time="0" value="half"/></animate></group>'),
            "cadence.value",
        ),
        (scene('<group id="g" opacity="dim"/>'), "cadence.value"),
    ],
)
def test_malformed_input_raises_a_typed_error(xml, code):
    with pytest.raises(CadenceError) as err:
        check(xml)
    assert err.value.to_dict()["code"] == code
    assert isinstance(err.value, SrstudioError)
    assert isinstance(err.value, ValueError)


def test_a_non_string_input_raises_a_typed_error():
    with pytest.raises(CadenceError) as err:
        check(42)  # type: ignore[arg-type]
    assert err.value.to_dict()["code"] == "cadence.input"


def test_an_adversarial_late_key_one_microsecond_past_its_frame():
    # 2/30 written as 0.066668: still within a write's rounding of frame 2? no, 1.33 us past it, so out of tolerance
    # and keyed for frame 3; the frame shows key 1, as intended
    times = [0.0, round(1 / FPS, 6), 0.066668, round(3 / FPS, 6)]
    report = check(scene(track(times), frames=4))
    assert report.clean
    assert fc.WRITE_TOL == pytest.approx(5e-7)


# --- the rendered rhythm: per-frame change, grouped by frame mod 3, even in every shot ---


def wave(first: int, last: int, *, held: bool = False) -> dict[int, float]:
    """A per-frame change that varies smoothly; ``held`` makes every f = 2 mod 3 frame a hold (near no change) and the
    frame after it a double step."""
    out = {}
    for f in range(first, last + 1):
        base = 1000.0 + 300.0 * ((f * 7) % 11) / 10
        if held and f % 3 == 2:
            base = 60.0
        elif held and f % 3 == 0:
            base *= 2
        out[f] = base
    return out


def test_an_even_rhythm_passes_in_every_shot():
    change = {**wave(0, 97), **wave(98, 195)}
    report = fc.even_change(change, [(0, 97), (98, 195)])
    assert report.clean
    assert [s.even for s in report.shots] == [True, True]
    assert all(s.ratio is not None and s.ratio > 0.8 for s in report.shots)
    assert report.shots[0].counts == (32, 33, 32)


def test_a_hold_every_third_frame_fails_its_shot_and_not_the_control():
    change = {**wave(0, 97, held=True), **wave(98, 195)}
    report = fc.even_change(change, [(0, 97), (98, 195)])
    assert not report.clean
    first, control = report.shots
    assert first.even is False
    assert first.ratio is not None and first.ratio < 0.1
    assert first.medians[2] == 60.0
    assert control.even is True
    assert report.failing() == (0,)


def test_the_change_across_a_cut_is_not_counted():
    change = {**wave(0, 97), **wave(98, 195)}
    change[98] = 0.0  # a cut can change anything; it is not a step of the motion
    report = fc.even_change(change, [(0, 97), (98, 195)])
    assert report.shots[1].first == 98
    assert sum(report.shots[1].counts) == 97


def test_a_shot_too_short_to_judge_is_reported_unjudged():
    change = {**wave(0, 97), **wave(98, 110)}
    report = fc.even_change(change, [(0, 97), (98, 110)])
    assert report.shots[1].even is None
    assert report.shots[1].ratio is None
    assert report.clean


def test_nothing_judged_is_not_clean():
    report = fc.even_change(wave(0, 10), [(0, 10)])
    assert report.shots[0].even is None
    assert not report.clean


def test_a_still_shot_is_even():
    report = fc.even_change({f: 0.0 for f in range(0, 60)}, [(0, 59)])
    assert report.shots[0].even is True
    assert report.shots[0].ratio == 1.0


@pytest.mark.parametrize(
    ("change", "shots", "code"),
    [
        ({0: 1.0, 1: float("nan")}, [(0, 1)], "rhythm.change"),
        ({0: 1.0, 1: -2.0}, [(0, 1)], "rhythm.change"),
        ({0: 1.0, 1: True}, [(0, 1)], "rhythm.change"),
        ({0: 1.0}, [(0, 3)], "rhythm.missing"),
        ({f: 1.0 for f in range(10)}, [(5, 2)], "rhythm.shots"),
        ({f: 1.0 for f in range(10)}, [(0, 5), (4, 9)], "rhythm.shots"),
        ({f: 1.0 for f in range(10)}, [], "rhythm.shots"),
        ({f: 1.0 for f in range(10)}, [(0, "9")], "rhythm.shots"),
    ],
)
def test_malformed_rhythm_input_raises_a_typed_error(change, shots, code):
    with pytest.raises(CadenceError) as err:
        fc.even_change(change, shots)
    assert err.value.to_dict()["code"] == code

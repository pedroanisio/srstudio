"""The master's levels (ADR 0172): illegal codes, out-of-gamut and oversaturated samples fail at 0; clipping is
reported, never gated. Every malformed engine answer is a typed error, never a pass."""

from __future__ import annotations

import copy
import json
import math
import stat
import subprocess
from pathlib import Path

import pytest

from srstudio import scopes
from srstudio.cli import main
from srstudio.errors import SrstudioError


def envelope(*, illegal: float | None = 0.0, gamut: float = 0.0, above: float = 0.0, white: float = 0.0) -> dict:
    """The shape ``scene-render scopes --format json`` prints, trimmed to what a check reads plus some it ignores."""
    channels = {"r": 0.0, "g": 0.0, "b": 0.0, "y": 0.0}
    return {
        "format": "scene-render-cli/1",
        "command": "scopes",
        "ok": True,
        "exit_code": 0,
        "error": None,
        "diagnostics": [],
        "result": {
            "schema": "scene-render-scopes/1",
            "file": "renders/reel.mp4",
            "frames": {"analysed": 128, "step": 5},
            "levels": {
                "clipping": {"black": dict(channels), "white": {**channels, "r": white}},
                "float_range": None,
                "illegal": illegal,
                "legal": {"depth": 8, "y": [16, 235], "c": [16, 240]},
                "samples": 265420800,
                "saturation": {
                    "above_limit": above,
                    "chroma_limit": 0.4467,
                    "max_chroma": 0.3514,
                    "out_of_gamut": gamut,
                },
            },
            "scopes": {"histogram": {"bins": 32}},
            "source": {"matrix": "BT.709", "depth": 8},
        },
    }


def text(data: dict) -> str:
    return json.dumps(data)


def test_a_clean_master_passes_and_its_measures_are_read():
    levels = scopes.parse(text(envelope(white=0.035)))
    assert levels == scopes.Levels(
        file="renders/reel.mp4", frames=128, step=5, illegal=0.0, out_of_gamut=0.0, oversaturated=0.0, clipped=0.035
    )
    assert scopes.judge(levels) == ()


@pytest.mark.parametrize(
    ("given", "measure", "value"),
    [
        ({"illegal": 0.00102}, "illegal", 0.00102),
        ({"gamut": 0.000372}, "out_of_gamut", 0.000372),
        ({"above": 1e-9}, "oversaturated", 1e-9),
    ],
)
def test_any_illegal_out_of_gamut_or_oversaturated_sample_fails_at_the_default_limit_of_zero(given, measure, value):
    found = scopes.judge(scopes.parse(text(envelope(**given))))
    assert found == (scopes.Finding(measure, value, 0.0),)
    assert measure in str(found[0]) and "%" in str(found[0])


def test_clipping_is_reported_and_never_gated():
    levels = scopes.parse(text(envelope(white=0.5)))
    assert scopes.judge(levels) == () and "clipped 50" in scopes.summary(levels)


def test_a_source_without_a_legal_range_has_no_illegal_measure_and_says_so():
    levels = scopes.parse(text(envelope(illegal=None)))
    assert levels.illegal is None and scopes.judge(levels) == ()
    assert "illegal n/a" in scopes.summary(levels)


def test_several_findings_are_all_named():
    found = scopes.judge(scopes.parse(text(envelope(illegal=0.1, gamut=0.2, above=0.3))))
    assert [f.measure for f in found] == ["illegal", "out_of_gamut", "oversaturated"]


def test_limits_are_finite_fractions():
    assert scopes.judge(scopes.parse(text(envelope(illegal=0.1))), scopes.Limits(illegal=0.2)) == ()
    for bad in (-0.1, math.nan, math.inf, 1.5):
        with pytest.raises(scopes.ScopesError, match="limit"):
            scopes.Limits(out_of_gamut=bad)


def _broken(path: tuple[str, ...], value: object) -> str:
    data = copy.deepcopy(envelope())
    holder = data
    for key in path[:-1]:
        holder = holder[key]
    if value is KeyError:
        del holder[path[-1]]
    else:
        holder[path[-1]] = value
    return text(data)


@pytest.mark.parametrize(
    ("raw", "said"),
    [
        ("", "not JSON"),
        ("not json {", "not JSON"),
        ("[]", "not an object"),
        (_broken(("format",), "scene-render-cli/2"), "format"),
        (_broken(("command",), "inspect"), "command"),
        (_broken(("ok",), False), "failed"),
        (_broken(("exit_code",), 3), "failed"),
        (_broken(("result", "schema"), "scene-render-scopes/2"), "schema"),
        (_broken(("result", "levels"), KeyError), "levels"),
        (_broken(("result", "levels", "saturation", "out_of_gamut"), KeyError), "out_of_gamut"),
        (_broken(("result", "levels", "saturation", "above_limit"), "0"), "above_limit"),
        (_broken(("result", "levels", "illegal"), -0.1), "illegal"),
        (_broken(("result", "levels", "illegal"), 1.01), "illegal"),
        (_broken(("result", "levels", "saturation", "out_of_gamut"), True), "out_of_gamut"),
        (_broken(("result", "levels", "clipping", "white", "r"), float("nan")), "clipping"),
        (_broken(("result", "levels", "clipping", "white"), {}), "clipping"),
        (_broken(("result", "frames", "analysed"), 0), "frames"),
        (_broken(("result", "file"), 7), "file"),
    ],
)
def test_a_malformed_answer_is_a_typed_error_never_a_pass(raw, said):
    with pytest.raises(scopes.ScopesError, match=said) as raised:
        scopes.parse(raw)
    assert isinstance(raised.value, SrstudioError) and raised.value.to_dict()["code"].startswith("scopes.")


def test_measure_runs_the_engine_read_only_with_the_step():
    seen = []

    def run(command, **_kw):
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, text(envelope()), "")

    assert scopes.measure(Path("renders/reel.mp4"), engine="scene-render", run=run).frames == 128
    assert seen == [["scene-render", "scopes", "renders/reel.mp4", "--step", "5", "--format", "json"]]


def test_an_engine_that_cannot_run_or_fails_is_a_typed_error(tmp_path):
    def missing(command, **_kw):
        raise FileNotFoundError(2, "No such file", command[0])

    with pytest.raises(scopes.ScopesError, match="cannot run"):
        scopes.measure(tmp_path / "a.mp4", engine="nowhere", run=missing)

    def refuses(command, **_kw):
        return subprocess.CompletedProcess(command, 2, "", "no such video")

    with pytest.raises(scopes.ScopesError, match="no such video"):
        scopes.measure(tmp_path / "a.mp4", engine="scene-render", run=refuses)
    with pytest.raises(scopes.ScopesError, match="step"):
        scopes.measure(tmp_path / "a.mp4", engine="scene-render", step=0, run=refuses)


def fake_engine(tmp_path: Path, data: dict, code: int = 0) -> Path:
    answer = tmp_path / f"answer-{abs(hash(text(data)))}.json"
    answer.write_text(text(data))
    engine = tmp_path / f"engine-{abs(hash(text(data)))}-{code}"
    engine.write_text(f'#!/bin/sh\n[ "$1" = scopes ] || exit 9\ncat "{answer}"\nexit {code}\n')
    engine.chmod(engine.stat().st_mode | stat.S_IXUSR)
    return engine


def test_the_gate_names_each_first_delivery_that_fails_and_leaves_the_rest(tmp_path):
    renders = tmp_path / "renders"
    renders.mkdir()
    for name in ("clean", "dirty"):
        (renders / f"{name}.mp4").write_bytes(b"video")

    def run(command, **_kw):
        dirty = Path(command[2]).stem == "dirty"
        return subprocess.CompletedProcess(command, 0, text(envelope(illegal=0.001 if dirty else 0.0)), "")

    drift = scopes.scope_defects(renders, {"a": "clean", "b": "dirty", "c": "absent"}, "scene-render", run=run)
    assert [d.name for d in drift] == ["dirty", "absent"]
    assert "illegal 0.1" in drift[0].reason and "no master" in drift[1].reason


def test_the_gate_turns_an_engine_error_into_a_refusal_of_that_reel(tmp_path):
    (tmp_path / "x.mp4").write_bytes(b"video")

    def run(command, **_kw):
        return subprocess.CompletedProcess(command, 0, "garbage", "")

    (drift,) = scopes.scope_defects(tmp_path, {"x": "x"}, "scene-render", run=run)
    assert drift.name == "x" and "not JSON" in drift.reason


def test_the_command_exits_0_on_a_clean_master_1_on_a_finding_and_2_on_an_error(tmp_path, capsys):
    video = tmp_path / "reel.mp4"
    video.write_bytes(b"video")
    assert main(["scopes", str(video), "--engine", str(fake_engine(tmp_path, envelope(white=0.01)))]) == 0
    assert "reel.mp4: illegal 0%" in capsys.readouterr().out
    assert main(["scopes", str(video), "--engine", str(fake_engine(tmp_path, envelope(gamut=0.0004)))]) == 1
    assert "out_of_gamut 0.04% > 0%" in capsys.readouterr().out
    assert main(["scopes", str(video), "--engine", str(fake_engine(tmp_path, envelope(), code=4))]) == 2
    assert main(["scopes", str(tmp_path / "absent.mp4"), "--engine", "scene-render"]) == 2

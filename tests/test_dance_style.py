"""Dance-style targets (ADR 0203): ranges derived from a reference's measures, a strict ``srstudio.dance-style/1.1.0``
record, and the check that lists, ranked, what one of our dances misses."""

import json

import pytest

from srstudio import dance, dance_style
from srstudio import dance_study as ds
from srstudio.music import Groove

GROOVE = Groove(120)
FPS = 15
REFERENCE = dance_style.Reference(
    description="a synthetic reference: the bounce preset on the realistic skeleton",
    source_sha256="0" * 64,
    estimator="srstudio-skeleton",
    estimator_version="1.0.0",
    model_sha256="0" * 64,
    seconds=8.0,
    frames=120,
    used=120,
    rejected={"lost": 0, "low_confidence": 0, "implausible": 0, "jump": 0, "arm": 0, "repeat": 0},
    bpm=120.0,
    beats_per_bar=4,
    offset_s=0.0,
)
BY = {"tool": "tests/test_dance_style.py", "model": "Claude Opus 5.5 (claude-opus-5-5) in Claude Code"}


def frames(move: str, bars: int = 4):
    return list(dance.frames(dance.moves()[move], GROOVE, 0.0, bars * GROOVE.bar, FPS))


@pytest.fixture(scope="module")
def bounce_style():
    reading = ds.measure_style(ds.dance_body(frames("bounce"), FPS), GROOVE)
    return dance_style.derive(
        reading, name="bounce", description="our own bounce", reference=REFERENCE, generated_by=BY
    )


def test_a_style_is_ranges_and_round_trips_its_record(bounce_style):
    knees = next(c for c in bounce_style.channels if c.name == "knees.bend")
    low, high = knees.cycles_per_beat
    assert low < 2.0 < high and knees.peak_to_peak[0] <= knees.peak_to_peak[1]
    assert knees.evidence == {"frames": 120, "windows": 5, "read": 5, "still": 0, "locked": 5, "timed": 5}
    assert dance_style.parse_style(dance_style.dump_style(bounce_style)) == bounce_style
    assert [c.name for c in bounce_style.channels] == list(ds.CHANNEL)
    assert "root.travel" in bounce_style.unmeasured
    travel = next(c for c in bounce_style.channels if c.name == "hands.travel")
    assert travel.level is not None and travel.peak_to_peak is None
    stance = next(c for c in bounce_style.channels if c.name == "stance.width")
    assert stance.level is not None and stance.level[1] - stance.level[0] >= dance_style.FLOOR["head_radii"] - 1e-9


def test_a_dance_meets_the_style_it_was_measured_from(bounce_style):
    found = dance_style.check(bounce_style, frames("bounce"), GROOVE, FPS)
    assert found.misses == () and found.score == 0


def test_another_dance_misses_and_the_misses_are_ranked(bounce_style):
    found = dance_style.check(bounce_style, frames("arm-pump"), GROOVE, FPS)
    assert found.misses and found.score > 0
    severities = [m.severity for m in found.misses]
    assert severities == sorted(severities, reverse=True)
    knees = [m for m in found.misses if m.channel == "knees.bend"]
    assert any(m.measure == "peak_to_peak" and "too small" in m.words for m in knees)
    assert any(m.ours is None and "no steady cycle" in m.words for m in knees)
    arms = [m for m in found.misses if m.channel == "arms.height" and m.measure == "peak_to_peak"]
    assert arms and "too big" in arms[0].words


def test_a_lag_target_is_checked():
    target = dance_style.LagTarget("hips", "chest", (0.1, 0.2), {"windows": 5, "read": 5})
    reading = ds.measure_style(ds.dance_body(frames("bounce"), FPS), GROOVE)
    style = dance_style.DanceStyle("lag", "a lag", BY, REFERENCE, (), (target,), {})
    (miss,) = style.misses(reading)
    assert miss.channel == "hips>chest" and miss.measure == "lag" and "too early" in miss.words
    silent = dance_style.DanceStyle("lag", "a lag", BY, REFERENCE, (), (target,), {})
    still = ds.measure_style(ds.dance_body(frames("arm-pump"), FPS), GROOVE)
    assert silent.misses(still)[0].ours is None


def _data(style):
    return json.loads(dance_style.dump_style(style))


def _edit(style, change):
    data = _data(style)
    change(data)
    return json.dumps(data)


@pytest.mark.parametrize(
    ("change", "error", "words"),
    [
        (lambda d: d.update(extra=1), dance_style.StyleFormatError, "unknown"),
        (lambda d: d.pop("lags"), dance_style.StyleFormatError, "missing"),
        (lambda d: d.update(schema="srstudio.dance-style/2.0.0"), dance_style.StyleSchemaError, "schema"),
        (lambda d: d.update(schema=3), dance_style.StyleFormatError, "schema"),
        (lambda d: d.update(name="Bad Name"), dance_style.StyleFormatError, "name"),
        (lambda d: d["channels"][1].update(peak_to_peak=[0.5, 0.1]), dance_style.StyleValueError, "ordered"),
        (lambda d: d["channels"][1].update(peak_to_peak=[0.1]), dance_style.StyleFormatError, "low, high"),
        (lambda d: d["channels"][1].update(unit="head_radii"), dance_style.StyleValueError, "measured in"),
        (lambda d: d["channels"][1].update(name="tail.wag"), dance_style.StyleValueError, "no channel"),
        (lambda d: d["channels"][1].update(trust="great"), dance_style.StyleValueError, "trust"),
        (lambda d: d["channels"][1].update(cycles_per_beat=[1.0, 40.0]), dance_style.StyleValueError, "lies in"),
        (lambda d: d["channels"][1].update(noise=True), dance_style.StyleFormatError, "finite"),
        (lambda d: d["channels"][1]["evidence"].update(read=99), dance_style.StyleValueError, "more windows"),
        (lambda d: d["channels"][1]["evidence"].update(windows=-1), dance_style.StyleValueError, "lies in"),
        (lambda d: d["channels"][10].update(peak_to_peak=[0.1, 0.2]), dance_style.StyleValueError, "level"),
        (lambda d: d["channels"].reverse(), dance_style.StyleValueError, "in that order"),
        (lambda d: d["lags"][0].update(lead="tail"), dance_style.StyleValueError, "parts of"),
        (lambda d: d["lags"][0]["evidence"].update(read=99), dance_style.StyleValueError, "more windows"),
        (lambda d: d["lags"].reverse(), dance_style.StyleValueError, "in that order"),
        (lambda d: d["reference"].update(used=1000), dance_style.StyleValueError, "lies in"),
        (lambda d: d["reference"]["rejected"].update(lost=100), dance_style.StyleValueError, "add up"),
        (lambda d: d["reference"].update(source_sha256="abc"), dance_style.StyleFormatError, "source_sha256"),
        (lambda d: d["unmeasured"].append({"channel": "Root", "why": "x"}), dance_style.StyleFormatError, "channel"),
        (lambda d: d.update(channels="all"), dance_style.StyleFormatError, "list"),
    ],
)
def test_a_record_outside_the_schema_is_refused_at_its_path(bounce_style, change, error, words):
    with pytest.raises(error, match=words):
        dance_style.parse_style(_edit(bounce_style, change))


@pytest.mark.parametrize("text", ['{"schema": NaN}', '{"a": 1, "a": 1}', "[", b"\xff"])
def test_malformed_text_is_refused(text):
    with pytest.raises(dance_style.StyleFormatError):
        dance_style.parse_style(text)


def test_an_oversized_or_missing_record_is_refused(tmp_path):
    with pytest.raises(dance_style.StyleFormatError, match="at most"):
        dance_style.parse_style(" " * (dance_style.MAX_BYTES + 1))
    with pytest.raises(dance_style.StyleFormatError, match="cannot read"):
        dance_style.load_style(tmp_path / "none.json")


def test_a_style_loads_from_a_file(tmp_path, bounce_style):
    path = tmp_path / "bounce.json"
    path.write_text(dance_style.dump_style(bounce_style))
    assert dance_style.load_style(path) == bounce_style


def test_only_a_reading_is_checked_and_only_a_style_checks(bounce_style):
    with pytest.raises(dance_style.DanceStyleError):
        bounce_style.misses({})
    with pytest.raises(dance_style.DanceStyleError):
        dance_style.check({}, frames("bounce"), GROOVE, FPS)
    with pytest.raises(dance_style.DanceStyleError):
        dance_style.derive({}, name="x", description="x", reference=REFERENCE, generated_by=BY)


def test_the_shipped_reference_style_loads_by_its_name():
    shipped = dance_style.styles()
    assert "studio-hiphop" in shipped
    style = shipped["studio-hiphop"]
    assert (
        style.reference.used + sum(style.reference.rejected[k] for k in dance_style.REJECTS[:4])
        <= style.reference.frames
    )
    assert "root.travel" in style.unmeasured and style.generated_by["tool"] == "tools/dance_study.py"


def test_a_style_file_is_named_after_its_style(tmp_path, bounce_style):
    (tmp_path / "bounce.json").write_text(dance_style.dump_style(bounce_style))
    (tmp_path / "notes.txt").write_text("not a style")
    assert list(dance_style.styles(tmp_path)) == ["bounce"]
    (tmp_path / "other.json").write_text(dance_style.dump_style(bounce_style))
    with pytest.raises(dance_style.StyleValueError, match="holds the style"):
        dance_style.styles(tmp_path)

"""A line asked at its own pace: a take that came out faster than a listener reads it is asked again slower, in the
same voice, and only that line; the manifest says the pace each take was asked at."""

import json
import shutil

import pytest

from srstudio import sketch
from srstudio.sketch import Line
from support.sketch import SK, FakeClient, confirm_stub


def _copy(src, dst, clip_in, clip_out, length, gain, ffmpeg, effect=""):
    shutil.copyfile(src, dst)
    return length


def _sketch(lines):
    return sketch.Sketch(SK.slug, SK.title, SK.speakers, lines, SK.beats, SK.end, cast=SK.cast)


def test_a_line_keeps_its_speakers_pace_unless_it_names_one():
    assert Line("a", "Hello.").speed is None


def test_only_the_line_with_a_speed_is_asked_at_it_and_the_manifest_says_so(tmp_path):
    first = SK.lines[0]
    lines = (Line(first.speaker, first.text, speed=0.86), *SK.lines[1:])
    client = FakeClient(tmp_path)
    rec = sketch.record(_sketch(lines), tmp_path, client, confirm=confirm_stub, conform_clip=_copy)
    own = {s.name: s.settings.speed for s in SK.speakers}
    assert client.requests[0][2] == 0.86
    assert [r[2] for r in client.requests[1:]] == [own[line.speaker] for line in SK.lines[1:]]
    assert rec.items[0]["speed"] == 0.86
    assert [item["speed"] for item in rec.items[1:]] == [own[line.speaker] for line in SK.lines[1:]]
    json.dumps(rec.items)  # the manifest stays plain data


@pytest.mark.parametrize("speed", [0.5, 1.5, float("nan"), "fast"])
def test_a_speed_outside_the_voices_range_is_refused_before_any_take(speed, tmp_path):
    first = SK.lines[0]
    lines = (Line(first.speaker, first.text, speed=speed), *SK.lines[1:])  # type: ignore[arg-type]
    client = FakeClient(tmp_path)
    with pytest.raises(sketch.SketchError, match="speed"):
        sketch.record(_sketch(lines), tmp_path, client, confirm=confirm_stub, conform_clip=_copy)
    assert client.requests == []


def test_the_range_is_the_voices_own():
    from srstudio.voice import VoiceSettings

    lo, hi = sketch.SPEEDS
    VoiceSettings(0.5, 0.5, 0.5, speed=lo)
    VoiceSettings(0.5, 0.5, 0.5, speed=hi)


def test_a_small_print_beat_asks_its_take_at_its_own_speed_and_only_that_one():
    from dataclasses import replace

    from support.smallprint import BEATS, SHOW

    beats = (BEATS[0], replace(BEATS[1], speed=0.88), *BEATS[2:])
    show = replace(SHOW, beats=beats)
    assert [line.speed for line in show.lines] == [None, 0.88, *([None] * (len(BEATS) - 2))]
    show.validate_sketch()
    with pytest.raises(sketch.SketchError, match="speed"):
        replace(SHOW, beats=(BEATS[0], replace(BEATS[1], speed=2.0), *BEATS[2:])).validate_sketch()

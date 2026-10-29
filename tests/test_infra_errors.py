"""The infrastructure modules' refusals are their own SrstudioError subclasses and still the builtin they always
were (ADR 0034): layout, registry, timeline, series, craft and recording."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from srstudio import craft, layout, recording, registry, series, timeline
from srstudio.errors import SrstudioError


def refused(call, error: type[Exception], builtin: type[Exception], match: str) -> None:
    with pytest.raises(error, match=match) as caught:
        call()
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, builtin)


def test_a_box_or_safe_area_that_is_no_region_is_a_region_error():
    refused(lambda: layout.Box(1, 0, 0, 0), layout.RegionError, ValueError, "not a box")
    refused(lambda: layout.SafeArea("1st", 0, 0, 0, 0), layout.RegionError, ValueError, "NCName")
    refused(lambda: layout.SafeArea("a", 0.6, 0, 0.6, 0), layout.RegionError, ValueError, "no region")


def test_registry_refusals_keep_their_builtins():
    refused(lambda: registry.register("vehicle", "car"), registry.RegistryError, ValueError, "unknown kind")
    refused(lambda: registry.get("prop", "no-such-prop"), registry.NotRegisteredError, KeyError, "no prop named")


def test_timeline_refusals_are_timeline_errors_and_a_missing_take_is_still_a_key_error():
    phrase = timeline.Phrase(0, "a", "Hi.", "Hi.", 0.0, 1.0)
    tl = timeline.Timeline(duration=2.0, phrases=[phrase], cuts=[], sound_effects=[])
    refused(lambda: tl.take("nope"), timeline.UnknownTakeError, KeyError, "no take 'nope'")
    assert isinstance(pytest.raises(timeline.TimelineError, tl.take, "nope").value, ValueError)
    refused(lambda: tl.word_time(0, "hi"), timeline.TimelineError, ValueError, "no timing file")


def test_series_and_craft_refusals_use_their_module_errors():
    take = SimpleNamespace(id="t", text="Hello there", words=[{"text": "Hello", "start": 0.1}])
    refused(lambda: series.word_at(take, "bye"), series.SeriesError, ValueError, "no word 0")
    refused(lambda: craft.pauses([], threshold=0), craft.CraftError, ValueError, "threshold")


def test_a_script_option_shadowing_a_shared_argument_is_a_recording_error():
    def clash(parser):
        parser.add_argument("--encoder", dest="ffmpeg")

    refused(
        lambda: recording.main(lambda *a, **k: None, None, argv=["p"], options=clash),
        recording.RecordingError,
        ValueError,
        "shadows",
    )

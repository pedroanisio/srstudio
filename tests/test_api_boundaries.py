"""Public API failures preserve typed errors and existing registered builders."""

import pytest

from srstudio import SrstudioError, Timeline, registry
from srstudio.timeline import TimelineError


def test_duplicate_registration_preserves_the_original(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, "prop", {})

    @registry.register("prop", "cup")
    def original():
        return "original"

    with pytest.raises(registry.RegistryError, match="prop.*cup.*already registered"):
        registry.register("prop", "cup")(lambda: "replacement")
    assert registry.get("prop", "cup").builder is original


def test_registration_can_explicitly_replace_a_builder(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, "prop", {})
    registry.register("prop", "cup")(lambda: "original")
    registry.register("prop", "cup", replace=True)(lambda: "replacement")
    assert registry.get("prop", "cup")() == "replacement"


@pytest.mark.parametrize("kind", ["porp", ""])
@pytest.mark.parametrize("lookup", [registry.entries, registry.catalog])
def test_catalog_lookup_rejects_unknown_kinds(lookup, kind):
    with pytest.raises(registry.RegistryError, match="unknown kind") as caught:
        lookup(kind=kind)
    assert isinstance(caught.value, SrstudioError)


@pytest.mark.parametrize(
    "data,field",
    [
        ({"duration": 1}, "phrases"),
        ({"phrases": []}, "duration"),
        ({"duration": "bad", "phrases": []}, "duration"),
        ({"duration": True, "phrases": []}, "duration"),
        ({"duration": 1, "phrases": None}, "phrases"),
        ({"duration": 1, "phrases": [None]}, "phrases 0"),
        ({"duration": 1, "phrases": [{"role": "a", "text": "hi", "start": "bad", "end": 1}]}, "start"),
        ({"duration": 1, "phrases": [{"role": "a", "text": "hi", "start": 0}]}, "end"),
        ({"duration": 1, "phrases": [], "camera_cuts": [{"angle": "wide"}]}, "time"),
        ({"duration": 1, "phrases": [], "sound_effects": [{"name": "ding", "start": None}]}, "start"),
        ({"duration": 1, "items": [{"id": "a"}]}, "actor"),
        ({"duration": 1, "items": None}, "items"),
        ([{"start": "bad", "end": 1, "text": "hi"}], "start"),
    ],
)
def test_malformed_timeline_input_raises_a_contextual_typed_error(data, field):
    with pytest.raises(TimelineError, match=field) as caught:
        Timeline.from_dict(data)
    assert isinstance(caught.value, SrstudioError)


def test_malformed_json_is_a_timeline_error(tmp_path):
    source = tmp_path / "dialogue.json"
    source.write_text('{"duration":')
    with pytest.raises(TimelineError, match="dialogue.json"):
        Timeline.load(source)


def test_take_alignment_accepts_existing_tuple_input():
    words = ({"text": "hi", "start": 0, "end": 0.5},)
    timeline = Timeline.from_takes(
        {
            "duration": 1,
            "items": [
                {
                    "id": "a",
                    "actor": "a",
                    "shot": "wide",
                    "text": "hi",
                    "start": 0,
                    "duration": 1,
                    "words": words,
                    "phones": (),
                }
            ],
        }
    )
    assert timeline.takes[0].words == words

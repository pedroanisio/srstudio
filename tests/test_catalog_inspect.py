"""A discovered part can be understood and used without reading its source."""

import inspect
import json

import pytest

from srstudio import Episode, EpisodeSpec, registry
from srstudio.cli import main


def test_location_details_show_signature_slots_and_documentation():
    details = registry.describe("location", "office-wide")
    assert details["signature"] == str(inspect.signature(registry.get("location", "office-wide").builder))
    assert details["slots"] == ["at_desk", "cactus"]
    assert "instanced" in details["documentation"]
    assert "ep.setup" in details["examples"][0]
    assert json.loads(json.dumps(details)) == details


@pytest.mark.parametrize(
    "kind,name",
    [("character", "manager"), ("graphic", "episode-slate"), ("location", "office-wide"), ("location", "cafe")],
)
def test_shipped_examples_build_valid_scenes(kind, name, project):
    ep = Episode(
        EpisodeSpec(slug="inspect", title="inspect", description="inspect", root=project, seed=1, signature=False)
    )
    examples = registry.describe(kind, name)["examples"]
    assert examples
    for example in examples:
        exec(compile(example, "<catalog example>", "exec"), {"ep": ep})
    assert ep.check() == []


def test_every_registered_part_has_a_bindable_call_template():
    for entry in registry.entries():
        details = registry.describe(entry.kind, entry.name)
        # Test argument structure without drawing or calling any builder.
        signature = inspect.signature(entry.builder)
        namespace = {p.name: object() for p in signature.parameters.values()}
        namespace["part"] = signature.bind
        exec(compile(details["call_template"], "<catalog template>", "exec"), namespace)


def test_plugin_metadata_supplies_unannotated_slots_and_examples(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, "location", {})

    @registry.register("location", "plugin-room", slots=("at_table",), examples=("part(cv, parent, at_table=seat)",))
    def room(cv, parent, at_table=None, colour="blue"):
        """A plugin room with a seat behind its table."""

    details = registry.describe("location", "plugin-room")
    assert details["slots"] == ["at_table"]
    assert details["examples"] == ["part(cv, parent, at_table=seat)"]
    assert details["parameters"][2]["required"] is False
    assert details["parameters"][3]["default"] == "'blue'"


def test_resolved_slot_annotations_are_recognized(monkeypatch):
    from srstudio.locations import Slot

    monkeypatch.setitem(registry._REGISTRY, "location", {})

    @registry.register("location", "annotated-room")
    def room(cv, parent, seat: Slot = None):
        return parent

    assert registry.describe("location", "annotated-room")["slots"] == ["seat"]


def test_inspection_does_not_call_the_builder(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, "prop", {})

    @registry.register("prop", "side-effect")
    def builder(cv, parent, *, size=10):
        raise AssertionError("inspection must never draw")

    details = registry.describe("prop", "side-effect")
    assert details["call_template"] == "part(cv, parent)"


def test_uninspectable_plugin_has_a_typed_error(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, "prop", {})

    @registry.register("prop", "opaque")
    def builder():
        return None

    builder.__signature__ = "invalid signature"
    with pytest.raises(registry.RegistryError, match="signature"):
        registry.describe("prop", "opaque")


def test_inspection_loads_requested_plugin(tmp_path, monkeypatch, capsys):
    import sys

    monkeypatch.setitem(registry._REGISTRY, "location", {})
    monkeypatch.syspath_prepend(str(tmp_path))
    plugin = tmp_path / "inspect_test_plugin.py"
    plugin.write_text(
        'from srstudio import register\n'
        '@register("location", "plugin-set", slots=("seat",))\n'
        'def room(cv, parent, seat=None):\n    return parent\n'
    )
    try:
        assert main(["inspect", "location", "plugin-set", "--plugins", "inspect_test_plugin", "--json"]) == 0
        assert json.loads(capsys.readouterr().out)["slots"] == ["seat"]
    finally:
        sys.modules.pop("inspect_test_plugin", None)


def test_bad_slot_metadata_is_refused_without_registering(monkeypatch):
    monkeypatch.setitem(registry._REGISTRY, "location", {})
    with pytest.raises(registry.RegistryError, match="missing"):
        registry.register("location", "bad", slots=("missing",))(lambda cv, parent: None)
    assert registry.entries("location") == []


def test_text_and_json_inspection_are_available_from_the_cli(capsys):
    assert main(["inspect", "location", "cafe"]) == 0
    text = capsys.readouterr().out
    assert "behind_counter" in text and "at_counter" in text and "on_counter" in text
    assert "Signature:" in text and "Call template:" in text
    assert main(["inspect", "character", "manager", "--json"]) == 0
    assert json.loads(capsys.readouterr().out) == registry.describe("character", "manager")


def test_inspection_of_an_unknown_part_reports_an_actionable_error(capsys):
    assert main(["inspect", "location", "offcie-wide"]) == 2
    error = capsys.readouterr().err
    assert "offcie-wide" in error and "office-wide" in error and "Traceback" not in error


def test_catalog_help_points_to_inspection(capsys):
    with pytest.raises(SystemExit) as stopped:
        main(["catalog", "--help"])
    assert stopped.value.code == 0
    assert "srstudio inspect" in capsys.readouterr().out

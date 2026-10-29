"""Persisted motion is a strict, bounded typed contract, suitable for packages and untrusted authoring input."""

import json
from copy import deepcopy

import pytest

from srstudio.limbs.model import HUMAN, ArmProfile, LimbError
from srstudio.limbs.motion import Action, Motion
from srstudio.limbs.serialization import load_motion, motion_dict, parse_motion, save_motion


def document():
    return motion_dict(Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),)))


def test_motion_roundtrips_through_json_and_private_atomic_files(tmp_path):
    motion = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),))
    data = motion_dict(motion)
    assert parse_motion(json.loads(json.dumps(data))) == motion
    file = save_motion(motion, tmp_path / "motion" / "motion.json")
    assert load_motion(file) == motion and file.stat().st_mode & 0o777 == 0o600
    assert sorted(p.name for p in file.parent.iterdir()) == ["motion.json"]


@pytest.mark.parametrize(
    "where,key",
    [
        ((), "extra"),
        (("motion",), "extra"),
        (("motion", "arm"), "typo"),
        (("motion", "actions", 0), "duration_seconds"),
    ],
)
def test_unknown_fields_are_rejected_at_every_nesting_level(where, key):
    data = document()
    node = data
    for name in where:
        node = node[name]
    node[key] = "untrusted"
    with pytest.raises(LimbError, match="unknown"):
        parse_motion(data)


@pytest.mark.parametrize("value", [True, "1", None, float("nan"), float("inf"), -1])
def test_wrong_types_nonfinite_numbers_and_invalid_dimensions_fail_semantically(value):
    data = document()
    data["motion"]["arm"]["upper"] = value
    with pytest.raises(LimbError):
        parse_motion(data)


def test_versions_missing_required_values_and_unbounded_input_are_rejected():
    data = document()
    data["schema"] = "srstudio.limbs/99.0.0"
    with pytest.raises(LimbError, match="schema"):
        parse_motion(data)
    data = document()
    del data["motion"]["hand"]["name"]
    with pytest.raises(LimbError, match="missing"):
        parse_motion(data)
    data = document()
    data["motion"]["actions"] = [deepcopy(data["motion"]["actions"][0]) for _ in range(10001)]
    with pytest.raises(LimbError, match="bound|budget"):
        parse_motion(data)


def test_malformed_and_oversized_files_do_not_get_coerced_to_an_empty_motion(tmp_path):
    file = tmp_path / "motion.json"
    file.write_text('{"schema":')
    with pytest.raises(LimbError):
        load_motion(file)
    file.write_bytes(b" " * (5 * 1024 * 1024 + 1))
    with pytest.raises(LimbError, match="size"):
        load_motion(file)

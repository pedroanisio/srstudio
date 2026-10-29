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


@pytest.mark.parametrize("depth", [65, 1000, 200000])
def test_deeply_nested_files_under_the_size_cap_fail_with_a_budget_error(tmp_path, depth):
    file = tmp_path / "deep.json"
    file.write_text("[" * depth + "]" * depth)
    with pytest.raises(LimbError, match="nesting") as caught:
        load_motion(file)
    assert caught.value.code == "budget"


def test_brackets_inside_strings_do_not_count_toward_the_nesting_bound(tmp_path):
    motion = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),))
    data = motion_dict(motion)
    data["generatedBy"] = "[{" * 500 + '\\"' + "}]" * 500
    file = tmp_path / "motion.json"
    file.write_text(json.dumps(data))
    assert load_motion(file) == motion


def test_motion_files_that_are_not_utf8_fail_as_invalid_documents(tmp_path):
    file = tmp_path / "motion.json"
    file.write_bytes(b'{"schema": "\xff"}')
    with pytest.raises(LimbError, match="UTF-8"):
        load_motion(file)


def test_an_unterminated_string_of_escaped_quotes_is_scanned_once_and_rejected(tmp_path):
    file = tmp_path / "motion.json"
    file.write_text('{"schema": "' + '\\"[{' * 100000)
    with pytest.raises(LimbError, match="cannot read motion document") as caught:
        load_motion(file)
    assert caught.value.code == "io"


@pytest.mark.parametrize(
    "original,duplicated",
    [
        ('"reach_policy": "strict"', '"reach_policy": "clamp", "reach_policy": "strict"'),
        ('"schema": "srstudio.limbs/1.1.0"', '"schema": "srstudio.limbs/1.1.0", "schema": "srstudio.limbs/1.1.0"'),
        ('"upper": 1.0', '"upper": 1.0, "upper": 1.0'),
    ],
)
def test_duplicate_object_keys_are_rejected_instead_of_last_one_winning(tmp_path, original, duplicated):
    text = json.dumps(document())
    assert original in text
    file = tmp_path / "motion.json"
    file.write_text(text.replace(original, duplicated, 1))
    with pytest.raises(LimbError, match="duplicate"):
        load_motion(file)


def test_saving_under_a_regular_file_raises_an_io_limb_error(tmp_path):
    blocker = tmp_path / "afile"
    blocker.write_text("x")
    motion = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),))
    with pytest.raises(LimbError, match="cannot write motion document") as caught:
        save_motion(motion, blocker / "motion.json")
    assert caught.value.code == "io"


def test_a_failed_replace_removes_the_temporary_file_and_raises_an_io_limb_error(tmp_path):
    target = tmp_path / "motion.json"
    target.mkdir()
    (target / "keep").write_text("x")
    motion = Motion(ArmProfile(), HUMAN, (Action("point", 0, 2),))
    with pytest.raises(LimbError, match="cannot write motion document") as caught:
        save_motion(motion, target)
    assert caught.value.code == "io"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["motion.json"]
    assert sorted(p.name for p in target.iterdir()) == ["keep"]

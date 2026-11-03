"""The gate's two tiers (ADR 0221): which tests leave the five-minute gate, and the measured table that says so."""

import json

import pytest

import tiers


def table(**tests):
    return {"schema_version": tiers.SCHEMA, "bound_seconds": tiers.BOUND, "tests": tests}


def test_an_engine_fixture_sends_a_test_to_the_full_tier_before_it_is_ever_measured():
    measured = tiers.parse(table())
    assert tiers.full("tests/test_a.py::test_new", {"tmp_path", "scene_render"}, measured)
    assert not tiers.full("tests/test_a.py::test_new", {"tmp_path"}, measured)


def test_a_measured_slow_or_gpu_test_goes_to_the_full_tier_and_a_fast_one_stays():
    measured = tiers.parse(
        table(
            **{
                "tests/test_a.py::test_slow": {"seconds": tiers.BOUND + 1, "gpu": False},
                "tests/test_a.py::test_gpu": {"seconds": 0.5, "gpu": True},
            }
        )
    )
    assert tiers.full("tests/test_a.py::test_slow", set(), measured)
    assert tiers.full("tests/test_a.py::test_gpu", set(), measured)
    assert not tiers.full("tests/test_a.py::test_fast", set(), measured)


def test_a_file_whose_measured_slow_tests_add_up_past_the_file_bound_leaves_whole():
    """A cache shared by a file's tests charges its cost to whichever test runs first, a different one each run."""
    half = tiers.FILE_BOUND / 2 + 1
    measured = tiers.parse(
        table(
            **{
                "tests/test_a.py::test_one": {"seconds": half, "gpu": False},
                "tests/test_a.py::test_two": {"seconds": half, "gpu": False},
                "tests/test_b.py::test_one": {"seconds": half, "gpu": False},
            }
        )
    )
    assert tiers.full("tests/test_a.py::test_never_measured_slow[x]", set(), measured)
    assert not tiers.full("tests/test_b.py::test_never_measured_slow", set(), measured)


def test_the_writer_keeps_only_what_leaves_the_gate():
    runs = {
        "tests/test_a.py::test_slow": tiers.Run(tiers.BOUND + 0.5, False),
        "tests/test_a.py::test_gpu": tiers.Run(0.2, True),
        "tests/test_a.py::test_fast": tiers.Run(tiers.BOUND - 0.5, False),
    }
    written = tiers.parse(json.loads(tiers.render(runs)))
    assert set(written) == {"tests/test_a.py::test_slow", "tests/test_a.py::test_gpu"}
    assert written["tests/test_a.py::test_gpu"] == tiers.Run(0.2, True)


@pytest.mark.parametrize(
    "data, said",
    [
        ([], "object"),
        ({"schema_version": "9.0.0", "bound_seconds": tiers.BOUND, "tests": {}}, "schema"),
        ({**table(), "extra": 1}, "fields"),
        ({"schema_version": tiers.SCHEMA, "tests": {}}, "fields"),
        ({**table(), "bound_seconds": tiers.BOUND + 1}, "bound"),
        (table(**{"tests/a.py::t": {"seconds": 1.0}}), "fields"),
        (table(**{"tests/a.py::t": {"seconds": 1.0, "gpu": False, "why": "x"}}), "fields"),
        (table(**{"tests/a.py::t": {"seconds": -1.0, "gpu": False}}), "seconds"),
        (table(**{"tests/a.py::t": {"seconds": float("nan"), "gpu": False}}), "seconds"),
        (table(**{"tests/a.py::t": {"seconds": True, "gpu": False}}), "seconds"),
        (table(**{"tests/a.py::t": {"seconds": 1.0, "gpu": 1}}), "gpu"),
        (table(**{"a.py::t": {"seconds": 1.0, "gpu": False}}), "node id"),
        (table(**{"tests/a.py::t": {"seconds": 0.5, "gpu": False}}), "neither"),
    ],
)
def test_a_malformed_table_is_refused(data, said):
    with pytest.raises(tiers.TierTableError, match=said):
        tiers.parse(data)


def test_the_committed_table_parses_and_names_only_collected_files():
    for node in tiers.load(tiers.TABLE):
        assert (tiers.TABLE.parent.parent / node.split("::")[0]).is_file(), node

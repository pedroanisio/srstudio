"""The gate's two tiers (ADR 0221): which tests leave the five-minute gate, and the measured table that says so."""

import ast
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


# -- a static check stays in the gate (ADR 0225) ----------------------------------------------------------------------
SCAN = "tests/test_gpu.py::test_every_engine_call_that_uses_the_gpu_takes_the_lock"


def test_a_static_test_stays_in_the_gate_whatever_a_loaded_run_measured():
    """The AST scan that ran 1.9 s alone was measured at 10.08 s on one loaded full run and left the gate."""
    measured = tiers.parse(table(**{SCAN: {"seconds": 10.08, "gpu": False}}))
    assert tiers.full(SCAN, set(), measured)
    assert not tiers.full(SCAN, set(), measured, static=True)


def test_a_static_test_stays_in_the_gate_when_its_file_leaves_whole():
    half = tiers.FILE_BOUND / 2 + 1
    measured = tiers.parse(
        table(
            **{
                "tests/test_a.py::test_one": {"seconds": half, "gpu": False},
                "tests/test_a.py::test_scan": {"seconds": half, "gpu": False},
            }
        )
    )
    assert tiers.full("tests/test_a.py::test_scan", set(), measured)
    assert not tiers.full("tests/test_a.py::test_scan", set(), measured, static=True)


def test_the_writer_never_lists_a_static_test_however_long_it_was_measured():
    runs = {SCAN: tiers.Run(10.08, False, static=True), "tests/test_a.py::test_slow": tiers.Run(tiers.BOUND + 1, False)}
    assert set(tiers.parse(json.loads(tiers.render(runs)))) == {"tests/test_a.py::test_slow"}


def test_a_static_test_that_asks_for_the_engine_is_refused():
    with pytest.raises(tiers.StaticPinError, match="engine"):
        tiers.full(SCAN, {"scene_render"}, tiers.parse(table()), static=True)


def test_a_static_test_seen_taking_the_gpu_is_refused_by_the_writer():
    with pytest.raises(tiers.StaticPinError, match="GPU"):
        tiers.render({SCAN: tiers.Run(0.1, True, static=True)})


def test_a_static_test_past_the_ceiling_is_refused_by_the_writer_not_kept_in_the_gate():
    """Noise inflates a static check a few times over, never past the ceiling: past it, the pin is wrong."""
    tiers.render({SCAN: tiers.Run(tiers.STATIC_CEILING, False, static=True)})
    with pytest.raises(tiers.StaticPinError, match="ceiling"):
        tiers.render({SCAN: tiers.Run(tiers.STATIC_CEILING + 0.01, False, static=True)})


def test_the_ceiling_is_far_above_the_bound():
    assert tiers.BOUND * 5 < tiers.STATIC_CEILING


class _Item:
    """What the collection hook reads from a pytest item: its node id, its fixtures and its markers."""

    def __init__(self, nodeid: str, *marks: str, fixtures: tuple[str, ...] = ()) -> None:
        self.nodeid, self.fixturenames, self.marks = nodeid, fixtures, list(marks)

    def get_closest_marker(self, name: str):
        return name if name in self.marks else None

    def add_marker(self, mark) -> None:
        self.marks.append(mark.name)


def test_the_collection_hook_keeps_a_static_test_listed_in_the_committed_table_in_the_gate():
    import conftest

    pinned, plain = _Item(SCAN, "static"), _Item(SCAN)
    conftest.pytest_collection_modifyitems(None, [pinned, plain])
    assert "slow" not in pinned.marks
    assert "slow" in plain.marks or SCAN not in tiers.load()


def test_the_collection_hook_refuses_a_static_test_that_asks_for_the_engine():
    import conftest

    with pytest.raises(pytest.UsageError, match="engine"):
        conftest.pytest_collection_modifyitems(None, [_Item(SCAN, "static", fixtures=("scene_render",))])


def _static(node: str) -> bool:
    """Whether the test function at ``node`` is decorated ``@pytest.mark.static``, read from its source."""
    path, name = node.split("::")
    tree = ast.parse((tiers.TABLE.parent.parent / path).read_text(encoding="utf-8"))
    (function,) = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name]
    return "pytest.mark.static" in {ast.unparse(d) for d in function.decorator_list}


PINNED = (
    SCAN,
    "tests/test_suite.py::test_no_module_under_tests_imports_a_test_module",
    "tests/test_decisions.py::test_every_cited_decision_record_exists",
    "tests/test_no_real_rclone.py::test_every_road_to_rclone_is_guarded",
    "tests/test_skeleton_bridges.py::test_the_skeleton_reaches_body_only_through_its_public_module",
    "tests/test_safe_area_required.py::test_no_library_builder_passes_an_undeclared_safe_area",
    "tests/test_safe_area_required.py::test_every_scene_written_outside_episode_declares_one_or_is_listed_as_never_delivered",
)


@pytest.mark.parametrize("node", PINNED)
def test_the_source_scans_are_pinned_to_the_gate(node):
    assert _static(node), node


def test_the_pin_reader_sees_an_unpinned_test():
    assert not _static("tests/test_tiers.py::test_the_pin_reader_sees_an_unpinned_test")

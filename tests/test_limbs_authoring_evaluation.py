"""Authoring observations stay separate from build timing and unsuccessful attempts."""

from dataclasses import asdict, replace

import pytest

from srstudio.limbs import LimbError
from srstudio.limbs.evaluation import AuthoringRecord, Pair, parse_authoring, summarize_authoring

PAIRS = (Pair("point", "Point right", "legacy", "spatial"),)


def record(**kwargs):
    return AuthoringRecord(
        **{"case": "point", "author": "one", "implementation": "legacy", "seconds": 120, "completed": True, **kwargs}
    )


def test_authoring_summary_reports_matched_successes_and_keeps_failures_separate():
    rows = (
        record(),
        record(implementation="spatial", seconds=90),
        record(author="two", seconds=10, completed=False),
        record(author="two", implementation="spatial", seconds=60),
    )
    result = summarize_authoring(PAIRS, rows)
    assert result["status"] == "observed" and result["authors"] == 2
    legacy = result["results"]["point"]["legacy"]
    assert legacy["attempts"] == 2 and legacy["completed"] == 1
    assert legacy["median_completed_seconds"] == 120
    assert result["paired"]["point"]["completed_pairs"] == 1
    assert result["paired"]["point"]["median_candidate_minus_baseline_seconds"] == -30
    assert "not verified" in result["provenance"]


def test_empty_authoring_and_failed_attempts_do_not_invent_successful_work():
    empty = summarize_authoring(PAIRS, ())
    assert empty["status"] == "awaiting_records" and empty["results"] is None
    result = summarize_authoring(PAIRS, (record(completed=False),))
    assert result["results"]["point"]["legacy"]["median_completed_seconds"] is None
    assert result["paired"]["point"]["median_candidate_minus_baseline_seconds"] is None


@pytest.mark.parametrize("changes", [{"case": "missing"}, {"implementation": "other"}])
def test_authoring_records_must_resolve_to_the_actual_comparison_task(changes):
    with pytest.raises(LimbError):
        summarize_authoring(PAIRS, (record(**changes),))


def test_duplicate_authoring_observations_and_invalid_pair_plans_are_rejected():
    with pytest.raises(LimbError, match="duplicate"):
        summarize_authoring(PAIRS, (record(), record(seconds=100)))
    for pairs in ((), PAIRS * 2):
        with pytest.raises(LimbError):
            summarize_authoring(pairs, ())


@pytest.mark.parametrize(
    "changes",
    [
        {"seconds": 0},
        {"seconds": float("nan")},
        {"seconds": True},
        {"seconds": 86401},
        {"completed": "yes"},
        {"notes": "x" * 2001},
    ],
)
def test_authoring_record_rejects_invalid_measurements(changes):
    with pytest.raises(LimbError):
        record(**changes)


def test_authoring_document_is_typed_versioned_and_rejects_unknown_fields():
    document = {"schema": "srstudio.limbs.authoring/1.0.0", "records": [asdict(record())]}
    assert parse_authoring(document) == (record(),)
    for bad in (
        None,
        {},
        {**document, "schema": "other"},
        {**document, "extra": True},
        {**document, "records": [{**document["records"][0], "extra": True}]},
        {**document, "records": [{"seconds": 120}]},
    ):
        with pytest.raises(LimbError):
            parse_authoring(bad)
    assert parse_authoring({**document, "records": [asdict(replace(record(), completed=False))]})[0].completed is False

"""Evaluation separates observed engineering cost, target residuals and real reviewer ratings."""

from dataclasses import replace

import pytest
from sr_core.scene import Scene

from srstudio import Canvas
from srstudio.limbs import HUMAN, ArmProfile, Camera, LimbError, Vec3
from srstudio.limbs.compile import BakeOptions, compile_motion
from srstudio.limbs.evaluation import Pair, Rating, Scores, measure, parse_ratings, plan_trials, summarize
from srstudio.limbs.motion import Action, Motion, Target


def drawing():
    scene = Scene(version="auto")
    scene.add_project(width=320, height=320, fps="24", duration=2)
    cv = Canvas(scene, font_asset=None)
    cv.rect(cv.comp, 10, 10, 100, 100, "#ffffff")
    return scene


def test_measurement_reports_actual_scene_cost_and_deterministic_injected_timings():
    ticks = iter((0, 1, 2, 5, 6, 8))
    result = measure("simple", drawing, repeats=3, clock=lambda: next(ticks))
    assert result.median_build_seconds == 2
    assert result.min_build_seconds == 1 and result.max_build_seconds == 3
    assert result.xml_bytes == len(drawing().to_bytes())
    assert result.nodes == len(list(drawing().iter()))
    assert result.shapes == 1 and result.source_lines > 0
    assert len(result.scene_sha256) == 64


def test_unstable_builds_and_invalid_measurement_options_are_rejected():
    index = [0]

    def unstable():
        scene = drawing()
        index[0] += 1
        next(scene.iter("project")).width = 320 + index[0]
        return scene

    with pytest.raises(LimbError, match="determin"):
        measure("unstable", unstable, repeats=2)
    with pytest.raises(LimbError):
        measure("invalid", drawing, repeats=0)


def test_blinded_plan_is_repeatable_and_has_no_implementation_names_in_public_trials():
    pairs = (Pair("point", "Point to the right", "legacy-stick", "spatial-stick"),)
    first = plan_trials(pairs, seed="study-1")
    assert first == plan_trials(pairs, seed="study-1")
    assert first[0].a != first[0].b
    public = first[0].public_dict()
    assert "legacy" not in str(public) and "spatial" not in str(public)
    assert public["a"].endswith("-A.mp4") and public["b"].endswith("-B.mp4")


def test_empty_and_incomplete_ratings_never_become_fabricated_preference_evidence():
    trials = plan_trials((Pair("point", "Point", "legacy", "spatial"),), seed="study-1")
    empty = summarize(trials, ())
    assert empty["status"] == "awaiting_ratings" and empty["results"] is None
    rating = Rating(trials[0].id, "reviewer-1", "a", Scores(5, 4, 3), Scores(2, 3, 4))
    partial = summarize(trials, (rating,), minimum_reviewers=2)
    assert partial["status"] == "partial" and partial["reviewers"] == 1
    winner = trials[0].a
    assert partial["results"][winner]["wins"] == 1
    assert partial["results"][winner]["clarity_mean"] == 5
    with pytest.raises(LimbError, match="duplicate"):
        summarize(trials, (rating, rating))
    with pytest.raises(LimbError, match="trial"):
        summarize(trials, (replace(rating, trial="absent"),))


def test_rating_document_rejects_unknown_fields_invalid_scores_and_model_invented_variants():
    data = {
        "schema": "srstudio.limbs.ratings/1.0.0",
        "ratings": [
            {
                "trial": "trial-001",
                "reviewer": "human-1",
                "preference": "tie",
                "a": {"clarity": 4, "naturalness": 4, "style_fit": 4},
                "b": {"clarity": 4, "naturalness": 4, "style_fit": 4},
            }
        ],
    }
    assert len(parse_ratings(data)) == 1
    for key, value in (("preference", "c"), ("extra", True)):
        bad = {**data, "ratings": [{**data["ratings"][0], key: value}]}
        with pytest.raises(LimbError):
            parse_ratings(bad)
    data["ratings"][0]["a"]["clarity"] = 6
    with pytest.raises(LimbError):
        parse_ratings(data)


@pytest.mark.parametrize("backend", ["baked", "auto", "native"])
def test_compilation_retains_explicit_reach_clamping_in_its_quality_evidence(backend):
    cv = Canvas(Scene(version="auto"), font_asset=None)
    m = Motion(ArmProfile(), HUMAN, (Action("point", duration=2, target=Target(Vec3(2, 0, 0))),), reach_policy="clamp")
    result = compile_motion(cv, cv.comp, m, id="clamp", backend=backend, options=BakeOptions(fps=4))
    assert result.report.max_reach_error > 1
    assert any(d.code == "unreachable" and d.residual > 1 for d in result.diagnostics)


@pytest.mark.parametrize("pairs,seed", [((), "seed"), ((Pair("x", "Task", "a", "b"),) * 2, "seed")])
def test_review_plan_rejects_missing_or_duplicate_tasks(pairs, seed):
    with pytest.raises(LimbError):
        plan_trials(pairs, seed=seed)


@pytest.mark.parametrize("args", [("", "Task", "a", "b"), ("x", "", "a", "b"), ("x", "Task", "a", "a")])
def test_review_pair_requires_identifiable_distinct_implementations(args):
    with pytest.raises(LimbError):
        Pair(*args)


@pytest.mark.parametrize(
    "document",
    [None, {}, {"schema": "other", "ratings": []}, {"schema": "srstudio.limbs.ratings/1.0.0", "ratings": [{}]}],
)
def test_review_parse_requires_supported_complete_document(document):
    with pytest.raises(LimbError):
        parse_ratings(document)


def test_complete_review_counts_both_sides_and_ties_without_changing_meaning_of_scores():
    trials = plan_trials((Pair("point", "Point", "legacy", "spatial"),), seed="study-1")
    first = Rating(trials[0].id, "one", "b", Scores(1, 2, 3), Scores(3, 4, 5))
    second = Rating(trials[0].id, "two", "tie", Scores(3, 4, 5), Scores(5, 2, 1))
    result = summarize(trials, (first, second), minimum_reviewers=2)
    assert result["status"] == "complete" and result["ratings"] == 2
    assert result["results"][trials[0].a]["clarity_mean"] == 2
    assert result["results"][trials[0].b]["wins"] == 1
    assert all(row["ties"] == 1 for row in result["results"].values())
    for count in (0, True, 1001):
        with pytest.raises(LimbError):
            summarize(trials, (), minimum_reviewers=count)
    with pytest.raises(LimbError):
        summarize((), ())
    with pytest.raises(LimbError, match="duplicate"):
        summarize(trials * 2, ())
    with pytest.raises(LimbError):
        Rating(trials[0].id, "one", "a", Scores(1, 2, 3), Scores(3, 4, 5), "x" * 2001)


def test_measure_rejects_non_scene_invalid_scene_and_reversed_clock():
    def non_scene():
        return None

    def invalid_scene():
        return Scene(version="auto")

    for builder in (non_scene, invalid_scene):
        with pytest.raises(LimbError):
            measure("invalid", builder, repeats=1)
    ticks = iter((2, 1))
    with pytest.raises(LimbError, match="backwards"):
        measure("clock", drawing, repeats=1, clock=lambda: next(ticks))
    with pytest.raises(LimbError, match="inspectable"):
        measure("opaque", len, repeats=1)


def test_automatic_spatial_fallback_retains_clamping_alongside_backend_diagnostic():
    cv = Canvas(Scene(version="auto"), font_asset=None)
    motion = Motion(
        ArmProfile(), HUMAN, (Action("point", duration=2, target=Target(Vec3(2, 0, 0.1))),), reach_policy="clamp"
    )
    result = compile_motion(
        cv, cv.comp, motion, id="spatial-clamp", camera=Camera(projection="perspective"), options=BakeOptions(fps=4)
    )
    assert result.backend == "baked"
    assert {d.code for d in result.diagnostics} >= {"backend", "unreachable"}
    assert result.report.to_dict()["max_reach_error"] > 1


def test_measure_refuses_lambda_builders_instead_of_leaking_a_syntax_error():
    builders = {"inline": lambda: drawing()}
    with pytest.raises(LimbError, match="def function"):
        measure("lambda", builders["inline"], repeats=1)
    with pytest.raises(LimbError, match="def function"):
        measure("multiline", lambda: drawing(), repeats=1)


def test_measure_refuses_renamed_lambdas_whose_source_is_not_a_def():
    table = {
        "a": lambda: drawing()  # this dict entry line does not parse on its own
    }
    fragment = table["a"]
    fragment.__name__ = "fragment"
    with pytest.raises(LimbError, match="parseable"):
        measure("fragment", fragment, repeats=1)
    assigned = lambda: drawing()  # noqa: E731
    assigned.__name__ = "assigned"  # its source line parses as an assignment, not a definition
    with pytest.raises(LimbError, match="def function"):
        measure("assigned", assigned, repeats=1)

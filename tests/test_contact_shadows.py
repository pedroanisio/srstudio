"""Every figure on screen has a contact shadow under each planted foot, in every state."""

from __future__ import annotations

import math

import pytest

from srstudio import contact_shadows as cs
from srstudio.contact_shadows import FootShadow, ShadowCheckError, check, parse
from srstudio.errors import SrstudioError


def foot(
    n: int,
    state: str = "dance",
    *,
    side: int = 0,
    lift: float = 0.0,
    mid: float = 500.0,
    shadow: float | None = 500.0,
    width: float | None = None,
    opacity: float | None = None,
    base: float = 60.0,
    who: str = "noor",
) -> FootShadow:
    """A foot whose shadow, unless told otherwise, is the size the rule gives for its lift."""
    rule_width, rule_opacity = cs.shadow_size(lift, base)
    width = rule_width if width is None else width
    opacity = rule_opacity if opacity is None else opacity
    return FootShadow(
        figure=who,
        frame=n,
        state=state,
        side=side,
        lift=lift,
        mid_x=mid,
        shadow_x=shadow,
        shadow_width=None if shadow is None else width,
        shadow_opacity=None if shadow is None else opacity,
        base_width=base,
    )


def feet(start: int, stop: int, state: str = "dance", **kwargs) -> list[FootShadow]:
    return [foot(n, state, side=s, **kwargs) for n in range(start, stop) for s in (0, 1)]


def only(report: cs.ShadowReport) -> cs.FigureShadows:
    assert len(report.figures) == 1
    return report.figures[0]


def test_the_planted_lift_and_the_tolerances_are_named_constants() -> None:
    assert cs.PLANTED_LIFT == 12.0
    assert cs.CENTRE_TOL == 1.0
    assert (cs.WIDTH_TOL, cs.OPACITY_TOL) == (0.02, 0.01)


def test_the_size_rule_shrinks_and_fades_a_shadow_as_its_foot_lifts() -> None:
    assert cs.shadow_size(0.0, 80.0) == pytest.approx((80.0, 0.38))
    assert cs.shadow_size(130.0, 80.0) == pytest.approx((80.0 * (1 - 130 / 400), 0.38 * 0.5))
    assert cs.shadow_size(1000.0, 80.0) == pytest.approx((80.0 * 0.4, 0.38 * 0.15))


def test_shadows_under_every_planted_foot_pass() -> None:
    report = check(feet(0, 10) + feet(10, 20, "walk") + feet(20, 30, "stare") + feet(30, 40, "exit"))
    assert report.clean
    shadows = only(report)
    assert (shadows.feet, shadows.planted, shadows.findings) == (80, 80, ())


def test_a_planted_foot_with_no_shadow_is_a_finding_in_any_state() -> None:
    rows = feet(0, 10) + feet(10, 20, "stare", shadow=None)
    report = check(rows)
    assert not report.clean
    found = only(report).findings
    assert {f.kind for f in found} == {"missing"}
    assert sorted({f.frame for f in found}) == list(range(10, 20))
    assert {f.state for f in found} == {"stare"}
    assert len(found) == 20


def test_the_v2_shape_fails_outside_the_dance_and_the_fixed_shape_passes() -> None:
    v2 = (
        feet(0, 5, "walk", shadow=None)
        + feet(5, 10, "stare", shadow=None)
        + feet(10, 20)
        + feet(20, 25, "exit", shadow=None)
    )
    fixed = feet(0, 5, "walk") + feet(5, 10, "stare") + feet(10, 20) + feet(20, 25, "exit")
    states = {f.state for f in only(check(v2)).findings}
    assert states == {"walk", "stare", "exit"}
    assert check(fixed).clean


def test_a_lifted_foot_needs_no_shadow() -> None:
    rows = feet(0, 10) + [foot(10, side=0), foot(10, side=1, lift=80.0, shadow=None)]
    assert check(rows).clean
    assert only(check(rows)).planted == 21


def test_a_foot_at_the_planted_lift_is_planted() -> None:
    rows = feet(0, 4) + [foot(4, side=0, lift=cs.PLANTED_LIFT, shadow=None)]
    assert [f.kind for f in only(check(rows)).findings] == ["missing"]


def test_a_shadow_off_the_ankle_to_toe_midpoint_is_a_finding() -> None:
    rows = feet(0, 4) + [foot(4, side=0, shadow=500.0 + 16.0)]
    found = only(check(rows)).findings
    assert [(f.frame, f.side, f.kind) for f in found] == [(4, 0, "off-centre")]
    assert found[0].detail == pytest.approx(16.0)


def test_a_shadow_within_the_centre_tolerance_is_centred_and_past_it_is_not() -> None:
    assert check(feet(0, 4) + [foot(4, side=0, shadow=500.0 + cs.CENTRE_TOL)]).clean
    assert not check(feet(0, 4) + [foot(4, side=0, shadow=500.0 + cs.CENTRE_TOL + 0.5)]).clean


def test_a_planted_foot_under_a_lifted_foot_s_shadow_is_a_size_finding() -> None:
    """The swap lag: the planted foot keeps, for a frame, the small faint shadow its raised drawing had."""
    small_width, faint = cs.shadow_size(90.0, 60.0)
    rows = feet(0, 4) + [foot(4, side=0, width=small_width, opacity=faint)]
    assert [(f.frame, f.kind) for f in only(check(rows)).findings] == [(4, "size")]


def test_a_lifted_foot_with_a_planted_size_shadow_is_a_size_finding() -> None:
    rows = feet(0, 4) + [foot(4, side=1, lift=90.0, width=60.0, opacity=0.38)]
    assert [(f.frame, f.side, f.kind) for f in only(check(rows)).findings] == [(4, 1, "size")]


def test_a_lifted_foot_s_shadow_is_held_to_its_centre_too() -> None:
    rows = feet(0, 4) + [foot(4, side=1, lift=90.0, shadow=540.0)]
    assert [(f.side, f.kind) for f in only(check(rows)).findings] == [(1, "off-centre")]


def test_a_lifted_foot_with_its_shadow_drawn_by_the_rule_passes() -> None:
    assert check(feet(0, 4) + [foot(4, side=1, lift=90.0)]).clean


@pytest.mark.parametrize(("dw", "dop"), [(0.03, 0.0), (0.0, 0.015)])
def test_a_size_off_by_more_than_the_tolerance_is_a_finding(dw: float, dop: float) -> None:
    width, opacity = cs.shadow_size(0.0, 60.0)
    rows = feet(0, 4) + [foot(4, side=0, width=width * (1 + dw), opacity=opacity + dop)]
    assert [f.kind for f in only(check(rows)).findings] == ["size"]


def test_a_size_within_the_tolerance_passes() -> None:
    width, opacity = cs.shadow_size(0.0, 60.0)
    assert check(feet(0, 4) + [foot(4, side=0, width=width * 1.019, opacity=opacity + 0.009)]).clean


@pytest.mark.parametrize(("width", "opacity"), [(0.0, 0.38), (60.0, 0.0)])
def test_a_shadow_of_no_width_or_no_opacity_is_missing(width: float, opacity: float) -> None:
    rows = feet(0, 4) + [foot(4, side=0, width=width, opacity=opacity)]
    assert [f.kind for f in only(check(rows)).findings] == ["missing"]


def test_each_figure_is_reported_alone() -> None:
    rows = feet(0, 10, who="dev") + feet(0, 10, who="noor", shadow=None)
    report = check(rows)
    by = {f.figure: f for f in report.figures}
    assert by["dev"].findings == () and len(by["noor"].findings) == 20
    assert not report.clean


def test_an_empty_run_raises() -> None:
    with pytest.raises(ShadowCheckError):
        check([])


def test_a_repeated_foot_raises() -> None:
    with pytest.raises(ShadowCheckError):
        check([foot(0), foot(0)])


def test_the_error_is_a_library_error() -> None:
    assert issubclass(ShadowCheckError, SrstudioError) and issubclass(ShadowCheckError, ValueError)


@pytest.mark.parametrize(
    "bad",
    [
        dict(figure=""),
        dict(state=""),
        dict(frame=-1),
        dict(frame=1.5),
        dict(side=2),
        dict(side=True),
        dict(lift=math.nan),
        dict(lift=-1.0),
        dict(mid_x=math.inf),
        dict(shadow_x=math.nan),
        dict(shadow_width=-1.0),
        dict(shadow_opacity=1.5),
        dict(shadow_x=None),
        dict(base_width=0.0),
        dict(base_width=math.nan),
    ],
)
def test_a_malformed_record_raises(bad: dict[str, object]) -> None:
    fields = dict(
        figure="noor",
        frame=0,
        state="dance",
        side=0,
        lift=0.0,
        mid_x=500.0,
        shadow_x=500.0,
        shadow_width=60.0,
        shadow_opacity=0.38,
        base_width=60.0,
    )
    fields.update(bad)
    with pytest.raises(ShadowCheckError):
        FootShadow(**fields)  # type: ignore[arg-type]


def test_a_shadow_is_all_three_fields_or_none() -> None:
    no_shadow = FootShadow("noor", 0, "dance", 0, 0.0, 500.0, None, None, None, 60.0)
    assert [f.kind for f in only(check([no_shadow])).findings] == ["missing"]


def test_parse_refuses_a_missing_or_unknown_field_and_a_row_that_is_no_mapping() -> None:
    row = dict(
        figure="noor",
        frame=0,
        state="dance",
        side=0,
        lift=0.0,
        mid_x=500.0,
        shadow_x=500.0,
        shadow_width=60.0,
        shadow_opacity=0.38,
        base_width=60.0,
    )
    assert parse([row]) == (FootShadow(**row),)  # type: ignore[arg-type]
    with pytest.raises(ShadowCheckError):
        parse([{**row, "extra": 1}])
    with pytest.raises(ShadowCheckError):
        parse([{k: v for k, v in row.items() if k != "lift"}])
    with pytest.raises(ShadowCheckError):
        parse([["noor"]])

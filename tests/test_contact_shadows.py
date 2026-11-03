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
    width: float = 60.0,
    opacity: float = 0.38,
    who: str = "noor",
) -> FootShadow:
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
    )


def feet(start: int, stop: int, state: str = "dance", **kwargs) -> list[FootShadow]:
    return [foot(n, state, side=s, **kwargs) for n in range(start, stop) for s in (0, 1)]


def only(report: cs.ShadowReport) -> cs.FigureShadows:
    assert len(report.figures) == 1
    return report.figures[0]


def test_the_planted_lift_and_centre_share_are_named_constants() -> None:
    assert cs.PLANTED_LIFT == 12.0
    assert cs.CENTRE_SHARE == 0.25


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
    rows = feet(0, 4) + [foot(4, side=0, shadow=500.0 + 0.25 * 60.0 + 1.0)]
    found = only(check(rows)).findings
    assert [(f.frame, f.side, f.kind) for f in found] == [(4, 0, "off-centre")]
    assert found[0].detail == pytest.approx(16.0)


def test_a_shadow_within_a_quarter_of_its_width_is_centred() -> None:
    assert check(feet(0, 4) + [foot(4, side=0, shadow=500.0 + 0.25 * 60.0)]).clean


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
    )
    fields.update(bad)
    with pytest.raises(ShadowCheckError):
        FootShadow(**fields)  # type: ignore[arg-type]


def test_a_shadow_is_all_three_fields_or_none() -> None:
    no_shadow = FootShadow("noor", 0, "dance", 0, 0.0, 500.0, None, None, None)
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
    )
    assert parse([row]) == (FootShadow(**row),)  # type: ignore[arg-type]
    with pytest.raises(ShadowCheckError):
        parse([{**row, "extra": 1}])
    with pytest.raises(ShadowCheckError):
        parse([{k: v for k, v in row.items() if k != "lift"}])
    with pytest.raises(ShadowCheckError):
        parse([["noor"]])

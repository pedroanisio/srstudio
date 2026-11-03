"""A figure may not jump between two frames past 1.5 times its own largest dance step (ADR pending)."""

from __future__ import annotations

import math

import pytest

from srstudio import figure_steps as fs
from srstudio.errors import SrstudioError
from srstudio.figure_steps import FigureFrame, FigureStepError, check, parse


def frame(
    n: int, state: str = "dance", *, hip: float | None = None, crown: float = 500.0, shot: int = 0, who: str = "noor"
):
    x = 100.0 + 10.0 * n if hip is None else hip
    return FigureFrame(
        figure=who, frame=n, state=state, shot=shot, hip_x=x, box=(x - 50, crown, x + 50, 1400.0), crown_y=crown
    )


def dance(start: int = 0, stop: int = 20, **kwargs) -> list[FigureFrame]:
    return [frame(n, **kwargs) for n in range(start, stop)]


def only(report: fs.StepReport) -> fs.FigureSteps:
    assert len(report.figures) == 1
    return report.figures[0]


def test_the_threshold_is_a_named_constant_of_one_and_a_half() -> None:
    assert fs.NORMAL_STEP_LIMIT == 1.5


def test_a_clean_figure_passes_and_reports_its_normal_step_per_measure() -> None:
    report = check(dance())
    steps = only(report)
    assert report.clean
    assert steps.findings == ()
    assert steps.normal == {"hip": 10.0, "box": 10.0, "crown": 0.0}
    assert steps.dance_steps == 19


def test_a_state_change_inside_the_limit_is_clean() -> None:
    rows = dance() + [frame(20, "exit", hip=100.0 + 10.0 * 19 + 15.0)]
    assert check(rows).clean


def test_a_snapped_hip_at_a_state_change_is_a_finding_on_its_frame() -> None:
    rows = [frame(n, "stare", hip=100.0) for n in range(5)] + dance(5, 25)
    steps = only(check(rows))
    found = {(f.measure, f.frame, f.state_change) for f in steps.findings}
    assert ("hip", 5, True) in found
    assert ("box", 5, True) in found
    snap = next(f for f in steps.findings if f.measure == "hip")
    assert snap.step == pytest.approx(50.0)
    assert snap.limit == pytest.approx(15.0)
    assert snap.states == ("stare", "dance")
    assert steps.largest["hip"] == (50.0, 5)


def test_a_crown_pop_is_a_finding_even_with_the_hip_still() -> None:
    wiggle = [frame(n, crown=500.0 + (n % 2) * 4.0) for n in range(20)]
    rows = wiggle + [frame(20, "exit", crown=440.0)]
    steps = only(check(rows))
    assert [(f.measure, f.frame) for f in steps.findings if f.measure == "crown"] == [("crown", 20)]
    assert steps.normal["crown"] == 4.0


def test_a_step_past_the_limit_outside_a_state_change_is_a_finding_too() -> None:
    rows = dance() + [frame(20, "exit", hip=300.0), frame(21, "exit", hip=340.0)]
    late = [f for f in only(check(rows)).findings if f.frame == 21 and f.measure == "hip"]
    assert len(late) == 1
    assert not late[0].state_change


def test_a_figure_with_no_dance_span_is_not_clean_and_says_so() -> None:
    report = check([frame(n, "walk") for n in range(10)])
    steps = only(report)
    assert not report.clean
    assert steps.status == "no-dance-span"
    assert steps.normal == {"hip": None, "box": None, "crown": None}
    assert steps.findings == ()


def test_one_dance_frame_is_no_dance_span() -> None:
    assert only(check([frame(0), frame(1, "exit")])).status == "no-dance-span"


def test_each_figure_is_held_to_its_own_step() -> None:
    fast = [frame(n, who="dev", hip=100.0 + 40.0 * n) for n in range(10)]
    slow = [frame(n, who="noor", hip=100.0 + 10.0 * n) for n in range(10)] + [frame(10, "exit", hip=250.0)]
    report = check(fast + slow)
    assert [s.figure for s in report.figures] == ["dev", "noor"]
    assert report.figures[0].findings == ()
    assert any(f.measure == "hip" for f in report.figures[1].findings)
    assert not report.clean


def test_a_camera_cut_is_not_a_step() -> None:
    rows = dance(0, 10) + dance(10, 20, shot=1, hip=900.0)
    steps = only(check(rows))
    assert steps.cuts == 1
    assert steps.findings == ()


def test_frames_off_screen_are_not_a_step() -> None:
    rows = dance(0, 10) + dance(20, 30, hip=900.0)
    steps = only(check(rows))
    assert steps.gaps == 1
    assert steps.findings == ()


def test_records_may_arrive_in_any_order() -> None:
    assert check(list(reversed(dance()))).clean


def test_an_empty_run_raises() -> None:
    with pytest.raises(FigureStepError, match="no frames"):
        check([])


def test_the_error_is_a_library_error() -> None:
    assert issubclass(FigureStepError, SrstudioError)
    assert issubclass(FigureStepError, ValueError)


def test_a_repeated_frame_raises() -> None:
    with pytest.raises(FigureStepError, match="twice"):
        check([frame(1), frame(1)])


@pytest.mark.parametrize(
    "bad",
    [
        {"hip_x": math.nan},
        {"crown_y": math.inf},
        {"frame": -1},
        {"frame": True},
        {"frame": 1.5},
        {"shot": -1},
        {"figure": ""},
        {"state": ""},
        {"box": (10.0, 10.0, 5.0, 20.0)},
        {"box": (10.0, 30.0, 20.0, 20.0)},
        {"box": (1.0, 2.0, 3.0)},
        {"box": (1.0, 2.0, math.nan, 4.0)},
        {"hip_x": "100"},
    ],
)
def test_a_malformed_record_raises(bad: dict[str, object]) -> None:
    row: dict[str, object] = dict(
        figure="noor", frame=1, state="dance", shot=0, hip_x=1.0, box=(0.0, 0.0, 2.0, 2.0), crown_y=0.0
    )
    with pytest.raises(FigureStepError):
        parse([{**row, **bad}])


def test_parse_refuses_a_missing_or_unknown_field_and_a_row_that_is_no_mapping() -> None:
    row = dict(figure="noor", frame=1, state="dance", shot=0, hip_x=1.0, box=[0.0, 0.0, 2.0, 2.0], crown_y=0.0)
    assert parse([row])[0].box == (0.0, 0.0, 2.0, 2.0)
    with pytest.raises(FigureStepError, match="crown_y"):
        parse([{k: v for k, v in row.items() if k != "crown_y"}])
    with pytest.raises(FigureStepError, match="extra"):
        parse([{**row, "extra": 1}])
    with pytest.raises(FigureStepError, match="mapping"):
        parse(["noor"])


# Travel: a slide judged by its change in step (option A), and the four shapes of the v5 pops.


def travel(start: int, stop: int, xs: list[float], state: str = "walk") -> list[FigureFrame]:
    return [frame(n, state, hip=x) for n, x in zip(range(start, stop), xs, strict=True)]


def wobble(start: int = 0, stop: int = 20, hip: float = 500.0) -> list[FigureFrame]:
    """A dance on the spot: the hip sways 10 px, so its largest step is 10 and its largest change in step 20."""
    return [frame(n, hip=hip + (10.0 if n % 2 else 0.0)) for n in range(start, stop)]


def ramp(n: int, start: float, end: float, ease) -> list[float]:
    return [start + (end - start) * ease(k / (n - 1)) for k in range(n)]


def test_the_travel_states_are_named() -> None:
    assert {"walk", "jog", "exit"} <= fs.TRAVEL


def test_a_cubic_in_slide_passes_although_its_steps_pass_the_plain_limit() -> None:
    rows = wobble(0, 20) + travel(20, 32, ramp(12, 510.0, 900.0, lambda u: u**3), "exit")
    steps = only(check(rows))
    largest, limit = steps.largest["hip"], steps.limit["hip"]
    assert largest is not None and limit is not None
    assert largest[0] > 3 * limit
    assert steps.findings == ()
    assert steps.normal_change == {"hip": 20.0, "box": 20.0, "crown": 0.0}


def test_a_slide_with_a_one_frame_jump_fails() -> None:
    xs = ramp(12, 510.0, 900.0, lambda u: u**3)
    xs[6] += 80.0
    steps = only(check(wobble(0, 20) + travel(20, 32, xs, "exit")))
    assert {(f.measure, f.frame, f.rule) for f in steps.findings} >= {("hip", 26, "travel"), ("hip", 27, "travel")}


def test_a_snap_between_two_travel_states_is_judged_by_the_plain_step() -> None:
    rows = wobble(0, 20) + travel(20, 25, [900.0, 890.0, 880.0, 870.0, 860.0], "walk")
    rows += travel(25, 30, [760.0, 750.0, 740.0, 730.0, 720.0], "jog")
    snap = [f for f in only(check(rows)).findings if f.frame == 25 and f.measure == "hip"]
    assert len(snap) == 1 and snap[0].rule == "step" and snap[0].states == ("walk", "jog")


def test_the_first_step_on_screen_has_no_change_to_judge() -> None:
    rows = travel(0, 6, [1300.0, 1250.0, 1205.0, 1165.0, 1130.0, 1100.0]) + wobble(6, 26, hip=1100.0)
    steps = only(check(rows))
    assert [f for f in steps.findings if f.frame <= 5] == []
    assert steps.unjudged == 1


def blended(a: float, b: float, n: int) -> list[float]:
    return [a + (b - a) * (3 * u * u - 2 * u**3) for u in ((k + 1) / n for k in range(n))]


def test_a_stare_to_dance_hip_snap_fails_and_its_blend_passes() -> None:
    stare = [frame(n, "stare", hip=380.0) for n in range(10)]
    snapped = only(check(stare + wobble(10, 30)))
    assert ("hip", 10) in {(f.measure, f.frame) for f in snapped.findings}
    eased = stare + [frame(10 + k, "stare", hip=x) for k, x in enumerate(blended(380.0, 500.0, 12))] + wobble(22, 42)
    assert only(check(eased)).findings == ()


def test_a_dance_to_exit_snap_fails_and_its_blend_passes() -> None:
    exit_ = [1.0, 2.0, 4.0, 8.0, 14.0, 22.0]
    snapped = wobble(0, 20) + travel(20, 26, [400.0 + d for d in exit_], "exit")
    assert ("hip", 20) in {(f.measure, f.frame) for f in only(check(snapped)).findings}
    eased = wobble(0, 20) + [frame(20 + k, hip=x) for k, x in enumerate(blended(510.0, 400.0, 12))]
    eased += travel(32, 38, [400.0 + d for d in exit_], "exit")
    assert only(check(eased)).findings == ()


def test_a_walk_to_stare_drawing_pop_at_an_aligned_hip_is_a_box_finding_and_its_blend_passes() -> None:
    def drawn(n: int, state: str, half: float) -> FigureFrame:
        return FigureFrame("noor", n, state, 0, 500.0, (500.0 - half, 500.0, 500.0 + half, 1400.0), 500.0)

    def dance_(start: int) -> list[FigureFrame]:
        return [drawn(n, "dance", 50.0 + (8.0 if n % 2 else 0.0)) for n in range(start, start + 20)]

    popped = [drawn(n, "walk", 110.0) for n in range(5)] + [drawn(n, "stare", 50.0) for n in range(5, 10)] + dance_(10)
    found = {(f.measure, f.frame) for f in only(check(popped)).findings}
    assert ("box", 5) in found and ("hip", 5) not in found
    walk = [drawn(n, "walk", 110.0) for n in range(5)]
    walk += [drawn(5 + k, "walk", w) for k, w in enumerate(blended(110.0, 50.0, 12))]
    eased = walk + [drawn(n, "stare", 50.0) for n in range(17, 22)] + dance_(22)
    assert only(check(eased)).findings == ()


# A box edge the frame cuts is the frame's edge, not the figure's: it has no drawn change in step.


def entering(start: int, xs: list[float], state: str = "walk", *, flag: bool = True, edge: float = 1080.0):
    """A figure 500 px wide sliding in from past the right edge: its box's right side is cut at ``edge`` for the first
    four frames, then it clears the edge at speed."""
    rows = []
    for n, x in zip(range(start, start + len(xs)), xs, strict=True):
        right = x + 250
        cut = right > edge
        rows.append(
            FigureFrame(
                figure="noor",
                frame=n,
                state=state,
                shot=0,
                hip_x=x,
                box=(x - 250, 500.0, min(right, edge), 1400.0),
                crown_y=500.0,
                clipped=(False, False, cut and flag, False),
            )
        )
    return rows


def test_a_slide_whose_box_edge_leaves_the_frame_edge_passes_with_the_cut_named() -> None:
    xs = ramp(12, 1250.0, 650.0, lambda u: 1 - (1 - u) ** 3)
    steps = only(check(entering(0, xs) + wobble(12, 32, hip=650.0)))
    assert [f for f in steps.findings if f.measure == "box" and f.rule == "travel"] == []


def test_the_same_slide_with_the_cut_unnamed_reads_the_frame_edge_as_a_snap() -> None:
    xs = ramp(12, 1250.0, 650.0, lambda u: 1 - (1 - u) ** 3)
    steps = only(check(entering(0, xs, flag=False) + wobble(12, 32, hip=650.0)))
    assert any(f.measure == "box" and f.rule == "travel" for f in steps.findings)


def test_a_snap_in_an_edge_the_frame_does_not_cut_is_still_a_finding() -> None:
    xs = ramp(12, 1250.0, 650.0, lambda u: 1 - (1 - u) ** 3)
    rows = entering(0, xs)
    k = 9
    r = rows[k]
    rows[k] = FigureFrame(
        r.figure, r.frame, r.state, r.shot, r.hip_x, (r.box[0] - 80.0, *r.box[1:]), r.crown_y, r.clipped
    )
    steps = only(check(rows + wobble(12, 32, hip=650.0)))
    assert ("box", k, "travel") in {(f.measure, f.frame, f.rule) for f in steps.findings}


def test_a_cut_edge_inside_the_dance_does_not_loosen_its_change_in_step() -> None:
    """A dancer at the frame's edge whose cut edge jumps as the cut comes and goes: the jump is the frame's."""
    rows = []
    for n in range(20):
        x = 500.0 + (10.0 if n % 2 else 0.0)
        cut = n % 4 == 0
        right = 1080.0 if cut else x + 50
        rows.append(
            FigureFrame("noor", n, "dance", 0, x, (x - 50, 500.0, right, 1400.0), 500.0, (False, False, cut, False))
        )
    assert only(check(rows)).normal_change["box"] == pytest.approx(20.0)


@pytest.mark.parametrize("clipped", [(True, False, False), (1, 0, 0, 0), "none", (False, False, None, False)])
def test_a_malformed_cut_raises(clipped: object) -> None:
    with pytest.raises(FigureStepError, match="clipped"):
        FigureFrame("noor", 0, "dance", 0, 1.0, (0.0, 0.0, 2.0, 2.0), 0.0, clipped)  # type: ignore[arg-type]


def test_parse_reads_the_cut_and_defaults_it_to_none_cut() -> None:
    row = dict(figure="noor", frame=1, state="dance", shot=0, hip_x=1.0, box=[0.0, 0.0, 2.0, 2.0], crown_y=0.0)
    assert parse([row])[0].clipped == (False, False, False, False)
    assert parse([{**row, "clipped": [False, True, False, False]}])[0].clipped == (False, True, False, False)

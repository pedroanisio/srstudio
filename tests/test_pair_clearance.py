"""No two figures on screen touch unless the choreography says they do."""

from __future__ import annotations

import math

import pytest

from srstudio import pair_clearance as pc
from srstudio.errors import SrstudioError
from srstudio.pair_clearance import DeclaredContact, FigureBones, PairClearanceError, check, contacts, parse

HALF = 6.5  # a Stick limb 17 px wide at scale 0.768, halved
HEAD_R = 70.0


def stance(who: str, frame: int, hip_x: float, spread: float, *, half: float = HALF) -> FigureBones:
    """A stick figure in frame px standing with its feet ``spread`` px either side of its hip: the wide stance of a
    dance, where two figures side by side meet at the feet first."""
    hip, neck, head = (hip_x, 1100.0), (hip_x, 860.0), (hip_x, 860.0 - HEAD_R)
    knees = ((hip_x - spread / 2, 1270.0), (hip_x + spread / 2, 1270.0))
    feet = ((hip_x - spread, 1430.0), (hip_x + spread, 1430.0))
    hands = ((hip_x - 60.0, 1080.0), (hip_x + 60.0, 1080.0))
    bones = (
        (neck, hip),
        (hip, knees[0]),
        (knees[0], feet[0]),
        (hip, knees[1]),
        (knees[1], feet[1]),
        (neck, hands[0]),
        (neck, hands[1]),
    )
    return FigureBones(figure=who, frame=frame, bones=bones, head=(head[0], head[1], HEAD_R), half_width=half)


def wide_run(frames: range, gap_at: dict[int, float], spacing: float, base_spread: float = 120.0) -> list[FigureBones]:
    """Dev and Noor ``spacing`` px apart at the hip, both opening the same stance by ``gap_at[f]`` extra px on frame
    ``f``: their facing feet close in by twice that."""
    out = []
    for f in frames:
        spread = base_spread + gap_at.get(f, 0.0)
        out += [stance("dev", f, 400.0, spread), stance("noor", f, 400.0 + spacing, spread)]
    return out


def only(report: pc.ClearanceReport) -> pc.PairClearance:
    assert len(report.pairs) == 1
    return report.pairs[0]


# -- the three cases the 60 s payoff showed, as small stand-ins: a real build's poses come from a take that stays out
# -- of the repository, so its result is the build's QA report, not a test


def test_feet_meeting_on_one_frame_fail_on_that_frame_only():
    """A touch on one frame of a run, as the delay-38 cut's stance at spacing 420: that frame alone fails."""
    run = wide_run(range(1756, 1782), {1767: 60.0}, spacing=322.0)  # 420 canon at 0.768
    pair = only(check(run))
    assert [x.frame for x in pair.findings] == [1767]
    assert pair.nearest[1] == 1767 and pair.nearest[0] <= 0
    assert not check(run).clean


def test_feet_meeting_through_the_wide_stance_fail_on_every_frame_of_it():
    """A touch held through a wide stance, as delay 10 at spacing 420: every frame of it fails, no other."""
    opened = dict.fromkeys(range(1753, 1762), 60.0)
    run = wide_run(range(1740, 1768), opened, spacing=322.0)
    pair = only(check(run))
    assert [x.frame for x in pair.findings] == list(range(1753, 1762))
    assert all(x.distance <= 0 for x in pair.findings)
    assert pair.box_gap[0] < 0 and 1753 <= pair.box_gap[1] <= 1761


def test_the_same_stance_spaced_wider_passes_with_its_clearance():
    """The same stance 161 px further apart, as spacing 630 at scale 0.768, keeps its feet clear."""
    opened = dict.fromkeys(range(1753, 1762), 60.0)
    report = check(wide_run(range(1740, 1768), opened, spacing=483.0))  # 630 canon at 0.768
    pair = only(report)
    assert report.clean and pair.findings == ()
    # facing feet at 400 + 180 and 883 - 180: 123 px between centre lines, less both half widths
    assert pair.nearest == (pytest.approx(123.0 - 2 * HALF), 1753)
    assert pair.box_gap == (pytest.approx(123.0 - 2 * HALF), 1753)
    assert pair.frames == 28 and pair.pair == ("dev", "noor")


# -- declared contact ----------------------------------------------------------------------------------------------


def test_a_declared_window_clears_only_its_own_pair_and_frames():
    opened = dict.fromkeys(range(1753, 1762), 60.0)
    run = wide_run(range(1740, 1768), opened, spacing=322.0)
    # a third figure, Theo, standing on Noor's other side and meeting her on the same frames
    run += [stance("theo", f, 722.0 + 322.0, 120.0 + opened.get(f, 0.0)) for f in range(1740, 1768)]
    declared = contacts([{"figures": ["noor", "dev"], "first": 1755, "last": 1758}])
    report = check(run, declared)
    by_pair = {p.pair: p for p in report.pairs}
    assert [x.frame for x in by_pair["dev", "noor"].findings] == [1753, 1754, 1759, 1760, 1761]
    assert [x.frame for x in by_pair["noor", "theo"].findings] == list(range(1753, 1762))
    assert by_pair["dev", "theo"].findings == ()
    assert by_pair["dev", "noor"].declared == 4
    assert not report.clean


def test_a_declared_window_covering_every_contact_leaves_the_run_clean():
    opened = dict.fromkeys(range(1753, 1762), 60.0)
    run = wide_run(range(1740, 1768), opened, spacing=322.0)
    report = check(run, [DeclaredContact(("dev", "noor"), 1753, 1761)])
    assert report.clean and only(report).declared == 9


def test_no_declaration_allows_no_contact():
    run = wide_run(range(0, 3), {1: 60.0}, spacing=322.0)
    assert [x.frame for x in only(check(run, ())).findings] == [1]


@pytest.mark.parametrize(
    "row",
    [
        {"figures": ["dev", "noor"], "first": 3},  # missing last
        {"figures": ["dev", "noor"], "first": 3, "last": 4, "why": "hug"},  # unknown field
        {"figures": ["dev", "dev"], "first": 3, "last": 4},  # a figure with itself
        {"figures": ["dev"], "first": 3, "last": 4},
        {"figures": ["dev", "noor", "theo"], "first": 3, "last": 4},
        {"figures": "dev,noor", "first": 3, "last": 4},
        {"figures": ["dev", ""], "first": 3, "last": 4},
        {"figures": ["dev", 7], "first": 3, "last": 4},
        {"figures": ["dev", "noor"], "first": 5, "last": 4},  # backwards
        {"figures": ["dev", "noor"], "first": -1, "last": 4},
        {"figures": ["dev", "noor"], "first": 1.0, "last": 4},
        {"figures": ["dev", "noor"], "first": True, "last": 4},
        ["dev", "noor", 3, 4],
    ],
)
def test_a_malformed_declaration_raises_a_typed_error(row):
    with pytest.raises(PairClearanceError) as caught:
        contacts([row])
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, ValueError)


def test_overlapping_declarations_for_one_pair_raise():
    with pytest.raises(PairClearanceError, match="overlap"):
        contacts(
            [{"figures": ["dev", "noor"], "first": 3, "last": 6}, {"figures": ["noor", "dev"], "first": 6, "last": 8}]
        )


def test_a_declaration_is_typed_and_its_pair_sorted():
    (d,) = contacts([{"figures": ["noor", "dev"], "first": 3, "last": 3}])
    assert d == DeclaredContact(("dev", "noor"), 3, 3)
    with pytest.raises(PairClearanceError):
        DeclaredContact(("noor", "dev"), 3, 3)  # built directly, the pair must already be sorted


# -- geometry ----------------------------------------------------------------------------------------------------


def bones_of(who, frame, *segs, head=None, half=0.0):
    return FigureBones(figure=who, frame=frame, bones=tuple(segs), head=head, half_width=half)


def test_crossing_bones_are_at_distance_zero_less_their_widths():
    a = bones_of("a", 0, ((0.0, 0.0), (10.0, 10.0)), half=1.0)
    b = bones_of("b", 0, ((0.0, 10.0), (10.0, 0.0)), half=2.0)
    finding = only(check([a, b])).findings[0]
    assert finding.distance == pytest.approx(-3.0)


def test_parallel_bones_apart_by_their_gap_less_the_half_widths():
    a = bones_of("a", 0, ((0.0, 0.0), (0.0, 100.0)), half=3.0)
    b = bones_of("b", 0, ((20.0, 50.0), (20.0, 150.0)), half=4.0)
    pair = only(check([a, b]))
    assert pair.nearest == (pytest.approx(13.0), 0) and pair.findings == ()
    assert pair.box_gap == (pytest.approx(13.0), 0)


def test_an_endpoint_nearest_the_other_bone_measures_point_to_segment():
    a = bones_of("a", 0, ((0.0, 0.0), (10.0, 0.0)))
    b = bones_of("b", 0, ((13.0, 4.0), (30.0, 40.0)))
    assert only(check([a, b])).nearest[0] == pytest.approx(5.0)


def test_heads_are_discs_their_outline_included():
    a = bones_of("a", 0, ((0.0, 200.0), (0.0, 300.0)), head=(0.0, 100.0, 50.0), half=2.0)
    b = bones_of("b", 0, ((150.0, 200.0), (150.0, 300.0)), head=(150.0, 100.0, 50.0), half=2.0)
    assert only(check([a, b])).nearest[0] == pytest.approx(150.0 - 100.0 - 4.0)
    c = bones_of("c", 0, ((95.0, 100.0), (95.0, 300.0)), half=2.0)  # a bone into a's head
    near = {p.pair: p.nearest[0] for p in check([a, c]).pairs}
    assert near["a", "c"] == pytest.approx(95.0 - 50.0 - 4.0)


def test_a_box_gap_is_the_separation_along_the_clearer_axis_and_negative_inside():
    a = bones_of("a", 0, ((0.0, 0.0), (100.0, 100.0)))
    b = bones_of("b", 0, ((50.0, 150.0), (200.0, 300.0)))  # below a: 50 px apart in y, overlapping in x
    assert only(check([a, b])).box_gap[0] == pytest.approx(50.0)
    c = bones_of("c", 0, ((0.0, 100.0), (100.0, 0.0)))  # the other diagonal of a's box
    assert only(check([a, c])).box_gap[0] == pytest.approx(-100.0)


def test_only_frames_with_both_figures_count():
    run = [stance("dev", f, 400.0, 120.0) for f in range(0, 10)] + [
        stance("noor", f, 722.0, 120.0) for f in range(5, 8)
    ]
    pair = only(check(run))
    assert pair.frames == 3


def test_a_lone_figure_has_no_pair_and_is_clean():
    report = check([stance("dev", f, 400.0, 120.0) for f in range(3)])
    assert report.pairs == () and report.clean


def test_a_contact_declared_for_figures_never_on_screen_together_raises():
    with pytest.raises(PairClearanceError, match="never"):
        check(wide_run(range(3), {}, spacing=322.0), [DeclaredContact(("dev", "zed"), 0, 2)])


# -- records -----------------------------------------------------------------------------------------------------


def row(**kw):
    base = dict(figure="dev", frame=0, bones=[[[0, 0], [1, 1]]], head=[0, -10, 5], half_width=1.5)
    base.update(kw)
    return base


def test_parse_reads_a_build_record():
    (r,) = parse([row()])
    assert r.bones == (((0.0, 0.0), (1.0, 1.0)),) and r.head == (0.0, -10.0, 5.0) and r.half_width == 1.5
    (n,) = parse([row(head=None)])
    assert n.head is None


@pytest.mark.parametrize(
    "bad",
    [
        dict(frame=-1),
        dict(frame=1.0),
        dict(frame=True),
        dict(figure=""),
        dict(bones=[]),
        dict(bones=[[[0, 0]]]),
        dict(bones=[[[0, 0], [1, math.nan]]]),
        dict(bones=[[[0, 0], [1, "1"]]]),
        dict(bones="0,0,1,1"),
        dict(head=[0, 0]),
        dict(head=[0, 0, 0]),
        dict(head=[0, 0, -3]),
        dict(half_width=-1),
        dict(half_width=math.inf),
    ],
)
def test_a_malformed_record_raises(bad):
    with pytest.raises(PairClearanceError):
        parse([row(**bad)])


def test_parse_refuses_missing_and_unknown_fields():
    r = row()
    del r["half_width"]
    with pytest.raises(PairClearanceError, match="missing"):
        parse([r])
    with pytest.raises(PairClearanceError, match="unknown"):
        parse([row(state="dance")])
    with pytest.raises(PairClearanceError):
        parse(["dev"])


def test_one_figure_twice_on_a_frame_raises():
    with pytest.raises(PairClearanceError, match="twice"):
        check([stance("dev", 0, 400.0, 120.0), stance("dev", 0, 500.0, 120.0)])


def test_no_records_raise():
    with pytest.raises(PairClearanceError):
        check([])


# -- a Stick pose's bones ------------------------------------------------------------------------------------------


def test_rig_bones_are_the_drawn_skeleton_of_a_stick_pose():
    from srstudio import stick

    pose = stick.STANDING["stand"]
    segs, head = pc.rig_bones(pose)
    assert len(segs) == 11  # spine, two legs of thigh, shin and foot, two arms of upper arm and forearm
    assert head == (float(pose.head[0]), float(pose.head[1]))
    ends = {p for s in segs for p in s}
    for joint in (pose.neck, pose.hip, *pose.knees, *pose.feet, *pose.elbows, *pose.hands):
        assert (float(joint[0]), float(joint[1])) in ends
    assert (tuple(map(float, stick.foot_end(pose, 0))) in ends) and (tuple(map(float, stick.foot_end(pose, 1))) in ends)

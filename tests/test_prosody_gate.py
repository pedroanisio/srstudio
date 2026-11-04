"""The prosody gate at first delivery (ADR 0234 d): every reel's findings are listed, a reel recorded before the gate
reads "unmeasured" and is never refused, a reel recorded to it is refused on any finding no reason waives, its verdict
is the gate's run again rather than the one recorded, and a waived finding is listed with its reason."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from srstudio import prosody_gate
from srstudio.prosody_gate import UNMEASURED, Reading
from srstudio.releases import Release
from srstudio.social import InstagramPost
from support.prosody import timeline


def release(slug: str) -> Release:
    return Release(slug, InstagramPost(title="t", description="d"), video=f"{slug}-video")


def recorded(root: Path, slug: str, document: object) -> None:
    (root / slug).mkdir(parents=True, exist_ok=True)
    text = document if isinstance(document, str) else json.dumps(document)
    (root / slug / "timeline.json").write_text(text)


def gated(timeline_: dict, *, passed: bool = True) -> dict:
    """The timeline as :func:`srstudio.takes.record` writes it: with its prosody section."""
    return timeline_ | {"prosody": timeline_.get("prosody", {}) | {"targets": {}, "findings": [], "passed": passed}}


def late_end(t: dict) -> dict:
    t["duration"] = 9.0  # 3.3 s of breath after the button
    return t


def read(root: Path, **documents: object) -> dict[str, Reading]:
    for slug, document in documents.items():
        if document is not None:
            recorded(root, slug, document)
    releases = {slug: release(slug) for slug in documents}
    return prosody_gate.read(releases, root, {slug: f"{slug}-video" for slug in documents})


# -- advisory everywhere ------------------------------------------------------------------------------------------
def test_a_reel_recorded_before_the_gate_reads_unmeasured_and_is_never_refused(tmp_path):
    old = late_end(timeline())  # it would fail the gate, had it been recorded to it
    readings = read(tmp_path, old=old, none=None)
    assert not readings["old"].measured and not readings["old"].refused
    assert prosody_gate.refusals(readings) == []
    assert prosody_gate.lines(readings) == [
        f"prosody none-video: {UNMEASURED} (no timeline.json), advisory",
        f"prosody old-video: {UNMEASURED} (timeline.json has no prosody section: recorded before the gate), advisory",
    ]


def test_a_clean_reel_reads_clean(tmp_path):
    readings = read(tmp_path, new=gated(timeline()))
    assert prosody_gate.lines(readings) == ["prosody new-video: clean"]
    assert prosody_gate.refusals(readings) == []


def test_a_reel_with_findings_lists_each_of_them(tmp_path):
    readings = read(tmp_path, new=gated(late_end(timeline()), passed=False))
    head, *rest = prosody_gate.lines(readings)
    assert head == "prosody new-video: REFUSED"
    assert rest == ["  take 04: end_breath 3.300 outside 0.3..1.2"]


# -- refusing only reels recorded to the gate ----------------------------------------------------------------------
def test_a_reel_recorded_to_the_gate_with_an_unwaived_finding_is_refused(tmp_path):
    (drift,) = prosody_gate.refusals(read(tmp_path, new=gated(late_end(timeline()), passed=False)))
    assert drift.name == "new-video"
    assert "prosody: take 04: end_breath 3.300 outside 0.3..1.2" in drift.reason
    assert "waive a target with its reason" in drift.reason


def test_the_recorded_verdict_is_not_trusted_the_gate_runs_again(tmp_path):
    stale = gated(late_end(timeline()), passed=True)  # says it passed; its numbers say otherwise
    (drift,) = prosody_gate.refusals(read(tmp_path, new=stale))
    assert "end_breath" in drift.reason


@pytest.mark.parametrize(
    ("document", "match"),
    [
        ("{not json", "timeline.json cannot be read"),
        ("[1, 2]", "timeline.json is not an object"),
        ({"items": [{"id": "01", "actor": "dev"}], "duration": 1.0, "prosody": {}}, "not measured"),
        ({"items": "x", "prosody": {}}, "not a timeline"),
        (gated(timeline()) | {"prosody": []}, "prosody is not an object"),
    ],
)
def test_a_timeline_the_gate_cannot_read_is_refused_not_passed(tmp_path, document, match):
    readings = read(tmp_path, bad=document)
    assert readings["bad"].refused and match in readings["bad"].error
    (drift,) = prosody_gate.refusals(readings)
    assert drift.name == "bad-video" and match in drift.reason
    assert prosody_gate.lines(readings)[0].startswith("prosody bad-video: REFUSED, ")


# -- waivers reach the report -------------------------------------------------------------------------------------
def test_a_waived_finding_passes_and_its_reason_is_in_the_report(tmp_path):
    t = late_end(timeline())
    t["items"][3]["direction"]["waive"] = [{"check": "end_breath", "reason": "the silence after is the joke"}]
    readings = read(tmp_path, new=gated(t, passed=True))
    assert prosody_gate.refusals(readings) == []
    assert prosody_gate.lines(readings) == [
        "prosody new-video: passes on its waivers",
        "  take 04: end_breath 3.300 outside 0.3..1.2 (waived: the silence after is the joke)",
    ]


def test_a_reel_waiver_reaches_the_report_too(tmp_path):
    t = timeline()
    for it in t["items"]:  # every line at 4.3 words a second: the reel over 3.6
        p = it["prosody"]
        n = int(4.3 * (p["last"] - p["first"]))
        p["words"] += [{"text": "w", "db": -20.0, "hz": 150.0}] * (n - len(p["words"]))
        p["words_per_second"] = round(n / (p["last"] - p["first"]), 3)
    t["prosody"] = {"waive": [{"check": "reel_pace", "reason": "an auctioneer sketch is fast"}]}
    lines = prosody_gate.lines(read(tmp_path, fast=gated(t)))
    assert lines[0] == "prosody fast-video: passes on its waivers"
    assert "(waived: an auctioneer sketch is fast)" in lines[1] and "reel: reel_pace" in lines[1]

"""The engine's strict findings at first delivery, and the records that clear a false one (ADR 0078)."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from srstudio import releases as release_files
from srstudio import strict_gate
from srstudio.cli import main
from srstudio.releases import Release
from srstudio.social import _ENTRY_KEYS, MANIFEST, MANIFEST_VERSION, InstagramPost
from srstudio.strict_gate import Cleared, Contrast, Fit, OnScreen, Record, StrictError, parse_record, strict_defects
from support.native import FONT

SLUG = "the-card"
VIDEO = "The_Card"
FPS = 24
SCENE = b'<scene><project width="108" height="192" fps="24" duration="2"/></scene>'
FILL, BACK = "#000000", "#ffffff"
SHORT = {
    "code": "LEG-SHORT",
    "severity": "warning",
    "path": "/scene/composition/group[1]/layer",
    "node": "card-layer",
    "time": [0.0, 0.375],
    "measured": 0.375,
    "limit": 0.8333,
    "unit": "s",
    "message": 'text "card-layer": drawn for 0.375 s (minimum 0.8333 s)',
}
DIM = {**SHORT, "code": "LEG-CONTRAST", "node": "sign-layer", "time": [1.0, 1.0], "measured": 3.9, "limit": 4.5}
CUT = {
    **SHORT,
    "code": "TXT-FIT",
    "node": "name-layer",
    "time": [0.0, 0.5],
    "measured": 60.0,
    "limit": 0.0,
    "unit": "px",
    "message": 'text "name-layer" is cut: it reaches 60 px past its box (clipped) or out of the frame',
}
POST = InstagramPost("A card", "A card that stays up.", ("#comedy",))
NOTE = {"code": "INERT-I13", "severity": "info", "path": "/scene/effects/effect[1]", "message": "an unread attribute"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture(scope="session")
def master(tmp_path_factory) -> Path:
    """Two seconds of a picture that changes on every frame: a frame cited by the wrong number does not match."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg decodes the frames")
    path = tmp_path_factory.mktemp("master") / "master.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=size=108x192:rate=24:duration=2",
         "-pix_fmt", "yuv420p", "-c:v", "libx264", "-preset", "ultrafast", str(path)],
        check=True,
    )  # fmt: skip
    return path


def still(video: Path, frame: int, out: Path) -> None:
    """Frame ``frame`` of ``video`` as a PNG, decoded as an author's measuring tool decodes it."""
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf", f"select=eq(n\\,{frame})", "-fps_mode", "passthrough",
         "-frames:v", "1", str(out)],
        check=True,
    )  # fmt: skip


class Reel:
    """A built, rendered reel on disk: its scene, report, video and the frames an author cut from the video."""

    def __init__(self, root: Path, master: Path) -> None:
        self.episodes, self.renders, self.records = root / "episodes", root / "renders", root / "strict"
        self.project = self.episodes / SLUG
        self.project.mkdir(parents=True)
        self.renders.mkdir()
        self.records.mkdir()
        (self.project / f"{SLUG}.scene.xml").write_bytes(SCENE)
        self.video = self.renders / f"{VIDEO}.mp4"
        shutil.copy(master, self.video)
        for frame in (0, 24, 47):
            still(master, frame, self.project / "qa" / "strict" / f"{frame}.png")
        self.report([SHORT])

    def report(self, findings: list[dict], **fields) -> None:
        document = {
            "format": "scene-render-report/1",
            "engine": {"name": "rs-scene-render", "version": "0.8.0"},
            "scene": {"sha256": sha(SCENE), "version": "1.1"},
            "output": {"id": "main", "width": 108, "height": 192, "start": 0.0, "end": 2.0},
            "findings": findings,
            **fields,
        }
        (self.project / "qa" / "render-report.json").write_text(json.dumps(document))

    def record(self, *cleared: dict, **fields) -> dict:
        document = {
            "schema_version": "1.0.0",
            "slug": SLUG,
            "scene_sha256": sha(SCENE),
            "video_sha256": sha(self.video.read_bytes()),
            "fps": FPS,
            "author": "worskpace-b1",
            "reviewer": "worskpace-e5",
            "cleared": list(cleared) or [on_screen()],
            **fields,
        }
        (self.records / f"{SLUG}.json").write_text(json.dumps(document))
        return document

    def defects(self, first: dict[str, str] | None = None) -> list[str]:
        releases = {SLUG: Release(SLUG, POST, video=VIDEO)}
        found = strict_defects(releases, self.episodes, self.renders, first or {SLUG: VIDEO}, self.records)
        return [str(d) for d in found]


def frame(number: int) -> dict:
    return {"frame": number, "path": f"qa/strict/{number}.png"}


def on_screen(**fields) -> dict:
    """A whole, true clearing of :data:`SHORT`: frames 0 to 47, two seconds."""
    measurement = {"first_frame": 0, "last_frame": 47, "seconds": 2.0, "minimum": 0.8333}
    return {
        "code": "LEG-SHORT",
        "node": "card-layer",
        "at": 0.0,
        "measurement": {**measurement, **fields.pop("measurement", {})},
        "frames": [frame(0), frame(47)],
        **fields,
    }


def measured_contrast(**fields) -> dict:
    """A whole, true clearing of :data:`DIM`: black on white at its worst frame."""
    measurement = {"first_frame": 0, "last_frame": 47, "lowest_frame": 24, "fill": FILL, "back": BACK, "ratio": 21.0,
                   "minimum": 4.5}  # fmt: skip
    return {
        "code": "LEG-CONTRAST",
        "node": "sign-layer",
        "at": 1.0,
        "measurement": {**measurement, **fields.pop("measurement", {})},
        "frames": [frame(24)],
        **fields,
    }


def fitted(**fields) -> dict:
    """A whole, true clearing of :data:`CUT`: cut while it comes in, inside its card from frame 24 to frame 47."""
    measurement = {"first_frame": 0, "rest_frame": 24, "last_frame": 47, "text": [20, 90, 80, 110],
                   "box": [10, 80, 100, 120], "limit": 0}  # fmt: skip
    return {
        "code": "TXT-FIT",
        "node": "name-layer",
        "at": 0.0,
        "measurement": {**measurement, **fields.pop("measurement", {})},
        "frames": [frame(0), frame(24), frame(47)],
        **fields,
    }


def record(*cleared: dict, **fields) -> dict:
    return {
        "schema_version": "1.0.0",
        "slug": SLUG,
        "scene_sha256": "a" * 64,
        "video_sha256": "b" * 64,
        "fps": FPS,
        "author": "worskpace-b1",
        "reviewer": "worskpace-e5",
        "cleared": list(cleared) or [on_screen()],
        **fields,
    }


@pytest.fixture
def reel(tmp_path, master) -> Reel:
    return Reel(tmp_path, master)


# -- the record ----------------------------------------------------------------------------------------------------
def test_a_whole_record_parses_into_its_types():
    parsed = parse_record(record(on_screen(), measured_contrast()))
    assert isinstance(parsed, Record) and parsed.slug == SLUG and parsed.reviewer == "worskpace-e5"
    short, dim = parsed.cleared
    assert isinstance(short, Cleared) and isinstance(short.measurement, OnScreen)
    assert short.measurement.seconds == 2.0 and short.frames[1].frame == 47
    assert isinstance(dim.measurement, Contrast) and dim.measurement.ratio == 21.0
    assert isinstance(parse_record(record(fitted())).cleared[0].measurement, Fit)


def edited(path: tuple, value) -> dict:
    """A true record with the value at ``path`` replaced."""
    document = copy.deepcopy(record())
    where = document
    for key in path[:-1]:
        where = where[key]
    where[path[-1]] = value
    return document


def without(path: tuple) -> dict:
    document = edited(path, None)
    where = document
    for key in path[:-1]:
        where = where[key]
    del where[path[-1]]
    return document


FIRST = ("cleared", 0)
MEASURED = (*FIRST, "measurement")


@pytest.mark.parametrize(
    ("document", "said"),
    [
        (None, "not an object"),
        ([], "not an object"),
        (record(colour=1), "unknown field colour"),
        (edited((*FIRST, "colour"), 1), "unknown field colour"),
        (edited((*MEASURED, "colour"), 1), "unknown field colour"),
        (edited((*FIRST, "frames", 0, "colour"), 1), "unknown field colour"),
        (without(("author",)), "missing field author"),
        (without(("reviewer",)), "missing field reviewer"),
        (without((*FIRST, "measurement")), "missing field measurement"),
        (without((*MEASURED, "seconds")), "missing field seconds"),
        (edited(("schema_version",), "2.0.0"), "version '2.0.0'"),
        (edited(("cleared",), []), "clears nothing"),
        (edited(("slug",), "Not A Slug"), "slug"),
        (edited(("scene_sha256",), "abc"), "scene_sha256"),
        (edited(("video_sha256",), "abc"), "video_sha256"),
        (edited(("fps",), 0), "fps"),
        (edited(("fps",), True), "fps"),
        (edited(("author",), "  "), "author"),
        (edited(("reviewer",), "worskpace-b1"), "the reviewer is the author"),
        (edited(("reviewer",), " WORSKPACE-B1 "), "the reviewer is the author"),
        (edited((*FIRST, "code"), "TXT-OVERFLOW"), "TXT-OVERFLOW is not a finding frames can prove false"),
        (edited((*FIRST, "code"), "LEG-SPEED"), "LEG-SPEED is not a finding frames can prove false"),
        (edited((*FIRST, "node"), ""), "node"),
        (edited((*FIRST, "at"), "soon"), "at"),
        (edited((*FIRST, "at"), float("nan")), "at"),
        (edited((*FIRST, "at"), True), "at"),
        (edited((*MEASURED, "first_frame"), -1), "first_frame"),
        (edited((*MEASURED, "first_frame"), 1.5), "first_frame"),
        (edited((*MEASURED, "first_frame"), 48), "first frame 48 is after the last 47"),
        (edited((*MEASURED, "seconds"), 9.0), "48 frames at 24 fps are 2.000 s, not 9.000 s"),
        (edited((*MEASURED, "minimum"), 0), "minimum"),
        (edited((*MEASURED, "minimum"), 3.0), "2.000 s does not reach the minimum of 3"),
        (edited((*FIRST, "frames"), []), "no frame"),
        (edited((*FIRST, "frames"), [frame(0)]), "does not cite frame 47"),
        (edited((*FIRST, "frames"), [{"frame": 0, "path": "/etc/passwd"}, frame(47)]), "inside the project"),
        (edited((*FIRST, "frames"), [{"frame": 0, "path": "../other/0.png"}, frame(47)]), "inside the project"),
        (record(on_screen(), on_screen()), "clears LEG-SHORT card-layer at 0.000 twice"),
    ],
)
def test_a_record_that_proves_nothing_is_refused(document, said):
    with pytest.raises(StrictError, match=said):
        parse_record(document)


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ({"lowest_frame": 48}, "worst frame 48 is outside 0 to 47"),
        ({"ratio": 3.54, "fill": "#888888"}, r"3\.54:1 does not reach the minimum of 4\.5"),
        ({"ratio": 5.0}, r"#000000 on #ffffff is 21\.00:1, not 5\.00:1"),
        ({"fill": "black"}, "fill"),
        ({"back": "#ffff"}, "back"),
        ({"ratio": True}, "ratio"),
    ],
)
def test_a_contrast_that_does_not_beat_its_minimum_or_its_colours_is_refused(change, said):
    with pytest.raises(StrictError, match=said):
        parse_record(record(measured_contrast(measurement=change)))


@pytest.mark.parametrize(
    ("change", "said"),
    [
        ({"rest_frame": 48}, "rest frame 48 is outside 0 to 47"),
        ({"first_frame": 25}, "rest frame 24 is outside 25 to 47"),
        ({"rest_frame": True}, "rest_frame"),
        ({"text": [20, 90, 80]}, "text .* is not a left, top, right and bottom"),
        ({"box": "the card"}, "box .* is not a left, top, right and bottom"),
        ({"text": [20, 90, 80, 90.5]}, "text"),
        ({"text": [-1, 90, 80, 110]}, "text"),
        ({"text": [80, 90, 20, 110]}, r"text \[80, 90, 20, 110\] has no area"),
        ({"box": [10, 120, 100, 80]}, r"box \[10, 120, 100, 80\] has no area"),
        ({"text": [5, 90, 80, 110]}, "the text is 5 px past its box at rest, limit 0 px"),
        ({"text": [20, 70, 80, 110]}, "the text is 10 px past its box at rest, limit 0 px"),
        ({"text": [20, 90, 103, 110]}, "the text is 3 px past its box at rest, limit 0 px"),
        ({"text": [20, 90, 80, 121]}, "the text is 1 px past its box at rest, limit 0 px"),
        ({"limit": -1}, "limit -1 is below zero"),
        ({"limit": True}, "limit"),
        ({"seconds": 2.0}, "unknown field seconds"),
    ],
)
def test_a_text_that_does_not_fit_at_rest_is_refused(change, said):
    with pytest.raises(StrictError, match=said):
        parse_record(record(fitted(measurement=change)))


def test_a_fit_needs_every_measured_field():
    document = fitted()
    del document["measurement"]["rest_frame"]
    with pytest.raises(StrictError, match="missing field rest_frame"):
        parse_record(record(document))


@pytest.mark.parametrize("missing", [0, 24, 47])
def test_a_fit_must_cite_its_entrance_and_both_ends_of_its_rest(missing):
    frames = [frame(n) for n in (0, 24, 47) if n != missing]
    with pytest.raises(StrictError, match=f"does not cite frame {missing}"):
        parse_record(record(fitted(frames=frames)))


def test_a_contrast_must_cite_its_worst_frame():
    with pytest.raises(StrictError, match="does not cite frame 24"):
        parse_record(record(measured_contrast(frames=[frame(0)])))


def test_a_measurement_exactly_at_the_minimum_clears_as_the_engine_counts_it():
    """The engine raises the finding on ``shown < minimum``, so equal to it is not a finding."""
    parse_record(record(on_screen(measurement={"minimum": 2.0})))


# -- the gate ------------------------------------------------------------------------------------------------------
def test_a_clean_report_ships_and_needs_no_record(reel):
    reel.report([])
    assert reel.defects() == []


def test_information_is_not_counted_as_strict_does_not_count_it(reel):
    reel.report([NOTE])
    assert reel.defects() == []


@pytest.mark.parametrize("severity", ["warning", "error"])
def test_a_finding_nobody_cleared_is_refused_with_its_numbers(reel, severity):
    reel.report([{**SHORT, "severity": severity}])
    assert reel.defects() == [f"{VIDEO}: --strict {severity}: LEG-SHORT card-layer at 0.000 measured 0.375 of 0.8333 s"]


def test_a_real_finding_of_another_kind_is_refused_even_when_the_rest_are_cleared(reel):
    fit = {**SHORT, "code": "TXT-FIT", "node": "sign", "measured": None, "limit": None, "unit": None, "time": None}
    reel.report([SHORT, fit])
    reel.record(on_screen())
    assert reel.defects() == [f"{VIDEO}: --strict warning: TXT-FIT sign"]


def test_a_text_cut_only_while_it_comes_in_ships_on_its_measured_rest(reel):
    reel.report([CUT, NOTE])
    reel.record(fitted())
    assert reel.defects() == []


def test_a_text_that_rests_exactly_as_the_cut_ends_ships(reel):
    reel.report([{**CUT, "time": [0.0, 1.0]}])
    reel.record(fitted())
    assert reel.defects() == []


@pytest.mark.parametrize("window", [[0.0, 1.5], [1.5, 1.75]])
def test_a_cut_after_the_text_came_to_rest_is_a_real_finding(reel, window):
    """The publishing side's words are "only while it's thrown in": a text cut at rest, or leaving, is cut."""
    reel.report([{**CUT, "time": window}])
    reel.record(fitted(at=window[0]))
    assert reel.defects() == [
        f"{VIDEO}: TXT-FIT name-layer: the report has it cut until {window[1]:.3f} s, "
        "and frame 24 at 1.000 s is its rest"
    ]


def test_a_cut_at_no_time_cannot_be_put_before_a_rest(reel):
    reel.report([{**CUT, "time": None}])
    reel.record(fitted())
    assert f"{VIDEO}: --strict warning: TXT-FIT name-layer measured 60 of 0 px" in reel.defects()


@pytest.mark.parametrize(
    ("box", "text"), [([10, 80, 108, 120], [20, 90, 108, 110]), ([10, 80, 100, 200], [20, 90, 80, 192])]
)
def test_a_text_inside_a_box_that_leaves_the_frame_is_refused(reel, box, text):
    reel.report([CUT])
    reel.record(fitted(measurement={"box": box, "text": text}))
    assert reel.defects() == [f"{VIDEO}: TXT-FIT name-layer: the text at {text} leaves the 108x192 frame"]


def test_a_fit_s_limit_is_the_report_s_and_not_the_author_s(reel):
    reel.report([CUT])
    reel.record(fitted(measurement={"limit": 5, "text": [5, 90, 80, 110]}))
    assert reel.defects() == [f"{VIDEO}: TXT-FIT name-layer: the record's minimum 5 is not the report's 0.0"]


def test_a_fit_s_frames_are_held_to_the_master(reel):
    reel.report([CUT])
    reel.record(fitted(frames=[frame(0), {"frame": 24, "path": "qa/strict/47.png"}, frame(47)]))
    assert reel.defects() == [f"{VIDEO}: TXT-FIT name-layer: qa/strict/47.png is not frame 24 of the master"]


def test_the_listing_gives_a_fit_its_rest_and_its_margin():
    assert str(parse_record(record(fitted())).cleared[0].measurement) == (
        "inside its box from frame 24 to frame 47, 0 px past it, limit 0 px, thrown in from frame 0"
    )


def test_a_reel_whose_findings_are_all_proven_false_ships(reel):
    reel.report([SHORT, DIM, NOTE])
    reel.record(on_screen(), measured_contrast())
    assert reel.defects() == []


def test_one_finding_left_uncleared_holds_the_reel(reel):
    reel.report([SHORT, DIM])
    reel.record(on_screen())
    assert reel.defects() == [f"{VIDEO}: --strict warning: LEG-CONTRAST sign-layer at 1.000 measured 3.9 of 4.5 s"]


@pytest.mark.parametrize("name", ["report", "scene"])
def test_a_reel_with_no_report_to_read_is_refused(reel, name):
    """No report is not a clean report: a reel encoded without one has not been checked at all."""
    (reel.project / {"report": "qa/render-report.json", "scene": f"{SLUG}.scene.xml"}[name]).unlink()
    assert len(found := reel.defects()) == 1 and found[0].startswith(f"{VIDEO}: no ")


@pytest.mark.parametrize(
    ("text", "said"),
    [
        ("not json", "not JSON"),
        ("[]", "not an object"),
        ('{"format": "scene-render-report/2"}', "scene-render-report/2"),
        ('{"format": "scene-render-report/1"}', "no findings"),
    ],
)
def test_a_report_that_cannot_be_read_is_refused(reel, text, said):
    (reel.project / "qa" / "render-report.json").write_text(text)
    assert len(found := reel.defects()) == 1 and said in found[0]


def test_a_report_of_another_scene_is_refused(reel):
    reel.report([], scene={"sha256": "c" * 64})
    assert reel.defects() == [f"{VIDEO}: the render report is of another scene: render it again"]


@pytest.mark.parametrize(("start", "end"), [(0.0, 1.0), (0.5, 2.0)])
def test_a_report_of_part_of_the_reel_is_refused(reel, start, end):
    """``encode --start --end`` rewrites the report, so a short preview would clear what it never rendered."""
    reel.report([], output={"id": "main", "width": 108, "height": 192, "start": start, "end": end})
    assert reel.defects() == [f"{VIDEO}: the render report covers {start:g} to {end:g} s of 2 s"]


def test_a_stale_record_that_matches_nothing_is_refused(reel):
    reel.report([SHORT])
    reel.record(on_screen(), measured_contrast())
    assert reel.defects() == [f"{VIDEO}: the record clears LEG-CONTRAST sign-layer at 1.000, which the report has not"]


def test_a_record_on_a_clean_report_is_stale(reel):
    reel.report([])
    reel.record(on_screen())
    assert reel.defects() == [f"{VIDEO}: the record clears LEG-SHORT card-layer at 0.000, which the report has not"]


def test_a_record_for_another_node_clears_nothing(reel):
    reel.record(on_screen(node="other-layer"))
    assert reel.defects() == [
        f"{VIDEO}: the record clears LEG-SHORT other-layer at 0.000, which the report has not",
        f"{VIDEO}: --strict warning: LEG-SHORT card-layer at 0.000 measured 0.375 of 0.8333 s",
    ]


def test_the_rule_s_minimum_is_the_report_s_and_not_the_author_s(reel):
    reel.record(on_screen(measurement={"minimum": 0.5}))
    assert reel.defects() == [f"{VIDEO}: LEG-SHORT card-layer: the record's minimum 0.5 is not the report's 0.8333"]


def test_a_measurement_of_other_frames_does_not_clear_the_finding(reel):
    """Frames 0 to 24 are a second of something, but the finding is at 1.5 s: they measured another text."""
    reel.report([{**SHORT, "time": [1.5, 1.7]}])
    reel.record(on_screen(at=1.5, measurement={"last_frame": 24, "seconds": 25 / 24}, frames=[frame(0), frame(24)]))
    assert reel.defects() == [
        f"{VIDEO}: LEG-SHORT card-layer: frames 0 to 24 are not when the report says it was drawn, 1.500 to 1.700 s"
    ]


def test_a_record_of_another_scene_is_refused(reel):
    reel.record(on_screen(), scene_sha256="c" * 64)
    assert reel.defects() == [f"{VIDEO}: the record was measured on another scene"]


def test_a_record_of_another_master_is_refused(reel):
    reel.record(on_screen(), video_sha256="c" * 64)
    assert reel.defects() == [f"{VIDEO}: the record was measured on another master"]


def test_a_record_with_no_master_to_prove_it_on_is_refused(reel):
    reel.record(on_screen())
    reel.video.unlink()
    assert reel.defects() == [f"{VIDEO}: no rendered video to prove its record on"]


def test_a_master_that_cannot_be_read_refuses_its_reel(reel):
    reel.video.write_bytes(b"not a video")
    reel.record(on_screen())
    found = reel.defects()
    assert len(found) == 1 and found[0].startswith(f"{VIDEO}: {VIDEO}.mp4: cannot read its stream")


def test_a_false_frame_rate_cannot_stretch_the_time_on_screen(reel):
    """48 frames at 12 fps read four seconds; the file says 24, whatever the record says."""
    reel.record(on_screen(measurement={"seconds": 4.0}), fps=12)
    assert reel.defects() == [f"{VIDEO}: the record says 12 fps, the master 24"]


def test_a_cited_frame_that_is_not_on_disk_is_refused(reel):
    reel.record(on_screen())
    (reel.project / "qa" / "strict" / "47.png").unlink()
    assert reel.defects() == [f"{VIDEO}: LEG-SHORT card-layer: no evidence at qa/strict/47.png"]


def test_a_cited_frame_that_is_not_that_frame_of_the_master_is_refused(reel):
    """Evidence is the master's own frame: one from elsewhere in the reel is an argument, not a measurement."""
    shutil.copy(reel.project / "qa" / "strict" / "24.png", reel.project / "qa" / "strict" / "47.png")
    reel.record(on_screen())
    assert reel.defects() == [f"{VIDEO}: LEG-SHORT card-layer: qa/strict/47.png is not frame 47 of the master"]


def test_a_cited_frame_past_the_end_of_the_master_is_refused(reel):
    still(reel.video, 47, reel.project / "qa" / "strict" / "90.png")
    reel.record(on_screen(measurement={"last_frame": 90, "seconds": 91 / 24}, frames=[frame(0), frame(90)]))
    assert reel.defects() == [f"{VIDEO}: LEG-SHORT card-layer: qa/strict/90.png is not frame 90 of the master"]


def test_a_malformed_record_refuses_its_reel_and_nobody_else_s(reel):
    (reel.records / f"{SLUG}.json").write_text("{")
    found = reel.defects()
    assert len(found) == 1 and found[0].startswith(f"{VIDEO}: {SLUG}.json: not JSON")


def test_a_record_filed_under_another_name_is_refused(reel):
    reel.record(on_screen(), slug="another-reel")
    assert reel.defects() == [f"{VIDEO}: {SLUG}.json is the record of another-reel"]


def test_only_a_first_delivery_is_read(reel):
    """A published reel is frozen: nothing about it may be opened, least of all a report it was never gated on."""
    (reel.project / "qa" / "render-report.json").write_text("not json")
    assert strict_defects({}, reel.episodes, reel.renders, {}, reel.records) == []


def test_the_engine_s_own_report_of_a_card_across_a_cut(tmp_path, scene_render):
    """The whole contract, on a real encode: one text on screen for all 48 frames, in two layers. The engine calls it
    short, the gate refuses it, the frames clear it. One layer's scene gives byte-identical frames and no finding."""
    layers = '<group id="g0" start="0" end="0.35"><layer id="t0-layer" x="190" y="800" asset="t0"/></group>'
    layers += '<group id="g1" start="0.35" end="2"><layer id="t1-layer" x="190" y="800" asset="t1"/></group>'
    texts = "".join(
        f'<text id="t{i}" text="SAME CARD" width="700" height="200" size="76" color="#000000" align="center" '
        'fontAsset="f"/>'
        for i in range(2)
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?><scene version="1.1">'
        '<project width="1080" height="1920" fps="24" duration="2" background="#ffffff"/>'
        '<metadata title="t"><accessibility description="d" contrastCheck="warn" legibilityCheck="warn"/></metadata>'
        f'<assets><font id="f" src="{FONT.name}" family="DejaVu Sans" weight="700"/>{texts}</assets>'
        f"<composition>{layers}</composition></scene>"
    )
    episodes, renders, records = tmp_path / "episodes", tmp_path / "renders", tmp_path / "strict"
    project = episodes / SLUG
    (project / "qa").mkdir(parents=True)
    renders.mkdir()
    records.mkdir()
    shutil.copy(FONT, project / FONT.name)
    (project / f"{SLUG}.scene.xml").write_text(document)
    video = renders / f"{VIDEO}.mp4"
    subprocess.run(
        [str(scene_render), "encode", f"{SLUG}.scene.xml", "-o", str(video), "--report", "qa/render-report.json"],
        cwd=project, capture_output=True, text=True, check=True,
    )  # fmt: skip
    releases = {SLUG: Release(SLUG, POST, video=VIDEO)}
    first = {SLUG: VIDEO}
    refused = [str(d) for d in strict_defects(releases, episodes, renders, first, records)]
    assert refused == [f"{VIDEO}: --strict warning: LEG-SHORT t0-layer at 0.000 measured 0.375 of 0.8333 s"]
    still(video, 0, project / "qa" / "strict" / "0.png")
    still(video, 47, project / "qa" / "strict" / "47.png")
    (records / f"{SLUG}.json").write_text(
        json.dumps(
            record(
                on_screen(node="t0-layer"), scene_sha256=sha(document.encode()), video_sha256=sha(video.read_bytes())
            )
        )
    )
    assert strict_defects(releases, episodes, renders, first, records) == []


# -- the listing ---------------------------------------------------------------------------------------------------
def scripts(tmp_path: Path, *documents: dict) -> Path:
    """An episodes folder with one release per slug and a record of each document."""
    folder = tmp_path / "scripts"
    (folder / "posts").mkdir(parents=True)
    (folder / "strict").mkdir()
    (folder / "posts" / "__init__.py").write_text("")
    for document in documents:
        (folder / "strict" / f"{document['slug']}.json").write_text(json.dumps(document))
    return folder


def delivery(tmp_path: Path, *videos: str) -> Path:
    folder = tmp_path / "ig"
    folder.mkdir()
    entries = {v: dict.fromkeys(_ENTRY_KEYS, "a" * 64) for v in videos}
    (folder / MANIFEST).write_text(json.dumps({"version": MANIFEST_VERSION, "videos": entries}))
    return folder


def test_the_listing_names_shipped_reels_their_numbers_and_their_evidence():
    releases = {"the-card": Release("the-card", POST, video="The_Card"), "waits": Release("waits", POST)}
    shipped = parse_record(record(on_screen(), measured_contrast()))
    waiting = parse_record(record(slug="waits"))
    lines = strict_gate.listing([shipped, waiting], releases, {"The_Card": {}, "Another": {}})
    assert lines == [
        "the-card: 2 cleared, author worskpace-b1, reviewer worskpace-e5",
        "  LEG-SHORT card-layer: on screen 2.000 s, frames 0 to 47, minimum 0.8333 s",
        "    frame 0: qa/strict/0.png",
        "    frame 47: qa/strict/47.png",
        "  LEG-CONTRAST sign-layer: lowest 21.00:1 at frame 24, #000000 on #ffffff, minimum 4.5:1",
        "    frame 24: qa/strict/24.png",
        "1 of 2 delivered reels shipped under the strict rule; 1 record waiting to deliver: waits",
    ]


def test_the_listing_with_nothing_under_the_rule_says_so():
    assert strict_gate.listing([], {}, {"The_Card": {}}) == ["0 of 1 delivered reels shipped under the strict rule"]


def test_strict_prints_the_listing(tmp_path, monkeypatch, capsys):
    folder = scripts(tmp_path, record(slug="the-card"))
    monkeypatch.setattr(release_files, "load", lambda posts: {"the-card": Release("the-card", POST, video="The_Card")})
    assert main(["strict", "--scripts", str(folder), "--delivery", str(delivery(tmp_path, "The_Card"))]) == 0
    out = capsys.readouterr().out
    assert "the-card: 1 cleared" in out and "1 of 1 delivered reels shipped under the strict rule" in out


def test_strict_refuses_a_bad_record(tmp_path, monkeypatch, capsys):
    folder = scripts(tmp_path, record(slug="the-card", reviewer="worskpace-b1"))
    monkeypatch.setattr(release_files, "load", lambda posts: {"the-card": Release("the-card", POST, video="The_Card")})
    assert main(["strict", "--scripts", str(folder), "--delivery", str(delivery(tmp_path))]) == 2
    assert "the reviewer is the author" in capsys.readouterr().err


def test_strict_refuses_a_record_of_a_reel_with_no_release(tmp_path, monkeypatch, capsys):
    folder = scripts(tmp_path, record(slug="the-card"))
    monkeypatch.setattr(release_files, "load", lambda posts: {})
    assert main(["strict", "--scripts", str(folder), "--delivery", str(delivery(tmp_path))]) == 2
    assert "the-card.json: no release" in capsys.readouterr().err


def test_strict_with_no_manifest_says_so_rather_than_counting_zero(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(release_files, "load", lambda posts: {})
    assert main(["strict", "--scripts", str(scripts(tmp_path)), "--delivery", str(tmp_path / "nowhere")]) == 2
    assert "no delivery manifest" in capsys.readouterr().err


def test_every_record_in_the_tree_parses_and_names_a_release():
    folder = Path(__file__).resolve().parent.parent / "episodes"
    known = release_files.load(folder / "posts")
    for path in sorted((folder / "strict").glob("*.json")):
        assert strict_gate.read_record(path).slug in known

"""Between Friends on Okayville: arc4d3's approvals of 4 Nov (Slack 1793837712.509019) let the-course pin its two
characters and pass the caption gate in its house white-outlined captions, and nothing else about the gate moves."""

from pathlib import Path

import numpy as np
import pytest

from srstudio import caption_gate, parts

APPROVAL_TS = "1793837712.509019"
INK, WHITE, FLOOR = (0x12, 0x14, 0x15), (255, 255, 255), (0x3A, 0x2E, 0x45)
# The-course's caption track as the scene writes it: the house look at y 1283 of a 1080 x 1920 frame.
SCENE = """<scene version="1.1">
  <project width="1080" height="1920" fps="30" duration="49.266667"/>
  <styles>
    <textStyle id="captions-text" size="53" color="{fill}" lineHeight="1.14" strokeColor="#121415" strokeWidth="8"/>
    <textStyle id="captions-active" basedOn="captions-text" color="#F4D492"/>
  </styles>
  <output id="main" burnCaptions="captions"/>
  <composition/>
  <captions>
    <captionTrack id="captions" style="captions-text" activeStyle="captions-active" maxLines="2" y="1283"/>
  </captions>
</scene>"""


def the_look() -> caption_gate.ApprovedLook:
    (look,) = [look for look in caption_gate.LOOKS if look.style == "Between Friends"]
    return look


def reel(tmp_path: Path, fill: str = "#FFFFFF") -> dict:
    scene, video = tmp_path / "the-course.scene.xml", tmp_path / "the-course.mp4"
    scene.write_text(SCENE.format(fill=fill))
    video.write_bytes(b"mp4")
    return dict(scene=scene, video=video)


def open_letters(video, band, **kw):
    """Frames of white rings with dark halos and open counters, as the house captions render."""
    top, bottom = band
    frame = np.full((bottom - top, 1080, 3), FLOOR, dtype=np.uint8)
    ys, xs = np.mgrid[0 : bottom - top, 0:1080]
    for i in range(8):
        d = np.hypot(xs - (100 + i * 120), ys - (bottom - top) / 2)
        frame[d <= 30] = INK
        frame[d <= 22] = WHITE
        frame[d <= 8] = INK
    return iter([frame] * 8)


@pytest.mark.parametrize("name", ["friends-leo", "friends-sam"])
def test_both_friends_are_pinnable_at_version_one_on_arc4d3s_words(name):
    version = parts.pin(name, 1)
    assert version.status == "approved" and version.approval is not None
    assert APPROVAL_TS in version.approval.words and "6580f817" in version.approval.words
    assert version.approval.date == "2026-11-04"


def test_the_white_outlined_look_is_approved_for_between_friends_on_arc4d3s_words():
    look = the_look()
    assert look.approved and look.approval is not None and look.approval.by == "arc4d3"
    assert APPROVAL_TS in look.approval.evidence and "7.73 s over Sam's shirt" in look.approval.evidence
    assert (look.fills, look.active, look.stroke, look.stroke_width) == (("#FFFFFF",), "#F4D492", "#121415", 8)


def test_the_course_captions_pass_the_gate_under_between_friends(tmp_path):
    assert caption_gate.band_of(reel(tmp_path)["scene"], the_look()) is not None
    assert caption_gate.check_reel("Between Friends", **reel(tmp_path), read=open_letters) == []


def test_the_gate_still_refuses_another_look_and_an_unrecorded_style(tmp_path):
    problems = caption_gate.check_reel("Between Friends", **reel(tmp_path, fill="#FFEEDD"), read=open_letters)
    assert problems == ["the captions are not an approved look of Between Friends (white-outlined)"]
    assert caption_gate.check_reel("Between Strangers", **reel(tmp_path), read=open_letters) == [
        "no caption look is approved for the style 'Between Strangers'"
    ]

"""What a new Stick reel shares: its spec, its word captions at one height, its mix, the frames that alternate."""

from types import SimpleNamespace

import pytest

from srstudio import STICK, stick, stick_reel
from srstudio.timeline import Take


def test_the_spec_is_the_style_s_with_a_private_report():
    spec = stick_reel.spec("/tmp/x", "hold-the-door", "R10", "Hold the Door", "A door.", 1)
    assert spec.slug == "hold-the-door" and spec.style is STICK and spec.dialogue == "timeline.json"
    assert spec.poster["path"] == "hold-the-door-cover.jpg" and spec.output_options["fps"] == "24"


def test_alternating_spans_cover_the_shot_turn_about():
    a, b = stick_reel.turns(1.0, 4.0)
    assert a[0] == (0.0, 0.25) and b[0] == (0.25, 0.5)
    assert max(end for _, end in a + b) == 1.0
    with pytest.raises(stick.StickDataError, match="rate"):
        stick_reel.turns(1.0, 0.0)
    with pytest.raises(stick.StickDataError, match="seconds"):
        stick_reel.turns(0.0, 4.0)


def test_the_caption_height_sits_in_the_approved_zone():
    from srstudio import caption_gate

    look = next(x for x in caption_gate.LOOKS if x.style == "Stick" and x.name == "white-word")
    assert look.zone[0] <= stick_reel.WORDS_Y < look.zone[1]


def test_a_placed_effect_starts_late_and_every_take_is_faded():
    class Take:
        id, start = "07", 2.0

    place = stick_reel.placing({"07": 0.5})
    assert place(Take)["start"] == 2.5 and place(Take)["fadeIn"]
    Take.id = "01"
    assert "start" not in place(Take)


@pytest.mark.parametrize(("sentences", "cues"), [(False, ["Bro Four hours"]), (True, ["Bro", "Four hours"])])
def test_a_new_reel_asks_for_cues_that_stop_at_a_sentence_end(monkeypatch, tmp_path, sentences, cues):
    drawn = []
    monkeypatch.setattr(stick_reel.stick, "words", lambda cv, group, lines, **kw: drawn.extend(c.text for c in lines))
    monkeypatch.setattr(stick_reel.fonts, "text_width", lambda font, text, size: 10.0 * len(text))
    (tmp_path / "font.ttf").write_bytes(b"font")
    cv = SimpleNamespace(comp=None, group=lambda parent, name: name)
    ep = SimpleNamespace(cv=cv, root=tmp_path, spec=SimpleNamespace(font="font.ttf"))
    words = [
        {"text": "Bro.", "start": 0.0, "end": 0.3},
        {"text": "Four", "start": 0.5, "end": 0.8},
        {"text": "hours", "start": 0.9, "end": 1.2},
    ]
    stick_reel.words(ep, [SimpleNamespace(start=0.0, end=2.0, words=words)], sentences=sentences)
    assert drawn == cues


CLOSE = ((300.0, 800.0), 1.4, (420.0, 800.0))  # focus, zoom, where the focus lands


def test_framing_says_where_faces_and_marks_land_through_the_camera():
    landed = stick_reel.check_framing(CLOSE, faces=[(300.0, 800.0)], marks=[(440.0, 1100.0)])
    assert landed == [(420.0, 800.0), pytest.approx((616.0, 1220.0))]


def test_a_face_that_the_camera_puts_on_the_bug_is_refused():
    with pytest.raises(stick.StickDataError, match="bug"):
        stick_reel.check_framing(((540.0, 960.0), 1.0, (540.0, 960.0)), faces=[(985.0, 300.0)])


def test_a_big_head_near_the_bug_is_refused_though_its_centre_is_clear():
    with pytest.raises(stick.StickDataError, match="bug"):
        stick_reel.check_framing(((540.0, 960.0), 2.0, (540.0, 960.0)), faces=[(760.0, 690.0)])


def test_a_face_in_the_caption_band_is_refused():
    with pytest.raises(stick.StickDataError, match="caption"):
        stick_reel.check_framing(CLOSE, faces=[(300.0, 1420.0)])


def test_a_face_off_the_frame_is_refused():
    with pytest.raises(stick.StickDataError, match="off the frame"):
        stick_reel.check_framing(CLOSE, faces=[(1000.0, 800.0)])


def test_a_mark_off_the_frame_or_under_the_captions_is_refused():
    with pytest.raises(stick.StickDataError, match="off the frame"):
        stick_reel.check_framing(CLOSE, marks=[(1100.0, 800.0)])
    with pytest.raises(stick.StickDataError, match="caption"):
        stick_reel.check_framing(CLOSE, marks=[(300.0, 1420.0)])


@pytest.mark.parametrize(
    "camera",
    [((0.0, 0.0), 0.0, (0.0, 0.0)), ((0.0, 0.0), float("nan"), (0.0, 0.0)), ((float("inf"), 0.0), 1.0, (0.0, 0.0))],
)
def test_a_camera_that_cannot_land_a_point_is_refused(camera):
    with pytest.raises(stick.StickDataError, match="camera"):
        stick_reel.check_framing(camera, faces=[(0.0, 0.0)])


def test_a_subtitle_starts_with_the_take_s_first_word_and_not_with_its_still():
    held = Take("01", "noor", "open", "Step one.", 0.0, 3.0, words=({"text": "Step", "start": 1.05, "end": 1.4},))
    plain = Take("02", "dev", "open", "Easy.", 3.0, 1.0)
    effect = Take("03", "sfx", "open", "", 4.0, 1.0)
    assert stick_reel.spoken_cues((held, plain, effect)) == [(1.05, 3.0, "Step one."), (3.0, 4.0, "Easy.")]


def test_the_clear_card_ends_at_the_bug_box():
    assert (1080 + stick_reel.CARD_CLEAR) / 2 <= stick_reel.BUG_BOX[0]

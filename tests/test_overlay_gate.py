"""A key line or a hook card that repeats the spoken caption while it is on screen is the same words printed twice.
The gate reads the overlay by what drew it, not by its words: a sign, a phone or a chart a character reads may match
the caption. A published video is frozen and never read."""

from __future__ import annotations

from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import DAYLIGHT, PEACH, Canvas, flat_counter, overlay_gate, stick, subtitles, toon_house
from srstudio.craft import CraftError
from srstudio.overlay_gate import Overlay, overlays, repeated_lines, repeats
from srstudio.releases import Release


def toon_canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def stick_canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background="#bda77a")
    return Canvas(scene, DAYLIGHT, font_asset="inter", namer=flat_counter("n"))


def key_line(text: str, start: float, end: float) -> bytes:
    cv = toon_canvas()
    toon_house.key_line(cv, cv.comp, text, start, end, measure=lambda t, size: 0.4 * size * len(t))
    return cv.scene.to_bytes(layout="pretty")


def hook(text: str, spans) -> bytes:
    cv = stick_canvas()
    g = stick.card(cv, cv.comp, text)
    cv.gate(g, spans)
    return cv.scene.to_bytes(layout="pretty")


def test_a_key_line_is_read_with_its_words_and_its_window():
    assert overlays(key_line("Lost the whole left side.", 1.5, 3.6)) == [
        Overlay("key line", "Lost the whole left side.", ((1.5, 3.6),))
    ]


def test_a_hook_card_is_read_through_its_gate():
    assert overlays(hook("When the call runs over", [(0.0, 1.0), (4.0, 5.0)])) == [
        Overlay("hook card", "When the call runs over", ((0.0, 1.0), (4.0, 5.0)))
    ]


def test_a_key_line_over_the_same_spoken_words_is_refused():
    found = repeats(key_line("Lost the whole left side.", 1.5, 3.6), [(1.44, 3.7, "Lost the whole left side.")])
    assert found == ['the key line "Lost the whole left side." repeats the caption on screen from 1.50 to 3.60 s']


def test_a_hook_card_over_the_same_spoken_words_is_refused():
    found = repeats(hook("Did you pack this yourself?", [(0.0, 2.0)]), [(1.0, 3.0, "did you pack this yourself")])
    assert found == ['the hook card "Did you pack this yourself?" repeats the caption on screen from 1.00 to 2.00 s']


def test_an_overlay_that_stops_where_the_words_start_passes():
    assert repeats(hook("Did you pack this yourself?", [(0.0, 1.0)]), [(1.0, 3.0, "Did you pack this yourself?")]) == []


def test_a_cue_that_holds_the_overlay_inside_a_longer_line_is_refused():
    assert repeats(key_line("How do you fold", 0.0, 2.0), [(1.0, 2.0, "Tell me how do you fold a fitted sheet?")])


def test_a_cue_inside_the_overlay_is_refused():
    assert repeats(key_line("Nobody touches the grill today.", 0.0, 2.0), [(1.0, 2.0, "Nobody touches\nthe grill.")])


def test_a_two_word_cue_that_the_overlay_opens_with_is_refused():
    assert repeats(key_line("Bin day is today.", 0.0, 2.0), [(1.0, 2.0, "Bin day.")])


@pytest.mark.parametrize("said", ["the", "Whole", "The left.", "A whole left arm.", "Lost the keys, left the side."])
def test_a_few_shared_words_are_not_a_repeat(said):
    assert repeats(key_line("Lost the whole left side.", 0.0, 2.0), [(0.0, 2.0, said)]) == []


def test_a_one_word_overlay_repeats_only_its_own_word():
    document = key_line("Sneezed.", 0.0, 2.0)
    assert repeats(document, [(0.0, 2.0, "Sneezed!")])
    assert repeats(document, [(0.0, 2.0, "He sneezed on Tuesday.")]) == []


def test_curly_and_straight_apostrophes_are_one_word():
    assert repeats(key_line("It's still down there.", 0.0, 2.0), [(0.0, 2.0, "It’s still down there.")])


def test_words_in_the_picture_may_match_the_caption():
    cv = stick_canvas()
    cv.text(cv.comp, cv.uid("sign"), "SECURITY CHECK AHEAD", 90, 300, 900, 200, 70)
    document = cv.scene.to_bytes(layout="pretty")
    assert overlays(document) == []
    assert repeats(document, [(0.0, 2.0, "Security check ahead.")]) == []


def test_a_white_card_at_another_place_is_not_the_hook_card():
    cv = stick_canvas()
    x, y, w, h, r = stick.CARD
    g = cv.group(cv.comp, "sign-on-the-wall", x=40)
    stick.box(cv, g, x, y + 200, w, h, "#ffffff", r=r)
    cv.text(g, cv.uid("sign"), "Security check ahead", x + 35, y + 208, w - 70, h - 16, 54)
    assert overlays(cv.scene.to_bytes(layout="pretty")) == []


def test_a_shot_window_above_the_overlay_cuts_it():
    cv = stick_canvas()
    shot = cv.group(cv.comp, "shot", start=5.0, end=7.0)
    stick.card(cv, shot, "When the call runs over")
    assert overlays(cv.scene.to_bytes(layout="pretty")) == [
        Overlay("hook card", "When the call runs over", ((5.0, 7.0),))
    ]


def test_a_gate_on_a_shots_own_clock_counts_from_the_shot():
    cv = stick_canvas()
    shot = cv.group(cv.comp, "shot", start=5.0, end=7.0)
    g = stick.card(cv, shot, "When the call runs over")
    cv.keys(g, "opacity", [(0.0, 1), (1.0, 0)], local=True)
    assert overlays(cv.scene.to_bytes(layout="pretty")) == [
        Overlay("hook card", "When the call runs over", ((5.0, 6.0),))
    ]


def test_a_shot_in_a_sequence_is_read_where_it_plays():
    cv = stick_canvas()
    run = cv.comp.add_sequence(id="run")
    run.add_group(id="first", end=2.0)
    shot = run.add_group(id="second", end=3.0)
    stick.card(cv, shot, "When the call runs over")
    assert overlays(cv.scene.to_bytes(layout="pretty")) == [
        Overlay("hook card", "When the call runs over", ((2.0, 5.0),))
    ]


def test_an_overlay_that_never_shows_is_not_listed():
    assert overlays(hook("When the call runs over", [])) == []


def test_a_document_that_is_not_a_scene_is_refused():
    with pytest.raises(CraftError, match="not a scene document"):
        overlays(b"<scene")


def release(slug: str = "a-b") -> Release:
    from test_releases import POST  # the smallest post a release takes

    return Release(slug, POST)


def write(episodes: Path, slug: str, document: bytes, cues) -> None:
    project = episodes / slug
    project.mkdir(parents=True)
    (project / f"{slug}.scene.xml").write_bytes(document)
    subtitles.write_srt(project / f"{slug}.srt", cues)


def test_a_reel_being_delivered_is_refused_by_name(tmp_path):
    write(tmp_path, "a-b", key_line("Lost the whole left side.", 1.5, 3.6), [(1.0, 3.0, "Lost the whole left side.")])
    made = release()
    drift = repeated_lines({"a-b": made}, tmp_path, {made.video_name})
    assert [d.name for d in drift] == [made.video_name]
    assert "repeats the caption" in drift[0].reason


def test_a_published_video_is_not_read(tmp_path):
    write(tmp_path, "a-b", key_line("Lost the whole left side.", 1.5, 3.6), [(1.0, 3.0, "Lost the whole left side.")])
    assert repeated_lines({"a-b": release()}, tmp_path, {}) == []


def test_a_project_with_no_scene_has_nothing_to_read(tmp_path):
    made = release()
    assert repeated_lines({"a-b": made}, tmp_path, {made.video_name}) == []


def test_a_scene_without_captions_or_overlays_has_nothing_to_compare(tmp_path):
    project = tmp_path / "a-b"
    project.mkdir()
    cv = stick_canvas()
    (project / "a-b.scene.xml").write_bytes(cv.scene.to_bytes(layout="pretty"))
    made = release()
    assert repeated_lines({"a-b": made}, tmp_path, {made.video_name}) == []


def test_an_overlay_with_no_captions_to_compare_is_refused_not_passed(tmp_path):
    project = tmp_path / "a-b"
    project.mkdir()
    (project / "a-b.scene.xml").write_bytes(key_line("Lost the whole left side.", 1.5, 3.6))
    made = release()
    drift = repeated_lines({"a-b": made}, tmp_path, {made.video_name})
    assert [d.reason for d in drift] == ['the key line "Lost the whole left side." has no captions to compare with']


def test_the_gate_is_exported():
    assert set(overlay_gate.__all__) == {"Overlay", "overlays", "repeated_lines", "repeats"}

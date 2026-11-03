"""A draft on a laptop's screen, stuck notes, a magnifier, an exclamation mark and a corkboard: each draws from its
defaults, nothing shows outside its time, and each refuses what cannot be read or placed."""

from __future__ import annotations

import re

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, registry, toon_drafts
from srstudio.cast_card import contrast
from srstudio.toon import ToonDataError
from srstudio.toon_drafts import Draft, Note


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="comic-neue", namer=flat_counter("k"))


def raw(cv: Canvas) -> str:
    return cv.scene.to_bytes(layout="pretty").decode()


@pytest.mark.parametrize(
    ("kind", "name", "builder"),
    [
        ("prop", "toon-laptop-screen", toon_drafts.laptop_screen),
        ("prop", "toon-stuck-notes", toon_drafts.stuck_notes),
        ("prop", "toon-magnifier", toon_drafts.magnifier),
        ("graphic", "toon-exclaim", toon_drafts.exclaim),
        ("prop", "toon-corkboard", toon_drafts.corkboard),
    ],
)
def test_the_parts_are_registered_and_draw_from_their_defaults(kind: str, name: str, builder) -> None:
    assert registry.get(kind, name).builder is builder
    cv = canvas()
    builder(cv, cv.comp)
    assert raw(cv)


def test_every_draft_of_a_screen_is_lettered_with_its_span() -> None:
    cv = canvas()
    toon_drafts.laptop_screen(
        cv, cv.comp, (Draft(0.0, 2.0, "DRAFT 31", "Hi Joan"), Draft(2.0, 4.0, "DRAFT 32", "Hello"))
    )
    text = raw(cv)
    assert "DRAFT 31" in text and "DRAFT 32" in text and "Hi Joan" in text and "Hello" in text


def test_drafts_that_run_backwards_are_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="rise"):
        toon_drafts.laptop_screen(cv, cv.comp, (Draft(3.0, 4.0, "A", "a"), Draft(1.0, 2.0, "B", "b")))


def test_a_draft_too_long_for_the_screen_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="screen"):
        toon_drafts.laptop_screen(cv, cv.comp, (Draft(0.0, 1.0, "A", "x" * (toon_drafts.BODY_MAX + 1)),))


def test_more_notes_than_places_are_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="notes"):
        toon_drafts.stuck_notes(cv, cv.comp, tuple(Note(float(k), "x") for k in range(len(toon_drafts.SPOTS) + 1)))


def test_a_note_too_long_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="note"):
        toon_drafts.stuck_notes(cv, cv.comp, (Note(0.0, "x" * (toon_drafts.NOTE_MAX + 1)),))


def test_a_board_clear_of_the_corner_badge() -> None:
    left, _top, width, _h = toon_drafts.BOARD
    assert left + width <= 508  # the bug box's left edge, reference pixels


def test_a_board_with_a_bad_slide_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="slides"):
        toon_drafts.corkboard(cv, cv.comp, slide=(3.0, 2.0))


def test_a_bad_scale_is_refused() -> None:
    cv = canvas()
    with pytest.raises(ToonDataError, match="scale"):
        toon_drafts.magnifier(cv, cv.comp, scale=0)


def test_text_read_through_the_glass_keeps_its_contrast() -> None:
    """The lens tints what is behind it: the screen's greyest word stays readable under the glass, on the frame too."""

    def under_lens(colour: str) -> str:
        channels = (int(colour[i : i + 2], 16) for i in (1, 3, 5))
        tint = (int(toon_drafts.LENS[i : i + 2], 16) for i in (1, 3, 5))
        mixed = (
            (1 - toon_drafts.LENS_TINT) * c + toon_drafts.LENS_TINT * t for c, t in zip(channels, tint, strict=True)
        )
        return "#" + "".join(f"{round(c):02x}" for c in mixed)

    assert contrast(under_lens(toon_drafts.HEAD_INK), under_lens(toon_drafts.GLASS)) >= 4.5


def test_the_ring_is_solid_and_only_the_lens_is_tinted() -> None:
    cv = canvas()
    toon_drafts.magnifier(cv, cv.comp)
    ring = re.search(rf'<shape [^>]*stroke="{toon_drafts.BRASS}"[^>]*>', raw(cv))
    assert ring is not None
    assert "opacity" not in ring.group(0)

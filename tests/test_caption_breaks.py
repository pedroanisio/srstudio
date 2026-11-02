"""Reading a built scene's caption breaks against the rule (ADR 0173): cue cuts, the engine's wraps and the kits'
own text lines, each only where the reel's lines run the two words together."""

from __future__ import annotations

import pytest

from srstudio import caption_breaks
from srstudio.caption_breaks import Fault

LINES = [
    "Leave him and open a candle shop.",
    "We fly to New York at ten. Pack light.",
    "Book the flight to New York for Sam now.",
]


def scene(texts: list[str] = (), cues: list[str] = (), chars: int = 24, rows: int = 2) -> bytes:  # type: ignore[assignment]
    assets = "".join(f'<text id="t{i}" text="{t}"/>' for i, t in enumerate(texts))
    layers = "".join(f'<layer asset="t{i}"/>' for i in range(len(texts)))
    track = "".join(f'<cue start="{i}" end="{i + 1}" text="{c}"/>' for i, c in enumerate(cues))
    return (
        f"<scene><assets>{assets}</assets><composition>{layers}</composition><captions>"
        f'<captionTrack id="c" maxCharsPerLine="{chars}" maxLines="{rows}">{track}</captionTrack></captions></scene>'
    ).encode()


def test_a_text_line_ending_on_a_weak_word_is_a_fault_when_another_break_fits():
    found = caption_breaks.audit(scene(["Leave him and", "open a candle shop."]), LINES)
    assert found == [Fault("text", "Leave him and", "open a candle shop.", "after the weak word 'and'", True)]


def test_lines_inside_one_text_layer_are_read_too():
    found = caption_breaks.audit(scene(["Leave him and&#10;open a candle shop."]), LINES)
    assert [(f.kind, f.before, f.after, f.other_fits) for f in found] == [
        ("text", "Leave him and", "open a candle shop.", True)
    ]


def test_a_break_between_texts_the_lines_do_not_run_together_is_not_read():
    assert caption_breaks.audit(scene(["Advisor", "candle shop."]), LINES) == []


def test_a_sentence_end_frees_the_break_even_when_the_caption_dropped_its_stop():
    assert caption_breaks.audit(scene(["We fly to New York at ten", "Pack light"]), LINES) == []


def test_a_cue_cut_inside_a_name_is_a_fault_and_the_engines_wrap_is_read_by_its_limits():
    found = caption_breaks.audit(scene(cues=["Book the flight to New", "York for Sam now."], chars=24, rows=1), LINES)
    assert found == [Fault("cue", "Book the flight to New", "York for Sam now.", "inside the name New York", True)]
    wrapped = caption_breaks.audit(scene(cues=["Leave him and open a candle shop."], chars=21, rows=2), LINES)
    assert wrapped == [Fault("wrap", "Leave him and open a", "candle shop.", "after the weak word 'a'", True)]


def test_a_forbidden_break_with_nothing_else_that_fits_is_named_as_such():
    (found,) = caption_breaks.audit(scene(["Leave him", "and open a", "candle shop."]), LINES)
    assert found == Fault("text", "and open a", "candle shop.", "after the weak word 'a'", False)


def test_a_document_that_is_not_xml_is_a_typed_error():
    with pytest.raises(caption_breaks.CaptionBreakError, match="not a scene"):
        caption_breaks.audit(b"<scene", LINES)
    with pytest.raises(caption_breaks.CaptionBreakError, match="whole number"):
        caption_breaks.audit(scene(cues=["x"]).replace(b'maxLines="2"', b'maxLines="two"'), LINES)

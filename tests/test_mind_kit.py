"""The mind kit: the channel's cards, its four mechanism visuals, its captions, its sting and its copy check."""

from __future__ import annotations

import importlib
import sys
import wave
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, mind_kit, registry, toon
from srstudio.styles import TOON
from srstudio.voice import Voice


def measure(text: str, size: float) -> float:
    return 0.55 * size * len(text)


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="30", duration=12.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset="fraunces", namer=flat_counter("k"))


def tree(cv: Canvas):
    return ET.fromstring(cv.scene.to_bytes(layout="pretty"))


def texts(cv: Canvas) -> list[str]:
    return [node.get("text") or (node.text or "") for node in tree(cv).iter() if node.tag.endswith("text")]


def study() -> mind_kit.Evidence:
    return mind_kit.Evidence("Lee & Ray", "2001", "Students wore a loud hat.", "Fewer noticed than they guessed.")


@pytest.mark.parametrize(
    ("kind", "name", "builder"),
    [
        ("graphic", "mind-name-card", mind_kit.name_card),
        ("graphic", "mind-evidence-card", mind_kit.evidence_card),
        ("graphic", "mind-captions", mind_kit.captions),
        ("location", "mind-stage", mind_kit.stage),
        ("prop", "mind-spotlight", mind_kit.spotlight),
        ("prop", "mind-memory-shelf", mind_kit.memory_shelf),
        ("prop", "mind-two-lines", mind_kit.two_lines),
        ("prop", "mind-lens", mind_kit.lens),
        ("graphic", "mind-stamp", mind_kit.stamp),
        ("graphic", "mind-zipper", mind_kit.zipper),
        ("graphic", "mind-named", mind_kit.named),
    ],
)
def test_the_parts_are_registered(kind, name, builder):
    assert registry.get(kind, name).builder is builder


def test_the_channel_keeps_the_toon_cast_but_not_its_letters_or_clock():
    assert mind_kit.MIND.font.family != TOON.font.family
    assert mind_kit.MIND.font.google is not None
    assert mind_kit.MIND.fps == 30
    assert mind_kit.MIND.mix.loudness == "-14"
    assert mind_kit.MIND.width == TOON.width and mind_kit.MIND.height == TOON.height
    assert TOON.fps == 24 and TOON.mix.loudness == "-16"


def test_a_card_stands_in_for_a_character_only_in_the_channels_cast():
    assert mind_kit.CARD in mind_kit.MIND_CAST.characters
    assert mind_kit.CARD not in mind_kit.MIND_CAST.lip_synced


def test_the_name_card_carries_the_catchphrase_and_the_name_once():
    cv = canvas()
    mind_kit.name_card(cv, cv.comp, "The Spotlight Effect", 1.0, 2.0, 5.0, measure)
    words = " ".join(texts(cv))
    assert words.count(mind_kit.CATCHPHRASE) == 1
    assert words.count("Spotlight") == 1


def test_the_name_waits_for_its_reveal():
    cv = canvas()
    mind_kit.name_card(cv, cv.comp, "The Spotlight Effect", 1.0, 2.0, 5.0, measure)
    named = next(n for n in tree(cv).iter() if n.get("id") == "name-card-name")
    assert float(named.get("start")) == 2.0


def test_the_name_fills_the_card_at_any_length():
    short, long = mind_kit.name_lines("Priming", measure), mind_kit.name_lines("The Baader Meinhof Phenomenon", measure)
    assert short[1] > long[1]
    assert long[1] >= mind_kit.NAME_MIN


@pytest.mark.parametrize(
    ("name", "start", "reveal", "end", "match"),
    [
        ("", 1.0, 2.0, 5.0, "a name card needs"),
        ("Effect", 3.0, 2.0, 5.0, "start < reveal < end"),
        ("Effect", 1.0, 6.0, 5.0, "start < reveal < end"),
        ("Effect", 1.0, 4.8, 5.0, "the name holds"),
        ("Pneumonoultramicroscopicsilicovolcanoconiosis", 1.0, 2.0, 5.0, "too long"),
    ],
)
def test_a_name_card_refuses_what_it_cannot_show(name, start, reveal, end, match):
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match=match):
        mind_kit.name_card(cv, cv.comp, name, start, reveal, end, measure)


def test_the_evidence_card_says_who_what_result_and_when():
    cv = canvas()
    mind_kit.evidence_card(cv, cv.comp, study(), 1.0, 5.0, measure)
    words = " ".join(" ".join(texts(cv)).split())
    for part in ("Lee & Ray", "2001", "Students wore a loud hat.", "Fewer noticed than they guessed."):
        assert part in words


@pytest.mark.parametrize(
    ("who", "year", "what", "result", "match"),
    [
        ("", "2001", "A", "B", "needs who"),
        ("Lee", "01", "A", "B", "a year of four digits"),
        ("Lee", "2001", "word " * 30, "B", "reads in about"),
        ("Lee", "2001", "A", "word " * 30, "reads in about"),
    ],
)
def test_evidence_refuses_what_a_viewer_cannot_read_in_time(who, year, what, result, match):
    with pytest.raises(mind_kit.MindKitError, match=match):
        mind_kit.Evidence(who, year, what, result)


def test_an_evidence_card_holds_long_enough_to_read():
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match="an evidence card holds"):
        mind_kit.evidence_card(cv, cv.comp, study(), 1.0, 2.0, measure)


def test_the_beam_arrives_at_its_start_and_can_sweep():
    cv = canvas()
    mind_kit.spotlight(cv, cv.comp, (300, 900), 1.0, 5.0, sweep=((1.0, 300.0), (2.0, 700.0)))
    assert [n for n in tree(cv).iter() if n.tag.endswith("animate") and n.get("property") == "x"]


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"foot": "here"}, "a beam's foot"),
        ({"start": 5.0, "end": 1.0}, "a beam needs"),
        ({"radius": 0.0}, "a beam's radius"),
        ({"sweep": ((1.0, 300.0), (1.0, 700.0))}, "a sweep"),
    ],
)
def test_a_beam_refuses_what_it_cannot_do(kwargs, match):
    cv = canvas()
    args = {"foot": (300, 900), "start": 1.0, "end": 5.0} | kwargs
    with pytest.raises(mind_kit.MindKitError, match=match):
        mind_kit.spotlight(cv, cv.comp, args.pop("foot"), args.pop("start"), args.pop("end"), **args)


def test_the_shelf_labels_its_files_and_pulls_one_out():
    cv = canvas()
    mind_kit.memory_shelf(cv, cv.comp, ("Keys", "Names"), pull=(1, 2.0), measure=measure)
    assert {"Keys", "Names"} <= set(texts(cv))
    assert [n for n in tree(cv).iter() if n.tag.endswith("animate") and n.get("property") == "y"]


def test_a_shelf_can_pull_out_more_than_one_file():
    cv = canvas()
    mind_kit.memory_shelf(cv, cv.comp, ("Keys", "Names", "Dates"), pull=(0, 1.0), also=((2, 3.0),), measure=measure)
    moved = {n.get("id") for n in tree(cv).iter() if n.find("./*[@property='y']") is not None}
    assert {"memory-shelf-file-0", "memory-shelf-file-2"} <= moved and "memory-shelf-file-1" not in moved


def test_a_shelf_with_nothing_more_to_pull_draws_what_it_drew():
    one, two = canvas(), canvas()
    mind_kit.memory_shelf(one, one.comp, ("Keys", "Names"), pull=(1, 2.0), measure=measure)
    mind_kit.memory_shelf(two, two.comp, ("Keys", "Names"), pull=(1, 2.0), measure=measure, also=())
    assert ET.tostring(tree(one)) == ET.tostring(tree(two))


@pytest.mark.parametrize(
    ("also", "match"),
    [(((5, 1.0),), "pulls out a file it has"), (((1, -1.0),), "pulls out a file it has"), (((0, 3.0),), "once")],
)
def test_a_shelf_refuses_a_further_pull_it_cannot_make(also, match):
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match=match):
        mind_kit.memory_shelf(cv, cv.comp, ("Keys", "Names"), pull=(0, 1.0), also=also, measure=measure)


@pytest.mark.parametrize(
    ("labels", "pull", "match"),
    [
        ((), None, "a shelf holds"),
        (("a", "b", "c", "d", "e"), None, "a shelf holds"),
        (("a",), (3, 1.0), "pulls out a file it has"),
        (("a",), (0, -1.0), "pulls out a file it has"),
    ],
)
def test_a_shelf_refuses_what_it_cannot_hold(labels, pull, match):
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match=match):
        mind_kit.memory_shelf(cv, cv.comp, labels, pull=pull, measure=measure)


def test_the_two_lines_stay_in_proportion():
    cv = canvas()
    mind_kit.two_lines(cv, cv.comp, ("Guessed", 0.5, "half"), ("Actually", 0.25, "a quarter"), 1.0, 5.0, measure)
    bars = {n.get("id"): n.find("./*[@width]") for n in tree(cv).iter() if str(n.get("id")).endswith("-bar")}
    wide = {name: float(shape.get("width")) for name, shape in bars.items()}
    assert wide["two-lines-expected-bar"] == pytest.approx(2 * wide["two-lines-actual-bar"])


@pytest.mark.parametrize(
    ("expected", "actual", "match"),
    [
        (("Guessed", 1.5, ""), ("Actually", 0.2, ""), "a line's value"),
        (("Guessed", 0.0, ""), ("Actually", 0.2, ""), "a line's value"),
        (("", 0.5, ""), ("Actually", 0.2, ""), "a line needs a label"),
    ],
)
def test_two_lines_refuse_what_they_cannot_draw(expected, actual, match):
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match=match):
        mind_kit.two_lines(cv, cv.comp, expected, actual, 1.0, 5.0, measure)


def test_the_lens_tints_what_it_passes_over():
    cv = canvas()
    mind_kit.lens(cv, cv.comp, (300, 900), 1.0, 5.0, path=((1.0, 300.0), (3.0, 700.0)))
    assert [n for n in tree(cv).iter() if n.tag.endswith("animate") and n.get("property") == "x"]


def test_the_lens_leaves_what_it_passes_over_bright():
    """Noticing sharpens a thing: a tint heavy enough to dull a car inside the glass says the opposite."""
    cv = canvas()
    mind_kit.lens(cv, cv.comp, (300, 900), 1.0, 5.0)
    glass = [n.get("fill") for n in tree(cv).iter() if (n.get("fill") or "").startswith(mind_kit.SPOT)]
    assert glass == [mind_kit.SPOT + mind_kit.GLASS]
    assert int(mind_kit.GLASS, 16) / 255 <= 0.15


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"radius": -1.0}, "a lens's radius"),
        ({"tint": "yellow"}, "a lens's tint"),
        ({"path": ((3.0, 0.0), (1.0, 2.0))}, "a lens's path"),
    ],
)
def test_a_lens_refuses_what_it_cannot_do(kwargs, match):
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match=match):
        mind_kit.lens(cv, cv.comp, (300, 900), 1.0, 5.0, **kwargs)


def test_captions_wrap_to_two_lines_and_mark_the_narrator():
    cv = canvas()
    lines = [
        toon.Line("a", "You are at the centre of your own attention, all day.", 0.0, 2.0, "narrator"),
        toon.Line("b", "What is?", 2.0, 3.0, "goat"),
    ]
    mind_kit.captions(cv, cv.comp, lines, measure, {"narrator": mind_kit.INK, "goat": mind_kit.SPOT})
    assert any("\n" in t for t in texts(cv))


def test_a_caption_that_cannot_fit_two_lines_stops_the_build():
    cv = canvas()
    lines = [toon.Line("a", "word " * 40, 0.0, 2.0, "narrator")]
    with pytest.raises(mind_kit.MindKitError, match="caption"):
        mind_kit.captions(cv, cv.comp, lines, measure, {})


def test_the_sting_is_a_short_wav(tmp_path):
    path = mind_kit.write_sting(tmp_path / "sting.wav", [1.0], 3.0)
    with wave.open(str(path)) as w:
        assert w.getnframes() / w.getframerate() == pytest.approx(3.0, abs=0.01)
    assert sum(seconds for *_, seconds in mind_kit.STING) < 1.0


@pytest.mark.parametrize(
    "bad",
    [
        "Send this to a friend",
        "Tag someone who does this",
        "Follow for more",
        "Comment below",
        "Science proves it",
        "You always do this",
        "That is so OCD",
        "What a narcissist",
        "Pure trauma",
        "He's bipolar about it",
        "So ADHD of you",
        "A bit autistic about it",
        "Pure autism",
    ],
)
def test_the_copy_check_refuses_bait_overclaiming_and_clinical_words(bad):
    with pytest.raises(mind_kit.MindKitError, match="copy"):
        mind_kit.check_copy(bad)


@pytest.mark.parametrize("fine", ["People notice you less than you think.", "One tiny stain.", "Commentary"])
def test_the_copy_check_lets_plain_sentences_through(fine):
    assert mind_kit.check_copy(fine) == fine


def test_an_evidence_card_can_hold_its_result_back():
    cv = canvas()
    mind_kit.evidence_card(cv, cv.comp, study(), 1.0, 6.0, measure, reveal=3.5)
    late = [g for g in tree(cv).iter() if g.get("id") == "evidence-card-result"]
    assert len(late) == 1 and float(late[0].get("start")) == 3.5
    assert len(late[0]) >= 1  # the group holds the lettering; the words live in the document's text assets
    assert "guessed." in " ".join(" ".join(texts(cv)).split())


def papers(cv: Canvas) -> list[dict]:
    """The card's paper, each with the moments it shows from its group."""
    found = []
    for group in tree(cv).iter("group"):
        for shape in group:
            if shape.tag == "shape" and shape.get("width") == "940":
                found.append(
                    {
                        "start": float(group.get("start")),
                        "end": float(group.get("end")),
                        "top": float(shape.get("y")),
                        "foot": float(shape.get("y")) + float(shape.get("height")),
                    }
                )
    return found


def lettering_feet(cv: Canvas) -> tuple[float, float]:
    """How far down the card's lettering runs: without the held-back result, and with it."""
    root = tree(cv)
    heights = {a.get("id"): float(a.get("height")) for a in root.iter("text")}
    foot = lambda layer: float(layer.get("y")) + heights[layer.get("asset")]  # noqa: E731
    late = next(g for g in root.iter("group") if g.get("id") == "evidence-card-result")
    held = {layer.get("id") for layer in late.iter("layer")}
    layers = list(root.iter("layer"))
    return max(foot(k) for k in layers if k.get("id") not in held), max(foot(k) for k in layers)


def test_a_held_back_result_leaves_no_blank_paper_waiting_for_it():
    cv = canvas()
    mind_kit.evidence_card(cv, cv.comp, study(), 1.0, 6.0, measure, reveal=3.5)
    before, after = papers(cv)
    pad = 44.0
    without, whole = lettering_feet(cv)
    assert before["foot"] == pytest.approx(without + pad, abs=1.0)  # the paper ends where its words do
    assert after["foot"] == pytest.approx(whole + pad, abs=1.0)
    assert before["top"] == after["top"]  # it grows downwards: what is on it does not move
    assert (before["start"], before["end"], after["start"], after["end"]) == (1.0, 3.5, 3.5, 6.0)  # a snap, no gap


def test_a_card_that_holds_nothing_back_is_one_paper():
    cv = canvas()
    mind_kit.evidence_card(cv, cv.comp, study(), 1.0, 6.0, measure)
    assert [(p["start"], p["end"]) for p in papers(cv)] == [(1.0, 6.0)]


def test_a_card_is_the_same_size_once_its_result_is_on_it():
    held, plain = canvas(), canvas()
    mind_kit.evidence_card(held, held.comp, study(), 1.0, 6.0, measure, reveal=3.5)
    mind_kit.evidence_card(plain, plain.comp, study(), 1.0, 6.0, measure)
    assert papers(held)[-1]["foot"] == papers(plain)[0]["foot"]


def test_an_evidence_card_shows_its_result_with_the_card_by_default():
    cv = canvas()
    mind_kit.evidence_card(cv, cv.comp, study(), 1.0, 6.0, measure)
    assert [g.get("start") for g in tree(cv).iter() if g.get("id") == "evidence-card-result"] == [None]


@pytest.mark.parametrize("reveal", [0.5, 1.0, 6.0, 7.0])
def test_a_held_back_result_comes_inside_the_card(reveal):
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match="result"):
        mind_kit.evidence_card(cv, cv.comp, study(), 1.0, 6.0, measure, reveal=reveal)


def test_the_finish_grades_a_node_and_blurs_nothing():
    cv = canvas()
    node = cv.group(cv.comp, "shot-001")
    mind_kit.finish(cv, node)
    kinds = {e.get("type") for e in tree(cv).iter() if e.tag.endswith("effect")}
    assert {"bloom", "vignette", "film-grain"} <= kinds and "blur" not in kinds


def test_a_far_plane_is_out_of_focus_and_the_key_is_light_only():
    cv = canvas()
    far = mind_kit.far(cv, cv.comp)
    cv.rect(far, 0, 0, 10, 10, "#ffffff")
    mind_kit.key(cv, cv.comp)
    assert {"blur"} <= {e.get("type") for e in tree(cv).iter() if e.tag.endswith("effect")}
    assert not any("sig-" in (node.get("id") or "") for node in tree(cv).iter())


def test_the_channel_keeps_a_stage_name_apart_from_a_card():
    assert {mind_kit.CARD, mind_kit.STAGE} <= set(mind_kit.MIND_CAST.characters)
    assert mind_kit.CARD != mind_kit.STAGE


PILOTS = (
    "spotlight_effect",
    "planning_fallacy",
    "frequency_illusion",
    "peak_end_rule",
    "learning_styles",
    "choice_blindness",
    "change_blindness",
)


def _pilot(module):
    folder = str(Path(__file__).parents[1] / "episodes" / "pilots")
    if folder not in sys.path:
        sys.path.insert(0, folder)
    return importlib.import_module(f"{module}_data")


def test_the_channels_narrator_is_bella():
    assert mind_kit.NARRATOR.voice == Voice(role="narrator", id="hpp4J3VqNfWAUOO0d1Us", name="Bella")
    assert mind_kit.NARRATOR.character is None  # heard only


@pytest.mark.parametrize("module", PILOTS)
def test_every_pilot_speaks_in_the_channels_voice_and_credits_it(module):
    pilot = _pilot(module)
    assert pilot.SKETCH.speakers[0] is mind_kit.NARRATOR
    assert "Bella (narrator)" in pilot.NARRATION
    assert "Bella" in pilot.POST.credit
    assert "Bella" in pilot.NOTE


@pytest.mark.parametrize("module", PILOTS)
def test_no_character_shares_the_narrators_voice(module):
    cast = _pilot(module).SKETCH.speakers[1:]
    assert cast and mind_kit.NARRATOR.voice.id not in {s.voice.id for s in cast}


def rects(cv: Canvas) -> list[dict[str, float]]:
    wanted = ("x", "y", "width", "height")
    return [{key: float(node.get(key, 0)) for key in wanted} for node in tree(cv).iter() if node.get("shape") == "rect"]


def test_a_stamp_carries_its_rows_and_its_source():
    cv = canvas()
    mind_kit.stamp(cv, cv.comp, ("93% of US students", "above the median."), "Svenson, 1981", 1.0, 3.0, measure)
    assert texts(cv) == ["93% of US students", "above the median.", "Svenson, 1981"]


def test_a_stamp_shrinks_to_the_safe_width_and_refuses_what_never_fits():
    long = "A" * 26
    cv = canvas()
    mind_kit.stamp(cv, cv.comp, (long,), "Lee, 2001", 1.0, 3.0, measure)
    assert len(texts(cv)) == 2
    with pytest.raises(mind_kit.MindKitError, match="does not fit"):
        mind_kit.stamp(canvas(), canvas().comp, ("A" * 200,), "Lee, 2001", 1.0, 3.0, measure)


def test_a_stamp_needs_evidence_a_span_and_clean_copy():
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match="a line of evidence"):
        mind_kit.stamp(cv, cv.comp, (), "Lee, 2001", 1.0, 3.0, measure)
    with pytest.raises(mind_kit.MindKitError):
        mind_kit.stamp(cv, cv.comp, ("Fine.",), "Lee, 2001", 3.0, 1.0, measure)
    with pytest.raises(mind_kit.MindKitError):
        mind_kit.stamp(cv, cv.comp, ("Science proves it.",), "Lee, 2001", 1.0, 3.0, measure)


def test_a_zipper_covers_the_whole_frame_and_every_row_has_both_sides():
    cv = canvas()
    mind_kit.zipper(cv, cv.comp, 0.4, 1.5)
    cloth = [r for r in rects(cv) if r["width"] == cv.width / 2]
    assert len(cloth) == 2 * mind_kit.ZIP_ROWS
    assert {r["x"] for r in cloth} == {0.0, cv.width / 2}
    assert min(r["y"] for r in cloth) == 0.0
    assert max(r["y"] + r["height"] for r in cloth) >= cv.height


def test_a_zipper_is_gone_soon_after_the_pull_ends():
    cv = canvas()
    node = mind_kit.zipper(cv, cv.comp, 0.4, 1.5)
    assert float(node.end) == pytest.approx(1.5 + mind_kit.ZIP_BEAT)


def test_a_zipper_runs_forward():
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError):
        mind_kit.zipper(cv, cv.comp, 1.5, 0.4)


@pytest.mark.parametrize(("scale", "pivot"), [(1.0, (540.0, 960.0)), (1.12, (700.0, 800.0)), (1.2, (560.0, 800.0))])
def test_a_name_lands_centred_on_the_captions_line_once_the_punch_has_happened(scale, pivot):
    cv = canvas()
    mind_kit.named(cv, cv.comp, "Lee effect", 1.0, 3.0, measure, scale, pivot)
    strip = rects(cv)[0]
    middle = pivot[0] + (strip["x"] + strip["width"] / 2 - pivot[0]) * scale
    top = pivot[1] + (strip["y"] - pivot[1]) * scale
    assert middle == pytest.approx(cv.width / 2, abs=0.05)
    assert top == pytest.approx(mind_kit.CAPTION_TOP, abs=0.05)


def test_a_name_cannot_be_drawn_under_a_pull_out_or_with_a_banned_word():
    cv = canvas()
    with pytest.raises(mind_kit.MindKitError, match="punch-in"):
        mind_kit.named(cv, cv.comp, "Lee effect", 1.0, 3.0, measure, 0.9)
    with pytest.raises(mind_kit.MindKitError):
        mind_kit.named(cv, cv.comp, "Science proves it", 1.0, 3.0, measure)

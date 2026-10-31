"""Toon sketches: the data checks, the derivations the build draws, the placement onto a recording, and the
recording loop with a fake client (what the real client parses and verifies is tested in test_voice.py)."""

import json
import shutil
import xml.etree.ElementTree as ET
from dataclasses import replace
from pathlib import Path

import pytest
from sr_core.scene import Scene

from srstudio import PEACH, Canvas, flat_counter, music, narration, sketch, toon
from srstudio.fonts import GoogleFont
from srstudio.sketch import Line
from srstudio.voice import Alignment
from support.sketch import BEATS, LINES, SK, SPEAKERS, FakeClient, confirm_stub, with_beats


def canvas() -> Canvas:
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1920, fps="24", duration=9.0, background=PEACH.background)
    return Canvas(scene, PEACH, font_asset=None, namer=flat_counter("k"))


# -- the data ---------------------------------------------------------------------------------------------------------
def test_a_consistent_sketch_passes_and_derives_its_cues_appearances_events_and_spans():
    sketch.check(SK)
    cues = sketch.cues(BEATS, SK.end, LINES)
    assert [(c["text"], c["start"], c["end"], c["speaker"]) for c in cues] == [
        ("Due at 9", 0.0, 3.0, "rex"),
        ("How is it going?", 3.0, 4.5, "boss"),
        ("Great", 4.5, 5.5, "rex"),
        ("Almost done", 5.5, 7.0, "rex"),
    ]
    assert [q.speaker for q in toon.parse_script(cues)] == ["rex", "boss", "rex", "rex"]
    assert [c["speaker"] for c in sketch.cues(BEATS, SK.end)] == ["dog"] * 4  # without the lines: who is on
    apps = sketch.appearances(BEATS, SK.end)
    assert [(a.who, a.start, a.end, len(a.poses)) for a in apps] == [("dog", 0.0, 7.0, 5), ("frog", 7.0, 9.0, 1)]
    assert apps[0].poses[1] == {"start": 1.5, "eyes": "half", "mouth": "flat", "arms": "type"}
    assert toon.parse_poses(apps[0].poses)[-1].start == 5.5
    assert sketch.events(BEATS, "buzz") == [(3.0, "")] and sketch.events(BEATS, "clock") == [(7.0, "01:00")]
    assert sketch.events(BEATS, "flash") == []
    assert sketch.line_spans(SK) == [(0.0, 3.0), (3.0, 4.5), (4.5, 9.0)]


@pytest.mark.parametrize(
    "change, match",
    [
        (lambda s: replace(s, speakers=(SPEAKERS[0], SPEAKERS[0])), "distinct names"),
        (lambda s: replace(s, speakers=(replace(SPEAKERS[0], character="owl"), SPEAKERS[1])), "distinct characters"),
        (lambda s: replace(s, speakers=(SPEAKERS[0], replace(SPEAKERS[1], character="dog"))), "distinct characters"),
        (lambda s: replace(s, lines=(*LINES, Line("nobody", "Hi."))), "known speaker"),
        (lambda s: replace(s, lines=(LINES[0], Line("boss", "  "), LINES[2])), "known speaker and some text"),
        (lambda s: with_beats(lambda b: [replace(b[0], start=0.5), *b[1:]]), "starts at 0"),
        (lambda s: with_beats(lambda b: [b[0], replace(b[1], start=0.05), *b[2:]]), "held less than"),
        (lambda s: with_beats(lambda b: [replace(b[0], who="owl"), *b[1:]]), "not in the Toon vocabulary"),
        (lambda s: with_beats(lambda b: [replace(b[0], eyes="laser"), *b[1:]]), "not in the Toon vocabulary"),
        (lambda s: with_beats(lambda b: [replace(b[0], word=None), *b[1:]]), "go together"),
        (lambda s: with_beats(lambda b: [replace(b[0], line=9), *b[1:]]), "no line 9"),
        (lambda s: with_beats(lambda b: [replace(b[0], word=40), *b[1:]]), "has no word 40"),
        (lambda s: with_beats(lambda b: [*b[:4], replace(b[4], line=1, word=0), b[5]]), "out of order"),
        (lambda s: with_beats(lambda b: [*b[:2], replace(b[2], line=None, word=None), *b[3:]]), "every line needs"),
        (lambda s: replace(s, end=7.1), "before the end"),
    ],
)
def test_inconsistent_sketches_are_refused(change, match):
    with pytest.raises(sketch.SketchError, match=match):
        sketch.check(change(SK))


def test_typing_bursts_sit_in_the_typing_beats_and_keep_clear_of_the_lines():
    bursts = sketch.typing_bursts(BEATS, SK.end)
    assert bursts and all(1.5 < t < 3.0 - 0.3 for t in bursts)
    assert sketch.typing_bursts(BEATS, SK.end, [(1.4, 2.2)]) == [t for t in bursts if t >= 2.2 + sketch.SPEECH_MARGIN]
    assert sketch.typing_bursts(BEATS, SK.end, [(0.0, 9.0)]) == []
    with pytest.raises(sketch.SketchError, match="start < end"):
        sketch.typing_bursts(BEATS, SK.end, [(2.0, 1.0)])


def test_draw_cast_puts_every_appearance_on_screen_in_turn():
    cv = canvas()
    groups = sketch.draw_cast(cv, cv.comp, BEATS, SK.end, taps=(1.8, 1.9))
    tree = ET.fromstring(cv.scene.to_bytes(layout="pretty"))
    runs = [g for g in tree.find("composition").iter("group") if g.get("start") is not None]
    assert len(groups) == 6 and [(g.get("start"), g.get("end")) for g in runs] == [
        ("0", "1.5"),
        ("1.5", "3"),
        ("3", "4.5"),
        ("4.5", "5.5"),
        ("5.5", "7"),
        ("7", "9"),
    ]
    assert len(runs[1].findall("group")) == 2  # the typing frames swap on the taps inside that run
    # a sticker rides on one character through every pose; the traced cat takes none
    from srstudio import toon_cast

    cv2 = canvas()
    note = toon_cast.sticky_note(185, 500)
    sketch.draw_cast(cv2, cv2.comp, BEATS, SK.end, taps=(1.8, 1.9), stickers={"dog": note})
    a = cv.scene.to_bytes(layout="pretty").count(b"<shape")
    assert (
        cv2.scene.to_bytes(layout="pretty").count(b"<shape") == a + 5 * 5
    )  # five note layers in each of the dog's five runs (the typing frames share them; the frog wears none)
    with pytest.raises(sketch.SketchError, match="no stickers"):
        sketch.draw_cast(canvas(), cv.comp, [replace(BEATS[0], who="cat")], 1.0, stickers={"cat": note})
    # a viseme track adds the lips group to the runs the character speaks in
    cv3 = canvas()
    sketch.draw_cast(cv3, cv3.comp, BEATS, SK.end, taps=(1.8, 1.9), mouths={"dog": [(0.2, "open"), (0.9, "closed")]})
    tree3 = ET.fromstring(cv3.scene.to_bytes(layout="pretty"))
    runs3 = [g for g in tree3.find("composition").iter("group") if g.get("start") is not None]
    assert len(runs3[0].findall("group")) == 1 and len(runs[0].findall("group")) == 0
    assert [len(g.findall("group")) for g in runs3[1:]] == [len(g.findall("group")) for g in runs[1:]]
    with pytest.raises(sketch.SketchError, match="no lip sync"):
        sketch.drawer_extras("cat", mouths={"cat": [(0.2, "open")]})
    assert sketch.drawer_extras("dog", {"dog": note}, {"dog": [(0.2, "open")]}) == {
        "stickers": note,
        "mouths": [(0.2, "open")],
    }
    assert sketch.drawer_extras("frog", {"dog": note}, {"dog": [(0.2, "open")]}) == {}


# -- lip sync ---------------------------------------------------------------------------------------------------------
def test_visemes_follow_the_letters_of_a_take_inside_what_was_kept_of_it():
    # "Pop up." said over 0.6 s from 0.1 s: p closed, o round, p closed, u round, p closed
    text = "Pop up."
    starts = tuple(round(0.1 + k * 0.1, 6) for k in range(len(text)))
    ends = tuple(round(a + 0.1, 6) for a in starts)
    al = Alignment(tuple(text), starts, ends)
    track = sketch.visemes(al, at=5.0, clip_in=0.1, kept=0.7)
    assert track[0] == (5.0, "closed") and track[-1][1] == "closed"  # closed on the last p, inside the span
    assert [v for _, v in track] == ["closed", "round", "closed", "round", "closed"]
    assert all(b > a for (a, _), (b, _) in zip(track, track[1:], strict=False))
    assert all(5.0 <= t <= 5.7 for t, _ in track)
    # a vowel opens, a consonant shows teeth, and only the kept part counts
    al2 = Alignment(("a", "s"), (0.0, 0.5), (0.5, 1.0))
    assert [v for _, v in sketch.visemes(al2, 0.0, 0.0, 1.0)] == ["open", "teeth", "closed"]
    assert sketch.visemes(al2, 2.0, 0.5, 0.5) == [(2.0, "teeth"), (2.5, "closed")]  # it starts on the s
    with pytest.raises(sketch.SketchError, match="placed at a second"):
        sketch.visemes(al2, -1.0, 0.0, 1.0)
    with pytest.raises(sketch.SketchError, match="more than 0 s"):
        sketch.visemes(al2, 0.0, 0.0, 0.0)
    # a take that speaks from its first sample, placed at a second that rounds up, opens on the sound alone
    track = sketch.visemes(al2, 2.0000006, 0.0, 1.0)
    assert track[0] == (2.000001, "open") and all(b > a for (a, _), (b, _) in zip(track, track[1:], strict=False))
    # takes join in order; a take on top of the last one is refused
    track = [(0.0, "open"), (1.0, "closed")]
    sketch.extend_track(track, [(1.0, "closed"), (1.1, "round"), (1.5, "closed")])
    assert track == [(0.0, "open"), (1.0, "closed"), (1.1, "round"), (1.5, "closed")]
    sketch.extend_track(track, [(2.0, "teeth"), (2.5, "closed")], "03")
    assert len(track) == 6
    with pytest.raises(sketch.SketchError, match="take 04 starts at 2.4"):
        sketch.extend_track(track, [(2.4, "open")], "04")


def test_record_writes_a_viseme_track_per_lip_synced_character(tmp_path):
    client = FakeClient(tmp_path)
    rec = sketch.record(SK, tmp_path, client, confirm=confirm_stub, conform_clip=copy_clip)
    mouths, end = sketch.load_mouths(tmp_path / "voiced" / "mouths.json")
    assert end == rec.end and set(mouths) == {"dog"}  # the boss is off screen: no character, no track
    track = mouths["dog"]
    spans = [(q["start"], q["start"] + q["duration"]) for q in rec.items if q["id"] in ("01", "03")]
    for a, b in spans:  # each of Rex's takes opens its mouth inside its span and closes it at the end
        inside = [v for t, v in track if a <= t <= b]
        assert "open" in inside or "round" in inside or "teeth" in inside
        assert [v for t, v in track if a <= t <= b][-1] == "closed"
    gap = [v for t, v in track if spans[0][1] < t < spans[1][0]]
    assert gap == []  # nothing between the takes
    assert all(b > a for (a, _), (b, _) in zip(track, track[1:], strict=False))


def test_voiced_mouths_round_trip_and_bad_files_are_refused(tmp_path):
    mouths = {"dog": [(0.5, "open"), (0.9, "closed")], "rabbit": []}
    sketch.write_voiced(tmp_path, BEATS, SK.end, LINES, mouths)
    assert sketch.load_mouths(tmp_path / "voiced" / "mouths.json") == (mouths, SK.end)
    sketch.write_voiced(tmp_path / "plain", BEATS, SK.end, LINES)
    assert not (tmp_path / "plain" / "voiced" / "mouths.json").exists()
    path = tmp_path / "bad.json"

    def doc(states, end=9.0, who="dog") -> str:
        return json.dumps({"end": end, "mouths": {who: states}})

    for text, match in (
        ("nope", "bad.json"),
        ('{"mouths": {}}', "end and mouths"),
        ('{"end": 9, "mouths": []}', "end and mouths"),
        (doc([], end="9"), "end must be"),
        (doc([], end=0), "end must be"),
        (doc([], who="cat"), "not a lip-synced"),
        (doc({}), "must be a list"),
        (doc([[0.5]]), "second, viseme"),
        (doc([[0.5, "open", 1]]), "second, viseme"),
        (doc([["0.5", "open"]]), "within 0..9"),
        (doc([[9.5, "open"]]), "within 0..9"),
        (doc([[true_(), "open"]]), "within 0..9"),
        (doc([[0.5, "smile"]]), "not one of"),
        (doc([[0.5, "open"], [0.5, "closed"]]), "must rise"),
        (doc([[0.5, "open"], [0.4, "closed"]]), "must rise"),
    ):
        path.write_text(text)
        with pytest.raises(sketch.SketchError, match=match):
            sketch.load_mouths(path)
    with pytest.raises(sketch.SketchError, match="missing.json"):
        sketch.load_mouths(tmp_path / "missing.json")


# -- the takes a head moves on -----------------------------------------------------------------------------------------
def test_record_writes_every_take_as_the_project_plays_it(tmp_path):
    rec = sketch.record(SK, tmp_path, FakeClient(tmp_path), confirm=confirm_stub, conform_clip=copy_clip)
    takes, end = sketch.load_speech(tmp_path / "voiced" / "speech.json")
    assert end == rec.end
    assert [t.id for t in takes] == [q["id"] for q in rec.items]
    assert [t.at for t in takes] == [q["start"] for q in rec.items]
    assert [t.kept for t in takes] == [q["duration"] for q in rec.items]
    assert [t.who for t in takes] == [
        {s.name: s.character for s in SPEAKERS}[line.speaker] for line in SK.lines
    ]  # the boss off screen has no character and is heard all the same
    assert None in [t.who for t in takes]
    for take, line in zip(takes, SK.lines, strict=True):
        assert take.alignment.text == line.text
        assert take.alignment.starts[0] == pytest.approx(0.0, abs=0.06)  # measured from the conformed file
        assert take.alignment.ends[-1] <= take.kept


def test_a_take_keeps_only_what_is_left_of_it_after_the_trim():
    full = Alignment(tuple("abcd"), (0.1, 0.5, 0.9, 1.3), (0.5, 0.9, 1.3, 1.7))
    take = sketch.kept_take("01", "dog", full, 2.0, 0.3, 0.8)
    assert take.alignment.characters == ("a", "b", "c")
    assert take.alignment.starts == pytest.approx((0.0, 0.2, 0.6))
    assert take.alignment.ends == pytest.approx((0.2, 0.6, 0.8))
    assert (take.at, take.kept, take.who, take.id) == (2.0, 0.8, "dog", "01")


def test_voiced_speech_round_trips_and_bad_files_are_refused(tmp_path):
    good = {"id": "01", "who": "dog", "at": 0.5, "kept": 1.0, "characters": ["a", "b"], "starts": [0.0, 0.2],
            "ends": [0.2, 0.4]}  # fmt: skip
    path = tmp_path / "speech.json"
    takes = [sketch.Take("01", "dog", 0.5, 1.0, Alignment(("a", "b"), (0.0, 0.2), (0.2, 0.4)))]
    sketch.write_speech(tmp_path, takes, 9.0)
    assert sketch.load_speech(tmp_path / "voiced" / "speech.json") == (takes, 9.0)

    def doc(end=9.0, **change) -> str:
        return json.dumps({"end": end, "takes": [good | change]})

    second = good | {"id": "02", "at": 0.1}
    for text, match in (
        ("nope", "speech.json"),
        ('{"takes": []}', "end and takes"),
        ('{"end": 9, "takes": {}}', "end and takes"),
        ('{"end": 9, "takes": [], "more": 1}', "end and takes"),
        (doc(end=0), "end must be"),
        (doc(end=True), "end must be"),
        (json.dumps({"end": 9, "takes": ["x"]}), "take 0"),
        (json.dumps({"end": 9, "takes": [good | {"pitch": 1}]}), "take 0"),
        (json.dumps({"end": 9, "takes": [{"id": "01"}]}), "take 0"),
        (doc(id="1"), "id"),
        (doc(id=1), "id"),
        (doc(who="gary"), "gary"),
        (doc(at=-1.0), "at"),
        (doc(at="1"), "at"),
        (doc(at=8.5), "past the end"),
        (doc(kept=0), "kept"),
        (doc(characters=["a"]), "one start and end per character"),
        (doc(characters=["a", 1]), "characters"),
        (doc(characters="ab"), "characters"),
        (doc(starts=[0.2, 0.0]), "rise"),
        (doc(starts=["0", 0.2]), "rise"),
        (doc(ends=[0.2, 1.4]), "inside the take"),
        (doc(ends=[0.2, 0.1]), "inside the take"),
        (json.dumps({"end": 9, "takes": [good, second]}), "time order"),
        (json.dumps({"end": 9, "takes": [good, good | {"at": 1.0}]}), "twice"),
    ):
        path.write_text(text)
        with pytest.raises(sketch.SketchError, match=match):
            sketch.load_speech(path)
    with pytest.raises(sketch.SketchError, match="missing.json"):
        sketch.load_speech(tmp_path / "missing.json")


def true_() -> bool:
    return True


# -- placing the picture on a recording -----------------------------------------------------------------------------
def fake_words(scale: float, offset: float = 0.0):
    starts, ends = [], []
    for (a, b), line in zip(sketch.line_spans(SK), LINES, strict=True):
        n = len(line.text.split())
        start, length = a * scale + offset, (b - a) * scale * 0.6
        starts.append([round(start + k * length / n, 6) for k in range(n)])
        ends.append(round(start + length, 6))
    return starts, ends


def test_placed_beats_follow_the_words_and_keep_the_silent_beats():
    starts, ends = fake_words(1.4)
    placed = sketch.place(SK, starts, ends)
    assert len(placed) == len(BEATS) and placed[0].start == 0
    for before, after in zip(BEATS, placed, strict=True):
        assert (after.who, after.caption, after.eyes, after.mouth, after.arms, after.event) == (
            before.who,
            before.caption,
            before.eyes,
            before.mouth,
            before.arms,
            before.event,
        )
        if before.line is not None and before.start > 0:
            word = starts[before.line][before.word]
            assert word - 1e-9 <= after.start <= word + sketch.CAPTION_LAG + 1e-9
    assert all(b.start - a.start >= sketch.MIN_STEP - 1e-9 for a, b in zip(placed, placed[1:], strict=False))
    # the silent typing beat keeps its scripted distance from the beat before; the frog's beat waits for the line
    assert (
        placed[1].start == pytest.approx(max(1.5, ends[0] + sketch.BLANK_GAP), abs=1e-6)
        or placed[1].start < starts[1][0]
    )
    assert placed[5].start >= ends[2] + sketch.BLANK_GAP - 1e-9
    sketch.check(replace(SK, beats=tuple(placed), end=placed[-1].start + 2))


def test_a_short_caption_holds_back_the_next_change_but_only_so_far():
    starts, ends = fake_words(1.0)
    starts[2] = [starts[2][0], starts[2][0] + 0.5, starts[2][0] + 0.9]
    placed = sketch.place(SK, starts, ends)
    assert placed[4].start == pytest.approx(placed[3].start + sketch.CAPTION_MIN)
    starts[2] = [starts[2][0], starts[2][0] + 0.2, starts[2][0] + 0.9]
    placed = sketch.place(SK, starts, ends)
    assert placed[4].start == pytest.approx(starts[2][1] + sketch.CAPTION_LAG)


def test_placing_refuses_takes_that_lack_the_words_or_lines():
    starts, ends = fake_words(1.0)
    with pytest.raises(sketch.SketchError, match="every line"):
        sketch.place(SK, starts[:-1], ends)
    starts[2] = starts[2][:1]
    with pytest.raises(sketch.SketchError, match="has no word"):
        sketch.place(SK, starts, ends)


def test_write_project_and_write_voiced_lay_out_the_files(tmp_path, monkeypatch):
    installed = []
    monkeypatch.setattr(sketch.fonts, "install", lambda font, folder: installed.append((font, Path(folder))))
    font = GoogleFont("Comic Neue", 700, italic=True)
    sketch.write_project(tmp_path, SK, font)
    assert installed == [(font, tmp_path / "assets" / "fonts")]
    assert json.loads((tmp_path / "script.json").read_text()) == sketch.cues(BEATS, SK.end, LINES)
    poses = json.loads((tmp_path / "assets" / "poses.json").read_text())
    assert [p["who"] for p in poses] == ["dog", "frog"] and toon.parse_poses(poses[0]["poses"])
    sketch.write_voiced(tmp_path, list(BEATS), SK.end)
    assert (tmp_path / "voiced" / "script.json").exists() and (tmp_path / "voiced" / "poses.json").exists()
    with pytest.raises(sketch.SketchError):
        sketch.write_project(tmp_path, replace(SK, end=1.0), font)


# -- recording --------------------------------------------------------------------------------------------------------
def copy_clip(src, dst, clip_in, clip_out, length, gain_db, ffmpeg):
    shutil.copy(src, dst)
    return length


def test_record_says_every_line_in_its_voice_places_the_beats_and_writes_the_manifest(tmp_path):
    client = FakeClient(tmp_path)
    rec = sketch.record(SK, tmp_path, client, confirm=confirm_stub, conform_clip=copy_clip)
    assert [(t, v) for t, v, _ in client.requests] == [
        ("The report is due at nine.", "Charlie"),
        ("How is it going?", "George"),
        ("Great. Almost done.", "Charlie"),
    ]
    assert [q["id"] for q in rec.items] == ["01", "02", "03"] and set(rec.voices) == {"rex", "boss"}
    assert all((tmp_path / q["audio"]).is_file() for q in rec.items)
    assert len(rec.beats) == len(BEATS) and rec.end >= rec.beats[-1].start + sketch.TAIL_AFTER_LAST
    first_word = rec.items[1]["start"] + 0.05 - (0.05 - sketch.SPEECH_LEAD)  # the take leads its first letter
    assert rec.beats[2].start == pytest.approx(first_word, abs=1 / 8000)  # on its word, the trim snapped to a sample
    assert rec.speech == [(q["start"], q["start"] + q["duration"]) for q in rec.items]
    heard = json.loads((tmp_path / "voice-transcript.json").read_text())
    assert heard["passed"] and [h["speaker"] for h in heard["lines"]] == ["rex", "boss", "rex"]
    assert json.loads((tmp_path / "voiced" / "script.json").read_text())[0]["text"] == "Due at 9"
    # the manifest the episode plays from passes the narration parser, effects included
    fx = tmp_path / "audio" / "buzz.wav"
    music.write_wav(fx, [0.0] * 800, 8000)
    effects = [sketch.effect("buzz", 3.0, -4.0, tmp_path, fx, taps=[3.0, 3.2])]
    doc = sketch.manifest(SK, rec, effects, "model-x", "premade voices")
    (tmp_path / "narration.json").write_text(json.dumps(doc))
    cues = narration.narration_cues(tmp_path / "narration.json", tmp_path)
    assert [c.id for c in cues] == ["01", "02", "03"]
    (buzz,) = narration.effect_cues(tmp_path / "narration.json", tmp_path)
    assert (buzz.start, buzz.gain_db, buzz.taps) == (3.0, -4.0, (3.0, 3.2))
    assert narration.manifest_duration(tmp_path / "narration.json") == rec.end
    assert doc["voice"]["rex"]["name"].startswith("Charlie") and doc["caption_duration"] == 9.0


def test_record_refuses_a_line_speech_to_text_did_not_hear_as_scripted(tmp_path):
    client = FakeClient(tmp_path, heard={"How is it going?": "How is it growing?"})
    with pytest.raises(sketch.SketchError, match=r"line 02 \(boss\).*growing"):
        sketch.record(SK, tmp_path, client, confirm=confirm_stub, conform_clip=copy_clip)
    heard = json.loads((tmp_path / "voice-transcript.json").read_text())
    assert not heard["passed"] and heard["lines"][1]["heard"] == "How is it growing?"
    assert not (tmp_path / "voiced").exists()


def test_record_takes_a_hearing_the_operator_accepted_and_reports_it(tmp_path):
    lines = (LINES[0], replace(LINES[1], heard=("How is it growing?",)), LINES[2])
    client = FakeClient(tmp_path, heard={"How is it going?": "How is it growing?"})
    rec = sketch.record(replace(SK, lines=lines), tmp_path, client, confirm=confirm_stub, conform_clip=copy_clip)
    assert [q["id"] for q in rec.items] == ["01", "02", "03"]
    heard = json.loads((tmp_path / "voice-transcript.json").read_text())
    assert heard["passed"] and heard["lines"][1]["accepted"] == ["How is it growing?"]
    assert "accepted" not in heard["lines"][0]


def test_record_still_refuses_a_hearing_that_was_not_accepted(tmp_path):
    lines = (LINES[0], replace(LINES[1], heard=("How is it growing?",)), LINES[2])
    client = FakeClient(tmp_path, heard={"How is it going?": "Who is it owing?"})
    with pytest.raises(sketch.SketchError, match=r"line 02 \(boss\).*owing"):
        sketch.record(replace(SK, lines=lines), tmp_path, client, confirm=confirm_stub, conform_clip=copy_clip)
    assert not json.loads((tmp_path / "voice-transcript.json").read_text())["passed"]


@pytest.mark.parametrize("heard", [("How is it going?",), ("how is it, going",), ("",), ("?!",)])
def test_check_refuses_an_accepted_hearing_that_is_the_line_itself_or_empty(heard):
    lines = (LINES[0], replace(LINES[1], heard=heard), LINES[2])
    with pytest.raises(sketch.SketchError, match=r"line 1.*accepted hearing"):
        sketch.check(replace(SK, lines=lines))


def test_voiced_beats_round_trip_and_bad_files_are_refused(tmp_path):
    sketch.write_voiced(tmp_path, BEATS, SK.end, LINES)
    beats, end = sketch.load_beats(tmp_path / "voiced" / "beats.json")
    assert beats == list(BEATS) and end == SK.end
    sketch.check(replace(SK, beats=tuple(beats), end=end))
    path = tmp_path / "bad.json"

    def beat(**changes) -> str:
        q = {"start": 0, "who": "dog", "caption": "", "eyes": "wide", "mouth": "flat", "arms": "desk"}
        return json.dumps({"end": 9.0, "beats": [{**q, "line": None, "word": None, "event": "", **changes}]})

    for text, match in (
        ("nope", "bad.json"),
        ('{"end": 9.0}', "end and beats"),
        ('{"end": "9", "beats": []}', "end must be"),
        ('{"end": 9.0, "beats": [{"start": 0}]}', "fields must be exactly"),
        (beat(start=True), "start must be"),
        (beat(who=1), "are strings"),
        (beat(line=0.5, word=0), "whole numbers"),
    ):
        path.write_text(text)
        with pytest.raises(sketch.SketchError, match=match):
            sketch.load_beats(path)
    with pytest.raises(sketch.SketchError, match="missing.json"):
        sketch.load_beats(tmp_path / "missing.json")

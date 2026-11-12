"""The Ink style: takes, phoneme mouths, caption pages, and a full square shot-sequence build."""

import inspect
import json
import xml.etree.ElementTree as ET

import pytest
from sr_core.scene import Scene

from srstudio import (
    INK,
    INK_MOUTH,
    MONO,
    Canvas,
    Episode,
    EpisodeSpec,
    Timeline,
    ink,
    phoneme_states,
    shared_counter,
    subtitles,
)
from support.ink_layout import WORDS, phones, router_take, square_canvas, takes_data


@pytest.fixture
def square_project(tmp_path):
    from support.generated import write_wav

    data = takes_data()
    (tmp_path / "timeline.json").write_text(json.dumps(data))
    for item in data["items"]:
        write_wav(tmp_path / item["audio"], [0.0] * 100)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "hand.ttf").write_bytes(b"\0")
    return tmp_path


def test_timeline_detects_takes():
    t = Timeline.from_dict(takes_data())
    assert [x.id for x in t.takes] == ["01", "02", "03", "04"]
    assert [p.role for p in t.phrases] == ["human", "printer", "human"]
    assert [c.angle for c in t.cuts] == ["desk", "printer", "printer-close", "human"]
    assert t.sound_effects[0].name == "[PRINTER WHIRRS]" and t.take("02").is_effect
    assert t.take("04").end == pytest.approx(6.0)
    with pytest.raises(KeyError):
        t.take("99")


def test_phoneme_states_map_letters_and_moods():
    states = phoneme_states(phones("ombx"), 0.32, "", INK_MOUTH)
    by = dict(states)
    assert by[0.0] == "round" and by[1 / 12] == "closed" and by[2 / 12] == "closed" and by[3 / 12] == "teeth"
    assert states[-1] == (0.32, "closed")
    assert {s for _, s in phoneme_states(phones("abc"), 0.24, "scream")} == {"shout", "closed"}
    assert dict(phoneme_states(phones("a"), 0.08, "angry"))[0.0] == "shout"


def test_caption_pages_break_at_sentences_and_width():
    cues = subtitles.chunk_words(WORDS, 2.1)
    assert [c[2] for c in cues] == ["OKAY.", "COME ON.", "COME ON!"]
    assert cues[0][0] == 0 and cues[0][1] == WORDS[1]["start"] and cues[-1][1] == 2.1
    long = [{"text": "word", "start": i * 0.1, "end": i * 0.1 + 0.05} for i in range(10)]
    assert all(len(c[2]) <= 31 for c in subtitles.chunk_words(long, 1.0))
    assert subtitles.srt_stamp(3661.5) == "01:01:01,500"


def test_caption_pages_shorter_than_the_minimum_merge_with_a_neighbour():
    # OKAY. 0-0.72, COME ON. 0.72-1.49, COME ON! 1.49-2.1: the last page is too short and joins the one before it.
    cues = subtitles.chunk_words(WORDS, 2.1, min_seconds=0.7)
    assert [(round(s, 2), round(e, 2), x) for s, e, x in cues] == [(0, 0.72, "OKAY."), (0.72, 2.1, "COME ON. COME ON!")]
    # A short page joins the next one when the text still fits.
    words = [
        {"text": "Go.", "start": 0.0, "end": 0.2},
        {"text": "Now", "start": 0.3, "end": 0.6},
        {"text": "please.", "start": 0.7, "end": 1.6},
    ]
    assert [c[2] for c in subtitles.chunk_words(words, 1.8, min_seconds=0.7)] == ["GO. NOW PLEASE."]
    # When no neighbour fits within max_chars the short page stays, and the default merges nothing.
    assert [c[2] for c in subtitles.chunk_words(words, 1.8, min_seconds=0.7, max_chars=12)] == ["GO.", "NOW PLEASE."]
    assert len(subtitles.chunk_words(WORDS, 2.1)) == 3
    with pytest.raises(ValueError, match="min_seconds"):
        subtitles.chunk_words(WORDS, 2.1, min_seconds=-1)


def test_an_orphan_word_takes_the_tail_of_the_page_before_it():
    line = (
        "I 0 .1 could. .15 .5 But 1 1.1 it's 1.15 1.3 not 1.35 1.5 the 1.55 1.65 same 1.7 2 "
        "when 2.1 2.25 I 2.3 2.35 do 2.4 2.55 it. 2.6 2.9"
    )
    toks = line.split()
    words = [{"text": toks[i], "start": float(toks[i + 1]), "end": float(toks[i + 2])} for i in range(0, len(toks), 3)]
    assert [c[2] for c in subtitles.chunk_words(words, 3.3)] == ["I COULD.", "BUT IT'S NOT THE SAME WHEN I DO", "IT."]
    cues = subtitles.chunk_words(words, 3.3, min_seconds=0.85)
    assert [(round(s, 2), round(e, 2), x) for s, e, x in cues] == [
        (0, 1.0, "I COULD."),
        (1.0, 2.4, "BUT IT'S NOT THE SAME WHEN I"),
        (2.4, 3.3, "DO IT."),
    ]
    # Moving two words works when one is not enough; a lone short page with no neighbour stays.
    tight = [dict(w) for w in words]
    tight[-1]["start"], tight[-2]["start"] = 3.0, 2.95
    assert [c[2] for c in subtitles.chunk_words(tight, 3.3, min_seconds=0.85)][-1] == "I DO IT."
    assert subtitles.chunk_words([{"text": "Hi.", "start": 0, "end": 0.2}], 0.5, min_seconds=0.85) == [(0, 0.5, "HI.")]


def test_a_short_page_nothing_fits_beside_does_not_stop_a_later_one_merging():
    words = [
        {"text": "Xxxxxxxxxx.", "start": 0.0, "end": 0.9},
        {"text": "Yyyyyyyyyy.", "start": 1.0, "end": 1.1},  # short, and no neighbour fits 12 characters with it
        {"text": "Zzzzzzzzzz.", "start": 1.2, "end": 2.9},
        {"text": "Go.", "start": 3.0, "end": 3.1},  # short, and joins the next page
        {"text": "Now.", "start": 3.2, "end": 3.9},
    ]
    cues = subtitles.chunk_words(words, 4.0, max_chars=12, min_seconds=0.7)
    assert [c[2] for c in cues] == ["XXXXXXXXXX.", "YYYYYYYYYY.", "ZZZZZZZZZZ.", "GO. NOW."]


def test_canvas_options():
    scene = Scene(version="auto")
    scene.add_project(width=1080, height=1080, fps="24", duration=2)
    cv = Canvas(scene, MONO, width=1080, height=1080, namer=shared_counter(), local_time=True)
    g = cv.group(cv.comp, "g")
    cv.keys(g, "rotation", [(0, 0), (0.5, 3)], kind="sine-in-out")
    assert ink.path(cv, g, "M0 0 L1 1", sw=0).stroke == cv.clear
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    assert root.find("paints") is None, "no gradient was asked for"
    anim = root.find(".//group[@id='g']/animate")
    assert anim.get("timeBase") == "local" and anim.get("defaultInterpolation") == "sine-in-out"
    assert root.find(".//shape").get("id") == "p1" and root.find(".//shape").get("height") == "1080"


def test_square_episode_builds_and_validates(square_project, tmp_path):
    ep = Episode(
        EpisodeSpec(
            slug="scene",
            title="t",
            description="t",
            root=square_project,
            seed=1,
            style=INK,
            font="assets/hand.ttf",
            output_options=dict(codec="h264", fps="24", crf="18"),
            poster=dict(time=1, path="cover.jpg"),
        )
    )
    shots = ep.sequence()
    ep.mix(loudness="-14", bit_depth=None)
    for take in ep.takes:
        g = ep.shot(shots, take)
        {
            "desk": lambda g=g, take=take: ink.desk_shot(ep.cv, g, take),
            "printer": lambda g=g, take=take: ink.printer_shot(ep.cv, g, take),
            "printer-close": lambda g=g, take=take: ink.printer_shot(ep.cv, g, take, close=True),
            "human": lambda g=g, take=take: ink.closeup(ep.cv, g, take, zoom=1.53),
        }[take.shot]()
        for start, end, text in (
            [(0, take.duration, take.text)] if take.is_effect else subtitles.chunk_words(take.words, take.duration)
        ):
            ink.caption(ep.cv, g, text, start=start, end=end)
        ep.take_audio(take, pan=0.08)
    with pytest.raises(ValueError):
        ep.mouth("human")
    out = ep.finish(tmp_path / "scene.xml")
    assert ep.check() == []
    root = ET.parse(out).getroot()
    assert root.find("project").get("fontPolicy") == "pinned" and root.find("output/poster") is not None
    assert [g.get("id") for g in root.find("composition/sequence")] == ["shot-01", "shot-02", "shot-03", "shot-04"]
    assert len(root.findall("audioMix/audioTrack")) == 4 and root.find("audioMix/master").get("loudness") == "-14"
    assert all(a.get("timeBase") == "local" for a in root.iter("animate"))


def animated(root, group_id, prop):
    """The ``values`` of every ``<animate property=prop>`` under the group ``group_id``."""
    g = root.find(f".//group[@id='{group_id}']")
    assert g is not None, group_id
    return [a for a in g.iter("animate") if a.get("property") == prop]


def test_router_talks_with_leds_and_voice_marks_and_signs_its_plate():
    scene, cv = square_canvas()
    g = cv.group(cv.comp, "r")
    ink.router(cv, g, router_take(), 200, 400, 1.2)
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    leds = [a for a in animated(root, "r", "opacity") if a.find("key") is not None]
    assert len(leds) >= ink.ROUTER_LEDS + 1, "every LED blinks and the voice marks fade"
    assert all(a.get("timeBase") == "local" for a in root.iter("animate"))
    ids = [n.get("id") for n in root.iter() if n.get("id")]
    assert any(i.startswith("sig-code") for i in ids), "the model plate carries the signature code"
    assert animated(root, "r", "rotation"), "the antennas bob while it talks"


def test_router_is_quiet_when_someone_else_speaks_and_unsigned_without_a_signature():
    scene, cv = square_canvas(signed=False)
    g = cv.group(cv.comp, "r")
    ink.router(cv, g, router_take(actor="human", text="The internet's down."), 200, 400)
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    assert animated(root, "r", "opacity") == [] and animated(root, "r", "rotation") == []
    assert not any((n.get("id") or "").startswith("sig-") for n in root.iter())


@pytest.mark.parametrize("power", ["down", "up"])
def test_router_power_down_and_up_step_the_leds(power):
    scene, cv = square_canvas()
    g = cv.group(cv.comp, "r")
    take = router_take(actor="sfx", text="[CLICK]", shot="router-close") if power == "down" else router_take()
    ink.router(cv, g, take, 200, 400, power=power)
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    led_keys = [
        [float(k.get("value")) for k in a.findall("key")]
        for a in animated(root, "r", "opacity")
        if len(a.findall("key")) >= 2
    ]
    assert len(led_keys) >= ink.ROUTER_LEDS
    first, last = led_keys[0][0], led_keys[-1][-1]
    assert (first > last) if power == "down" else (first < last)


def test_router_refuses_an_unknown_power_state_and_a_drop_outside_the_take():
    scene, cv = square_canvas()
    g = cv.group(cv.comp, "r")
    with pytest.raises(ValueError, match="power"):
        ink.router(cv, g, router_take(), 0, 0, power="sideways")
    with pytest.raises(ValueError, match="drop_at"):
        ink.router(cv, g, router_take(), 0, 0, drop_at=9.0)


def test_router_drop_at_turns_every_led_off_at_that_moment():
    scene, cv = square_canvas()
    g = cv.group(cv.comp, "r")
    ink.router(cv, g, router_take(text="Connected. Oh, wait. No."), 200, 400, drop_at=1.5)
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    ends = [
        (float(a.findall("key")[-1].get("time")), float(a.findall("key")[-1].get("value")))
        for a in animated(root, "r", "opacity")
    ]
    assert sum(1 for t, v in ends if t == pytest.approx(1.5) and v < 0.2) >= ink.ROUTER_LEDS


def test_hand_reaches_or_presses_the_router_button():
    scene, cv = square_canvas()
    g = cv.group(cv.comp, "h")
    ink.hand(cv, g, 900, 700, 1.0, action="press", at=0.4)
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    keys = animated(root, "h", "x") + animated(root, "h", "y")
    assert keys and any(float(k.get("time")) == pytest.approx(0.4) for a in keys for k in a.findall("key"))
    with pytest.raises(ValueError, match="action"):
        ink.hand(cv, g, 0, 0, action="wave")


@pytest.mark.parametrize("action", ink.HAND_ACTIONS)
@pytest.mark.parametrize("at", [-1.0, 0.0, float("nan"), float("inf"), True])
def test_hand_refuses_an_action_time_that_is_not_a_positive_number_of_seconds(action, at):
    _, cv = square_canvas()
    with pytest.raises(ink.InkError, match="lands at a time over 0 s"):
        ink.hand(cv, cv.group(cv.comp, "h"), 900, 700, action=action, at=at)


def test_router_shots_place_the_router_on_its_shelf():
    scene, cv = square_canvas()
    for close in (False, True):
        g = cv.group(cv.comp, f"shot-{int(close)}")
        ink.router_shot(cv, g, router_take(), close=close)
    g = cv.group(cv.comp, "wide")
    ink.router_wide(cv, g, router_take(actor="sfx", text="[CHAIR SCRAPE]", shot="wide"))
    root = ET.fromstring(scene.to_bytes(layout="pretty"))
    assert root.find(".//group[@id='shot-0']") is not None and root.find(".//group[@id='shot-1']") is not None
    wide = root.find(".//group[@id='wide']")
    assert sum(1 for n in wide.iter() if (n.get("id") or "").startswith("sig-cactus")) == 1
    assert sum(1 for n in wide.iter() if (n.get("id") or "").startswith("sig-code")) == 1
    assert scene.check() == []


def router_takes_data():
    items = [
        ("01", "human", "desk", "impatient", "Come on. Load. Load!", False),
        ("02", "router", "router", "calm", "Hi. Everything okay over there?", False),
        ("03", "human", "human", "question", "The internet's down.", False),
        ("06", "router", "router-close", "calm", "I could. But it's not the same when I do it.", False),
        ("09", "sfx", "wide", "", "[CHAIR SCRAPE]", True),
        ("10", "human", "router-close", "angry", "Fine. Off.", False),
        ("11", "sfx", "router-close", "", "[CLICK]", True),
        ("12", "human", "router-close", "impatient", "...and on.", False),
        ("19", "router", "router", "calm", "Connected. Oh, wait. No.", False),
        ("20", "sfx", "human", "angry", "[ROUTER BEEP]", True),
    ]
    out, start = [], 0.0
    for id, actor, shot, mood, text, effect in items:
        q = dict(id=id, actor=actor, shot=shot, mood=mood, text=text, start=start, duration=1.5, speech_duration=1.3)
        q["audio"] = f"audio/{'fx' if effect else 'take'}-{id}.wav"
        if not effect:
            step = 1.2 / len(text.split())
            q["words"] = [
                {"text": w, "start": 0.1 + i * step, "end": 0.1 + (i + 0.8) * step} for i, w in enumerate(text.split())
            ]
            q["phones"] = phones(text.lower(), 1.2 / len(text))
        else:
            q["speech_duration"], q["seconds"] = 0, 1.0
        out.append(q)
        start += 1.5
    return {"duration": start, "tempo_adjustment": 1.0, "items": out}


def test_router_episode_builds_and_validates(tmp_path):
    from support.generated import write_wav

    data = router_takes_data()
    (tmp_path / "timeline.json").write_text(json.dumps(data))
    for item in data["items"]:
        write_wav(tmp_path / item["audio"], [0.0] * 100)
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "hand.ttf").write_bytes(b"\0")
    ep = Episode(
        EpisodeSpec(
            slug="router",
            title="t",
            description="t",
            root=tmp_path,
            seed=2,
            style=INK,
            font="assets/hand.ttf",
            signature_code="SR-1028",
        )
    )
    shots = ep.sequence()
    ep.mix(loudness="-14", bit_depth=None)
    for take in ep.takes:
        g = ep.shot(shots, take)
        ink.router_scene(ep.cv, g, take)
        ep.take_audio(take)
    out = ep.finish(tmp_path / "scene.xml")
    root = ET.parse(out).getroot()
    assert len(root.find("composition/sequence")) == 10 and len(root.findall("audioMix/audioTrack")) == 10
    assert sum(1 for n in root.iter() if (n.get("id") or "").startswith("sig-code")) >= 5


@pytest.mark.parametrize("fn", [ink.router, ink.router_shot, ink.router_wide, ink.router_scene])
def test_the_router_parts_take_no_frame_rate_they_would_never_read(fn):
    assert "fps" not in inspect.signature(fn).parameters

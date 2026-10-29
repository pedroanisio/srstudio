"""The Cactus (Comedy Cut 21): the schedule keeps every line and effect in order with the holds the jokes need, the
cuts run office, café, park, office, and the built episode shows exactly one cactus in every location, the
performing signature cactus (ADR 0039), its code drawn inline for the push-in that fills the frame with it.

The build runs the episode's own script on a dry project: silent clips of a stand-in length at every generated
item's cache path, placed by the episode's schedule as :func:`srstudio.interview.place` would place them, each
line's hearing cached as :func:`srstudio.interview.hear` leaves it, its words spread evenly over the take."""

import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from srstudio import signature
from srstudio.generated import PlacedClip, Placement
from srstudio.interview import FPS, Timing, declarations
from srstudio.layout import LayoutError, find_engine
from srstudio.sample import SYSTEM_FONTS, write_wav
from srstudio.voice import ElevenLabsClient

EPISODES = Path(__file__).resolve().parent.parent / "episodes"
SPEECH = [1.5, 1.4, 0.9, 1.3, 2.6, 0.6, 2.4, 1.6, 2.7]  # stand-ins for the recorded lines, seconds
EFFECT = {"cup": 0.5, "flutter": 1.1, "swivel": 1.7, "pop": 0.35}
LOCATIONS = (
    "wide-office-angle",
    "candidate-reverse-angle",
    "location-cafe",
    "location-park",
    "desk-office-angle",
    "applicant-reverse-angle",
)
CACTUS = re.compile(r"sig-cactus(-\d+)?\Z")


@pytest.fixture(scope="module")
def audio():
    sys.path.insert(0, str(EPISODES))
    try:
        import the_cactus_audio
    finally:
        sys.path.pop(0)
    return the_cactus_audio


def timing(audio) -> Timing:
    plan = audio.schedule(SPEECH, EFFECT)
    iv = audio.INTERVIEW
    phrases = [
        {
            "role": line.role,
            "text": line.text,
            "caption": line.caption,
            "voice": iv.voices[line.role].id,
            "voice_name": iv.voices[line.role].name,
            "speed": line.speed,
            "start": round(start, 6),
            "end": round(start + length, 6),
            "trim_seconds": 0.0,
        }
        for line, start, length in zip(iv.lines, plan.lines, SPEECH, strict=True)
    ]
    last = phrases[-1]["end"]
    reaction = last + iv.reaction_after
    ending = reaction + iv.reaction_hold
    return Timing(phrases, dict(plan.effects), last, reaction, ending, math.ceil((ending + iv.end_card) * FPS) / FPS)


def spans(audio):
    t = timing(audio)
    return [(p["start"], p["end"]) for p in t.phrases], t.effects, t


def test_the_script_has_the_series_voices_and_a_seeded_effect_for_each_sound(audio):
    assert {line.role for line in audio.SCRIPT} == set(audio.VOICES) == {"manager", "candidate", "ava", "milo"}
    assert len({v.id for v in audio.VOICES.values()}) == 4
    _, effects = declarations(audio.INTERVIEW)
    assert [g.seed for g in effects] == [audio.SEED + k for k in range(len(audio.EFFECTS))]
    assert not any(ch.isdigit() for line in audio.SCRIPT for ch in line.text)  # speech-to-text writes numbers


def test_lines_follow_each_other_and_every_effect_plays_alone_in_its_gap(audio):
    lines, fx, t = spans(audio)
    assert all(a[1] < b[0] for a, b in zip(lines, lines[1:], strict=False))
    gaps = {"cup": 1, "flutter": 4, "swivel": 4}  # after line i (0-based), before the next
    for name, i in gaps.items():
        assert lines[i][1] < fx[name] and fx[name] + EFFECT[name] < lines[i + 1][0], name
    assert fx["flutter"] + EFFECT["flutter"] < fx["swivel"]
    assert t.reaction < fx["pop"] and fx["pop"] + EFFECT["pop"] <= t.duration  # the pop, then the hard cut


def test_the_jokes_get_their_holds(audio):
    lines, fx, t = spans(audio)
    reveal = fx["swivel"] + audio.SWING
    assert lines[5][0] - reveal >= 1.2  # the cactus faces him, held, before "No."
    assert t.reaction - lines[-1][1] >= 1.2  # the question hangs before the cut to the cactus
    assert t.duration - fx["pop"] <= 1.0 and audio.INTERVIEW.end_card == 0  # no card after the bloom
    assert "five years" in audio.SCRIPT[-1].text and audio.SCRIPT[1].text == "It came with the chair."


def test_the_cuts_run_office_cafe_park_office_and_end_on_the_bloom(audio):
    lines, fx, t = spans(audio)
    extra = audio.extra(t)
    cuts = extra["camera_cuts"]
    times = [c["time"] for c in cuts]
    assert times == sorted(times) and times[0] == 0
    assert [c["angle"] for c in cuts] == [
        "wide",
        "candidate",
        "cafe",
        "park",
        "chair",
        "manager",
        "code",
        "applicant",
        "bloom",
    ]
    at = {c["angle"]: c["time"] for c in cuts}
    assert lines[1][1] < at["cafe"] < fx["cup"] < lines[2][0]  # the café opens on the cup
    assert lines[3][1] < at["park"] < lines[4][0] and lines[4][1] < fx["flutter"]
    assert fx["flutter"] + EFFECT["flutter"] < at["chair"] < fx["swivel"]  # the chair's back before it turns
    assert fx["swivel"] + audio.SWING < at["manager"] < lines[5][0]
    assert lines[5][1] < at["code"] < lines[6][0] and lines[6][0] - at["code"] >= audio.PUSH  # the code, then the line
    assert lines[7][1] < at["applicant"] < lines[8][0] and at["bloom"] == t.reaction < extra["bloom_start"]
    assert extra["bloom_start"] == fx["pop"] and lines[3][1] < extra["turn_start"] < at["park"] - 0.9
    assert {extra[k] for k in ("cafe_start", "park_start", "chair_start", "push_start", "sit_start")} <= set(times)


# -- the build -------------------------------------------------------------------------------------------------------
def hear_evenly(root: Path, take: Path, text: str, length: float) -> None:
    """Cache the take's transcript: the script's words, each given an equal share of the take."""
    said = text.split()
    step = length / len(said)
    words = [{"text": w, "start": i * step, "end": (i + 0.8) * step, "type": "word"} for i, w in enumerate(said)]
    body = {"language_code": "en", "language_probability": 1.0, "text": text, "words": words}
    ElevenLabsClient(
        root / "assets" / "elevenlabs", key="dry", multipart_transport=lambda *a: (body, "dry")
    ).transcribe(take)


def dry_project(root: Path, audio) -> Path:
    """A project as the recording would leave it, every clip silent but for a tone and of its stand-in length."""
    t = timing(audio)
    iv = audio.INTERVIEW
    lines, effects = declarations(iv)
    clips, sounds = [], []
    lengths = dict(zip([g.id for g in lines], SPEECH, strict=True)) | EFFECT
    starts = dict(zip([g.id for g in lines], [p["start"] for p in t.phrases], strict=True)) | t.effects
    for g in [*lines, *effects]:
        wav = root / g.cache
        wav.parent.mkdir(parents=True, exist_ok=True)
        write_wav(wav, [(0.0, lengths[g.id])], lengths[g.id], rate=48000)
        role = "dialogue" if g.kind == "speech" else "effects"
        placement = Placement(start=round(starts[g.id], 6), clip_out=lengths[g.id], role=role,
                              language="en" if role == "dialogue" else None)  # fmt: skip
        clips.append(PlacedClip(g, hashlib.sha256(wav.read_bytes()).hexdigest(), placement).to_dict())
        if role == "dialogue":
            hear_evenly(root, wav, g.prompt, lengths[g.id])
        if role == "effects":
            sounds.append({"name": g.id, "start": placement.start, "duration": lengths[g.id], "generator": "dry"})
    write_wav(root / "assets" / "room-tone.wav", [], t.duration, rate=48000)
    shutil.copyfile(next(f for f in SYSTEM_FONTS if f.exists()), root / "assets" / "DejaVuSans-Bold.ttf")
    timeline = {
        "title": iv.title,
        "language": "en-US",
        "duration": t.duration,
        "phrases": t.phrases,
        "sound_effects": sounds,
        "clips": clips,
        **audio.extra(t),
    }
    (root / "dialogue.json").write_text(json.dumps(timeline, indent=2) + "\n")
    return root


@pytest.fixture(scope="module")
def built(audio, tmp_path_factory):
    try:
        find_engine(None)
    except LayoutError:
        pytest.skip("the overlay check needs scene-render (SRSTUDIO_ENGINE)")
    if not any(f.exists() for f in SYSTEM_FONTS):
        pytest.skip("the dry project needs DejaVu Sans Bold")
    root = dry_project(tmp_path_factory.mktemp("the-cactus"), audio)
    subprocess.run([sys.executable, str(EPISODES / "the_cactus.py"), str(root)], check=True, capture_output=True)
    document = (root / "the-cactus.scene.xml").read_bytes()
    return ET.fromstring(document), document


def _group(root, id):
    (g,) = [el for el in root.iter("group") if el.get("id") == id]
    return g


def test_every_location_shows_exactly_one_cactus_and_the_episode_is_signed(built):
    root, document = built
    assert signature.missing(document) == []
    for location in LOCATIONS:
        marks = [el for el in _group(root, location).iter("group") if CACTUS.match(el.get("id") or "")]
        assert len(marks) == 1, location
    every = [el for el in root.iter("group") if CACTUS.match(el.get("id") or "")]
    assert len(every) == len(LOCATIONS)  # nothing outside a location draws one


def test_the_cactus_in_the_executive_chair_turns_with_it_and_its_code_is_drawn_inline(built):
    root, _ = built
    desk = _group(root, "desk-office-angle")
    front = _group(desk, "executive-turn-front")
    (cactus,) = [el for el in front.iter("group") if CACTUS.match(el.get("id") or "")]
    code = [el for el in cactus.iter("group") if (el.get("id") or "").startswith("sig-code")]
    assert len(code) == 1 and len(code[0].findall("shape")) == 7
    assert desk.find(".//instance") is None  # inline: the push-in does not soften it


def test_the_push_in_fills_the_frame_with_the_code_without_cutting_it(audio):
    scale = audio.SEAT[2] * audio.PUSH_TO
    width, height = signature.text_width("SR-1028", signature.POT_CODE) * scale, signature.POT_CODE * scale
    assert 0.6 * 1080 <= width <= 1080 - 2 * 80  # fills the frame, inside the side margins
    assert height >= 4 * 21.6 and audio.PUSH_Y + height / 2 < 1240  # far above the legible size, above the captions


def test_the_release_declares_the_cover_and_the_recurring_cast():
    sys.path.insert(0, str(EPISODES))
    try:
        from posts.the_cactus import RELEASE
    finally:
        sys.path.pop(0)
    assert RELEASE.cover and "cactus" in RELEASE.tags.recurring
    assert (RELEASE.tags.territory, RELEASE.post.thumbnail.kicker) == ("job-hunting", "Comedy Cut 21")

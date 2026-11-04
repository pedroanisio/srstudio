"""Text to Dialogue (ADR 0234): the request, the typed parse of the answer, the per-turn cuts, the cache, and every
malformed, inconsistent or adversarial answer refused before anything is cached.

No network: the transport is injected. Audio is a real MP3 made by ffmpeg, so decoding and the cuts run."""

import base64
import copy
import json
import shutil
import subprocess

import pytest

from srstudio.dialogue import DIALOGUE_API, MAX_CHARS, Turn, parse_dialogue, payload, say
from srstudio.direction import Direction, DirectionError, Pause
from srstudio.errors import MissingKeyError
from srstudio.narration import wav_seconds
from srstudio.voice import ElevenLabsClient, Voice, VoiceOutputError, VoiceSettings

LEO = Voice(role="leo", id="RolvCZ4e0AkAR2dzyTx0", name="Christopher")
WILL = Voice(role="candidate", id="bIHbv24MWmeRgasZH58o", name="Will")
V4 = VoiceSettings.expressive(0.4)
SECONDS = 2.4


def _mp3(tmp_path_factory, name: str, graph: list[str]) -> bytes:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    out = tmp_path_factory.mktemp(name) / f"{name}.mp3"
    cmd = ["ffmpeg", "-v", "error", "-y", *graph, "-ar", "44100", "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k"]
    subprocess.run([*cmd, str(out)], check=True)
    return out.read_bytes()


@pytest.fixture(scope="module")
def mp3(tmp_path_factory) -> bytes:
    return _mp3(tmp_path_factory, "tone", ["-f", "lavfi", "-i", f"sine=frequency=220:duration={SECONDS}"])


@pytest.fixture(scope="module")
def half_silent(tmp_path_factory) -> bytes:
    """A tone that stops before the first turn's segment ends, then silence: the second of two turns says nothing."""
    graph = ["-f", "lavfi", "-i", "sine=frequency=220:duration=1.0"]
    graph += [
        "-f",
        "lavfi",
        "-i",
        f"anullsrc=r=44100:cl=mono:d={SECONDS - 1.0}",
        "-filter_complex",
        "concat=n=2:v=0:a=1",
    ]
    return _mp3(tmp_path_factory, "half", graph)


def answer(request: dict, audio: bytes) -> dict:
    """The answer the API gives: the inputs joined with nothing between them, one segment per turn, the turns meeting
    end to start and each turn's letters spread inside its own segment."""
    texts = [i["text"] for i in request["inputs"]]
    span = (SECONDS - 0.05) / len(texts)
    chars, starts, ends, segments = [], [], [], []
    offset = 0
    for k, (text, item) in enumerate(zip(texts, request["inputs"], strict=True)):
        t0, step = k * span, (span - 0.2) / len(text)
        for j, c in enumerate(text):
            chars.append(c)
            starts.append(round(t0 + 0.1 + j * step, 3))
            ends.append(round(t0 + 0.1 + (j + 1) * step, 3))
        segments.append({
            "voice_id": item["voice_id"],
            "start_time_seconds": round(t0, 3),
            "end_time_seconds": round(t0 + span, 3),
            "character_start_index": offset,
            "character_end_index": offset + len(text),
            "dialogue_input_index": k,
        })  # fmt: skip
        offset += len(text)
    alignment = {"characters": chars, "character_start_times_seconds": starts, "character_end_times_seconds": ends}
    return {
        "audio_base64": base64.b64encode(audio).decode(),
        "alignment": alignment,
        "normalized_alignment": copy.deepcopy(alignment),
        "voice_segments": segments,
    }


class Transport:
    def __init__(self, audio: bytes, spoil=None):
        self.audio, self.spoil, self.calls = audio, spoil, []

    def __call__(self, url, request, headers):
        self.calls.append((url, request, headers))
        body = answer(request, self.audio)
        if self.spoil is not None:
            self.spoil(body)
        return body, f"req-{len(self.calls)}"


TURNS = (Turn("Did you feed the dog?", LEO), Turn("Dog food. Discipline.", WILL))
ELEVEN = tuple(Turn("Hi.", Voice(f"r{i}", f"id{i}", f"n{i}")) for i in range(11))


def client(tmp_path, transport, key="k"):
    return ElevenLabsClient(tmp_path / "cache", key, seed=52026, transport=transport)


# -- the request --------------------------------------------------------------------------------------------------
def test_a_dialogue_sends_every_turn_with_its_voice_and_only_the_settings_a_dialogue_takes(tmp_path, mp3):
    transport = Transport(mp3)
    said = say(client(tmp_path, transport), TURNS, settings=V4, seed=7)
    ((url, request, headers),) = transport.calls
    assert url == DIALOGUE_API and headers["xi-api-key"] == "k"
    assert request == {
        "inputs": [{"text": "Did you feed the dog?", "voice_id": LEO.id},
                   {"text": "Dog food. Discipline.", "voice_id": WILL.id}],
        "model_id": "eleven_v4",
        "settings": {"stability": 0.4, "similarity": 0.75},
        "seed": 7,
        "apply_text_normalization": "auto",
    }  # fmt: skip
    assert [s.line.text for s in said] == [t.text for t in TURNS]
    assert [s.line.voice for s in said] == [LEO, WILL]
    assert all(s.line.model == "eleven_v4" and s.line.seed == 7 for s in said)


def test_each_turn_is_cut_on_its_segments_and_its_alignment_spells_its_own_words_on_the_cut(tmp_path, mp3):
    said = say(client(tmp_path, Transport(mp3)), TURNS, settings=V4)
    assert said[0].start == 0 and said[0].end == pytest.approx(said[1].start)
    for s, turn in zip(said, TURNS, strict=True):
        assert s.line.alignment.text == turn.text
        assert s.line.alignment.starts[0] == pytest.approx(0.1, abs=0.002)  # the cut starts at its segment
        assert wav_seconds(s.line.wav) == pytest.approx(s.end - s.start, abs=0.06)
    assert said[1].line.seed == 52026  # the client's seed when none is given


def test_tags_and_stress_are_sent_but_the_turns_alignment_holds_only_the_line(tmp_path, mp3):
    transport = Transport(mp3)
    turns = (TURNS[0], Turn("Dog food. Discipline.", WILL, Direction(tags=("sighs",), emphasis=("Discipline",))))
    said = say(client(tmp_path, transport), turns, settings=V4)
    assert transport.calls[0][1]["inputs"][1]["text"] == "[sighs] Dog food. DISCIPLINE."
    assert said[1].line.alignment.text == "Dog food. Discipline."


def test_a_cached_dialogue_is_read_back_and_verified_without_a_request(tmp_path, mp3):
    first = say(client(tmp_path, Transport(mp3)), TURNS, settings=V4)
    again = Transport(mp3)
    second = say(client(tmp_path, again, key=""), TURNS, settings=V4)
    assert again.calls == []
    assert [s.line.alignment for s in second] == [s.line.alignment for s in first]
    record = json.loads(first[0].line.timing_file.read_text())
    assert record["request_id"] == "req-1" and "audio_base64" not in record["response"]
    assert record["lines"] == [t.text for t in TURNS]


def test_another_seed_is_another_dialogue(tmp_path, mp3):
    transport = Transport(mp3)
    c = client(tmp_path, transport)
    say(c, TURNS, settings=V4, seed=1)
    say(c, TURNS, settings=V4, seed=2)
    assert [call[1]["seed"] for call in transport.calls] == [1, 2]


def test_an_uncached_dialogue_needs_the_key(tmp_path, mp3):
    with pytest.raises(MissingKeyError):
        say(client(tmp_path, Transport(mp3), key=""), TURNS, settings=V4)


# -- refused before any request -----------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("turns", "model", "settings", "match"),
    [
        (TURNS, "eleven_multilingual_v2", V4, "does not say dialogue"),
        (TURNS[:1], "eleven_v4", V4, "at least two turns"),
        (TURNS, "eleven_v4", VoiceSettings(0.4, 0.75, 0.3, 1.0), "no style and no speed"),
        (TURNS, "eleven_v4", VoiceSettings(0.4, 0.75, 0.0, 0.9), "no style and no speed"),
        ((TURNS[0], Turn("Dog food.", WILL, Direction(post_hold=0.5))), "eleven_v4", V4, "its own timing"),
        ((TURNS[0], Turn("Dog food.", WILL, Direction(pre_hold=0.5))), "eleven_v4", V4, "its own timing"),
        ((TURNS[0], Turn("Dog food.", WILL, Direction(takes=2))), "eleven_v4", V4, "its own timing"),
        ((TURNS[0], Turn("Dog food.", WILL, Direction(model="eleven_v3"))), "eleven_v4", V4, "said by eleven_v4"),
        ((TURNS[0], Turn("Dog food.", WILL, Direction(model="eleven_multilingual_v2", pauses=(Pause("Dog", 0.4),)))),
         "eleven_v4", V4, "model eleven_multilingual_v2"),
        ((TURNS[0], Turn("x" * MAX_CHARS, WILL)), "eleven_v4", V4, "at most 2000 characters"),
        (ELEVEN, "eleven_v4", V4, "at most 10 voices"),
    ],
)  # fmt: skip
def test_a_dialogue_the_api_would_misread_is_refused_before_any_request(tmp_path, mp3, turns, model, settings, match):
    transport = Transport(mp3)
    with pytest.raises(DirectionError, match=match):
        say(client(tmp_path, transport), turns, model=model, settings=settings)
    assert transport.calls == []


@pytest.mark.parametrize("seed", [-1, 2**32, True, 1.5])
def test_a_seed_outside_the_apis_range_is_refused(seed):
    with pytest.raises(DirectionError, match="seed is an integer"):
        payload(TURNS, "eleven_v4", V4, seed)


# -- the answer, untrusted ----------------------------------------------------------------------------------------
def _set(path, value):
    def spoil(body):
        *head, last = path
        node = body
        for key in head:
            node = node[key]
        node[last] = value

    return spoil


def _drop(key):
    return lambda body: body.pop(key)


def _swap_segments(body):
    body["voice_segments"].reverse()


def _merge_segments(body):
    a, b = body["voice_segments"]
    a["character_end_index"] = b["character_end_index"]
    body["voice_segments"] = [a]


def _overlap(body):
    body["voice_segments"][1]["start_time_seconds"] = 0.3


def _letter_outside(body):
    """The first turn's last letter ends well into the second turn's segment, every time still in order."""
    body["alignment"]["character_end_times_seconds"][20] = 1.25


def _split_short(body):
    body["voice_segments"][0]["character_end_index"] -= 1


@pytest.mark.parametrize(
    ("spoil", "match"),
    [
        (_set(("extra",), 1), "unknown field"),
        (_drop("voice_segments"), "voice_segments is missing"),
        (_drop("alignment"), "alignment is missing"),
        (_set(("audio_base64",), "not base64!"), "not valid base64"),
        (_set(("audio_base64",), 5), "empty or not a string"),
        (_set(("voice_segments",), []), "non-empty list"),
        (_set(("voice_segments",), "x"), "non-empty list"),
        (_set(("voice_segments", 0, "speaker"), "x"), "unknown field"),
        (_set(("voice_segments", 0, "voice_id"), WILL.id), "said by"),
        (_set(("voice_segments", 0, "voice_id"), 3), "not a string"),
        (_set(("voice_segments", 0, "start_time_seconds"), float("nan")), "finite time"),
        (_set(("voice_segments", 0, "character_start_index"), -1), "index >= 0"),
        (_set(("voice_segments", 1, "dialogue_input_index"), 5), "not one of the 2 sent"),
        (_swap_segments, "out of order|starts at letter|not the next"),
        (_merge_segments, "not the next"),
        (_split_short, "starts at letter"),
        (_overlap, "before the previous segment ends"),
        (_letter_outside, "outside its segment"),
        (_set(("alignment", "characters", 0), "B"), "does not match the sent turns"),
    ],
)  # fmt: skip
def test_a_malformed_or_inconsistent_answer_is_invalid_output_and_caches_nothing(tmp_path, mp3, spoil, match):
    with pytest.raises(VoiceOutputError, match=match):
        say(client(tmp_path, Transport(mp3, spoil)), TURNS, settings=V4)
    assert not (tmp_path / "cache").exists() or list((tmp_path / "cache").iterdir()) == []


def test_an_answer_that_is_not_an_object_is_invalid_output():
    with pytest.raises(VoiceOutputError, match="JSON object"):
        parse_dialogue(["audio"], ["a"], ["v"])


def test_a_turn_that_is_silent_in_the_dialogue_is_refused_and_caches_nothing(tmp_path, half_silent):
    with pytest.raises(VoiceOutputError, match="turn 1 .* is silent"):
        say(client(tmp_path, Transport(half_silent)), TURNS, settings=V4)
    assert not (tmp_path / "cache").exists() or list((tmp_path / "cache").iterdir()) == []


def test_an_answer_whose_audio_is_far_shorter_than_its_alignment_is_refused(tmp_path, mp3):
    def stretch(body):
        times = body["alignment"]["character_end_times_seconds"]
        times[-1] = 9.0
        body["voice_segments"][-1]["end_time_seconds"] = 9.0

    with pytest.raises(VoiceOutputError, match="inconsistent with the alignment"):
        say(client(tmp_path, Transport(mp3, stretch)), TURNS, settings=V4)


def test_a_cached_record_without_its_response_is_invalid_output(tmp_path, mp3):
    first = say(client(tmp_path, Transport(mp3)), TURNS, settings=V4)
    record = first[0].line.timing_file
    record.chmod(0o600)
    record.write_text(json.dumps({"request": {}}))
    with pytest.raises(VoiceOutputError, match="without its response"):
        say(client(tmp_path, Transport(mp3), key=""), TURNS, settings=V4)

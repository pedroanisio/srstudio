"""Per-line voice direction (ADR 0234): the schema, the text each model is sent, the alignment taken back to the line's
own letters, the requests the client makes, and the cache keys of every undirected line left as they were.

No network: the transport is injected. Audio is a real MP3 made by ffmpeg, so decoding and the duration check run."""

import base64
import json
import shutil
import subprocess

import pytest

from srstudio.direction import (
    AUDIO_TAGS,
    MODELS,
    Direction,
    DirectionError,
    Pause,
    Rendered,
    model_spec,
    render,
    seeds,
    spoken,
)
from srstudio.voice import (
    Alignment,
    ElevenLabsClient,
    Transcript,
    TranscriptMismatch,
    Voice,
    VoiceOutputError,
    VoiceRequestError,
    VoiceSettings,
    Word,
    check_transcript,
)

LEO = Voice(role="leo", id="RolvCZ4e0AkAR2dzyTx0", name="Christopher")
WILL = Voice(role="candidate", id="bIHbv24MWmeRgasZH58o", name="Will")
V2 = VoiceSettings(0.30, 0.75, 0.65, 0.80)
V4 = VoiceSettings.expressive(0.4)


def aligned(text: str, step: float = 0.04) -> dict:
    n = len(text)
    return {
        "characters": list(text),
        "character_start_times_seconds": [round(i * step, 3) for i in range(n)],
        "character_end_times_seconds": [round((i + 1) * step, 3) for i in range(n)],
    }


def alignment_of(text: str, step: float = 0.04) -> Alignment:
    return Alignment.parse(aligned(text, step))


@pytest.fixture(scope="module")
def mp3(tmp_path_factory) -> bytes:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required")
    out = tmp_path_factory.mktemp("mp3") / "tone.mp3"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=1.3", "-ar", "44100"]
    subprocess.run([*cmd, "-ac", "1", "-c:a", "libmp3lame", "-b:a", "128k", str(out)], check=True)
    return out.read_bytes()


class Transport:
    """Answers each request with audio and an alignment of exactly the text it was sent, as the API does."""

    def __init__(self, audio: bytes, step: float = 0.03):
        self.audio, self.step = audio, step
        self.calls: list[tuple[str, dict[str, object]]] = []

    def __call__(self, url, payload, headers):
        self.calls.append((url, payload))
        text = payload["text"]
        body = {"audio_base64": base64.b64encode(self.audio).decode(), "alignment": aligned(text, 1.2 / len(text))}
        return body, f"req-{len(self.calls)}"


# -- the schema ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("changes", "match"),
    [
        ({"model": "eleven_v9"}, "not one this kit has checked"),
        ({"tags": ("angrily",)}, "not documented"),
        ({"tags": "sighs"}, "tags is a tuple"),
        ({"tags": ("sighs", "sighs")}, "named twice"),
        ({"quality": "[quietly]"}, "short lowercase description"),
        ({"quality": "x" * 41}, "short lowercase description"),
        ({"quality": "Quietly"}, "short lowercase description"),
        ({"emphasis": ("dog food",)}, "single words"),
        ({"emphasis": ("Dog", "dog")}, "named twice"),
        ({"emphasis": ["dog"]}, "emphasis is a tuple"),
        ({"pauses": ("just",)}, "Pause values"),
        ({"pauses": tuple(Pause(w, 0.5) for w in "abcd")}, "at most 3 pauses"),
        ({"pre_hold": -0.1}, "pre_hold is 0 to"),
        ({"post_hold": float("nan")}, "post_hold is 0 to"),
        ({"post_hold": 7.0}, "post_hold is 0 to"),
        ({"speed": 1.5}, "speed must be within"),
        ({"takes": 0}, "takes is 1 to"),
        ({"takes": 7}, "takes is 1 to"),
        ({"takes": True}, "takes is 1 to"),
        ({"takes": 3, "pick": 3}, "pick is a take of"),
        ({"pick": -1}, "pick is a take of"),
        ({"context": "yes"}, "context is True or False"),
    ],
)
def test_a_malformed_direction_is_a_typed_error(changes, match):
    with pytest.raises(DirectionError, match=match):
        Direction(**changes)


@pytest.mark.parametrize(
    ("after", "seconds", "nth", "match"),
    [("two words", 0.5, 0, "one word"), ("just", 0.0, 0, "0.1 to 3.0"), ("just", 3.5, 0, "0.1 to 3.0"),
     ("just", 0.5, -1, "non-negative"), ("just", 0.5, True, "non-negative")],
)  # fmt: skip
def test_a_malformed_pause_is_a_typed_error(after, seconds, nth, match):
    with pytest.raises(DirectionError, match=match):
        Pause(after, seconds, nth)


def test_a_direction_error_is_a_voice_request_error_so_existing_handlers_catch_it():
    assert issubclass(DirectionError, VoiceRequestError)


def test_the_tag_allow_list_is_the_documented_one_and_an_accent_is_a_pattern():
    assert {"sighs", "whispers", "sarcastic", "curious", "excited", "swallows", "laughs"} <= AUDIO_TAGS
    assert Direction(tags=("strong French accent".lower(),)).tags == ("strong french accent",)
    with pytest.raises(DirectionError):
        Direction(tags=("strong accent",))


def test_seeds_start_at_the_scripts_seed_so_one_take_is_the_request_it_always_was():
    assert seeds(1028, 1) == (1028,)
    assert seeds(1028, 3) == (1028, 1029, 1030)
    assert seeds(2**32 - 1, 2) == (2**32 - 1, 0)


# -- what each model takes ---------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("model", "direction", "match"),
    [
        ("eleven_multilingual_v2", Direction(tags=("sighs",)), "speaks an audio tag aloud"),
        ("eleven_multilingual_v2", Direction(quality="quietly"), "speaks an audio tag aloud"),
        ("eleven_multilingual_v2", Direction(emphasis=("discipline",)), "no documented stress"),
        ("eleven_v3", Direction(pauses=(Pause("just", 0.5),)), "takes no break tag"),
        ("eleven_v4", Direction(pauses=(Pause("just", 0.5),)), "takes no break tag"),
        ("eleven_v3", Direction(context=True), "refuses previous and next text"),
        ("eleven_v4", Direction(speed=0.8), "ignores speed"),
        ("eleven_v3", Direction(speed=0.8), "ignores speed"),
    ],
)
def test_an_option_the_model_does_not_take_is_refused(model, direction, match):
    with pytest.raises(DirectionError, match=match):
        direction.check_for(model)


def test_the_options_each_model_takes_are_accepted():
    assert Direction(pauses=(Pause("just", 0.5),), context=True, speed=0.8).check_for("eleven_multilingual_v2").breaks
    v4 = Direction(tags=("sighs",), quality="flat", emphasis=("x",), context=True).check_for("eleven_v4")
    assert v4.tags and v4.context and not v4.style
    assert Direction(tags=("sighs",), speed=1.0).check_for("eleven_v3").tags
    assert set(MODELS) == {"eleven_multilingual_v2", "eleven_v3", "eleven_v4"}
    with pytest.raises(DirectionError, match="not one this kit"):
        model_spec("eleven_flash_v2_5")


# -- the sent text and the line's own letters ---------------------------------------------------------------------
def test_tags_and_stress_shape_the_sent_text_and_map_back_to_the_line():
    line = "Just... discipline."
    r = render(line, Direction(tags=("sighs",), quality="quietly, holding back", emphasis=("discipline",)), "eleven_v4")
    assert r.text == "[sighs] [quietly, holding back] Just... DISCIPLINE."
    assert "".join(line[j] for j in r.source if j is not None) == line
    back = spoken(alignment_of(r.text), r)
    assert back.text == line and len(back.starts) == len(line)
    assert back.starts[0] == pytest.approx(len("[sighs] [quietly, holding back] ") * 0.04)  # the tag keeps its time


def test_a_stressed_word_is_capitalised_wherever_it_is_and_only_as_a_whole_word():
    r = render("Dog food, not dogma. A dog.", Direction(emphasis=("dog",)), "eleven_v3")
    assert r.text == "DOG food, not dogma. A DOG."


def test_a_pause_is_a_break_tag_after_its_word_on_v2_and_the_time_spans_the_break():
    r = render("Just discipline.", Direction(pauses=(Pause("Just", 1.0),)), "eleven_multilingual_v2")
    assert r.text == 'Just <break time="1.0s" /> discipline.'
    second = render("No. No. Fine.", Direction(pauses=(Pause("no", 0.4, nth=1),)), "eleven_multilingual_v2")
    assert second.text == 'No. No <break time="0.4s" />. Fine.'
    end = render("Fine.", Direction(pauses=(Pause("fine", 0.5),)), "eleven_multilingual_v2")
    assert end.text == 'Fine <break time="0.5s" />.'
    # the provider's alignment holds the tag with zero-width times (probe p3): it maps back to the line
    chars = list(r.text)
    starts = [0.0, 0.1, 0.2, 0.3, 0.33] + [1.39] * 22 + [1.39 + 0.05 * i for i in range(11)]
    ends = [0.1, 0.2, 0.3, 0.33, 1.39] + [1.39] * 22 + [1.44 + 0.05 * i for i in range(11)]
    back = spoken(Alignment(tuple(chars), tuple(starts), tuple(ends)), r)
    assert back.text == "Just discipline." and back.ends[4] == 1.39  # the space before the break carries the pause


@pytest.mark.parametrize(
    ("line", "direction", "match"),
    [
        ("Just discipline.", Direction(emphasis=("feelings",)), "not in the line"),
        ("Just discipline.", Direction(pauses=(Pause("feelings", 0.5),)), "no such word"),
        ("No. No.", Direction(pauses=(Pause("no", 0.5, nth=2),)), "no such word"),
        ("No. No.", Direction(pauses=(Pause("no", 0.5), Pause("No", 0.3))), "same word"),
        ("[sighs] Fine.", Direction(), "no tags or markup"),
        ("Fine <break/>.", None, "no tags or markup"),
        ("   ", None, "needs words"),
    ],
)
def test_a_direction_that_does_not_fit_its_line_is_refused(line, direction, match):
    model = "eleven_v3" if direction is not None and direction.emphasis else "eleven_multilingual_v2"
    with pytest.raises(DirectionError, match=match):
        render(line, direction, model)


def test_an_alignment_of_other_text_is_invalid_output():
    r = render("Fine.", Direction(tags=("sighs",)), "eleven_v4")
    with pytest.raises(VoiceOutputError, match="does not match the requested"):
        spoken(alignment_of("[sighs] Fine!"), r)
    forged = Rendered("Fine.", "[x] Fine.", (None, None, None, None, 0, 1, 2, 3, 3))
    with pytest.raises(VoiceOutputError, match="do not spell the line"):
        spoken(alignment_of("[x] Fine."), forged)
    with pytest.raises(DirectionError, match="maps every"):
        Rendered("a", "ab", (0,))


# -- the client's requests ----------------------------------------------------------------------------------------
def test_undirected_requests_keep_the_cache_keys_they_had_before_direction():
    """Golden keys computed on develop 0d120676, before this change: every published take is found where it was."""
    assert ElevenLabsClient("/x", "").fingerprint("In your chair.", WILL, VoiceSettings(0.42, 0.75, 0.24, 1.0)) == (
        "92d1bb508f025f00ac65"
    )
    client = ElevenLabsClient("/x", "", seed=1028)
    assert client.fingerprint("Just... discipline.", LEO, V2) == "050d13a8e1397987fd59"
    assert client.payload("Hi.", V2) == {
        "text": "Hi.",
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.3, "similarity_boost": 0.75, "style": 0.65, "speed": 0.8,
                           "use_speaker_boost": True},
        "seed": 1028,
        "apply_text_normalization": "auto",
    }  # fmt: skip


def test_an_undirected_synthesis_sends_the_old_request_and_a_seed_or_context_needs_a_direction(tmp_path, mp3):
    transport = Transport(mp3)
    client = ElevenLabsClient(tmp_path, "k", seed=1028, transport=transport)
    line = client.synthesize("Just... discipline.", LEO, V2)
    assert transport.calls[0][1] == client.payload("Just... discipline.", V2)
    assert line.timing_file.stem == "050d13a8e1397987fd59" and line.model == "eleven_multilingual_v2"
    assert line.seed is None
    for kw in ({"seed": 3}, {"previous_text": "Hi."}, {"next_text": "Bye."}):
        with pytest.raises(VoiceRequestError, match="part of a direction"):
            client.synthesize("Just... discipline.", LEO, V2, **kw)


def test_a_directed_v4_request_carries_tags_stress_seed_and_only_the_settings_v4_takes(tmp_path, mp3):
    transport = Transport(mp3)
    client = ElevenLabsClient(tmp_path, "k", seed=1028, transport=transport)
    d = Direction(model="eleven_v4", tags=("sighs",), emphasis=("discipline",), context=True)
    line = client.synthesize("Just... discipline.", LEO, V4, direction=d, seed=1030, previous_text="I don't.")
    sent = transport.calls[0][1]
    assert sent == {
        "text": "[sighs] Just... DISCIPLINE.",
        "model_id": "eleven_v4",
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.75},
        "seed": 1030,
        "apply_text_normalization": "auto",
        "previous_text": "I don't.",
    }
    assert line.text == "Just... discipline." and line.alignment.text == "Just... discipline."  # no tag leaks
    assert line.model == "eleven_v4" and line.seed == 1030
    meta = json.loads(line.timing_file.read_text())
    assert meta["line"] == "Just... discipline." and meta["model"] == "eleven_v4"
    assert meta["alignment"]["characters"][0] == "["  # the record keeps what the provider aligned
    again = ElevenLabsClient(tmp_path, "", seed=1028).synthesize(
        "Just... discipline.", LEO, V4, direction=d, seed=1030, previous_text="I don't."
    )  # cached, and re-read through the same mapping
    assert again.alignment == line.alignment and len(transport.calls) == 1


def test_takes_on_distinct_seeds_are_cached_apart(tmp_path, mp3):
    transport = Transport(mp3)
    client = ElevenLabsClient(tmp_path, "k", seed=7, transport=transport)
    d = Direction(model="eleven_v4", takes=2)
    a, b = (client.synthesize("Allergies.", LEO, V4, direction=d, seed=s) for s in seeds(7, 2))
    assert a.timing_file != b.timing_file and [c[1]["seed"] for c in transport.calls] == [7, 8]


def test_a_v2_direction_sends_a_break_the_full_settings_and_the_neighbouring_lines(tmp_path, mp3):
    transport = Transport(mp3)
    client = ElevenLabsClient(tmp_path, "k", seed=1028, transport=transport)
    d = Direction(pauses=(Pause("Just", 0.8),), speed=0.9, context=True)
    line = client.synthesize("Just discipline.", LEO, V2, direction=d, previous_text="a", next_text="b")
    sent = transport.calls[0][1]
    assert sent["text"] == 'Just <break time="0.8s" /> discipline.' and sent["voice_settings"]["speed"] == 0.9
    assert sent["voice_settings"]["style"] == 0.65 and (sent["previous_text"], sent["next_text"]) == ("a", "b")
    assert line.alignment.text == "Just discipline." and line.settings.speed == 0.9


def test_a_directed_request_is_refused_before_any_request_when_it_does_not_fit_its_model(tmp_path):
    transport = Transport(b"")
    client = ElevenLabsClient(tmp_path, "k", transport=transport)
    with pytest.raises(DirectionError, match="takes no style"):
        client.synthesize("Fine.", LEO, V2, direction=Direction(model="eleven_v4"))
    with pytest.raises(DirectionError, match="speaks an audio tag aloud"):
        client.synthesize("Fine.", LEO, V2, direction=Direction(tags=("sighs",)))
    with pytest.raises(DirectionError, match="context=True"):
        client.synthesize("Fine.", LEO, V2, direction=Direction(), previous_text="Hi.")
    assert transport.calls == [] and not list(tmp_path.iterdir())


def test_a_directed_answer_that_spells_other_text_caches_nothing(tmp_path, mp3):
    def lying(url, payload, headers):
        return {"audio_base64": base64.b64encode(mp3).decode(), "alignment": aligned("Fine.", 0.2)}, "r"

    client = ElevenLabsClient(tmp_path, "k", transport=lying)
    with pytest.raises(VoiceOutputError, match="does not match the requested"):
        client.synthesize("Fine.", LEO, V4, direction=Direction(model="eleven_v4", tags=("sighs",)))
    assert not tmp_path.exists() or not list(tmp_path.iterdir())


def test_expressive_settings_are_the_two_v4_takes():
    assert V4 == VoiceSettings(0.4, 0.75, 0.0, 1.0, use_speaker_boost=False)


# -- the speech check hears the words, never the tags -------------------------------------------------------------
def heard(text: str) -> Transcript:
    return Transcript("en", 1.0, text, tuple(Word(w, 0, 0, "word") for w in text.split()))


def test_a_performed_sound_reported_as_an_event_passes_on_a_tagged_line_only():
    check_transcript(heard("[sighs] Just discipline"), "Just... discipline.", events=True)
    with pytest.raises(TranscriptMismatch):
        check_transcript(heard("[sighs] Just discipline"), "Just... discipline.")  # an untagged line: still a finding


def test_a_tag_spoken_aloud_still_fails_the_speech_check():
    """Probe p8: on multilingual v2 "[sighs] Allergies." was heard as "Size allergies?"."""
    with pytest.raises(TranscriptMismatch):
        check_transcript(heard("Size allergies?"), "Allergies.", events=True)
    with pytest.raises(TranscriptMismatch):
        check_transcript(heard("sighs Allergies."), "Allergies.", events=True)


def test_authority_is_bound_to_master_check_line_bounds_and_message():
    from dataclasses import replace

    from srstudio.authority import AuthorityError, Disposition, Message

    d = Disposition(
        master_sha256="a" * 64,
        check="opening",
        line=None,
        reason="a deliberately held opening",
        bounds=None,
        scope="production",
        requester="builder",
        message=Message("arc4d3", "slack://approval", "Approved this held opening."),
        exact_message="Approved this held opening.",
    )
    d.validate("a" * 64, "opening", None, "a deliberately held opening", None, "production")
    for changes in (
        {"master_sha256": "b" * 64},
        {"check": "lra"},
        {"line": "01"},
        {"reason": "another held opening reason"},
        {"bounds": (0.0, 1.0)},
        {"scope": "rafa"},
    ):
        with pytest.raises(AuthorityError):
            replace(d, **changes).validate("a" * 64, "opening", None, "a deliberately held opening", None, "production")


@pytest.mark.parametrize(
    "changes",
    [
        {"requester": "arc4d3"},
        {"exact_message": "a different approval"},
        {"master_sha256": ""},
        {"message_author": "builder"},
        {"reference": ""},
        {"scope": "rafa"},
        {"bounds": (0.0, float("nan"))},
    ],
)
def test_missing_stale_self_authored_and_reserved_authority_refuses(changes):
    from srstudio.authority import AuthorityError, Disposition, Message

    kw = dict(
        master_sha256="a" * 64,
        check="opening",
        line=None,
        reason="a deliberately held opening",
        bounds=None,
        scope="production",
        requester="builder",
        message=Message(
            changes.pop("message_author", "arc4d3"),
            changes.pop("reference", "slack://approval"),
            "Approved this held opening.",
        ),
        exact_message="Approved this held opening.",
    )
    kw.update(changes)
    with pytest.raises(AuthorityError):
        d = Disposition(**kw)
        d.validate("a" * 64, "opening", None, "a deliberately held opening", None, "production")


def test_reserved_scope_requires_pedro():
    from srstudio.authority import Disposition, Message

    d = Disposition(
        "a" * 64,
        "c7",
        None,
        "accept this measured master",
        None,
        "new_pilot",
        "builder",
        Message("Pedro", "slack://pedro", "Approved this master."),
        "Approved this master.",
    )
    d.validate("a" * 64, "c7", None, d.reason, None, "new_pilot")

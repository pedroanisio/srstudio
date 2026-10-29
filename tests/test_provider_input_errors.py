"""Requests refused before they reach a provider, and a lip-sync score of nothing, are their own SrstudioError
subclasses and still the ValueError they always were (ADR 0034): voice, compose and lipsync."""

from __future__ import annotations

import pytest

from srstudio import compose, lipsync, voice
from srstudio.errors import SrstudioError


def refused(call, error: type[Exception], match: str) -> None:
    with pytest.raises(error, match=match) as caught:
        call()
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, ValueError)


def test_voice_requests_out_of_range_are_voice_request_errors(tmp_path):
    refused(lambda: voice.VoiceSettings(2.0, 0.5, 0.0), voice.VoiceRequestError, "stability")
    refused(lambda: voice.VoiceSettings(0.5, 0.5, 0.0, speed=2.0), voice.VoiceRequestError, "speed")
    client = voice.ElevenLabsClient(tmp_path, "", model="m", seed=1)
    refused(lambda: client.sound_effect("door", 99.0), voice.VoiceRequestError, "seconds")
    refused(lambda: client.sound_effect("door", 1.0, prompt_influence=2), voice.VoiceRequestError, "prompt_influence")


def test_music_requests_it_cannot_make_are_compose_errors(tmp_path):
    refused(lambda: compose.Chunk("", 10.0, ("jazz",)), compose.ComposeError, "chunk name")
    refused(lambda: compose.Chunk("verse", 1.0, ("jazz",)), compose.ComposeError, "duration")
    refused(lambda: compose.Plan(()), compose.ComposeError, "at least one chunk")
    plan = compose.Plan((compose.Chunk("verse", 10.0, ("jazz",)),))
    client = compose.MusicClient(tmp_path, key="k")
    refused(lambda: client.compose(plan, seed=-1, bpm=120), compose.ComposeError, "seed")


def test_a_score_of_no_takes_is_a_lip_sync_error():
    refused(lambda: lipsync.score([], lipsync.SPEECH_MOUTH), lipsync.LipSyncError, "no")

"""Every refusal of an :class:`~srstudio.Episode` is an :class:`~srstudio.episode.EpisodeError`: a
:class:`~srstudio.errors.SrstudioError` that is still the built-in it always was (ADR 0034)."""

from __future__ import annotations

import pytest

from srstudio import CEL, SOFT, Episode
from srstudio.episode import EpisodeArgumentError, EpisodeError, EpisodeFileError, SceneCheckError
from srstudio.errors import SrstudioError
from srstudio.soundtrack import PhonemeStyle
from support.audio import clips_project, spec
from support.cel import silent_project


def refused(call, error: type[EpisodeError], builtin: type[Exception], match: str) -> None:
    with pytest.raises(error, match=match) as caught:
        call()
    assert isinstance(caught.value, SrstudioError) and isinstance(caught.value, builtin)


def test_the_episode_errors_are_srstudio_errors_and_their_builtins():
    assert issubclass(EpisodeError, SrstudioError) and issubclass(EpisodeError, ValueError)
    assert issubclass(EpisodeFileError, EpisodeError) and issubclass(EpisodeFileError, FileNotFoundError)
    assert issubclass(EpisodeArgumentError, EpisodeError) and issubclass(EpisodeArgumentError, TypeError)
    assert issubclass(SceneCheckError, EpisodeError)


def test_a_missing_caption_font_is_an_episode_file_error(project):
    refused(lambda: Episode(spec(project, font="assets/missing.ttf")), EpisodeFileError, FileNotFoundError, "missing")


def test_a_mouth_the_episode_cannot_drive_is_refused(project, tmp_path):
    silent = Episode(spec(silent_project(tmp_path), style=CEL))
    refused(lambda: silent.mouth("manager"), EpisodeArgumentError, TypeError, "no mouth model")
    refused(lambda: silent.mouth("manager", style=SOFT.mouths[SOFT.palettes[0].name]), EpisodeError, ValueError,
            "no soundtrack")  # fmt: skip
    voiced = Episode(spec(project))
    refused(lambda: voiced.mouth("manager", style=PhonemeStyle()), EpisodeArgumentError, TypeError, "MouthStyle")


def test_bad_captions_audio_and_cover_calls_are_refused(project, tmp_path):
    ep = Episode(spec(project))
    refused(lambda: ep.default_captions(lead=-1), EpisodeError, ValueError, "caption lead")
    refused(lambda: ep.generated_audio(clips=[]), EpisodeError, ValueError, "at least one clip")
    refused(lambda: ep.audio(duck=-12), EpisodeArgumentError, TypeError, "duck=")
    refused(lambda: ep.hide_on_cover(), EpisodeError, ValueError, "at least one node")
    node = ep.comp.add_group(id="hook")
    ep.hide_on_cover(node)
    refused(lambda: ep.hide_on_cover(node), EpisodeError, ValueError, "already hidden")
    clips = Episode(spec(clips_project(project, tmp_path), style=SOFT, font=None))
    music = [("groove", "assets/groove.wav", {"role": "music"})]
    refused(lambda: clips.audio(extra=music, duck=3), EpisodeError, ValueError, "negative number of dB")
    effects = [("groove", "assets/groove.wav", {"role": "effects"})]
    refused(lambda: clips.audio(extra=effects, duck=-12), EpisodeError, ValueError, "no music track")

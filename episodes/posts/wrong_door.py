"""The release of wrong-door."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "wrong-door",
    InstagramPost(
        title="Have you ever left a room the wrong way?",
        description=(
            "Great interview. Terrible exit.\nA Soft sketch on Okayville, voiced with ElevenLabs premade voices Will "
            "(Pip) and Eric (Bo); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Eric. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=("#jobinterview", "#awkward", "#office", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("He stayed till Wednesday", 3.6, number=204),
    ),
    tags=Tags("job-hunting", "protagonist", "embarrassment", recurring=("pip", "bo"), test="sp-speakers", arm="a"),
    style="Soft",
    parts={
        "bo": 1,
        "captions": 1,
        "pip": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-closet": 1,
        "soft-door": 1,
        "soft-handshake": 1,
        "soft-laptop": 1,
        "soft-meeting-room": 1,
        "soft-mop": 1,
        "soft-mug": 1,
        "soft-notice": 1,
    },
    comedy=Scores(author=18, reviewer=17),
    cover=True,
)

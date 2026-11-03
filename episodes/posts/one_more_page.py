"""The release of one-more-page."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "one-more-page",
    InstagramPost(
        title="One story, then lights out?",
        description=(
            "Pip is four and has never lost a negotiation.\nBo is on page two.\nA Soft sketch on Okayville, voiced "
            "with ElevenLabs premade voices Will (Pip) and Eric (Bo); every character is original, drawn in "
            "code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Will and Eric. Original characters, drawn in code. Sound effects "
            "synthesized in code."
        ),
        hashtags=('#parenting', '#bedtime', '#parentsbelike', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail(
            "Two stories,\nwater, hall light", 0.2, "Okayville", focus=(560.0, 1240.0), zoom=1.3, place="top"
        ),
    ),
    tags=Tags("family", "other-person", "affection", test="sp-hook_motion", arm="a"),
    style="Soft",
    cover=True,
    parts={
        "bo": 1,
        "captions": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-bedroom": 1,
        "soft-bedside-lamp": 1,
        "soft-briefcase": 1,
        "soft-handshake": 1,
        "soft-necktie": 1,
        "soft-open-briefcase": 1,
        "soft-picture-book": 1,
        "soft-quilt-pull": 1,
        "soft-time-card": 1,
        "soft-wall-clock": 1,
    },
    comedy=Scores(author=15, reviewer=18),
)

"""The release of quiet-please."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "quiet-please",
    InstagramPost(
        title="Why does it only happen in silent rooms?",
        description=(
            "Your stomach only speaks in silent rooms, and across the room another stomach answers."
            "\n"
            "A Soft sketch voiced with an ElevenLabs premade voice; original characters drawn in code."
        ),
        credit="Voice: ElevenLabs premade voice Eric (Bo). Stomachs synthesized.",
        hashtags=("#okayville", "#hungry", "#library", "#stomachgrowl", "#animatedcomedy"),
        thumbnail=Thumbnail("HELLO.", 17.65, "Silent room", place="bottom"),
    ),
    tags=Tags(
        "relationships",
        "other-person",
        "affection",
        recurring=("bo", "pip", "juno"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="best friend",
    ),
    style="Soft",
    parts={
        "bo": 1,
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-book": 1,
        "soft-hush-finger": 1,
        "soft-laptop": 1,
        "soft-meeting-room": 1,
        "soft-notice": 1,
        "soft-rumble": 1,
        "soft-swivel-chair": 1,
        "soft-yogurt": 1,
    },
    comedy=Scores(18, 17),
)

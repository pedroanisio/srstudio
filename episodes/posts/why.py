"""The release of why."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "why",
    InstagramPost(
        title="Why is the sky blue?",
        description=(
            "Five whys is all it takes to reach the edge of human knowledge.\n"
            "Pip is four. Bo has a degree and it did not come up."
        ),
        credit="Voices: ElevenLabs premade voices Jessica (Pip) and Eric (Bo). Foley synthesised.",
        hashtags=(
            "#parenting",
            "#toddlers",
            "#parentsbelike",
            "#relatable",
            "#animatedshorts",
            "#comedyshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Why?", 1.0, place="top"),
    ),
    style="Soft",
    # soft-briefcase, soft-necktie and soft-playroom join these at version 1 once the operator decides them: a release
    # cannot pin a proposed version, so until then the delivery pin check refuses this reel.
    tags=Tags(
        territory="family",
        cause="other-person",
        emotion="affection",
        recurring=("pip", "bo"),
        test="sp-hook_motion",
        arm="a",
        recipient="a",
    ),
    parts={
        "bo": 1,
        "captions": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-briefcase": 1,
        "soft-necktie": 1,
        "soft-playroom": 1,
    },
)

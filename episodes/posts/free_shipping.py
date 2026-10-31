"""The release of free-shipping."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "free-shipping",
    InstagramPost(
        title="How far would you go for free shipping?",
        description=(
            "Have you ever spent twenty one dollars to save six?\n"
            "Juno and Pip, a tiny whisk, and a bird feeder for a bird they do not have."
        ),
        credit="Voices: ElevenLabs premade voices Laura (Juno) and Will (Pip). Foley synthesized.",
        hashtags=("#okayville", "#freeshipping", "#onlineshopping", "#relatable", "#animatedcomedy"),
        thumbnail=Thumbnail("Free\nshipping!", 14.6, "A week later", place="bottom"),
    ),
    style="Soft",
    tags=Tags(territory="money-services", cause="protagonist", emotion="embarrassment", test="sp-hook_motion", arm="a"),
    comedy=Scores(author=17, reviewer=17),
    parts={
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-chair": 1,
        "soft-desk": 1,
        "soft-laptop": 1,
        "soft-office": 1,
        "soft-parcels": 1,
        "soft-status-badge": 1,
        "soft-whisk": 1,
    },
)

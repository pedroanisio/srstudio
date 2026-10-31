"""The release of still-bright."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "still-bright",
    InstagramPost(
        title="Who is Dale, and is he okay?",
        description=(
            "How long have you ever spent reading the reviews of something that costs twelve dollars?\n"
            "Juno and Pip, and a man called Dale, who keeps them updated."
        ),
        credit="Voices: ElevenLabs premade voices Laura (Juno), Will (Pip) and Eric (Dale). Foley synthesized.",
        hashtags=("#okayville", "#reviews", "#onlineshopping", "#relatable", "#animatedcomedy"),
        thumbnail=Thumbnail("She was\nright.", 23.0, "Dale's last update", place="top"),
    ),
    style="Soft",
    tags=Tags(territory="everyday-tech", cause="protagonist", emotion="affection", test="sp-hook_motion", arm="b"),
    comedy=Scores(author=18, reviewer=17),
    parts={
        # soft-glare-lamp is drawn too; it stays out until it is approved: a release cannot pin a proposed version.
        "bo": 1,
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-chair": 1,
        "soft-desk": 1,
        "soft-home": 1,
        "soft-laptop": 1,
        "soft-office": 1,
        "soft-phone": 1,
        "soft-sofa": 1,
        "soft-time-card": 1,
    },
)

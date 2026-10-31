"""The release of the-tongs."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-tongs",
    InstagramPost(
        title="Who runs the grill at your family barbecue?",
        description=(
            "At a barbecue one person holds the tongs, and nobody else may touch the meat."
            "\n"
            "A Soft sketch voiced with ElevenLabs premade voices; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Eric (Bo), Will (Pip) and Laura (Juno). Foley synthesized.",
        hashtags=("#okayville", "#bbq", "#grilldad", "#familybbq", "#animatedcomedy"),
        thumbnail=Thumbnail("He has\ntwo.", 12.35, "Family barbecue", place="top"),
    ),
    tags=Tags(
        "family",
        "other-person",
        "recognition",
        recurring=("bo", "pip", "juno"),
        test="sp-hook_motion",
        arm="b",
        recipient="b",
        to="family",
    ),
    style="Soft",
    parts={
        # soft-bottle is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-grill is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-pizza-box is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-smoke is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        # soft-tongs is drawn too; it is held at the pin gate: a release cannot pin a proposed version.
        "bo": 1,
        "captions": 1,
        "juno": 1,
        "pip": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "soft-bench": 1,
        "soft-park": 1,
        "soft-phone": 1,
    },
    comedy=Scores(18, 18),
)

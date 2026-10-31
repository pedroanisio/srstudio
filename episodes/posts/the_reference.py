"""The release of the-reference."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "the-reference",
    InstagramPost(
        title="Who did you put down as your reference?",
        description=(
            "A good reference knows your strengths, your weaknesses, and exactly what you owe her.\nA Cutout "
            "sketch on Okayville, voiced with ElevenLabs premade voices Lily (Rosa), Liam (Milo) and Eric (the "
            "manager); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Lily, Liam and Eric. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=('#jobhunting', '#jobinterview', '#officehumor', '#animatedshorts', '#okayville'),
        thumbnail=Thumbnail("Is he\nreliable?", 4.2, "Okayville"),
    ),
    tags=Tags("job-hunting", "other-person", "triumph", test="sp-hook_motion", arm="b"),
    style="Cutout",
    parts={
        # banknotes, cue-cards, robe-and-blazer also drawn:
        # a release cannot pin a proposed version, so they join once approved.
        "captions": 1,
        "customer": 1,
        "home-study": 1,
        "papers": 1,
        "rosa": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "speakerphone": 1,
    },
    comedy=Scores(author=15, reviewer=18),
)

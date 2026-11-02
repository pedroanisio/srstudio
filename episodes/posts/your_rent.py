"""The release of your-rent."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "your-rent",
    InstagramPost(
        title="What did your dad say about your rent?",
        description=(
            "He was outraged by what she pays, right up to the moment he worked out what he could charge.\nA Toon "
            "sketch on Okayville, voiced with ElevenLabs premade voices Brian (Dad), Matilda (Fern) and Will "
            "(Lewis); every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Brian, Matilda and Will. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=("#rent", "#dads", "#movingbackhome", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Dad names his price", 12.6, number=212),
    ),
    tags=Tags(
        "family",
        "other-person",
        "recognition",
        recurring=("dad", "fern", "lewis"),
        test="sp-length",
        arm="short",
        also=(("sp-speakers", "b"),),
        send_to="your dad",
        send_line="You're twenty-two hundred.",
    ),
    style="Toon",
    video="your-rent-v2",  # the keeper: the first master ran four lines into the ones before them
    parts={
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-captions": 1,
        "toon-frog": 2,
        "toon-goat": 1,
        "toon-kitchen": 1,
        "toon-ledge": 1,
        "toon-mug": 1,
        "toon-raccoon": 2,
    },
    comedy=Scores(author=17, reviewer=16),
    cover=True,
)

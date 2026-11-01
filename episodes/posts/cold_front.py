"""The release of cold-front."""

from srstudio.comedy_floor import Scores
from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import ShowCover

RELEASE = Release(
    "cold-front",
    InstagramPost(
        title="What time did yours text?",
        description=(
            "The forecast called it. She still answered.\nA Collage sketch on Okayville, voiced with ElevenLabs"
            " premade voices Daniel (Omar), Jessica (Deb) and Sarah (Priya); every character is original, drawn in"
            " code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Daniel, Jessica and Sarah. Original characters, drawn in code. Sound "
            "effects synthesized in code."
        ),
        hashtags=("#ex", "#dating", "#bestfriend", "#animatedshorts", "#okayville"),
        thumbnail=ShowCover("Exes moving in tonight", 14.2, number=205, focus=(570.0, 915.0), zoom=1.2),
    ),
    tags=Tags(
        "relationships",
        "protagonist",
        "recognition",
        recurring=("omar", "deb", "priya"),
        test="sp-length",
        arm="short",
        also=(("sp-speakers", "b"),),
        send_to="your best friend",
        send_line="He doesn't miss you. He's cold.",
    ),
    style="Collage",
    parts={
        "collage-arm": 1,
        "collage-bubble": 1,
        "collage-deb": 1,
        "collage-duvet": 1,
        "collage-living-room": 1,
        "collage-newsroom": 1,
        "collage-omar": 1,
        "collage-phone": 1,
        "collage-sign": 1,
        "show-bug": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
    comedy=Scores(author=17, reviewer=17),
    cover=True,
)

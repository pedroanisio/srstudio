"""The release of scene."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "scene",
    InstagramPost(  # printer-recreation: the project slug of the square cartoon
        title="The printer was fine this morning.",
        description=(
            "A printer that makes startup noises instead of printing, and knows exactly when you are in a hurry.\n"
            "This is a procedural, hand-built vector recreation of Mark Kacy's printer cartoon, with newly "
            "synthesized performances. Original idea, writing and design: Mark Kacy."
        ),
        credit="Recreation of a cartoon by Mark Kacy. Voices: ElevenLabs premade voices Chris and Callum.",
        hashtags=(
            "#printerproblems",
            "#officehumor",
            "#cartoon",
            "#handdrawn",
            "#animatedshorts",
            "#recreation",
            "#markkacy",
            "#workcomedy",
        ),
        thumbnail=Thumbnail("Use the\nblack ink!", 37.0, "Printer", place="top"),
    ),
    video="Printer_Recreation",
    builder="printer_recreation",
    parts={
        "doodle": 1,
        "ink-closeup": 1,
        "ink-desk": 1,
        "ink-desk-shot": 1,
        "ink-laptop": 1,
        "ink-printer-shot": 1,
        "ink-wide": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "talking-printer": 1,
    },
)

"""The release of storage-full."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "storage-full",
    InstagramPost(
        title="A pigeon just did a backflip. Your phone says storage full.",
        description=(
            "Delete fourteen photos of the same sunset? Still full. The pigeon is waiting. The phone has one more "
            "suggestion.\n"
            "Comedy Cut 23: Milo from the café, on the park bench, with a choice to make."
        ),
        credit="Voices: ElevenLabs premade voices Liam and Alice. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#storagefull",
            "#phonelife",
            "#techhumor",
            "#pigeons",
            "#everydaylife",
            "#animatedshorts",
            "#comedyshorts",
        ),
        thumbnail=Thumbnail(
            "Storage\nfull.", 1.42, "Comedy Cut 23", place="top"
        ),  # the pigeon upside down, mid-backflip
    ),
    cover=True,
    tags=Tags(
        "everyday-tech", "protagonist", "embarrassment", recurring=("milo", "pigeon"), test="sp-hook_motion", arm="b"
    ),
    characters={"customer": 1, "pigeon": 1},
)

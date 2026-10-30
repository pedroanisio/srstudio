"""The release of accept-all."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "accept-all",
    InstagramPost(
        title="My dad refuses to accept cookies. All eight hundred partners.",
        description=(
            "A website wants Gary's cookies. Kai says just click accept. Gary is managing his preferences instead, "
            "one advertising partner at a time, and there are eight hundred of them.\n"
            "A Collage sketch voiced with ElevenLabs premade voices Chris (Gary) and River (Kai), lip-synced to their "
            "words; every character is original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices Chris and River. Original characters, drawn in code. Sound effects "
            "synthesised in code."
        ),
        hashtags=("#cookies", "#privacy", "#internet", "#dadlife", "#relatable", "#animatedshorts", "#satire"),
        thumbnail=Thumbnail("Partner one: no.\nPartner two: no.", 9.0, "Collage 17", None, 1.0, place="bottom"),
    ),
    tags=Tags("everyday-tech", "protagonist", "tension", recurring=("gary", "kai"), test="sp-hook_motion", arm="b"),
)

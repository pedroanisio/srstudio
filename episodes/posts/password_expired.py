"""The release of password-expired."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "password-expired",
    InstagramPost(
        title="Why does my password expire every month?",
        description=(
            "Bruno's password expired again. IT rejects the new one: too similar to the old one. How does IT know "
            "his old one? They keep them all, in a spreadsheet. Was the spreadsheet password protected? It was. It "
            "expired.\n"
            "A Toon sketch voiced with ElevenLabs premade voices Bill (Bruno) and Alice (Pip), lip-synced to their "
            "words; original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Bill and Alice. Original characters, drawn in code.",
        hashtags=(
            "#passwords",
            "#ithelpdesk",
            "#cybersecurity",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#lipsync",
        ),
        thumbnail=Thumbnail("Why does my\npassword expire?", 1.0, "Toon 13", (470, 1130), 1.35),
    ),
)

"""The release of message-failed."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "message-failed",
    InstagramPost(
        title="Wait. Did I just send that to my boss?",
        description=(
            "A text about the boss went to the boss. He begs the router to drop the Wi-Fi, and it does: the message "
            "fails. Then the router retries it, because it hates failing. The boss is typing.\n"
            "A square pen-and-ink cartoon voiced with ElevenLabs premade voices Chris and Daniel."
        ),
        credit="Voices: ElevenLabs premade voices Chris and Daniel. Sound effects generated with ElevenLabs.",
        hashtags=(
            "#wrongchat",
            "#texting",
            "#officehumor",
            "#techhumor",
            "#animatedshorts",
            "#inkdrawing",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Sent to\nthe boss.", 1.4, "Ink 04", (540, 420), 1.5),
    ),
    cover=True,
    parts={
        "doodle": 1,
        "ink-closeup": 1,
        "ink-phone": 1,
        "ink-phone-shot": 1,
        "ink-router-shot": 1,
        "signature-cactus": 1,
        "signature-code": 1,
        "talking-router": 1,
    },
)

"""The release of heard-back."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "heard-back",
    InstagramPost(
        title="Mid-interview, the rejection email arrives. Then it asks for a rating.",
        description=(
            "The interview is going really well. Otto asks when he will hear back, and hears back, mid-sentence. "
            "That's automatic, ignore it. Then the hiring team asks him to rate the interview. Then it emails "
            "Dana.\n"
            "A Toon sketch with Dana and Otto, voiced with ElevenLabs premade voices Jessica and Daniel; original "
            "characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices Jessica (Dana) and Daniel (Otto). Buzz and sting synthesised.",
        hashtags=(
            "#jobsearch",
            "#jobinterview",
            "#rejectionemail",
            "#jobhunting",
            "#animatedshorts",
            "#comedyshorts",
            "#cartoon",
        ),
        thumbnail=Thumbnail("This is going\nreally well", 1.0, "Toon 21"),
    ),
    tags=Tags("job-hunting", "institution", "recognition", recurring=("dana", "otto"), test="sp-hook_motion", arm="b"),
    parts={
        "signature-cactus": 1,
        "signature-code": 1,
        "toon-bear": 1,
        "toon-board-text": 1,
        "toon-captions": 1,
        "toon-desk": 1,
        "toon-dog": 1,
        "toon-meeting": 1,
        "toon-mug": 1,
        "toon-room": 1,
        "toon-toast": 1,
    },
)

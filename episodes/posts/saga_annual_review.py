"""The release of saga-annual-review."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-annual-review",
    InstagramPost(
        title='Why do the enforcers never hit anything?',
        description=(
            "Enforcer Seven's annual review: nine thousand shots fired, zero hits. Zero damage, zero complaints, "
            "zero paperwork. Enforcer of the year. And the ones who hit things? We don't talk about Gary.\nA Saga "
            'sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade '
            'voices George (narrator), Callum (Lord Gloom) and Liam (Seven); the Directorate and every character '
            'are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Callum and Liam. Sound effects generated with ElevenLabs. '
            'Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=(
            '#performancereview',
            '#corporatelife',
            '#kpi',
            '#worklife',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Shots fired: 9000.\nHits: zero.', 9.0, 'Saga 02', (540, 890), 1.0),
    ),
    cover=True,
    characters={"saga-enforcer": 1, "saga-gloom": 1},
)

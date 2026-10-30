"""The release of saga-known-issue."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-known-issue",
    InstagramPost(
        title='Why did the battle cube have a hole?',
        description=(
            'The deadliest station in the galaxy has a hole that blows it up. Somebody reported it nine years '
            'ago. Lord Gloom asks Enforcer Seven for the priority: medium, then low, then nice to have. The '
            'Directorate has since built a new cube; the hole is now listed as a feature.\nA Saga sketch, a '
            'space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade voices George '
            '(narrator), Callum (Lord Gloom) and Liam (Seven); the Directorate and every character are original, '
            'drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Callum and Liam. Sound effects generated with ElevenLabs. '
            'Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=(
            '#backlog',
            '#softwareengineering',
            '#techdebt',
            '#bugreport',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Why does the cube\nhave a hole?', 13.0, 'Saga 01', (540, 890), 1.0),
    ),
    cover=True,
    parts={
        "saga-bridge": 1,
        "saga-cube": 1,
        "saga-enforcer": 1,
        "saga-entry": 1,
        "saga-gloom": 1,
        "saga-handbook": 1,
        "saga-holo": 1,
        "saga-hook": 1,
        "saga-space": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)

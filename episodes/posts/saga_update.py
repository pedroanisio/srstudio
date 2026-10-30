"""The release of saga-update."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-update",
    InstagramPost(
        title='Worst possible time for a software update?',
        description=(
            'Mid-chase, Rook says punch it. The jump drive has other plans: an update is ready. Skip it? It wants '
            'to know if tonight works. Tonight works. Is this tonight? The update also removed the jump drive, '
            'for security reasons.\nA Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced '
            'with ElevenLabs premade voices George (narrator), Roger (Rook) and River (Juno); the Directorate and '
            'every character are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Roger and River. Sound effects generated with ElevenLabs. '
            'Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=(
            '#softwareupdate',
            '#updates',
            '#tech',
            '#remindmelater',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Worst time for\nan update?', 8.0, 'Saga 05', (540, 890), 1.0),
    ),
    cover=True,
    parts={
        "saga-cockpit": 1,
        "saga-cockpit-console": 1,
        "saga-entry": 1,
        "saga-fighter": 1,
        "saga-freighter": 1,
        "saga-handbook": 1,
        "saga-holo": 1,
        "saga-hook": 1,
        "saga-juno": 1,
        "saga-rook": 1,
        "saga-space": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)

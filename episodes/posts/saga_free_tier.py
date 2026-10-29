"""The release of saga-free-tier."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-free-tier",
    InstagramPost(
        title='Can you feel the energy that binds the galaxy?',
        description=(
            'Elder Mabel teaches Juno the Flow. Juno feels it: a pebble. Boulders are Flow Plus, mind tricks are '
            'Flow Premium, billed yearly, and free gets you commercials. That great disturbance? The renewal.\nA '
            'Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade '
            'voices George (narrator), Lily (Elder Mabel) and River (Juno); the Directorate and every character '
            'are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Lily and River. Music composed with ElevenLabs Music. '
            'Original characters, drawn in code.'
        ),
        hashtags=(
            '#subscriptions',
            '#freemium',
            '#cancelsubscription',
            '#streaming',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Can you feel\nthe Flow?', 8.5, 'Saga 06', (540, 890), 1.0),
    ),
    cover=True,
)

"""The release of saga-group-chat."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-group-chat",
    InstagramPost(
        title='Worst way to find out who your father is?',
        description=(
            'On the dunes, Lord Gloom makes the big reveal. Juno already knows: Dad posted it in the family group '
            'chat. And sent it to the whole Directorate.\nA Saga sketch, a space-opera parody narrated by a '
            'deadpan field guide, voiced with ElevenLabs premade voices George (narrator), Callum (Lord Gloom) '
            'and River (Juno); the Directorate and every character are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Callum and River. Sound effects generated with ElevenLabs. '
            'Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=('#groupchat', '#familychat', '#dads', '#parenting', '#spaceopera', '#animatedshorts', '#satire'),
        thumbnail=Thumbnail('Juno. I am\nyour father.', 4.5, 'Saga 03', (540, 890), 1.0),
    ),
    cover=True,
    parts={
        "saga-desert": 1,
        "saga-enforcer": 1,
        "saga-entry": 1,
        "saga-gloom": 1,
        "saga-handbook": 1,
        "saga-holo": 1,
        "saga-hook": 1,
        "saga-juno": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)

"""The release of saga-open-plan."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-open-plan",
    InstagramPost(
        title='Why are the walls closing in?',
        description=(
            'The trash compactor walls are closing in. Facilities calls it an upgrade: please submit a ticket, '
            "about nine years. Then Enforcer Seven walks in for his hot desk. He's only in on Tuesdays.\nA Saga "
            'sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade '
            'voices George (narrator), Jessica (the facilities droid), Roger (Rook), River (Juno) and Liam '
            '(Seven); the Directorate and every character are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Jessica, Roger, River and Liam. Sound effects generated '
            'with ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=(
            '#openplan',
            '#hotdesking',
            '#returntooffice',
            '#officelife',
            '#spaceopera',
            '#animatedshorts',
            '#satire',
        ),
        thumbnail=Thumbnail('Why are the walls\nclosing in?', 14.0, 'Saga 07', (540, 890), 1.0),
    ),
    cover=True,
    parts={
        "saga-compactor": 1,
        "saga-droid": 1,
        "saga-enforcer": 1,
        "saga-entry": 1,
        "saga-handbook": 1,
        "saga-holo": 1,
        "saga-hook": 1,
        "saga-juno": 1,
        "saga-rook": 1,
        "signature-cactus": 1,
        "signature-code": 1,
    },
)

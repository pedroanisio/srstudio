"""The release of saga-card-reader."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-card-reader",
    InstagramPost(
        title='What does a smuggler fear most?',
        description=(
            'Rook orders one drink in a rough cantina. The bar droid turns the card reader around: add a tip? No '
            'tip. Every patron turns to stare. Fine, the biggest one. The receipt goes straight to the '
            'Directorate.\nA Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with '
            'ElevenLabs premade voices George (narrator), Roger (Rook) and Jessica (the bar droid); the '
            'Directorate and every character are original, drawn in code.'
        ),
        credit=(
            'Voices: ElevenLabs premade voices George, Roger and Jessica. Sound effects generated with '
            'ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code.'
        ),
        hashtags=('#tipping', '#tipscreen', '#tipflation', '#bartender', '#spaceopera', '#animatedshorts', '#satire'),
        thumbnail=Thumbnail('What does a\nsmuggler fear?', 8.5, 'Saga 04', (540, 890), 1.0),
    ),
    cover=True,
)

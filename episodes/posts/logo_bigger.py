"""The release of logo-bigger."""

from srstudio.releases import Release
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "logo-bigger",
    InstagramPost(
        title="Can you make the logo bigger?",
        description=(
            "The client wants the logo bigger. Then bigger. Then the size of the building. Then it should pop. "
            "Then smaller. Rex sends the invoice.\n"
            "A Toon sketch voiced with ElevenLabs premade voices George (the client), Matilda (Fern) and Charlie "
            "(Rex); original characters drawn in code."
        ),
        credit="Voices: ElevenLabs premade voices George, Matilda and Charlie. Original characters, drawn in code.",
        hashtags=(
            "#makeitbigger",
            "#designerproblems",
            "#clientfeedback",
            "#officehumor",
            "#workcomedy",
            "#animatedshorts",
            "#vectoranimation",
        ),
        thumbnail=Thumbnail("Can you make\nit bigger?", 16.5, "Toon 04", (700, 950), 1.2),
    ),
    characters={"toon-dog": 1, "toon-frog": 1},
)

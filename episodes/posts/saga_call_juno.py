"""The release of saga-call-juno."""

from srstudio.releases import Release, Tags
from srstudio.social import InstagramPost
from srstudio.thumbnail import Thumbnail

RELEASE = Release(
    "saga-call-juno",
    InstagramPost(
        title="She asked the smart speaker to call her granddaughter. It called the dark lord.",
        description=(
            "Elder Mabel gets a smart speaker. She asks it to call Juno. It calls Lord Gloom. She asks again. It "
            "calls Lord Gloom, mobile. He answers, and she tells him he sounds tired and should wear something warm. "
            "He has a cape.\n"
            "A Saga sketch, a space-opera parody narrated by a deadpan field guide, voiced with ElevenLabs premade "
            "voices George (narrator), Lily (Elder Mabel), Jessica (the speaker) and Callum (Lord Gloom); the "
            "Directorate and every character are original, drawn in code."
        ),
        credit=(
            "Voices: ElevenLabs premade voices George, Lily, Jessica and Callum. Sound effects generated with "
            "ElevenLabs. Music composed with ElevenLabs Music. Original characters, drawn in code."
        ),
        hashtags=(
            "#smartspeaker",
            "#voiceassistant",
            "#grandma",
            "#wrongnumber",
            "#spaceopera",
            "#animatedshorts",
            "#satire",
        ),
        thumbnail=Thumbnail("Call Juno.\nCalling Lord Gloom.", 6.6, "Saga 15", (540, 890), 1.0),
    ),
    cover=True,
    tags=Tags(
        "everyday-tech",
        "institution",
        "affection",
        recurring=("mabel", "gloom", "droid"),
        test="sp-hook_motion",
        arm="a",
    ),  # fmt: skip
)

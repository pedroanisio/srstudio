#!/usr/bin/env python3
"""Choice Blindness — a pilot of "There's a Name for That" (see choice_blindness_data.py for the script).

python3 choice_blindness.py PROJECT --init     # script.json, assets/poses.json and the pinned Fraunces
python3 choice_blindness.py PROJECT            # the silent master on the scripted timing
python3 choice_blindness.py PROJECT --voice    # the narrated master from the recording (choice_blindness_audio.py)

A pilot, not an Okayville reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from pathlib import Path

from choice_blindness_data import (
    ACCESSIBILITY,
    DESCRIPTION,
    FIGURES,
    HEADS,
    NARRATION,
    OUTPUT,
    SEED,
    SKETCH,
    TINTS,
    VERSIONS,
    dress,
    foam,
    lens,
    no_desk,
    validate,
)

from srstudio import mind_kit
from srstudio.toon_sketch import Staging, build

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
    versions=VERSIONS,
    desk=no_desk,
    lit=True,
    camera=lens,
    figures=FIGURES,
    heads=HEADS,
    on_face={"goat": foam},
    style=mind_kit.MIND,
    bare=(mind_kit.CARD, mind_kit.STAGE),
    captions=mind_kit.captions,
    finish=mind_kit.finish,
    output=OUTPUT,
    crf="21",
)
ep = build(Path(sys.argv[1]).resolve(), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.finish()

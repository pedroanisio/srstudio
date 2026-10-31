#!/usr/bin/env python3
"""Inside the Circle — a pilot of the Maps channel (see inside_the_circle_data.py for the script).

python3 inside_the_circle.py PROJECT --init     # script.json, assets/poses.json, the pinned Lexend and the map layers
python3 inside_the_circle.py PROJECT            # the silent master on the scripted timing
python3 inside_the_circle.py PROJECT --voice    # the narrated master from the recording (inside_the_circle_audio.py)

A pilot, not a @tuxmeme reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from pathlib import Path

from inside_the_circle_data import (
    ACCESSIBILITY,
    DESCRIPTION,
    FIGURES,
    NARRATION,
    OUTPUT,
    SEED,
    SKETCH,
    TINTS,
    VERSIONS,
    dress,
    no_desk,
    validate,
)

from srstudio import map_kit
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
    heads=("hamster",),
    figures=FIGURES,
    style=map_kit.MAPS,
    bare=(map_kit.CARD,),
    captions=map_kit.captions,
    finish=map_kit.finish,
    output=OUTPUT,
    crf="23",
)
root = Path(sys.argv[1]).resolve()
map_kit.install(root)
ep = build(root, STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.finish()

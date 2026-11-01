#!/usr/bin/env python3
"""Dig Straight Down — Maps #3 (see dig_straight_down_data.py for the script).

python3 dig_straight_down.py PROJECT --init     # script.json, assets/poses.json, the pinned Lexend and the map layers
python3 dig_straight_down.py PROJECT            # the silent master on the scripted timing
python3 dig_straight_down.py PROJECT --voice    # the narrated master from the recording (dig_straight_down_audio.py)

A pilot, not an Okayville reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from pathlib import Path

from dig_straight_down_data import (
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

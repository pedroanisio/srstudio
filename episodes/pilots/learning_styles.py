#!/usr/bin/env python3
"""The Meshing Hypothesis — a pilot of "There's a Name for That" (see learning_styles_data.py for the script).

python3 learning_styles.py PROJECT --init     # script.json, assets/poses.json and the pinned Fraunces
python3 learning_styles.py PROJECT            # the silent master on the scripted timing
python3 learning_styles.py PROJECT --voice    # the narrated master from the recording (learning_styles_audio.py)

A pilot, not a @tuxmeme reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from pathlib import Path

from learning_styles_data import (
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
    figures=FIGURES,
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

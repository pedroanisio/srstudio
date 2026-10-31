#!/usr/bin/env python3
"""The Peak-End Rule — a pilot of "There's a Name for That" (see peak_end_rule_data.py for the script).

python3 peak_end_rule.py PROJECT --init     # script.json, assets/poses.json and the pinned Fraunces
python3 peak_end_rule.py PROJECT            # the silent master on the scripted timing
python3 peak_end_rule.py PROJECT --voice    # the narrated master from the recording (peak_end_rule_audio.py)

A pilot, not a @tuxmeme reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from pathlib import Path

from peak_end_rule_data import (
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
    heads=("sloth",),
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

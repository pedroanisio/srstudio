#!/usr/bin/env python3
"""Explain a Zipper — a pilot of "There's a Name for That" #4 (see explain_a_zipper_data.py for the script).

python3 explain_a_zipper.py PROJECT --init     # script.json, assets/poses.json and the pinned Fraunces
python3 explain_a_zipper.py PROJECT            # the silent master on the scripted timing
python3 explain_a_zipper.py PROJECT --voice    # the narrated master from the recording (explain_a_zipper_audio.py)

A pilot, not an Okayville reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from pathlib import Path

from explain_a_zipper_data import (
    ACCESSIBILITY,
    BLEED,
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
    style=mind_kit.MIND,
    bare=(mind_kit.CARD, mind_kit.STAGE),
    captions=mind_kit.captions,
    finish=mind_kit.finish,
    output=OUTPUT,
    bleed=BLEED,
    crf="21",
)
ep = build(Path(sys.argv[1]).resolve(), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.finish()

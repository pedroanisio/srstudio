#!/usr/bin/env python3
"""Real Roast — a pilot of News Compiler, the parody desk (see real_roast_data.py for the script).

python3 real_roast.py PROJECT --init     # script.json, assets/poses.json and the pinned Barlow Condensed
python3 real_roast.py PROJECT            # the silent master on the scripted timing
python3 real_roast.py PROJECT --voice    # the voiced master from the recording (real_roast_audio.py)

A pilot, not a @tuxmeme reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from pathlib import Path

from real_roast_data import (
    ACCESSIBILITY,
    ACTS,
    DESCRIPTION,
    NARRATION,
    OUTPUT,
    SEED,
    SKETCH,
    TINTS,
    VERSIONS,
    overlay,
    validate,
)

from srstudio import news_kit
from srstudio.toon_sketch import Staging, build

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=news_kit.stage(ACTS),
    versions=VERSIONS,
    desk=news_kit.desk,
    style=news_kit.NEWS,
    bare=news_kit.NEWS_CAST.characters,
    captions=news_kit.captions,
    finish=news_kit.finish,
    overlay=overlay,
    output=OUTPUT,
    crf="21",
)
ep = build(Path(sys.argv[1]).resolve(), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.finish()

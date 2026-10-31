#!/usr/bin/env python3
"""Seabird Jet Lag — a real roast of News Compiler (see seabird_jet_lag_data.py for the script).

python3 seabird_jet_lag.py PROJECT --init     # script.json, assets/poses.json and the pinned Barlow Condensed
python3 seabird_jet_lag.py PROJECT            # the silent master on the scripted timing
python3 seabird_jet_lag.py PROJECT --voice    # the voiced master from the recording (seabird_jet_lag_audio.py)

A pilot, not an Okayville reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from pathlib import Path

import news_story
from seabird_jet_lag_data import (
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

from srstudio import news_inked, news_kit
from srstudio.toon_sketch import Staging, build

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=news_inked.stage(ACTS),
    versions=VERSIONS,
    desk=news_inked.desk,
    style=news_kit.NEWS,
    bare=news_kit.NEWS_CAST.characters,
    captions=news_inked.captions,
    finish=news_kit.finish,
    overlay=overlay,
    output=OUTPUT,
    crf="21",
)
ep = build(Path(sys.argv[1]).resolve(), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    news_story.hide_on_cover(ep)
    ep.finish()

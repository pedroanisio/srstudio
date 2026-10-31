#!/usr/bin/env python3
"""Someone Else — a Toon sketch: canceling your internet is a breakup (see someone_else_data.py for the script).

python3 someone_else.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 someone_else.py PROJECT            # the silent master on the scripted timing
python3 someone_else.py PROJECT --voice    # the narrated master from the recording (someone_else_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from someone_else_data import (
    ACCESSIBILITY,
    DESCRIPTION,
    FIGURES,
    NARRATION,
    SEED,
    SKETCH,
    STICKERS,
    TINTS,
    WIDE,
    dress,
    validate,
)
from srstudio.toon_sketch import Staging, build
from srstudio.toon_world import no_desk

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
    versions=PINS[SKETCH.slug],
    desk=no_desk,
    lit=True,
    figures=FIGURES,
    stickers=STICKERS,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

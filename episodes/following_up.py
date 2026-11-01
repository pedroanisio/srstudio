#!/usr/bin/env python3
"""Following Up — the sketch as data (see following_up_data.py for the script).

python3 following_up.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 following_up.py PROJECT            # the silent master on the scripted timing
python3 following_up.py PROJECT --voice    # the narrated master from the recording (following_up_audio.py)
"""

import sys

from _common import project_root
from following_up_data import (
    ACCESSIBILITY,
    BARE,
    DESCRIPTION,
    FIGURES,
    HEADS,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    dress,
    lens,
    tired,
    validate,
)
from instagram_posts import PINS, POSTS
from srstudio import toon_world
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
    versions=PINS[SKETCH.slug],
    desk=toon_world.no_desk,
    on_face={"rabbit": tired},
    figures=FIGURES,
    camera=lens,
    heads=HEADS,
    bare=BARE,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

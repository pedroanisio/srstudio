#!/usr/bin/env python3
"""Since I Was Six — the sketch as data (see since_i_was_six_data.py for the script).

python3 since_i_was_six.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 since_i_was_six.py PROJECT            # the silent master on the scripted timing
python3 since_i_was_six.py PROJECT --voice    # the narrated master from the recording (since_i_was_six_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from since_i_was_six_data import (
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
    tear,
    validate,
)
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
    loudness="-14",
    desk=toon_world.no_desk,
    on_face={"dog": tear},
    figures=FIGURES,
    camera=lens,
    heads=HEADS,
    bare=BARE,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

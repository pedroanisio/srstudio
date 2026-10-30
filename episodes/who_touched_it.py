#!/usr/bin/env python3
"""Who Touched It — a Toon sketch: Dad and the thermostat (see who_touched_it_data.py for the script).

python3 who_touched_it.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 who_touched_it.py PROJECT            # the silent master on the scripted timing
python3 who_touched_it.py PROJECT --voice    # the narrated master from the recording (who_touched_it_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from srstudio.toon_sketch import Staging, build
from who_touched_it_data import (
    ACCESSIBILITY,
    DESCRIPTION,
    FIGURES,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    dress,
    lens,
    no_desk,
    validate,
)

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
    camera=lens,
    figures=FIGURES,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

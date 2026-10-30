#!/usr/bin/env python3
"""It's Soaking — a Toon sketch: the pan in the sink (see its_soaking_data.py for the script).

python3 its_soaking.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 its_soaking.py PROJECT            # the silent master on the scripted timing
python3 its_soaking.py PROJECT --voice    # the narrated master from the recording (its_soaking_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from its_soaking_data import (
    ACCESSIBILITY,
    DESCRIPTION,
    FIGURES,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    dress,
    no_desk,
    validate,
)
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
    desk=no_desk,
    lit=True,
    figures=FIGURES,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

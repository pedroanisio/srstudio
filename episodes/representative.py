#!/usr/bin/env python3
"""Representative — a Toon sketch: Gus against a phone menu (see representative_data.py for the script).

python3 representative.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 representative.py PROJECT            # the silent master on the scripted timing
python3 representative.py PROJECT --voice    # the narrated master from the recording (representative_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from representative_data import (
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
    camera=lens,
    figures=FIGURES,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

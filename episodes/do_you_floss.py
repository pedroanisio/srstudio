#!/usr/bin/env python3
"""Do You Floss — a Toon sketch: Rex and Fern at the dentist (see do_you_floss_data.py for the script).

python3 do_you_floss.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 do_you_floss.py PROJECT            # the silent master on the scripted timing
python3 do_you_floss.py PROJECT --voice    # the narrated master from the recording (do_you_floss_audio.py)
"""

import sys

from _common import project_root
from do_you_floss_data import (
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
from instagram_posts import PINS, POSTS
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

#!/usr/bin/env python3
"""Full Coverage — a Toon sketch: the agent is not allowed to say (see full_coverage_data.py for the script).

python3 full_coverage.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 full_coverage.py PROJECT            # the silent master on the scripted timing
python3 full_coverage.py PROJECT --voice    # the narrated master from the recording (full_coverage_audio.py)
"""

import sys

from _common import project_root
from full_coverage_data import ACCESSIBILITY, DESCRIPTION, FIGURES, NARRATION, SEED, SKETCH, TINTS, dress, validate
from instagram_posts import PINS, POSTS
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
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

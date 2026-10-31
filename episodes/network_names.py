#!/usr/bin/env python3
"""Network Names — a Toon sketch: two neighbors who never met (see network_names_data.py for the script).

python3 network_names.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 network_names.py PROJECT            # the silent master on the scripted timing
python3 network_names.py PROJECT --voice    # the narrated master from the recording (network_names_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from network_names_data import ACCESSIBILITY, DESCRIPTION, FIGURES, NARRATION, SEED, SKETCH, TINTS, dress, validate
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

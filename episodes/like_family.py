#!/usr/bin/env python3
"""Like Family — a Toon sketch (see like_family_data.py for the script; the build is toon_sketch.build).

python3 like_family.py PROJECT --init    # script.json, assets/poses.json and the pinned Comic Neue
python3 like_family.py PROJECT           # the silent master on the scripted timing
python3 like_family.py PROJECT --voice   # the narrated master from narration.json (like_family_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from like_family_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate
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
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

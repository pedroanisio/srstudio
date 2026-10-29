#!/usr/bin/env python3
"""Like Family — a Toon sketch (see like_family_data.py for the script; the build is _toon_sketch.build).

python3 like_family.py PROJECT --init    # script.json, assets/poses.json and the pinned Comic Neue
python3 like_family.py PROJECT           # the silent master on the scripted timing
python3 like_family.py PROJECT --voice   # the narrated master from narration.json (like_family_audio.py)
"""

import sys

from _common import project_root
from _toon_sketch import Staging, build
from instagram_posts import POSTS
from like_family_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[SKETCH.slug])
ep.finish()

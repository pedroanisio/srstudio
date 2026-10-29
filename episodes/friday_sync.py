#!/usr/bin/env python3
"""Friday Sync — a Toon sketch (see friday_sync_data.py for the script; the build is toon_sketch.build).

python3 friday_sync.py PROJECT --init    # script.json, assets/poses.json and the pinned Comic Neue
python3 friday_sync.py PROJECT           # the silent master on the scripted timing
python3 friday_sync.py PROJECT --voice   # the narrated master from narration.json (friday_sync_audio.py)
"""

import sys

from _common import project_root
from friday_sync_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate
from instagram_posts import POSTS
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
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

#!/usr/bin/env python3
"""Reply All — a Toon sketch (see reply_all_data.py for the script; the build is toon_sketch.build).

python3 reply_all.py PROJECT --init    # script.json, assets/poses.json and the pinned Comic Neue
python3 reply_all.py PROJECT           # the silent master on the scripted timing
python3 reply_all.py PROJECT --voice   # the narrated master from narration.json (reply_all_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from reply_all_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate
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
ep.instagram(POSTS[SKETCH.slug])
ep.finish()

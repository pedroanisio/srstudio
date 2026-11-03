#!/usr/bin/env python3
"""Cold Front — a Collage sketch (see cold_front_data.py for the script; the build is collage_sketch.build).

python3 cold_front.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 cold_front.py PROJECT            # the silent master on the scripted timing
python3 cold_front.py PROJECT --voice    # the narrated master from the recording (cold_front_audio.py)
"""

import sys

from _common import project_root
from cold_front_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

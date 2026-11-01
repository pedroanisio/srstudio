#!/usr/bin/env python3
"""Two Weeks — a Collage sketch (see two_weeks_data.py for the script; the build is collage_sketch.build).

python3 two_weeks.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 two_weeks.py PROJECT            # the silent master on the scripted timing
python3 two_weeks.py PROJECT --voice    # the narrated master from the recording (two_weeks_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from two_weeks_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

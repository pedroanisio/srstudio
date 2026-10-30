#!/usr/bin/env python3
"""Best Angle — a Collage sketch (see best_angle_data.py for the script; the build is collage_sketch.build).

python3 best_angle.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 best_angle.py PROJECT            # the silent master on the scripted timing
python3 best_angle.py PROJECT --voice    # the narrated master from the recording (best_angle_audio.py)
"""

import sys

from _common import project_root
from best_angle_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

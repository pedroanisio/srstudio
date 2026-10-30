#!/usr/bin/env python3
"""Graded Date — a Collage sketch (see graded_date_data.py for the script; the build is collage_sketch.build).

python3 graded_date.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 graded_date.py PROJECT            # the silent master on the scripted timing
python3 graded_date.py PROJECT --voice    # the narrated master from the recording (graded_date_audio.py)
"""

import sys

from _common import project_root
from graded_date_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

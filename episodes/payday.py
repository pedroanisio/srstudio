#!/usr/bin/env python3
"""Payday — a Collage sketch (see payday_data.py for the script; the build is collage_sketch.build).

python3 payday.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 payday.py PROJECT            # the silent master on the scripted timing
python3 payday.py PROJECT --voice    # the narrated master from the recording (payday_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from payday_data import STAGING
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

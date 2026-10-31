#!/usr/bin/env python3
"""Your Lasagna — a Collage sketch (see your_lasagna_data.py for the script; the build is collage_sketch.build).

python3 your_lasagna.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 your_lasagna.py PROJECT            # the silent master on the scripted timing
python3 your_lasagna.py PROJECT --voice    # the narrated master from the recording (your_lasagna_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from your_lasagna_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

#!/usr/bin/env python3
"""On This Day — a Collage sketch (see on_this_day_data.py for the script; the build is collage_sketch.build).

python3 on_this_day.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 on_this_day.py PROJECT            # the silent master on the scripted timing
python3 on_this_day.py PROJECT --voice    # the narrated master from the recording (on_this_day_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from on_this_day_data import STAGING
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

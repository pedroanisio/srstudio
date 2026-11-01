#!/usr/bin/env python3
"""Tell Us — a Collage sketch (see tell_us_data.py for the script; the build is collage_sketch.build).

python3 tell_us.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 tell_us.py PROJECT            # the silent master on the scripted timing
python3 tell_us.py PROJECT --voice    # the narrated master from the recording (tell_us_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from tell_us_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

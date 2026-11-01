#!/usr/bin/env python3
"""Thought of You — a Collage sketch (see thought_of_you_data.py for the script; the build is collage_sketch.build).

python3 thought_of_you.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 thought_of_you.py PROJECT            # the silent master on the scripted timing
python3 thought_of_you.py PROJECT --voice    # the narrated master from the recording (thought_of_you_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from thought_of_you_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

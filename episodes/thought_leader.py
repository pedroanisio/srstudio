#!/usr/bin/env python3
"""Thought Leader — a Collage sketch (see thought_leader_data.py for the script; the build is collage_sketch.build).

python3 thought_leader.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 thought_leader.py PROJECT            # the silent master on the scripted timing
python3 thought_leader.py PROJECT --voice    # the narrated master from the recording (thought_leader_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from thought_leader_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[STAGING.sketch.slug])
ep.finish()

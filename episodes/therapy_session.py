#!/usr/bin/env python3
"""Therapy Session — a Collage sketch (see therapy_session_data.py for the script; the build is collage_sketch.build).

python3 therapy_session.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 therapy_session.py PROJECT            # the silent master on the scripted timing
python3 therapy_session.py PROJECT --voice    # the narrated master from the recording (therapy_session_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from therapy_session_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[STAGING.sketch.slug])
ep.finish()

#!/usr/bin/env python3
"""Intervention — a Collage sketch (see intervention_data.py for the script; the build is _collage_sketch.build).

python3 intervention.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 intervention.py PROJECT            # the silent master on the scripted timing
python3 intervention.py PROJECT --voice    # the narrated master from the recording (intervention_audio.py)
"""

import sys

from _collage_sketch import build
from _common import project_root
from instagram_posts import POSTS
from intervention_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[STAGING.sketch.slug])
ep.finish()

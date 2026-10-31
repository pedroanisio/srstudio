#!/usr/bin/env python3
"""It's Gone — a Collage sketch (see its_gone_data.py for the script; the build is collage_sketch.build).

python3 its_gone.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 its_gone.py PROJECT            # the silent master on the scripted timing
python3 its_gone.py PROJECT --voice    # the narrated master from the recording (its_gone_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from its_gone_data import STAGING
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

#!/usr/bin/env python3
"""I'll Get This — a Collage sketch (see ill_get_this_data.py for the script; the build is collage_sketch.build).

python3 ill_get_this.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 ill_get_this.py PROJECT            # the silent master on the scripted timing
python3 ill_get_this.py PROJECT --voice    # the narrated master from the recording (ill_get_this_audio.py)
"""

import sys

from _common import project_root
from ill_get_this_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

#!/usr/bin/env python3
"""The scale: a Collage sketch; the script and the staging are in the_scale_data.py.

python3 the_scale.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 the_scale.py PROJECT            # the silent master on the scripted timing
python3 the_scale.py PROJECT --voice    # the narrated master from the recording (the_scale_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from the_scale_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

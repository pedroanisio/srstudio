#!/usr/bin/env python3
"""You have it: a Collage sketch; the script and the staging are in you_have_it_data.py.

python3 you_have_it.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 you_have_it.py PROJECT            # the silent master on the scripted timing
python3 you_have_it.py PROJECT --voice    # the narrated master from the recording (you_have_it_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from you_have_it_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

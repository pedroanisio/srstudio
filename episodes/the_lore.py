#!/usr/bin/env python3
"""The Lore — a Collage sketch (see the_lore_data.py for the script; the build is collage_sketch.build).

python3 the_lore.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 the_lore.py PROJECT            # the silent master on the scripted timing
python3 the_lore.py PROJECT --voice    # the narrated master from the recording (the_lore_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from the_lore_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

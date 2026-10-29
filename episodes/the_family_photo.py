#!/usr/bin/env python3
"""The Family Photo — a Collage sketch (see the_family_photo_data.py for the script; the build is collage_sketch.build).

python3 the_family_photo.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 the_family_photo.py PROJECT            # the silent master on the scripted timing
python3 the_family_photo.py PROJECT --voice    # the narrated master from the recording (the_family_photo_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.collage_sketch import build
from the_family_photo_data import STAGING

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[STAGING.sketch.slug])
ep.finish()

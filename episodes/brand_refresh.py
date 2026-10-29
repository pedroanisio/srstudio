#!/usr/bin/env python3
"""Brand Refresh — a Collage sketch (see brand_refresh_data.py for the script; the build is _collage_sketch.build).

python3 brand_refresh.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 brand_refresh.py PROJECT            # the silent master on the scripted timing
python3 brand_refresh.py PROJECT --voice    # the narrated master from the recording (brand_refresh_audio.py)
"""

import sys

from _collage_sketch import build
from _common import project_root
from brand_refresh_data import STAGING
from instagram_posts import POSTS

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[STAGING.sketch.slug])
ep.finish()

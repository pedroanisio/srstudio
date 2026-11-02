#!/usr/bin/env python3
"""Big Font — a Collage sketch (see big_font_data.py for the script; the build is collage_sketch.build).

python3 big_font.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 big_font.py PROJECT            # the silent master on the scripted timing
python3 big_font.py PROJECT --voice    # the narrated master from the recording (big_font_audio.py)
"""

import sys

from _common import project_root
from big_font_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

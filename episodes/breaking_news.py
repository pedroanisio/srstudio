#!/usr/bin/env python3
"""Breaking News — a Collage sketch (see breaking_news_data.py for the script; the build is collage_sketch.build).

python3 breaking_news.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 breaking_news.py PROJECT            # the silent master on the scripted timing
python3 breaking_news.py PROJECT --voice    # the narrated master from the recording (breaking_news_audio.py)
"""

import sys

from _common import project_root
from breaking_news_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[STAGING.sketch.slug])
ep.finish()

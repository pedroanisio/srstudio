#!/usr/bin/env python3
"""Exciting Opportunity — a Collage sketch (see exciting_opportunity_data.py; the build is collage_sketch.build).

python3 exciting_opportunity.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 exciting_opportunity.py PROJECT            # the silent master on the scripted timing
python3 exciting_opportunity.py PROJECT --voice    # the narrated master from exciting_opportunity_audio.py
"""

import sys

from _common import project_root
from exciting_opportunity_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

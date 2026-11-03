#!/usr/bin/env python3
"""First sip: a Collage sketch; the script and the staging are in first_sip_data.py.

python3 first_sip.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 first_sip.py PROJECT            # the silent master on the scripted timing
python3 first_sip.py PROJECT --voice    # the narrated master from the recording (first_sip_audio.py)
"""

import sys

from _common import project_root
from first_sip_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

#!/usr/bin/env python3
"""Gritty Reboot — a Collage sketch (see gritty_reboot_data.py for the script; the build is collage_sketch.build).

python3 gritty_reboot.py PROJECT --init     # script.json, assets/poses.json and the pinned Luckiest Guy
python3 gritty_reboot.py PROJECT            # the silent master on the scripted timing
python3 gritty_reboot.py PROJECT --voice    # the narrated master from the recording (gritty_reboot_audio.py)
"""

import sys

from _common import project_root
from gritty_reboot_data import STAGING
from instagram_posts import POSTS
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[STAGING.sketch.slug])
ep.finish()

#!/usr/bin/env python3
"""The Last Guy: a Toon sketch; the script and the staging are in the_last_guy_data.py.

python3 the_last_guy.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 the_last_guy.py PROJECT            # the silent master on the scripted timing
python3 the_last_guy.py PROJECT --voice    # the narrated master from the recording (the_last_guy_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from srstudio.toon_sketch import Staging, build
from the_last_guy_data import SKETCH, STAGING_ARGS, validate

validate(SKETCH)
ep = build(
    project_root(__file__), Staging(sketch=SKETCH, versions=PINS[SKETCH.slug], **STAGING_ARGS), set(sys.argv[2:])
)
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

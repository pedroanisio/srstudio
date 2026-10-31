#!/usr/bin/env python3
"""Fitted sheet: a Toon sketch; the script and the staging are in fitted_sheet_data.py.

python3 fitted_sheet.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 fitted_sheet.py PROJECT            # the silent master on the scripted timing
python3 fitted_sheet.py PROJECT --voice    # the narrated master from the recording (fitted_sheet_audio.py)
"""

import sys

from _common import project_root
from fitted_sheet_data import SKETCH, STAGING_ARGS, validate
from instagram_posts import PINS, POSTS
from srstudio.toon_sketch import Staging, build

validate(SKETCH)
ep = build(
    project_root(__file__), Staging(sketch=SKETCH, versions=PINS[SKETCH.slug], **STAGING_ARGS), set(sys.argv[2:])
)
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

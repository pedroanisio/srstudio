#!/usr/bin/env python3
"""One symptom: a Toon sketch; the script and the staging are in one_symptom_data.py.

python3 one_symptom.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 one_symptom.py PROJECT            # the silent master on the scripted timing
python3 one_symptom.py PROJECT --voice    # the narrated master from the recording (one_symptom_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from one_symptom_data import SKETCH, STAGING_ARGS, validate
from srstudio.toon_sketch import Staging, build

validate(SKETCH)
ep = build(
    project_root(__file__), Staging(sketch=SKETCH, versions=PINS[SKETCH.slug], **STAGING_ARGS), set(sys.argv[2:])
)
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

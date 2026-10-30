#!/usr/bin/env python3
"""The Report — a Toon sketch with Rex and Fern (see the_report_data.py for the script).

python3 the_report.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 the_report.py PROJECT            # the silent master on the scripted timing
python3 the_report.py PROJECT --voice    # the narrated master: narration.json (the_report_audio.py), the beats
                                      # moved to the voices' words, the keyboard, the phone and the sting heard
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from srstudio.toon_sketch import Staging, build
from the_report_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, STICKER, TINTS, dress, validate

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
    versions=PINS[SKETCH.slug],
    stickers={"dog": STICKER},
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

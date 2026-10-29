#!/usr/bin/env python3
"""Out of Office — a Toon sketch with Pip and Bruno, home on vacation (see out_of_office_data.py for the script).

python3 out_of_office.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 out_of_office.py PROJECT            # the silent master on the scripted timing
python3 out_of_office.py PROJECT --voice    # the narrated master: narration.json (out_of_office_audio.py), the beats
                                         # moved to the voices' words, the mouths on their letters, the sting heard
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from out_of_office_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate
from srstudio.toon_sketch import Staging, build

validate(SKETCH)
STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=dress,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

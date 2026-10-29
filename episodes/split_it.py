#!/usr/bin/env python3
"""Split It — a Toon sketch with Brock and Mia at dinner (see split_it_data.py for the script).

python3 split_it.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 split_it.py PROJECT            # the silent master on the scripted timing
python3 split_it.py PROJECT --voice    # the narrated master: narration.json (split_it_audio.py), the beats moved to
                                       # the voices' words, the mouths on their letters, the sting heard
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from split_it_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate
from srstudio import toon_dinner
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
    desk=toon_dinner.table,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[SKETCH.slug])
ep.finish()

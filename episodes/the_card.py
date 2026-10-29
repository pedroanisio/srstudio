#!/usr/bin/env python3
"""The Card — a Toon sketch (see the_card_data.py for the script; the build is toon_sketch.build).

python3 the_card.py PROJECT --init    # script.json, assets/poses.json and the pinned Comic Neue
python3 the_card.py PROJECT           # the silent master on the scripted timing
python3 the_card.py PROJECT --voice   # the narrated master from narration.json (the_card_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from srstudio.toon_sketch import Staging, build
from the_card_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate

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

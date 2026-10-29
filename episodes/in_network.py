#!/usr/bin/env python3
"""In Network — a Toon sketch with Gil at home and Dana in claims (see in_network_data.py for the script).

python3 in_network.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 in_network.py PROJECT            # the silent master on the scripted timing
python3 in_network.py PROJECT --voice    # the narrated master: narration.json (in_network_audio.py), the beats
                                         # moved to the voices' words, the mouths on their letters, the sting heard
"""

import sys

from _common import project_root
from in_network_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, STICKERS, TINTS, dress, validate
from instagram_posts import POSTS
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
    stickers=STICKERS,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
ep.instagram(POSTS[SKETCH.slug])
ep.finish()

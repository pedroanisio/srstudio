#!/usr/bin/env python3
"""My Machine — a Toon sketch with Mia and Rex over an outage (see my_machine_data.py for the script).

python3 my_machine.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 my_machine.py PROJECT            # the silent master on the scripted timing
python3 my_machine.py PROJECT --voice    # the narrated master: narration.json (my_machine_audio.py), the beats
                                        # moved to the voices' words, the mouths on their letters, the sting heard
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from my_machine_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, push, validate
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
    camera=push,
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

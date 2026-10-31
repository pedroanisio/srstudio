#!/usr/bin/env python3
"""Voice Note — a Toon sketch: twelve minutes without the news (see voice_note_data.py for the script).

python3 voice_note.py PROJECT --init     # script.json, assets/poses.json and the pinned Comic Neue
python3 voice_note.py PROJECT            # the silent master on the scripted timing
python3 voice_note.py PROJECT --voice    # the narrated master from the recording (voice_note_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import PINS, POSTS
from srstudio.toon_sketch import Staging, build
from srstudio.toon_world import no_desk
from voice_note_data import (
    ACCESSIBILITY,
    DESCRIPTION,
    FIGURES,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    WIDE,
    dress,
    lens,
    validate,
)

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
    desk=no_desk,
    lit=True,
    camera=lens,
    figures=FIGURES,
    bare=(WIDE,),
)
ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[SKETCH.slug])
    ep.finish()

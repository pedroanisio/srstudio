#!/usr/bin/env python3
"""Password Expired — a Toon sketch (see password_expired_data.py for the script; the build is _toon_sketch.build).

python3 password_expired.py PROJECT --init    # script.json, assets/poses.json and the pinned Comic Neue
python3 password_expired.py PROJECT           # the silent master on the scripted timing
python3 password_expired.py PROJECT --voice   # the narrated master from narration.json (password_expired_audio.py)
"""

import sys

from _common import project_root
from _toon_sketch import Staging, build
from instagram_posts import POSTS
from password_expired_data import ACCESSIBILITY, DESCRIPTION, NARRATION, SEED, SKETCH, TINTS, dress, validate

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
ep.instagram(POSTS[SKETCH.slug])
ep.finish()

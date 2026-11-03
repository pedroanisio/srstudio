#!/usr/bin/env python3
"""It's Grown On Me (see grown_on_me_data.py for the script), in plain clay on the sofa room.

python3 grown_on_me.py PROJECT --init [--variant]   # script.json, assets/poses.json and the pinned font
python3 grown_on_me.py PROJECT --voice              # the narrated master in clay, from the frames under PROJECT/clay
python3 grown_on_me.py PROJECT --voice --flat       # the flat control: the same staging with the cards in

The clay frames come first, from this reel's own staging (examples/clay_sofa/clay_sofa_study.py perform and render
with --reel grown_on_me_data), on the room's plates under PROJECT/plates and PROJECT/clean-plates. The ending is the
one the project's recording holds (grown_on_me_data.sketch_for): --variant picks the one without the last "Fine."
before anything is recorded.
"""

import sys
from pathlib import Path

from _common import project_root
from grown_on_me_data import (
    ACCESSIBILITY,
    BARE,
    DESCRIPTION,
    NARRATION,
    SEED,
    SKETCH,
    TINTS,
    dress,
    overlay,
    sketch_for,
)
from grown_on_me_data import validate as checked
from instagram_posts import PINS, POSTS
from srstudio import toon_world
from srstudio.toon_sketch import Staging, build

CLAY = Path(__file__).resolve().parent.parent / "examples" / "clay_sofa"
FLAGS = {"--init", "--voice", "--variant", "--flat"}

flags = set(sys.argv[2:])
if flags - FLAGS:
    raise SystemExit(f"the flags are {' '.join(sorted(FLAGS))}")
root = project_root(__file__)
sketch = sketch_for(root, "--variant" in flags)
checked(sketch)
own = dict(
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    versions=PINS[SKETCH.slug],  # both endings are one release
    overlay=overlay,
    loudness="-14",
    bleed=True,
)
if "--flat" in flags or "--init" in flags:
    staging = Staging(sketch=sketch, dress=dress, desk=toon_world.no_desk, bare=BARE, **own)
else:
    sys.path[:0] = [str(CLAY), str(CLAY.parent / "paintover_proof")]
    import clay_sofa_study

    import grown_on_me_data

    clay_sofa_study.bind(grown_on_me_data)
    staging = clay_sofa_study.episode_staging(root, sketch, **own)
ep = build(root, staging, flags - {"--variant", "--flat"})
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[sketch.slug])
    ep.finish()

#!/usr/bin/env python3
"""Sensor: a Collage sketch; the script and the staging are in sensor_data.py.

python3 sensor.py PROJECT --init     # script.json, assets/poses.json and the pinned font
python3 sensor.py PROJECT            # the silent master on the scripted timing
python3 sensor.py PROJECT --voice    # the narrated master from the recording (sensor_audio.py)
"""

import sys

from _common import project_root
from instagram_posts import POSTS
from sensor_data import STAGING
from srstudio.collage_sketch import build

ep = build(project_root(__file__), STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    ep.instagram(POSTS[STAGING.sketch.slug])
    ep.finish()

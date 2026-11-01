#!/usr/bin/env python3
"""The Unwritten Rules #3, a door: Rafa's episode of the talking-head show (see unwritten_rules_door_data.py).

python3 unwritten_rules_door.py PROJECT --init     # script.json and the pinned Fraunces
python3 unwritten_rules_door.py PROJECT            # the silent master on the scripted timing
python3 unwritten_rules_door.py PROJECT --voice    # the voiced master from the recording

A pilot, not an Okayville reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys

from unwritten_rules_door_data import SHOW

from srstudio import rafa_show

rafa_show.run(SHOW, sys.argv)

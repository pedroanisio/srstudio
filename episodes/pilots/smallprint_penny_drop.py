#!/usr/bin/env python3
"""Small Print #1, the penny: Rafa's episode of the explainer show (see smallprint_penny_drop_data.py).

python3 smallprint_penny_drop.py PROJECT --init     # script.json and the pinned Fraunces
python3 smallprint_penny_drop.py PROJECT            # the silent master on the scripted timing
python3 smallprint_penny_drop.py PROJECT --voice    # the voiced master from the recording

A pilot for Small Print: it has no release, and it renders outside the Instagram folder.
"""

import sys

from smallprint_penny_drop_data import SHOW

from srstudio import smallprint

smallprint.run(SHOW, sys.argv)

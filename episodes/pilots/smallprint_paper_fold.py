#!/usr/bin/env python3
"""Small Print #2, the paper: Rafa's episode of the explainer show (see smallprint_paper_fold_data.py).

python3 smallprint_paper_fold.py PROJECT --init     # script.json and the pinned Fraunces
python3 smallprint_paper_fold.py PROJECT            # the silent master on the scripted timing
python3 smallprint_paper_fold.py PROJECT --voice    # the voiced master from the recording

A pilot for Small Print: it has no release, and it renders outside the Instagram folder.
"""

import sys

from smallprint_paper_fold_data import SHOW

from srstudio import smallprint

smallprint.run(SHOW, sys.argv)

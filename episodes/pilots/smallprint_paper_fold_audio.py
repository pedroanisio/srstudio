#!/usr/bin/env python3
"""The recording of smallprint_paper_fold: every line said by Will, heard back, placed at his own pace, with the
foley synthesised; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 smallprint_paper_fold_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from smallprint_paper_fold_data import SHOW, foley

from srstudio import smallprint

main = smallprint.audio_main(SHOW, __doc__, foley)


if __name__ == "__main__":
    sys.exit(main())

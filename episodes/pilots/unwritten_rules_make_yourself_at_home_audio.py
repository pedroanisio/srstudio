#!/usr/bin/env python3
"""The recording of unwritten_rules_make_yourself_at_home: every line said by Will, heard back, placed at his own pace, with the foley synthesised;
see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 unwritten_rules_make_yourself_at_home_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from unwritten_rules_make_yourself_at_home_data import SHOW, foley

from srstudio import rafa_show

main = rafa_show.audio_main(SHOW, __doc__, foley)


if __name__ == "__main__":
    sys.exit(main())

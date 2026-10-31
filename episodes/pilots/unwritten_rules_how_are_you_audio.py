#!/usr/bin/env python3
"""The recording of unwritten_rules_how_are_you: every line said by Will, heard back, placed at his own pace, with the
foley and the bed synthesised; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 unwritten_rules_how_are_you_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from unwritten_rules_how_are_you_data import MOUTH, NOTE, SEED, SKETCH, foley, validate_sketch

from srstudio.toon_sketch import recorder

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate_sketch, foley_of=foley)


if __name__ == "__main__":
    sys.exit(main())

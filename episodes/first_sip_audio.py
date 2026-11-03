#!/usr/bin/env python3
"""First sip: the recording, every line said by its ElevenLabs premade voice and heard back by speech-to-text.

    SRSTUDIO_ALLOW_CLOUD=1 python3 first_sip_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from first_sip_data import NOTE, STAGING
from srstudio.collage_sketch import MOUTH, recorder

main = recorder(STAGING, NOTE, __doc__, mouth=MOUTH)


if __name__ == "__main__":
    sys.exit(main())

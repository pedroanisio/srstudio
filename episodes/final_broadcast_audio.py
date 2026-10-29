#!/usr/bin/env python3
"""Final Broadcast — the recording: every line said by its ElevenLabs premade voice, heard back by speech-to-text,
placed
at the speakers' own pace, the effects synthesised; see _collage_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 final_broadcast_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from _collage_sketch import MOUTH, recorder
from final_broadcast_data import NOTE, STAGING

main = recorder(STAGING, NOTE, __doc__, mouth=MOUTH)


if __name__ == "__main__":
    sys.exit(main())

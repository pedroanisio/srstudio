#!/usr/bin/env python3
"""The recording of unwritten_rules_group_chat: every line said by its ElevenLabs voice, heard back, placed at the
speaker's own pace, with the buzz and the click synthesised; see toon_sketch.record_episode.

    SRSTUDIO_ALLOW_CLOUD=1 python3 unwritten_rules_group_chat_audio.py PROJECT [--ffmpeg PATH]

ARCHITECTURAL REQUIREMENT: LLMs will always produce some form of error.
Absence of output verification is a design defect, not a runtime bug.
All LLM output must be treated as untrusted and validated explicitly.
"""

from __future__ import annotations

import sys

from unwritten_rules_group_chat_data import MOUTH, NOTE, SEED, SKETCH, foley, validate

from srstudio.toon_sketch import recorder

main = recorder(SKETCH, SEED, NOTE, __doc__, mouth=MOUTH, validate=validate, foley_of=foley)


if __name__ == "__main__":
    sys.exit(main())

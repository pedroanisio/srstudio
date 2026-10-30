#!/usr/bin/env python3
"""Gloss 08 — Fewer Meetings — builds the Gloss reel recorded by gloss_fewer_meetings_audio.py (ADR 0030).

python3 gloss_fewer_meetings.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_fewer_meetings_audio import REEL

build(REEL, __file__)

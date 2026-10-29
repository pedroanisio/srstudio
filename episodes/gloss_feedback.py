#!/usr/bin/env python3
"""Gloss 04 — Feedback — builds the Gloss reel recorded by gloss_feedback_audio.py (ADR 0030).

python3 gloss_feedback.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_feedback_audio import REEL

build(REEL, __file__)

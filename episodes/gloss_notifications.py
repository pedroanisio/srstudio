#!/usr/bin/env python3
"""Gloss 09 — Notifications — builds the Gloss reel recorded by gloss_notifications_audio.py (ADR 0030).

python3 gloss_notifications.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _gloss import build
from gloss_notifications_audio import REEL

build(REEL, __file__)

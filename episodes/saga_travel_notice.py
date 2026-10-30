#!/usr/bin/env python3
"""Saga 16 — Travel Notice — builds the Saga reel recorded by saga_travel_notice_audio.py (ADR 0025).

python3 saga_travel_notice.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_travel_notice_audio import REEL

build(REEL, __file__)

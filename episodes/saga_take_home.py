#!/usr/bin/env python3
"""Saga 14 — Take-Home — builds the Saga reel recorded by saga_take_home_audio.py (ADR 0025).

python3 saga_take_home.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_take_home_audio import REEL

build(REEL, __file__)

#!/usr/bin/env python3
"""Saga — builds the Saga reel recorded by saga_moving_day_audio.py (ADR 0025).

python3 saga_moving_day.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_moving_day_audio import REEL

build(REEL, __file__)

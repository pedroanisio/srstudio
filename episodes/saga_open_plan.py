#!/usr/bin/env python3
"""Saga 07 — Open Plan — builds the Saga reel recorded by saga_open_plan_audio.py (ADR 0025).

python3 saga_open_plan.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_open_plan_audio import REEL

build(REEL, __file__)

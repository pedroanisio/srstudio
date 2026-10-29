#!/usr/bin/env python3
"""Saga 06 — Free Tier — builds the Saga reel recorded by saga_free_tier_audio.py (ADR 0025).

python3 saga_free_tier.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_free_tier_audio import REEL

build(REEL, __file__)

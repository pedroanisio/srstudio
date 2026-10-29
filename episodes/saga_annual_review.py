#!/usr/bin/env python3
"""Saga 02 — Annual Review — builds the Saga reel recorded by saga_annual_review_audio.py (ADR 0025).

python3 saga_annual_review.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_annual_review_audio import REEL

build(REEL, __file__)

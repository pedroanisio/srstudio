#!/usr/bin/env python3
"""Saga 18 — Friday Deploy — builds the Saga reel recorded by saga_friday_deploy_audio.py (ADR 0025).

python3 saga_friday_deploy.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_friday_deploy_audio import REEL

build(REEL, __file__)

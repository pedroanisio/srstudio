#!/usr/bin/env python3
"""Saga 01 — Known Issue — builds the Saga reel recorded by saga_known_issue_audio.py (ADR 0025).

python3 saga_known_issue.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_known_issue_audio import REEL

build(REEL, __file__)

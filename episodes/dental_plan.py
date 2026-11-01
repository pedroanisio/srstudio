#!/usr/bin/env python3
"""Saga 19 — Dental Plan: builds the scene from the recording (:mod:`dental_plan_audio`).

python3 dental_plan.py PROJECT
"""

from __future__ import annotations

from _saga import build
from dental_plan_audio import REEL

if __name__ == "__main__":
    build(REEL, __file__)

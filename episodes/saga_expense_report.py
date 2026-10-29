#!/usr/bin/env python3
"""Saga — builds the Saga reel recorded by saga_expense_report_audio.py (ADR 0025).

python3 saga_expense_report.py PROJECT    # → PROJECT/<slug>.scene.xml
"""

from _saga import build
from saga_expense_report_audio import REEL

build(REEL, __file__)

#!/usr/bin/env python3
"""The Unwritten Rules, the group chat: a pilot of the talking-head show (see unwritten_rules_group_chat_data.py).

python3 unwritten_rules_group_chat.py PROJECT --init     # script.json, assets/poses.json and the pinned Fraunces
python3 unwritten_rules_group_chat.py PROJECT            # the silent master on the scripted timing
python3 unwritten_rules_group_chat.py PROJECT --voice    # the voiced master from the recording

A pilot, not an Okayville reel: it has no release and no post, and it renders outside the Instagram folder.
"""

import sys
from functools import lru_cache, partial
from pathlib import Path

from unwritten_rules_group_chat_data import (
    ACCESSIBILITY,
    ACTS,
    DESCRIPTION,
    NARRATION,
    OUTPUT,
    PUSH,
    SEED,
    SIGN_OFF,
    SKETCH,
    TINTS,
    VERSIONS,
    overlay,
    validate,
)

from srstudio import host_kit, toon
from srstudio.fonts import text_width
from srstudio.layout import VERTICAL
from srstudio.toon_sketch import Staging, build

validate(SKETCH)
ROOT = Path(sys.argv[1]).resolve()
VOICED = "--voice" in sys.argv


@lru_cache(maxsize=1)
def plan_of(end: float):
    return host_kit.head_plan(ROOT, end, VOICED)


def words():
    return host_kit.spoken(ROOT) if VOICED else ()


STAGING = Staging(
    sketch=SKETCH,
    seed=SEED,
    description=DESCRIPTION,
    accessibility=ACCESSIBILITY,
    narration=NARRATION,
    tints=TINTS,
    dress=host_kit.stage(ACTS, plan_of),
    versions=VERSIONS,
    desk=host_kit.shelf,
    style=host_kit.HOST,
    bare=host_kit.HOST_CAST.characters,
    captions=lambda *_: None,  # the engine's track, added to the built episode below
    camera=partial(host_kit.framing, PUSH),
    finish=host_kit.finish,
    overlay=overlay,
    safe_area=VERTICAL,
    output=OUTPUT,
    crf="25",
)
ep = build(ROOT, STAGING, set(sys.argv[2:]))
if ep is not None:  # None: --init wrote the project files
    font = (ROOT / ep.spec.font).read_bytes()
    ep.hide_on_cover(
        *host_kit.captions(
            ep, toon.load_script(ROOT / ep.spec.dialogue), partial(text_width, font), words(), (SIGN_OFF,)
        )
    )
    ep.finish()

"""The funny-reels skill keeps the standing full-size review in the words it was set in (ADR 0073)."""

from pathlib import Path

import pytest

SKILL = Path(__file__).resolve().parent.parent / ".claude/skills/funny-reels/SKILL.md"


@pytest.mark.parametrize(
    "rule",
    [
        "Make the full-size frame review a standing gate for every Okayville batch from now on",
        "Full-size frame review on each reel's first render, not after the batch.",
        "deliver batch by batch, a batch never waits for another",
        "someone who is not the author",
        "before going on to the next reel",
    ],
)
def test_the_skill_keeps_the_standing_review_in_its_own_words(rule):
    assert rule in " ".join(SKILL.read_text().split())

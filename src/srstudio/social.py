"""Social captions for a finished episode: a typed Instagram post and the ``ig.txt`` it is written to.

The post is data first (title, description, credit, hashtags) and text second, so a caption can be
checked against Instagram's limits before anyone pastes it. ``ig.txt`` is the plain-text rendering:
title, blank line, description, blank line, credit, blank line, hashtags on one line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

__all__ = ["InstagramPost", "InstagramPostError", "CAPTION_LIMIT", "HASHTAG_LIMIT", "TITLE_LIMIT", "FILE_NAME"]

CAPTION_LIMIT = 2200  # characters Instagram accepts in one caption
HASHTAG_LIMIT = 30  # hashtags Instagram accepts in one caption
TITLE_LIMIT = 125  # characters shown in the feed before "… more"
FILE_NAME = "ig.txt"
_HASHTAG = re.compile(r"^#[^\W\d_][\w]*$", re.UNICODE)


class InstagramPostError(ValueError):
    """The post breaks one of Instagram's limits or the house rules; ``problems`` lists every reason."""

    def __init__(self, problems: list[str]):
        super().__init__("; ".join(problems))
        self.problems = problems


@dataclass(frozen=True)
class InstagramPost:
    title: str
    description: str
    hashtags: tuple[str, ...] = ()
    credit: str = ""
    language: str = "en-US"
    extra: dict = field(default_factory=dict)  # anything a publisher wants to carry along (alt text, cover time)

    def problems(self) -> list[str]:
        out = []
        title, description = self.title.strip(), self.description.strip()
        if not title:
            out.append("title is empty")
        if "\n" in title:
            out.append("title spans more than one line")
        if len(title) > TITLE_LIMIT:
            out.append(f"title has {len(title)} characters; the feed shows {TITLE_LIMIT} before folding")
        if not description:
            out.append("description is empty")
        if len(self.hashtags) > HASHTAG_LIMIT:
            out.append(f"{len(self.hashtags)} hashtags; Instagram accepts {HASHTAG_LIMIT}")
        bad = [h for h in self.hashtags if not _HASHTAG.match(h)]
        if bad:
            out.append(f"hashtags must be '#' plus letters, digits or '_' and start with a letter: {bad}")
        lowered = [h.lower() for h in self.hashtags]
        if len(set(lowered)) != len(lowered):
            out.append("duplicate hashtags")
        n = len(self.text())
        if n > CAPTION_LIMIT:
            out.append(f"caption has {n} characters; Instagram accepts {CAPTION_LIMIT}")
        return out

    def validate(self) -> InstagramPost:
        problems = self.problems()
        if problems:
            raise InstagramPostError(problems)
        return self

    def text(self) -> str:
        blocks = [self.title.strip(), self.description.strip()]
        if self.credit.strip():
            blocks.append(self.credit.strip())
        if self.hashtags:
            blocks.append(" ".join(self.hashtags))
        return "\n\n".join(blocks) + "\n"

    def write(self, folder: Path, name: str = FILE_NAME) -> Path:
        """Validate, then write the caption as ``<folder>/ig.txt`` (mode 600) and return its path."""
        self.validate()
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_text(self.text(), encoding="utf-8")
        path.chmod(0o600)
        return path

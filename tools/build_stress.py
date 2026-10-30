"""Build the word-stress table of srstudio.head_motion from a CMU Pronouncing Dictionary ``cmudict.dict`` file.

Usage: build_stress.py CMUDICT_DICT OUT_GZ

One line per word, ``word<TAB>digits``: the stress digit of each syllable of the word's first pronunciation (1 primary,
2 secondary, 0 none). The gzip header carries no time or name, so the same dictionary gives the same bytes."""

from __future__ import annotations

import gzip
import sys
from pathlib import Path


def table(text: str) -> str:
    """The stress lines of a ``cmudict.dict`` text, its first pronunciation of each word, in the dictionary's order."""
    lines = []
    for line in text.splitlines():
        word, *phones = line.split("#")[0].split()
        if "(" in word:
            continue  # a variant pronunciation
        digits = "".join(phone[-1] for phone in phones if phone[-1].isdigit())
        lines.append(f"{word}\t{digits}\n")
    return "".join(lines)


def main() -> None:
    source, out = Path(sys.argv[1]), Path(sys.argv[2])
    with out.open("wb") as raw, gzip.GzipFile(filename="", mode="wb", compresslevel=9, fileobj=raw, mtime=0) as gz:
        gz.write(table(source.read_text(encoding="utf-8")).encode("utf-8"))


if __name__ == "__main__":
    main()

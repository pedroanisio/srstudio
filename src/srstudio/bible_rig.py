"""The rig rule of the cast bible (ADR 0069): a recurring figure's base rig stays as published, and only clothes and
props change per reel. arc4d3's standing rule, Slack 1793513568.110249; the bible records it as ``base-rig-stays``.

For a Stick figure the base rig is what :class:`~srstudio.stick.Look` calls ``hair`` and ``neck``: the silhouette of the
head and whether the torso reaches it. ``glasses``, ``tie``, ``apron``, ``cap`` and ``sunhat`` are clothes and props,
and they may change from reel to reel. A new field of ``Look`` has to be placed in one of the two lists, or the test
that holds them against the dataclass fails.

What the check can see. A reel is a script that draws its figures with ``stick.rig``; the look of each figure reaches
code only there, and no figure carries a name. So :func:`drawn_looks` runs the reel's builder once in a copy of its
project and records every look it draws, and :func:`check` holds those looks against the base rig each recurring
figure was published with (:data:`PUBLISHED`): a look with a recurring figure's hair and another neck is that figure
drawn with another base rig. A look with other hair is another person, a stranger or a guest, and is left alone, so a
recurring figure redrawn with new hair is beyond what code can prove. The published base rigs are written here as
data, not read from the library's own constants, so a change to those constants cannot move the baseline with it.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import sys
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from pathlib import Path

from . import bible_inventory
from .bible_check import Finding, rig_parts
from .releases import Release
from .social import DeliveryError

__all__ = [
    "BASE_RIG",
    "CLOTHES_AND_PROPS",
    "PUBLISHED",
    "RigError",
    "check",
    "check_release",
    "draws_stick_figures",
    "drawn_looks",
]

BASE_RIG = ("hair", "neck")
CLOTHES_AND_PROPS = ("glasses", "tie", "apron", "cap", "sunhat")
RULE = "base-rig-stays (arc4d3, Slack 1793513568.110249)"
TIMEOUT = 300  # seconds: a builder runs for a few seconds; the bound is for one that does not return


@dataclass(frozen=True)
class BaseRig:
    hair: str
    neck: bool


# The recurring Stick figures and the base rig every published reel draws them with (the-exit, turn-this-car,
# more-tired and the others that name Dev or Noor; ``bible rig`` over the published reels shows no exception).
PUBLISHED: dict[str, BaseRig] = {"dev": BaseRig("cowlick", False), "noor": BaseRig("bun", False)}

HARNESS = """
import dataclasses, json, runpy, sys
epdir, script, project = sys.argv[1:4]
sys.path.insert(0, epdir)
sys.argv = [script, project]
from srstudio import stick
seen = []
checked = stick.check_look
def spy(look):
    seen.append(dataclasses.asdict(look))
    return checked(look)
stick.check_look = spy
runpy.run_path(epdir + "/" + script, run_name="__main__")
print("LOOKS " + json.dumps(seen))
"""


class RigError(DeliveryError):
    """The reel's looks could not be read, so the rig rule could not be checked: nothing is delivered on that."""


def script_of(slug: str) -> str:
    return slug.replace("-", "_") + ".py"


def drawn_looks(slug: str, scripts: Path, episodes: Path, scratch: Path) -> list[dict]:
    """Every look the reel's builder draws, as ``Look`` fields, read by running the builder in a copy of its project.

    The copy lives under ``scratch`` and is removed after; the builder writes its scene there, never into the
    project. A builder that is missing, fails, runs past :data:`TIMEOUT` or prints no looks is a :class:`RigError`:
    a rule that passes because nothing was read is a control that cannot fail."""
    script, project = scripts / script_of(slug), episodes / slug
    if not script.is_file():
        raise RigError(f"{slug}: no builder at {script}; the rig rule cannot read its looks")
    if not project.is_dir():
        raise RigError(f"{slug}: no project at {project}; the rig rule cannot read its looks")
    copy = scratch / f"rig-{slug}"
    shutil.rmtree(copy, ignore_errors=True)
    scratch.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(project, copy)
        try:
            done = subprocess.run(
                [sys.executable, "-c", HARNESS, str(scripts), script.name, str(copy)],
                capture_output=True,
                text=True,
                timeout=TIMEOUT,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RigError(f"{slug}: its builder ran past {TIMEOUT} s; the rig rule cannot read its looks") from exc
    finally:
        shutil.rmtree(copy, ignore_errors=True)
    if done.returncode != 0:
        raise RigError(f"{slug}: its builder failed ({done.stderr.strip().splitlines()[-1:] or 'no message'})")
    lines = [line for line in done.stdout.splitlines() if line.startswith("LOOKS ")]
    if len(lines) != 1:
        raise RigError(f"{slug}: its builder printed {len(lines)} look lists, expected one")
    try:
        looks = json.loads(lines[0].removeprefix("LOOKS "))
    except json.JSONDecodeError as exc:
        raise RigError(f"{slug}: its look list is not JSON: {exc}") from exc
    if not looks:
        raise RigError(f"{slug}: its builder drew no figure, so the rig rule read nothing")
    fields = {f.name for f in _look_fields()}
    if not isinstance(looks, list) or any(not isinstance(x, dict) or set(x) != fields for x in looks):
        raise RigError(f"{slug}: its looks are not made of the fields {sorted(fields)}")
    return looks


def _look_fields() -> tuple[dataclasses.Field, ...]:
    from .stick import Look

    return dataclasses.fields(Look)


def check(slug: str, names: Collection[str], looks: Iterable[dict]) -> list[Finding]:
    """What breaks the rig rule in ``looks``: a look with a recurring figure's hair and another neck, for each of the
    recurring figures ``names`` that the reel names. Clothes and props are never compared."""
    found: list[Finding] = []
    drawn = list(looks)
    for name in sorted(set(names) & set(PUBLISHED)):
        base = PUBLISHED[name]
        bad = sorted({bool(look["neck"]) for look in drawn if look["hair"] == base.hair} - {base.neck})
        for neck in bad:
            found.append(
                Finding(
                    slug,
                    "rig",
                    f"{name!r} was published with hair {base.hair} and neck {base.neck}; the reel draws {base.hair} "
                    f"with neck {neck}. Only {', '.join(CLOTHES_AND_PROPS)} change per reel: {RULE}",
                )
            )
    return found


def draws_stick_figures(release: Release) -> bool:
    """Whether the release draws Stick figures: it says so in its style, or it pins a rig part (a reel that is not
    delivered yet pins nothing, and a reel delivered with another style field can still pin the rig)."""
    return release.style == "Stick" or bool(set(release.parts or ()) & rig_parts())


def check_release(release: Release, episodes: Path, scripts: Path, scratch: Path) -> list[Finding]:
    """The rig rule for one release: a Stick reel's looks read from its builder, held against the figures it names."""
    if not draws_stick_figures(release):
        return []
    project = episodes / release.slug
    heard = bible_inventory.speakers(project) if project.is_dir() else {}
    names = {*(release.tags.recurring if release.tags else ()), *heard}
    if not names & set(PUBLISHED):
        return []  # no recurring figure named, so nothing for the rule to hold, and no builder to run
    return check(release.slug, names, drawn_looks(release.slug, scripts, episodes, scratch))

"""The rig rule of the cast bible (ADR 0069). arc4d3, Slack 1793513568.110249, ruling on Dev's red tie and the neck: "a
recurring figure's base rig stays as published, and only clothes and props change per reel." The bible records it as
``base-rig-stays``.

For a Stick figure the base rig is what :class:`~srstudio.stick.Look` calls ``hair``, ``glasses`` and ``neck``: the
silhouette of the head, the glasses that tell Noor from Dev, and whether the torso reaches the head. ``tie``, ``apron``,
``cap`` and ``sunhat`` are clothes and props: "a costume can change with the story". ``brows`` goes with them: it is off
only so a cap's band can sit where they go, and the head keeps its silhouette. A new field of ``Look`` has to be placed
in one of the two lists, or the test that holds them against the dataclass fails.

What the check can see. A reel is a script, and a figure carries no name. So :func:`drawn_looks` runs the reel's builder
once in a copy of its project and records every look it draws, with the name the drawing gives away: the actor of the
take whose ``phones`` a rig's mouth speaks, the actor of the take as long as a sleeper's ``talk``, or the name on a call
tile. :func:`check` holds each named figure to its base rig in :data:`PUBLISHED`, in full. A look that no one speaks
from may be an extra recombined from the same options, so it counts only for the neck arc4d3 ruled off: a recurring
figure's hair with another neck. A figure the reel names and no one is drawn as is a finding too, so a silent figure
redrawn from scratch does not pass. The published base rigs are written here as data, not read from the library's own
constants, so a change to those constants cannot move the baseline with it.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Collection, Iterable, Mapping
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
    "RULE",
    "RULING",
    "BaseRig",
    "Drawn",
    "RigError",
    "check",
    "check_release",
    "draws_stick_figures",
    "drawn_looks",
    "rig_parts",
    "script_of",
]

BASE_RIG = ("hair", "glasses", "neck")
CLOTHES_AND_PROPS = ("tie", "apron", "cap", "sunhat", "brows")
RULING = "a recurring figure's base rig stays as published, and only clothes and props change per reel."
RULE = "base-rig-stays (arc4d3, Slack 1793513568.110249)"
TIMEOUT = 300  # seconds: a builder runs for a few seconds; the bound is for one that does not return


@dataclass(frozen=True, order=True)
class BaseRig:
    hair: str
    glasses: bool
    neck: bool

    def __str__(self) -> str:
        return f"hair {self.hair}, glasses {self.glasses}, neck {self.neck}"


@dataclass(frozen=True)
class Drawn:
    """One drawn figure: the name its drawing gives away (empty when it gives none) and its base rig. The clothes are
    read to check the look is whole, and dropped: nothing may compare them."""

    who: str
    rig: BaseRig


# The recurring Stick figures, the characters of the bible drawn by the shared rig, and the base rig the published reels
# draw each with: the-exit, more-tired, third-snore, the-viewing and the others that name them. A test holds the
# names to the bible, so a new recurring figure has to be placed here. ``bible rig`` over the published reels lists the
# reels that do not keep them.
PUBLISHED: dict[str, BaseRig] = {
    "dev": BaseRig("cowlick", False, False),
    "gary": BaseRig("spiky", False, False),
    "noor": BaseRig("bun", True, False),
}

HARNESS = """
import dataclasses, json, runpy, sys
from pathlib import Path
epdir, script, project = sys.argv[1:4]
sys.path.insert(0, epdir)
sys.argv = [script, project]
from srstudio import stick, stick_flat
timeline = Path(project, "timeline.json")
items = json.loads(timeline.read_text())["items"] if timeline.is_file() else []
def key(phones):
    return json.dumps(list(phones), sort_keys=True)
def table(rows):
    found = {}
    for k, actor in rows:
        found.setdefault(k, set()).add(actor)
    return found
speaking = table((key(q["phones"]), q["actor"]) for q in items if q.get("phones"))
talking = table((round(q["speech_duration"], 3), q["actor"]) for q in items if q.get("speech_duration"))
def only(actors):
    return next(iter(actors)) if len(actors) == 1 else ""
def by_phones(kw):
    return only(speaking.get(key(kw.get("phones") or ()), ()))
def by_talk(kw):
    talk = kw.get("talk") or ()
    return only(talking.get(round(talk[0][1] - talk[0][0], 3), ())) if talk else ""
who, seen = [""], []
def record(look, name):
    seen.append({**dataclasses.asdict(look), "who": name.strip().lower()})
def named(draw, name_of):
    def spy(*a, **kw):
        who.append(name_of(kw))
        try:
            return draw(*a, **kw)
        finally:
            who.pop()
    return spy
def everywhere(name, old, new):
    for module in list(sys.modules.values()):
        if getattr(module, "__dict__", {}).get(name) is old:
            setattr(module, name, new)
checked = stick.check_look
def look_spy(look):
    record(look, who[-1])
    return checked(look)
everywhere("check_look", checked, look_spy)
everywhere("rig", stick.rig, named(stick.rig, by_phones))
everywhere("murphy_bed", stick_flat.murphy_bed, named(stick_flat.murphy_bed, by_talk))
tile = stick.Tile.__init__
def tile_spy(self, *a, **kw):
    tile(self, *a, **kw)
    record(self.look, self.name)
stick.Tile.__init__ = tile_spy
runpy.run_path(epdir + "/" + script, run_name="__main__")
print("LOOKS " + json.dumps(seen))
"""


class RigError(DeliveryError):
    """The reel's looks could not be read, so the rig rule could not be checked: nothing is delivered on that."""


def script_of(slug: str) -> str:
    return slug.replace("-", "_") + ".py"


def _parse(slug: str, row: object) -> Drawn:
    """One recorded look, to its exact fields: a builder's output is read as untrusted."""
    fields = {f.name: f for f in _look_fields()}
    if not isinstance(row, Mapping) or set(row) != {*fields, "who"}:
        raise RigError(f"{slug}: its looks are not made of the fields {sorted({*fields, 'who'})}")
    hair, glasses, neck, who = row["hair"], row["glasses"], row["neck"], row["who"]
    for name, value, kind in (("hair", hair, str), ("glasses", glasses, bool), ("neck", neck, bool), ("who", who, str)):
        if not isinstance(value, kind):
            raise RigError(f"{slug}: a look's {name} is not a {kind.__name__}: {value!r}")
    return Drawn(who, BaseRig(hair, glasses, neck))


def drawn_looks(slug: str, scripts: Path, episodes: Path) -> list[Drawn]:
    """Every look the reel's builder draws, read by running the builder in a copy of its project.

    The copy is a temporary folder, removed after; the builder writes its scene there, never into the project. A builder
    that is missing, fails, runs past :data:`TIMEOUT` or prints no looks is a :class:`RigError`: a rule that passes
    because nothing was read is a control that cannot fail."""
    script, project = scripts / script_of(slug), episodes / slug
    if not script.is_file():
        raise RigError(f"{slug}: no builder at {script}; the rig rule cannot read its looks")
    if not project.is_dir():
        raise RigError(f"{slug}: no project at {project}; the rig rule cannot read its looks")
    with tempfile.TemporaryDirectory(prefix="srstudio-rig-") as scratch:
        copy = Path(scratch) / slug
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
    if done.returncode != 0:
        raise RigError(f"{slug}: its builder failed ({done.stderr.strip().splitlines()[-1:] or 'no message'})")
    lines = [line for line in done.stdout.splitlines() if line.startswith("LOOKS ")]
    if len(lines) != 1:
        raise RigError(f"{slug}: its builder printed {len(lines)} look lists, expected one")
    try:
        looks = json.loads(lines[0].removeprefix("LOOKS "))
    except json.JSONDecodeError as exc:
        raise RigError(f"{slug}: its look list is not JSON: {exc}") from exc
    if not isinstance(looks, list):
        raise RigError(f"{slug}: its looks are not made of the fields of a look")
    if not looks:
        raise RigError(f"{slug}: its builder drew no figure, so the rig rule read nothing")
    return [_parse(slug, row) for row in looks]


def _look_fields() -> tuple[dataclasses.Field, ...]:
    from .stick import Look

    return dataclasses.fields(Look)


def check(slug: str, names: Collection[str], drawn: Iterable[Drawn]) -> list[Finding]:
    """What breaks the rig rule in ``drawn``, for each recurring figure of ``names``. Clothes are never seen."""
    found: list[Finding] = []
    figures = list(drawn)
    rigs = {d.rig for d in figures}
    for name in sorted(set(names) & set(PUBLISHED)):
        base = PUBLISHED[name]
        theirs = {d.rig for d in figures if d.who == name}
        extras = {d.rig for d in figures if not d.who and d.rig.hair == base.hair and d.rig.neck != base.neck}
        broken = sorted((theirs | extras) - {base})
        for other in broken:
            found.append(
                Finding(slug, "rig", f"{name!r} was published with {base}; the reel draws them with {other}. {_said()}")
            )
        if not broken and base not in rigs:
            found.append(
                Finding(
                    slug,
                    "rig",
                    f"{name!r} is named in the reel and no figure is drawn with the base rig {base}. {_said()}",
                )
            )
    return found


def _said() -> str:
    return f'{RULE}: "{RULING}" Clothes and props are {", ".join(CLOTHES_AND_PROPS)}.'


def draws_stick_figures(release: Release) -> bool:
    """Whether the release draws Stick figures: it says so in its style, or it pins a rig part (a reel that is not
    delivered yet pins nothing, and a reel delivered with another style field can still pin the rig)."""
    return release.style == "Stick" or bool(set(release.parts or ()) & rig_parts())


def check_release(release: Release, episodes: Path, scripts: Path) -> list[Finding]:
    """The rig rule for one release: a Stick reel's looks read from its builder, held against the figures it names."""
    if not draws_stick_figures(release):
        return []
    project = episodes / release.slug
    heard = bible_inventory.speakers(project) if project.is_dir() else {}
    names = {*(release.tags.recurring if release.tags else ()), *heard}
    if not names & set(PUBLISHED):
        return []  # no recurring figure named, so nothing for the rule to hold, and no builder to run
    return check(release.slug, names, drawn_looks(release.slug, scripts, episodes))

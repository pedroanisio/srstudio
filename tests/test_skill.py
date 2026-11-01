"""The funny-reels skill stays true as the library grows: every name it cites resolves, and it hard-codes no inventory.

The catalog's characters, locations, props and styles change with every episode, so the skill sends agents to the
live commands instead of listing them. These tests fail when a cited module, function, command, decision or path
disappears, and when a registered part or style name, or a dated snapshot, creeps back into the text.
"""

import importlib
import pkgutil
import re
from pathlib import Path

import pytest

import srstudio
from srstudio import registry
from srstudio.cli import main
from srstudio.styles import STYLES

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".claude" / "skills" / "funny-reels" / "SKILL.md"
TEXT = SKILL.read_text()
FRONT, BODY = re.fullmatch(r"---\n(.*?)\n---\n(.*)", TEXT, re.S).groups()
SPANS = re.findall(r"`([^`\n]+)`", BODY)
MODULES = {m.name for m in pkgutil.iter_modules(srstudio.__path__)}
FILE_SUFFIX = re.compile(r"\.(md|py|json|jpg|png|txt|mp4|zip|service|path)$")
DOTTED = re.compile(r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+")


def _field(name: str) -> str:
    m = re.search(rf"^{name}: (.+)$", FRONT, re.M)
    assert m, f"frontmatter has no {name}"
    return m.group(1)


def _references() -> list[str]:
    """Dotted code names the skill cites (``srstudio.takes``, ``Episode.audio(duck=)``), calls stripped."""
    refs = []
    for span in SPANS:
        name = span.split("(", 1)[0]
        if DOTTED.fullmatch(name) and not FILE_SUFFIX.search(name) and ":" not in span:
            refs.append(name)
    return refs


def _resolve(name: str) -> object:
    parts = name.split(".")
    if parts[0] == "srstudio":
        obj = importlib.import_module(".".join(parts[:2]))
        rest = parts[2:]
    elif parts[0] in MODULES:
        obj, rest = importlib.import_module(f"srstudio.{parts[0]}"), parts[1:]
    else:
        owners = [importlib.import_module(f"srstudio.{m}") for m in sorted(MODULES) if m not in ("__main__",)]
        found = [vars(mod)[parts[0]] for mod in owners if parts[0] in vars(mod)]
        assert found, f"{parts[0]} is defined nowhere in srstudio"
        obj, rest = found[0], parts[1:]
    for attr in rest:
        obj = getattr(obj, attr)
    return obj


def test_the_frontmatter_names_the_skill_and_versions_it():
    assert _field("name") == SKILL.parent.name
    assert len(_field("description")) > 80
    assert re.fullmatch(r"\d+\.\d+\.\d+", _field("schema_version"))
    assert "generated-by" in FRONT


def test_the_skill_cites_code_at_all():
    assert len(_references()) >= 10  # the resolver below must have something to check


@pytest.mark.parametrize("name", _references())
def test_every_cited_module_and_function_exists(name):
    _resolve(name)


@pytest.mark.parametrize("command", sorted({m for s in SPANS for m in re.findall(r"^srstudio ([\w-]+)", s)}))
def test_every_cited_cli_command_exists(command):
    with pytest.raises(SystemExit) as done:
        main([command, "--help"])
    assert done.value.code == 0


@pytest.mark.parametrize("number", sorted(set(re.findall(r"ADR (\d{4})", BODY))))
def test_every_cited_decision_exists(number):
    assert list((ROOT / "docs" / "decisions").glob(f"{number}-*.md")), f"ADR {number} is missing"


@pytest.mark.parametrize(
    "path", sorted({s for s in SPANS if re.match(r"(src|docs|episodes|tools|tests)/", s) and "<" not in s})
)
def test_every_cited_repository_path_exists(path):
    assert (ROOT / path).exists(), path


def test_the_skill_lists_no_registered_part_or_style_by_name():
    """Inventories drift: the skill names the commands that list parts and styles, never the parts themselves."""
    parts = {e.name for e in registry.entries()}
    styles = {s.slug for s in STYLES.values()} | {s.name for s in STYLES.values()}
    assert parts, "the registry is empty, so this test proves nothing"
    assert sorted(set(SPANS) & (parts | styles)) == []


def test_the_skill_holds_no_dated_snapshot():
    """A fact pinned to a date ("unused on 2026-10-28") goes stale; the skill says which command measures it."""
    assert re.findall(r"\b\d{4}-\d{2}-\d{2}\b", BODY) == []


def test_the_skill_names_the_live_inventory_commands():
    for command in ("srstudio catalog", "srstudio styles", "srstudio usage"):
        assert f"`{command}" in BODY, command


def test_every_srstudio_command_is_named(capsys):
    """The tests above hold the skill to the code. This holds the code to the skill: no command goes unsaid."""
    with pytest.raises(SystemExit):
        main(["--help"])
    commands = re.search(r"\{([a-z,-]+)\}", capsys.readouterr().out).group(1).split(",")
    assert sorted(set(commands) - set(re.findall(r"srstudio ([a-z][a-z-]*)", BODY))) == []

"""The systemd units in tools/systemd: the Drive publisher packs original episodes, and packing validates each package
with the engine, so the unit must name the engine (without it every new original is held back unpacked)."""

from pathlib import Path

UNITS = Path(__file__).resolve().parent.parent / "tools" / "systemd"


def environment(unit: str) -> dict[str, str]:
    env = {}
    for line in (UNITS / unit).read_text().splitlines():
        if line.startswith("Environment="):
            key, _, value = line.removeprefix("Environment=").partition("=")
            env[key] = value
    return env


def test_the_drive_publisher_names_the_engine_and_the_packages():
    env = environment("srstudio-drive.service")
    assert env["SRSTUDIO_ENGINE"] == "%h/worskpace/generated/bin/scene-render"
    assert env["SRSTUDIO_PACKAGES"] == "%h/worskpace/generated/packages"

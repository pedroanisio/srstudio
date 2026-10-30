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


def test_the_catalog_page_is_built_from_the_measured_usage():
    """The registry no longer says which episodes use a part (ADR 0032): without the usage report the page would
    claim none, so the unit hands it the one ``srstudio usage`` last wrote."""
    unit = (UNITS / "srstudio-catalog.service").read_text()
    command = unit[unit.index("ExecStart=") :].split("\nEnvironment=")[0]
    assert "--usage generated/catalog/usage.json" in command


def test_the_catalog_page_reads_which_reels_pin_which_version():
    """Without the release files the page can only say the pins were not read (ADR 0053)."""
    unit = (UNITS / "srstudio-catalog.service").read_text()
    assert "--releases srstudio/episodes/posts" in unit[unit.index("ExecStart=") :]


def test_the_catalog_is_written_as_a_site_and_served_on_loopback():
    build = (UNITS / "srstudio-catalog.service").read_text()
    assert "--site generated/catalog/site" in build and "--out" not in build
    web = (UNITS / "srstudio-catalog-web.service").read_text()
    command = next(line for line in web.splitlines() if line.startswith("ExecStart="))
    assert command.endswith("serve generated/catalog/site --host 127.0.0.1 --port 8765")
    assert "Restart=on-failure" in web

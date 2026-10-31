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
    """Without the release files the page can only say the pins were not read (ADR 0061)."""
    unit = (UNITS / "srstudio-catalog.service").read_text()
    assert "--releases srstudio/episodes/posts" in unit[unit.index("ExecStart=") :]


def test_the_catalog_is_written_as_a_site_and_served_on_loopback():
    build = (UNITS / "srstudio-catalog.service").read_text()
    assert "--site generated/catalog/site" in build and "--out" not in build
    web = (UNITS / "srstudio-catalog-web.service").read_text()
    command = next(line for line in web.splitlines() if line.startswith("ExecStart="))
    assert command.endswith("serve generated/catalog/site --host 127.0.0.1 --port 8765")
    assert "Restart=on-failure" in web


def exec_start(unit: str) -> list[str]:
    """The words of a unit's ExecStart, continuation lines joined."""
    text = (UNITS / unit).read_text().replace("\\\n", " ")
    command = next(line for line in text.splitlines() if line.startswith("ExecStart="))
    return command.removeprefix("ExecStart=").split()


def option(words: list[str], name: str) -> str:
    return words[words.index(name) + 1]


def test_the_usage_report_the_page_reads_is_the_one_a_unit_writes():
    """Nothing but ``srstudio usage`` writes the report, and the page unit only reads it: without a unit that runs it
    the report ages and the page claims the parts of the episodes it was last measured on."""
    reads = option(exec_start("srstudio-catalog.service"), "--usage")
    writes = option(exec_start("srstudio-usage.service"), "--out")
    assert exec_start("srstudio-usage.service")[1] == "usage"
    # the page unit starts in the workspace, the usage unit in its srstudio folder
    assert (Path("worskpace") / reads).resolve() == (Path("worskpace/srstudio") / writes).resolve()


def test_the_usage_unit_measures_what_the_other_units_read():
    words = exec_start("srstudio-usage.service")
    page = exec_start("srstudio-catalog.service")
    for name in ("--episodes", "--packages"):
        assert (Path("worskpace/srstudio") / option(words, name)).resolve() == (
            Path("worskpace") / option(page, name)
        ).resolve()
    assert "--arg" not in words  # no per-episode option kept by hand: the measure finds what each episode needs
    unit = (UNITS / "srstudio-usage.service").read_text()
    assert "Type=oneshot" in unit and "UMask=0077" in unit
    env = environment("srstudio-usage.service")
    assert env["SRSTUDIO_ENGINE"] == "%h/worskpace/generated/bin/scene-render"
    assert env["SRSTUDIO_PACKAGES"] == "%h/worskpace/generated/packages"


def test_a_new_episode_or_a_library_commit_starts_the_measure_and_a_new_report_the_page():
    def watched(path_unit: str) -> set[str]:
        lines = (UNITS / path_unit).read_text().splitlines()
        return {line.removeprefix("PathChanged=") for line in lines if line.startswith("PathChanged=")}

    measuring = watched("srstudio-usage.path")
    assert {"%h/worskpace/generated/episodes", "%h/worskpace/srstudio/.git/refs/heads"} <= measuring
    assert "Unit=srstudio-usage.service" in (UNITS / "srstudio-usage.path").read_text()
    assert "%h/worskpace/generated/catalog/usage.json" in watched("srstudio-catalog.path")
    # a pilot's render and its project are in folders of their own (ADR 0054), which the top level does not show
    assert "%h/worskpace/generated/renders/pilots" in watched("srstudio-catalog.path")
    assert {f"%h/worskpace/generated/episodes/pilots{x}" for x in ("", "/mind", "/maps", "/news", "/host")} <= measuring
    # a report write must not start another measure
    assert "%h/worskpace/generated/catalog" not in measuring

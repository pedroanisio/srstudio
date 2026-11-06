"""The strict gate reads a project's render reports newest first, the write-once -vN ones by number (ADR 0236)."""

from srstudio.strict_gate import _reports


def test_reports_are_newest_first_by_number(tmp_path):
    qa = tmp_path / "qa"
    qa.mkdir()
    for name in ("render-report.json", "render-report-v2.json", "render-report-v10.json", "render-report-v9.json"):
        (qa / name).write_text("{}")
    assert [p.name for p in _reports(tmp_path)] == [
        "render-report-v10.json",
        "render-report-v9.json",
        "render-report-v2.json",
        "render-report.json",
    ]


def test_names_that_are_not_versions_are_not_reports(tmp_path):
    qa = tmp_path / "qa"
    qa.mkdir()
    for name in ("render-report-vx.json", "render-report-v1.json", "render-report-v0.json", "render-report-v2.txt"):
        (qa / name).write_text("{}")
    assert _reports(tmp_path) == []
    (qa / "render-report-v3.json").write_text("{}")
    assert [p.name for p in _reports(tmp_path)] == ["render-report-v3.json"]

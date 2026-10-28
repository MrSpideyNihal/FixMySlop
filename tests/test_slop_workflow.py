"""Tests for the agent-facing workflow: safe fixes, brief, SARIF, hook, MCP server, init."""
import io
import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fixmyslop.cli.cli_app import app, run_scan
from fixmyslop.core.mcp_server import serve
from fixmyslop.core.report_builder import ReportBuilder
from fixmyslop.core.slop.brief import build_fix_brief, upsert_guide, GUIDE_START
from fixmyslop.core.slop.engine import SlopEngine, slop_score, grade
from fixmyslop.core.slop.fixers import apply_safe_fixes

runner = CliRunner()

SLOPPY_TSX = (
    'export default function Hero() {\n'
    '  // Initialize the count\n'
    '  const count = 0;\n'
    '  return (\n'
    '    <div className="bg-gradient-to-r from-purple-600 to-pink-500">\n'
    '      <h1>Revolutionize your workflow</h1>\n'
    '      <a href="#">Learn more</a>\n'
    '    </div>\n'
    '  );\n'
    '}\n'
)


def _project(tmp_path: Path) -> Path:
    (tmp_path / "package.json").write_text('{"dependencies": {"react": "18"}}', encoding="utf-8")
    (tmp_path / "Hero.tsx").write_text(SLOPPY_TSX, encoding="utf-8")
    (tmp_path / "util.py").write_text("try:\n    x = 1\nexcept:\n    raise\n", encoding="utf-8")
    return tmp_path


def test_run_scan_reports_and_scores(tmp_path):
    report, _ = run_scan([str(_project(tmp_path))], use_static=False)
    rules = {i.rule_id for i in report.issues}
    assert {"ui/ai-gradient", "ui/marketing-slop", "a11y/dead-link", "slop/bare-except"} <= rules
    assert report.grade in "ABCDF" and report.slop_score > 0


def test_committed_artifacts_flags_tracked_node_modules(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    artifact = project / "node_modules" / "package" / "index.js"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("module.exports = 1;\n", encoding="utf-8")
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    subprocess.run(["git", "add", "node_modules"], cwd=project, check=True)

    report, _ = run_scan([str(project)], use_static=False)
    findings = [i for i in report.issues if i.rule_id == "slop/committed-artifacts"]

    assert len(findings) == 1
    finding = findings[0]
    assert finding.severity == "LOW"
    assert finding.category == "Code Slop"
    assert "1 file under node_modules/ is committed" in finding.description
    assert "git rm -r --cached <path>" in finding.suggested_fix
    assert ".gitignore" in finding.suggested_fix


def test_committed_artifacts_clean_repo_without_gitignore_is_not_reported(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    subprocess.run(["git", "add", "main.py"], cwd=project, check=True)

    report, _ = run_scan([str(project)], use_static=False)

    assert "slop/committed-artifacts" not in {i.rule_id for i in report.issues}


def test_committed_artifacts_rule_is_configurable(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    artifact = project / "node_modules" / "package" / "index.js"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("module.exports = 1;\n", encoding="utf-8")
    (project / ".fixmyslop.yml").write_text(
        "disable:\n  - slop/committed-artifacts\n", encoding="utf-8",
    )
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    subprocess.run(["git", "add", "node_modules"], cwd=project, check=True)

    report, _ = run_scan([str(project)], use_static=False)

    assert "slop/committed-artifacts" not in {i.rule_id for i in report.issues}


def test_committed_artifacts_only_applies_inside_git_repositories(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    artifact = project / "node_modules" / "package" / "index.js"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("module.exports = 1;\n", encoding="utf-8")

    report, _ = run_scan([str(project)], use_static=False)

    assert "slop/committed-artifacts" not in {i.rule_id for i in report.issues}


def test_committed_artifacts_reports_one_counted_finding_per_kind(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    tracked_paths = [
        "node_modules/a/index.js",
        "node_modules/b/index.js",
        ".venv/bin/python",
        "venv/bin/python",
        "__pycache__/module.pyc",
        "src/module.pyc",
        "action.yml",
        "dist/app.js",
        "build/app.js",
        ".next/app.js",
        ".DS_Store",
        "src/.DS_Store",
        "debug.log",
        "logs/server.log",
        "tests/sample.log",
        "fixtures/parser.log",
    ]
    for name in tracked_paths:
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("artifact\n", encoding="utf-8")
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    subprocess.run(["git", "add", *tracked_paths], cwd=project, check=True)

    report, _ = run_scan([str(project)], use_static=False)
    findings = [i for i in report.issues if i.rule_id == "slop/committed-artifacts"]
    descriptions = [finding.description for finding in findings]

    assert len(findings) == 6
    assert any("2 files under node_modules/" in description for description in descriptions)
    assert any("2 files under .venv/ or venv/" in description for description in descriptions)
    assert any("2 files under __pycache__/ or matching *.pyc" in description for description in descriptions)
    assert any("1 file under .next/" in description for description in descriptions)
    assert any("2 files named .DS_Store" in description for description in descriptions)
    assert any("2 files matching *.log" in description for description in descriptions)


@pytest.mark.parametrize("scan_kind", ["changed", "single_file"])
def test_committed_artifacts_skipped_for_narrow_scans(tmp_path, scan_kind):
    project = tmp_path / "project"
    source = project / "src" / "b.py"
    artifact = project / "node_modules" / "package" / "index.js"
    source.parent.mkdir(parents=True)
    artifact.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    artifact.write_text("module.exports = 1;\n", encoding="utf-8")
    subprocess.run(["git", "init", "--quiet"], cwd=project, check=True)
    subprocess.run(["git", "add", "src/b.py", "node_modules"], cwd=project, check=True)

    if scan_kind == "changed":
        report, _ = run_scan([str(project)], changed=True, use_static=False)
    else:
        report, _ = run_scan([str(source)], use_static=False)

    assert "slop/committed-artifacts" not in {i.rule_id for i in report.issues}


def test_safe_fixes_preserve_behavior_and_line_endings(tmp_path):
    project = _project(tmp_path)
    crlf = project / "crlf.py"
    crlf.write_bytes(b"try:\r\n    x = 1\r\nexcept:\r\n    raise\r\n")
    report, _ = run_scan([str(project)], use_static=False)
    applied = apply_safe_fixes(report.issues)
    assert applied
    assert "except Exception:" in (project / "util.py").read_text(encoding="utf-8")
    assert b"except Exception:\r\n" in crlf.read_bytes()
    assert "Initialize the count" not in (project / "Hero.tsx").read_text(encoding="utf-8")


def test_brief_lists_issues_with_fix_hints(tmp_path):
    report, _ = run_scan([str(_project(tmp_path))], use_static=False)
    brief = build_fix_brief(report.issues, lambda p: Path(p).name)
    assert "## UI direction" in brief
    assert "Hero.tsx" in brief and "ui/ai-gradient" in brief
    assert "How to fix each rule" in brief
    assert "## Production bar" in brief and "before and after your changes" in brief


def test_sarif_export(tmp_path):
    report, _ = run_scan([str(_project(tmp_path))], use_static=False)
    sarif = json.loads(ReportBuilder().export(report, "sarif"))
    run = sarif["runs"][0]
    assert sarif["version"] == "2.1.0"
    assert run["results"] and run["tool"]["driver"]["rules"]
    assert all(not r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"].startswith("/")
               for r in run["results"])


def test_score_and_grade():
    assert slop_score([], 1000) == 0.0
    assert grade(0) == "A" and grade(90) == "F"


def test_scan_cli_formats_and_fail_on(tmp_path):
    project = _project(tmp_path)
    result = runner.invoke(app, ["scan", str(project), "-f", "compact", "--no-static", "--fail-on", "medium"])
    assert result.exit_code == 1
    assert "ui/ai-gradient" in result.stdout
    clean = tmp_path / "clean"
    clean.mkdir()
    (clean / "ok.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert runner.invoke(app, ["scan", str(clean), "--no-static", "--fail-on", "low"]).exit_code == 0


def test_hook_blocks_only_on_edited_lines(tmp_path):
    project = _project(tmp_path)
    payload = {"tool_name": "Edit", "cwd": str(project),
               "tool_input": {"file_path": str(project / "Hero.tsx"),
                              "new_string": "      <h1>Revolutionize your workflow</h1>"}}
    result = runner.invoke(app, ["hook"], input=json.dumps(payload))
    assert result.exit_code == 2
    assert "ui/marketing-slop" in result.output
    assert "ui/ai-gradient" not in result.output  # not part of this edit

    payload["tool_input"]["new_string"] = "  const count = 0;"
    assert runner.invoke(app, ["hook"], input=json.dumps(payload)).exit_code == 0


def test_mcp_server_roundtrip(tmp_path, monkeypatch):
    project = _project(tmp_path)
    monkeypatch.chdir(project)
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
         "params": {"name": "check_slop", "arguments": {"paths": ["Hero.tsx"]}}},
        {"jsonrpc": "2.0", "id": 4, "method": "nope"},
    ]
    out = io.StringIO()
    serve(io.StringIO("\n".join(json.dumps(r) for r in requests) + "\n"), out)
    responses = [json.loads(line) for line in out.getvalue().splitlines()]
    assert [r["id"] for r in responses] == [1, 2, 3, 4]
    assert {t["name"] for t in responses[1]["result"]["tools"]} >= {"check_slop", "fix_safe"}
    assert "ui/ai-gradient" in responses[2]["result"]["content"][0]["text"]
    assert responses[3]["error"]["code"] == -32601


def test_init_is_idempotent(tmp_path):
    for _ in range(2):
        result = runner.invoke(app, ["init", str(tmp_path), "--claude", "--cursor", "--agents"])
        assert result.exit_code == 0
    settings = json.loads((tmp_path / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert len(settings["hooks"]["PostToolUse"]) == 1
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").count(GUIDE_START) == 1
    assert (tmp_path / ".claude" / "skills" / "fixmyslop" / "SKILL.md").exists()
    assert "fixmyslop" in json.loads((tmp_path / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
    assert (tmp_path / ".fixmyslop.yml").exists()


def test_upsert_guide_preserves_existing_content(tmp_path):
    path = tmp_path / "AGENTS.md"
    path.write_text("# My rules\n\nBe nice.\n", encoding="utf-8")
    upsert_guide(path)
    upsert_guide(path)
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# My rules") and text.count(GUIDE_START) == 1


def test_rules_command():
    result = runner.invoke(app, ["rules", "ui/ai-gradient"])
    assert result.exit_code == 0 and "Fix:" in result.stdout


def test_engine_is_fast(tmp_path):
    """Hundreds of files should scan in well under a few seconds."""
    import time
    for n in range(200):
        (tmp_path / f"C{n}.tsx").write_text(SLOPPY_TSX, encoding="utf-8")
    engine = SlopEngine(tmp_path)
    start = time.time()
    for path in tmp_path.glob("*.tsx"):
        engine.check_file(path, SLOPPY_TSX)
    assert time.time() - start < 5


def test_html_report_is_self_contained_and_safe(tmp_path):
    project = _project(tmp_path)
    (project / "x.tsx").write_text('<p>Lorem ipsum</p>\n// "</script><script>alert(1)</script>"\n', encoding="utf-8")
    report, _ = run_scan([str(project)], use_static=False)
    page = ReportBuilder().export(report, "html")
    assert page.startswith("<!DOCTYPE html>") and "FixMySlop" in page
    assert "http://" not in page and "https://" not in page          # no external requests
    assert page.count("<script") == 2                                 # data + app script only
    assert "Copy fix prompt" in page and "ui/ai-gradient" in page


def test_scan_open_writes_report(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))
    result = runner.invoke(app, ["scan", str(_project(tmp_path)), "--no-static", "--open", "--fail-on", "none"])
    assert result.exit_code == 0
    assert (tmp_path / ".fixmyslop" / "report.html").exists() and opened


def test_baseline_hides_existing_and_survives_line_shifts(tmp_path):
    """Accept today's issues; moving code around must not resurface them, new slop must still show."""
    from fixmyslop.core.slop.baseline import write_baseline
    project = _project(tmp_path)
    report, engine = run_scan([str(project)], use_static=False, use_baseline=False)
    assert report.issues
    write_baseline(project, report.issues, engine.relpath)

    hero = project / "Hero.tsx"
    hero.write_text("// header comment added above everything\n\n" + hero.read_text(encoding="utf-8"), encoding="utf-8")
    report, _ = run_scan([str(project)], use_static=False)
    assert report.issues == [] and report.baselined > 0

    hero.write_text(hero.read_text(encoding="utf-8") + '<a href="#">new dead link</a>\n', encoding="utf-8")
    report, _ = run_scan([str(project)], use_static=False)
    assert [i.rule_id for i in report.issues] == ["a11y/dead-link"]
    assert run_scan([str(project)], use_static=False, use_baseline=False)[0].baselined == 0


def test_baseline_command_and_fail_on_only_new(tmp_path):
    project = _project(tmp_path)
    assert runner.invoke(app, ["baseline", str(project), "--no-static"]).exit_code == 0
    assert (project / ".fixmyslop-baseline.json").exists()
    assert runner.invoke(app, ["scan", str(project), "--no-static", "--fail-on", "low"]).exit_code == 0
    assert runner.invoke(app, ["scan", str(project), "--no-static", "--fail-on", "low", "--no-baseline"]).exit_code == 1



def test_empty_scan_says_nothing_was_scanned(tmp_path):
    (tmp_path / "notes.txt").write_text("hello", encoding="utf-8")
    result = runner.invoke(app, ["scan", str(tmp_path), "--no-static", "--fail-on", "none"])
    assert "Nothing was scanned" in result.stdout and "Clean." not in result.stdout

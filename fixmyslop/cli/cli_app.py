"""
FixMySlop CLI — fully functional without the GUI.

    fixmyslop scan [PATHS]          deterministic slop scan (no LLM, ~instant)
    fixmyslop fix [PATHS]           safe auto-fixes, then hand the rest to your agent
    fixmyslop init                  install hooks/rules for Claude Code, Cursor, CI…
    fixmyslop hook                  Claude Code PostToolUse hook (reads JSON on stdin)
    fixmyslop rules [RULE_ID]       list / explain rules
"""
import json
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.markup import escape

from fixmyslop.macros import (
    APP_NAME, APP_VERSION, DEFAULT_MODEL, DEFAULT_BASE_URL, DEFAULT_API_KEY,
    SCAN_MODE_TURBO, SCAN_MODE_DEEP, DEFAULT_SCAN_MODE, SEVERITY_RANK,
    REPORT_FORMAT_TEXT, REPORT_FORMAT_PDF, is_scannable,
)
from fixmyslop.cli.cli_output import (
    console, print_banner, print_report, print_error, print_success, print_info,
    print_warning, print_llm_warning, print_slop_report, stderr_console,
)

app = typer.Typer(
    name="fixmyslop",
    help=f"{APP_NAME} — the slop linter for the AI-agent era. "
         "Finds AI slop in UI and code instantly, then lets your agent fix it.",
    add_completion=True,
    no_args_is_help=True,
)

_FORMATS = {"text", "compact", "markdown", "html", "json", "csv", "sarif", "prompt", "pdf"}
_SUFFIX_FORMATS = {
    ".md": "markdown", ".markdown": "markdown", ".html": "html", ".htm": "html", ".json": "json",
    ".csv": "csv", ".sarif": "sarif", ".pdf": "pdf", ".txt": "prompt",
}

# ─── Shared options ─────────────────────────────────────────────────────────
_PATHS = typer.Argument(None, help="Files or folders to scan (default: current directory)")
_MODEL = typer.Option(DEFAULT_MODEL, "--model", "-m", envvar="FIXMYSLOP_MODEL", help="LLM model tag (for --llm / --agent llm)")
_BASE_URL = typer.Option(DEFAULT_BASE_URL, "--base-url", "-b", envvar="FIXMYSLOP_BASE_URL",
                         help="OpenAI-compatible API URL (Ollama, LM Studio, OpenRouter, OpenAI…)")
_API_KEY = typer.Option(DEFAULT_API_KEY, "--api-key", envvar="FIXMYSLOP_API_KEY", help="API key for the LLM endpoint")
_CHANGED = typer.Option(False, "--changed", help="Only scan files changed vs the base branch (+ uncommitted)")
_BASE = typer.Option(None, "--base", help="Base branch for --changed (default: origin/HEAD, main, master)")


# ─── Pipeline ───────────────────────────────────────────────────────────────

def _resolve_root(targets: list[Path]) -> Path:
    """Project root used for config, manifests and relative paths."""
    from fixmyslop.utils.git_utils import git_root
    first = targets[0]
    repo = git_root(first)
    if repo is not None:
        return repo
    if len(targets) == 1:
        return first if first.is_dir() else first.parent
    return Path.cwd().resolve()


def _collect_files(targets: list[Path], changed: bool, base: Optional[str]) -> Optional[list[Path]]:
    """Explicit file list for the scan (None = let the scanner walk the single target)."""
    from fixmyslop.core.scanner import Scanner
    from fixmyslop.utils.git_utils import changed_files
    if changed:
        files: list[Path] = []
        for target in targets:
            found = changed_files(target if target.is_dir() else target.parent, base)
            if found is None:
                print_warning("--changed needs a git repository; scanning everything instead.")
                return _collect_files(targets, False, base)
            files += [f for f in found if target.is_dir() or f == target.resolve()]
        return files
    if len(targets) == 1 and targets[0].is_dir():
        return None
    files = []
    for target in targets:
        files += [target] if target.is_file() else Scanner(str(target)).files()
    return files


def run_scan(paths: Optional[list[str]], *, changed: bool = False, base: Optional[str] = None,
             use_static: bool = True, llm_client=None, scan_mode: str = DEFAULT_SCAN_MODE,
             online: bool = False, only: Optional[list[str]] = None, min_severity: str = "low",
             show_progress: bool = False, use_baseline: bool = True):
    """Scan paths and return (report, engine). Shared by scan, fix, ui, hook-free flows.

    With use_baseline, issues recorded in .fixmyslop-baseline.json are hidden (counted in report.baselined).
    """
    from fixmyslop.core.scanner import Scanner
    from fixmyslop.core.analyzer import Analyzer
    from fixmyslop.core.report_builder import ReportBuilder
    from fixmyslop.core.slop.engine import SlopEngine, at_or_above
    from fixmyslop.core.slop.config import load_config

    targets = [Path(p).resolve() for p in (paths or ["."])]
    for target in targets:
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {target}")
    root = _resolve_root(targets)
    config = load_config(root)
    if only:
        config.only = list(only)
    engine = SlopEngine(root, config=config, online=online)
    for target in targets:
        config.allow(engine.relpath(target))

    files = _collect_files(targets, changed, base)
    engine.whole_project = files is None and not any(t.is_file() for t in targets)
    scan_dir = targets[0] if files is None else root
    scanner = Scanner(str(scan_dir), only_files=files)
    file_list = [f for f in scanner.files() if not config.is_excluded(engine.relpath(f))]
    scanner = Scanner(str(scan_dir), only_files=file_list)

    analyzer = Analyzer(
        llm_client=llm_client, use_static_tools=use_static, scan_mode=scan_mode, slop_engine=engine,
        max_retries=2,
    )
    analyzer.prepare(file_list)

    start = time.time()
    issues = []
    total = len(file_list)
    for index, (file_path, content) in enumerate(scanner.scan(), 1):
        if show_progress and llm_client:
            console.print(f"  [dim]\\[{index}/{total}][/dim] {escape(engine.relpath(file_path))}")
        issues.extend(analyzer.analyze_file(file_path, content))
    issues.extend(analyzer.finalize())
    if only:  # --only selects FixMySlop rule groups, so drop third-party tool findings
        issues = [i for i in issues if i.source_tool == "fixmyslop"]
    issues = at_or_above(issues, min_severity) if min_severity.lower() != "info" else issues

    baselined = 0
    if use_baseline:
        from fixmyslop.core.slop.baseline import apply_baseline, load_baseline
        accepted = load_baseline(root)
        if accepted:
            issues, baselined = apply_baseline(issues, accepted, engine.relpath, root)

    report = ReportBuilder().build(
        repo_path=str(root),
        issues=issues,
        total_files=total,
        scanned_files=engine.files_scanned,
        scan_time_s=time.time() - start,
        model_used=llm_client.model if llm_client else "rules + static tools" if use_static else "rules",
        scan_mode=scan_mode if llm_client else "rules",
        lines_scanned=engine.lines_scanned,
    )
    report.baselined = baselined
    if any(i.rule_id.startswith(("ui/", "a11y/")) for i in issues):
        report.design_context = engine.theme.design_context()
    return report, engine


def _make_llm_client(model: str, base_url: str, api_key: str, required: bool = True):
    """Create a working LLM client, auto-picking an installed model. None if unreachable."""
    from fixmyslop.core.llm_client import LLMClient
    client = LLMClient(base_url=base_url, api_key=api_key, model=model)
    if client.is_available():
        if model and client.model != model:
            print_info(f"Model '{model}' not found — using '{client.model}'")
        return client
    if required:
        print_error(f"No LLM reachable at {base_url}. Start Ollama/LM Studio, or point --base-url at a "
                    "cloud endpoint (set FIXMYSLOP_API_KEY).")
        raise typer.Exit(2)
    return None


def _check_threshold(report, fail_on: str, config_fail_on: str) -> int:
    """Exit code for --fail-on (CLI flag wins over config)."""
    from fixmyslop.core.slop.engine import at_or_above
    threshold = (fail_on or config_fail_on or "").strip().lower()
    if not threshold or threshold == "none":
        return 0
    if threshold.upper() not in SEVERITY_RANK:
        print_error(f"Invalid --fail-on '{threshold}'. Use critical|high|medium|low|none.")
        return 2
    return 1 if at_or_above(report.issues, threshold) else 0


# ─── scan ───────────────────────────────────────────────────────────────────

@app.command()
def scan(
    paths: Optional[list[str]] = _PATHS,
    fmt: str = typer.Option(REPORT_FORMAT_TEXT, "--format", "-f", "--output", "-o",
                            help="text | compact (for agents) | markdown | html | json | csv | sarif | prompt | pdf"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Write the report to a file"),
    fail_on: str = typer.Option("", "--fail-on", help="Exit 1 if any issue ≥ this severity: critical|high|medium|low|none"),
    min_severity: str = typer.Option("low", "--min-severity", help="Hide issues below this severity"),
    only: Optional[list[str]] = typer.Option(None, "--only", help="Only these rule groups/ids: ui, a11y, slop, sec, deps, ui/ai-gradient…"),
    changed: bool = _CHANGED,
    base: Optional[str] = _BASE,
    no_static: bool = typer.Option(False, "--no-static", help="Skip ruff/bandit/semgrep (rules only)"),
    online: bool = typer.Option(False, "--online", help="Verify suspicious imports against PyPI/npm"),
    limit: int = typer.Option(60, "--limit", help="Max issues printed in text mode (0 = all)"),
    no_baseline: bool = typer.Option(False, "--no-baseline", help="Also show issues accepted in .fixmyslop-baseline.json"),
    open_report: bool = typer.Option(False, "--open", help="Write the interactive HTML report and open it in a browser"),
    fix: bool = typer.Option(False, "--fix", help="Apply safe deterministic fixes after scanning"),
    llm: bool = typer.Option(False, "--llm", help="Also run an LLM review pass (slow; local or cloud model)"),
    mode: str = typer.Option(DEFAULT_SCAN_MODE, "--mode", help="LLM review depth: turbo | deep"),
    model: str = _MODEL,
    base_url: str = _BASE_URL,
    api_key: str = _API_KEY,
    no_llm: bool = typer.Option(False, "--no-llm", hidden=True, help="Deprecated: LLM is off by default"),
    retries: int = typer.Option(2, "--retries", hidden=True),
):
    """Scan for AI slop: UI tells, code slop, security holes, hallucinated packages."""
    from fixmyslop.core.slop.config import load_config
    from fixmyslop.core.slop.fixers import fixable, apply_safe_fixes
    from fixmyslop.core.report_builder import ReportBuilder, relative_path
    from fixmyslop.core.agents import detect_agent, AGENTS

    fmt = fmt.lower().strip()
    if fmt == "md":
        fmt = "markdown"
    if save and fmt == REPORT_FORMAT_TEXT:
        fmt = _SUFFIX_FORMATS.get(Path(save).suffix.lower(), "markdown")
    if fmt not in _FORMATS:
        print_error(f"Unknown format '{fmt}'. Use one of: {', '.join(sorted(_FORMATS))}")
        raise typer.Exit(2)
    scan_mode = mode.strip().lower()
    if scan_mode not in {SCAN_MODE_TURBO, SCAN_MODE_DEEP}:
        print_error("Invalid --mode. Use 'turbo' or 'deep'.")
        raise typer.Exit(2)

    text_mode = fmt == REPORT_FORMAT_TEXT
    pending_update = None
    if text_mode:
        print_banner(APP_NAME, APP_VERSION)
        from fixmyslop.utils import update_check
        pending_update = update_check.start()                # PyPI check in the background, once a day

    client = None
    if llm and not no_llm:
        client = _make_llm_client(model, base_url, api_key)
        if text_mode:
            print_llm_warning(client.model, scan_mode)

    try:
        if text_mode and not llm:
            with console.status("Scanning…", spinner="dots"):
                report, engine = run_scan(paths, changed=changed, base=base, use_static=not no_static,
                                          llm_client=client, scan_mode=scan_mode, online=online,
                                          only=only, min_severity=min_severity,
                                          use_baseline=not no_baseline)
        else:
            report, engine = run_scan(paths, changed=changed, base=base, use_static=not no_static,
                                      llm_client=client, scan_mode=scan_mode, online=online, only=only,
                                      min_severity=min_severity, show_progress=text_mode,
                                      use_baseline=not no_baseline)
    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1) from None

    def rel(path: str) -> str:
        return relative_path(report, path)

    if fix:
        applied = apply_safe_fixes(report.issues)
        if applied:
            print_success(f"Applied {sum(applied.values())} safe fix(es) in {len(applied)} file(s). "
                          "Review with `git diff`.")
            report.issues = [i for i in report.issues if not i.applied]

    if open_report:
        import webbrowser
        from fixmyslop.core.agents import work_dir
        report_path = work_dir(Path(report.repo_path)) / "report.html"
        report_path.write_text(ReportBuilder().export(report, "html"), encoding="utf-8")
        webbrowser.open(report_path.as_uri())
        (print_success if text_mode else stderr_console().print)(f"Opened {report_path}")

    if text_mode:
        agent_key = detect_agent()
        target = " ".join(paths) if paths else "."
        print_slop_report(report, rel, limit=limit, fixable_count=len(fixable(report.issues)),
                          agent_hint=AGENTS[agent_key].name if agent_key else "", target=target)
        _print_update_notice(pending_update(1.0) if pending_update else None)
    elif not save:
        sys.stdout.write(ReportBuilder().export(report, fmt))
        sys.stdout.write("\n")

    if save:
        builder = ReportBuilder()
        if fmt == REPORT_FORMAT_PDF:
            builder.export_pdf(report, save)
        else:
            Path(save).write_text(builder.export(report, fmt), encoding="utf-8")
        (print_success if text_mode else stderr_console().print)(f"Report saved to {save}")

    code = _check_threshold(report, fail_on, load_config(Path(report.repo_path)).fail_on)
    if code:
        raise typer.Exit(code)


# ─── fix ────────────────────────────────────────────────────────────────────

@app.command()
def fix(
    paths: Optional[list[str]] = _PATHS,
    agent: str = typer.Option("auto", "--agent", "-a", help="auto | claude | codex | gemini | llm | none"),
    agent_cmd: Optional[str] = typer.Option(None, "--agent-cmd",
                                            help="Custom agent command; {brief} = brief path, {prompt} = instruction"),
    safe_only: bool = typer.Option(False, "--safe-only", "--safe", help="Only apply safe deterministic fixes"),
    no_safe: bool = typer.Option(False, "--no-safe", help="Skip safe deterministic fixes"),
    min_severity: str = typer.Option("low", "--min-severity", help="Only hand off issues ≥ this severity"),
    only: Optional[list[str]] = typer.Option(None, "--only", help="Only these rule groups/ids"),
    rounds: int = typer.Option(2, "--rounds", help="Agent fix → re-scan rounds"),
    changed: bool = _CHANGED,
    base: Optional[str] = _BASE,
    yes: bool = typer.Option(False, "--yes", "-y", help="Don't ask for confirmation"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Print the fix brief instead of running an agent"),
    model: str = _MODEL,
    base_url: str = _BASE_URL,
    api_key: str = _API_KEY,
):
    """Fix slop: safe auto-fixes first, then hand the rest to Claude Code / Codex / Gemini / any LLM."""
    from fixmyslop.core.slop.fixers import fixable, apply_safe_fixes
    from fixmyslop.core.slop.brief import build_fix_brief
    from fixmyslop.core.report_builder import relative_path
    from fixmyslop.core import agents as agent_mod

    print_banner(APP_NAME, APP_VERSION)

    def do_scan():
        with console.status("Scanning…", spinner="dots"):
            return run_scan(paths, changed=changed, base=base, only=only, min_severity=min_severity)

    try:
        report, _ = do_scan()
    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1) from None
    root = Path(report.repo_path)
    before_score, before_count = report.slop_score, len(report.issues)

    def rel(path: str) -> str:
        return relative_path(report, path)

    if not report.issues:
        print_success("Nothing to fix — the scan is clean.")
        return
    print_info(f"Found {before_count} issue(s) · slop score {report.slop_score:g} ({report.grade})")

    if not no_safe and fixable(report.issues):
        applied = apply_safe_fixes(report.issues, dry_run=dry_run)
        verb = "Would apply" if dry_run else "Applied"
        if applied:
            print_success(f"{verb} {sum(applied.values())} safe fix(es) in {len(applied)} file(s)")
            if not dry_run:
                report, _ = do_scan()

    if safe_only:
        _print_delta(before_score, before_count, report)
        return
    remaining = report.issues
    if not remaining:
        _print_delta(before_score, before_count, report)
        return

    target = " ".join(paths) if paths else "."
    brief = build_fix_brief(remaining, rel, targets=target, design_context=report.design_context)
    if dry_run:
        console.print()
        console.print(brief, markup=False, highlight=False)
        return

    chosen = agent.lower().strip()
    if agent_cmd:
        chosen = "custom"
    elif chosen == "auto":
        chosen = agent_mod.detect_agent() or "llm"
    if chosen == "none":
        path = agent_mod.write_brief(root, brief)
        print_info(f"Fix brief written to {path}. Paste it into your agent, or run:\n"
                   f"  claude \"Fix everything in {path.relative_to(root).as_posix()}\"")
        return
    if chosen not in agent_mod.AGENTS and chosen not in ("llm", "custom"):
        print_error(f"Unknown agent '{agent}'. Use auto, claude, codex, gemini, llm or none.")
        raise typer.Exit(2)

    files = sorted({i.file_path for i in remaining})
    if chosen == "llm":
        client = _make_llm_client(model, base_url, api_key, required=False)
        if client is None:
            path = agent_mod.write_brief(root, brief)
            print_warning("No coding agent (claude/codex/gemini) on PATH and no LLM endpoint reachable.")
            print_info(f"Fix brief written to {path} — hand it to any agent, or rerun with "
                       "--base-url/--api-key/--model pointing at an LLM.")
            raise typer.Exit(1)
        _fix_with_llm(client, remaining, rel, yes)
    else:
        name = "custom command" if chosen == "custom" else agent_mod.AGENTS[chosen].name
        if not yes and not typer.confirm(
                f"Hand {len(remaining)} issue(s) in {len(files)} file(s) to {name}? It will edit files in {root}",
                default=True):
            raise typer.Exit(0)
        for round_no in range(1, max(1, rounds) + 1):
            brief_path = agent_mod.write_brief(root, build_fix_brief(remaining, rel, targets=target,
                                                                     design_context=report.design_context))
            console.rule(f"[bold]{name}[/bold] · round {round_no} · {len(remaining)} issue(s)")
            try:
                code = agent_mod.run_agent(chosen, root, brief_path, custom_cmd=agent_cmd)
            except FileNotFoundError as e:
                print_error(str(e))
                raise typer.Exit(1) from None
            if code != 0:
                print_warning(f"{name} exited with code {code}")
            report, _ = do_scan()
            remaining = report.issues
            if not remaining:
                break
            print_info(f"{len(remaining)} issue(s) remain after round {round_no}")

    report, _ = do_scan()
    _print_delta(before_score, before_count, report)
    if report.issues:
        print_info("Remaining issues: run `fixmyslop scan` to review them.")


def _fix_with_llm(client, issues, rel, yes: bool):
    """Per-file whole-file rewrite through an OpenAI-compatible LLM, with validation and review."""
    from collections import defaultdict
    from rich.syntax import Syntax
    from fixmyslop.core import agents as agent_mod

    by_file = defaultdict(list)
    for issue in issues:
        by_file[issue.file_path].append(issue)
    print_info(f"Fixing {len(by_file)} file(s) with {client.model} (whole-file rewrite + validation)")
    for file_path, file_issues in sorted(by_file.items()):
        path = Path(file_path)
        with console.status(f"{rel(file_path)} · {len(file_issues)} issue(s)…", spinner="dots"):
            try:
                rewrite = agent_mod.llm_rewrite_file(client, path, file_issues)
            except Exception as e:
                print_warning(f"{rel(file_path)}: LLM request failed ({e})")
                continue
        if rewrite.rejected_reason:
            print_warning(f"{rel(file_path)}: rejected — {rewrite.rejected_reason}")
            continue
        console.print(Syntax(rewrite.diff, "diff", theme="ansi_dark", word_wrap=True))
        if yes or typer.confirm(f"Apply this change to {rel(file_path)}?", default=True):
            agent_mod.apply_rewrite(rewrite)
            print_success(f"Updated {rel(file_path)}")


def _print_delta(before_score: float, before_count: int, report):
    """Before/after summary."""
    after = report.slop_score
    style = "green" if after < before_score else "yellow"
    console.print(
        f"\n[bold]Slop score[/bold] {before_score:g} → [{style}]{after:g}[/{style}] ({report.grade})   "
        f"issues {before_count} → {len(report.issues)}\n"
    )


# ─── hook (Claude Code / Cursor / any agent) ────────────────────────────────

@app.command()
def hook(
    paths: Optional[list[str]] = typer.Argument(None, help="Files to check (default: read hook JSON from stdin)"),
    min_severity: str = typer.Option("", "--min-severity", help="Block only on issues ≥ this (default: config, MEDIUM)"),
    whole_file: bool = typer.Option(False, "--whole-file", help="Report issues anywhere in the file, not just edited lines"),
):
    """Agent hook: check files the agent just edited; exit 2 with feedback so it fixes them.

    Install with `fixmyslop init --claude`. Reads Claude Code's PostToolUse JSON on stdin.
    """
    from fixmyslop.core.slop.engine import SlopEngine, at_or_above
    from fixmyslop.core.slop.config import load_config
    from fixmyslop.utils.file_utils import read_file_safe
    from fixmyslop.utils.git_utils import git_root

    payload = {}
    if not paths and not sys.stdin.isatty():
        try:
            raw = sys.stdin.read()
            payload = json.loads(raw) if raw.strip() else {}
        except ValueError:
            payload = {}
    tool_input = payload.get("tool_input") or {}
    file_paths = list(paths or [])
    for key in ("file_path", "path", "notebook_path"):
        value = tool_input.get(key) or payload.get(key)
        if isinstance(value, str):
            file_paths.append(value)
    new_strings = _edited_snippets(tool_input) or _edited_snippets(payload)
    cwd = Path(payload.get("cwd") or Path.cwd())

    messages = []
    for raw_path in dict.fromkeys(file_paths):
        path = Path(raw_path)
        if not path.is_absolute():
            path = cwd / path
        if not path.is_file() or not is_scannable(path):
            continue
        root = git_root(path) or path.parent
        config = load_config(root)
        engine = SlopEngine(root, config=config)
        content = read_file_safe(path)
        if content is None:
            continue
        issues = engine.check_file(path, content)
        threshold = (min_severity or config.hook_min_severity or "MEDIUM")
        issues = at_or_above(issues, threshold)
        if new_strings and not whole_file:
            ranges = _line_ranges(content, new_strings)
            if ranges:
                issues = [i for i in issues if any(a <= i.line_start <= b for a, b in ranges)]
        if not issues:
            continue
        rel = engine.relpath(path)
        lines = [f"{rel}:"]
        for issue in sorted(issues, key=lambda i: i.line_start)[:15]:
            lines.append(f"  L{issue.line_start} [{issue.severity}] {issue.rule_id}: {issue.title} "
                         f"- fix: {issue.suggested_fix}")
        messages.append("\n".join(lines))

    if messages:
        try:  # agents read hook stderr as UTF-8; Windows defaults to the ANSI code page
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        err = stderr_console()
        err.print("FixMySlop found slop in the code you just wrote:\n" + "\n".join(messages) +
                  "\nFix these now. If one is a genuine false positive, add a "
                  "`fixmyslop-ignore[<rule-id>]` comment with a short reason.",
                  markup=False, highlight=False, soft_wrap=True)
        raise typer.Exit(2)


def _edited_snippets(data: dict) -> list[str]:
    """New text written by Write/Edit/MultiEdit (Claude Code) or edits (Cursor)."""
    snippets = []
    for key in ("new_string", "content"):
        if isinstance(data.get(key), str) and key == "new_string":
            snippets.append(data[key])
    for edit in data.get("edits") or []:
        if isinstance(edit, dict):
            value = edit.get("new_string") or edit.get("newString") or edit.get("new_text")
            if isinstance(value, str):
                snippets.append(value)
    return [s for s in snippets if s.strip()]


def _line_ranges(content: str, snippets: list[str]) -> list[tuple[int, int]]:
    """1-based line ranges where each edited snippet now lives in the file."""
    ranges = []
    for snippet in snippets:
        index = content.find(snippet)
        if index == -1:
            continue
        start = content.count("\n", 0, index) + 1
        ranges.append((start, start + snippet.count("\n")))
    return ranges


# ─── init ───────────────────────────────────────────────────────────────────

@app.command()
def init(
    path: str = typer.Argument(".", help="Project root"),
    claude: bool = typer.Option(False, "--claude", help="Claude Code: skill + MCP server + live hook + CLAUDE.md rules"),
    cursor: bool = typer.Option(False, "--cursor", help="Cursor: MCP server + .cursor/rules/fixmyslop.mdc"),
    agents_md: bool = typer.Option(False, "--agents", help="AGENTS.md rules (Codex, Gemini, Copilot, Jules…)"),
    github: bool = typer.Option(False, "--github", help="GitHub Action with PR annotations"),
    pre_commit: bool = typer.Option(False, "--pre-commit", help="pre-commit hook"),
    all_targets: bool = typer.Option(False, "--all", help="Everything above"),
    user: bool = typer.Option(False, "--user", help="Install the skill for ALL your projects (~/.claude/skills)"),
):
    """Set up FixMySlop in a project: config, agent skill + MCP tool, live agent hook, CI."""
    from fixmyslop.core import integrations as integ
    from fixmyslop.core.skill import install_skill

    if user:
        print_banner(APP_NAME, APP_VERSION)
        print_success(install_skill(Path.home() / ".claude"))
        print_info("Claude Code will now reach for FixMySlop in every project. For the MCP tool everywhere:\n"
                   "  claude mcp add --scope user fixmyslop -- fixmyslop mcp")
        return

    root = Path(path).resolve()
    if not root.is_dir():
        print_error(f"Not a directory: {root}")
        raise typer.Exit(1)
    print_banner(APP_NAME, APP_VERSION)
    print_success(integ.write_config(root))

    chosen = {
        "claude": claude or all_targets, "cursor": cursor or all_targets, "agents": agents_md or all_targets,
        "github": github or all_targets, "pre-commit": pre_commit or all_targets,
    }
    if not any(chosen.values()):
        for target in integ.detect_targets(root):
            chosen[target] = True
    installers = {
        "claude": integ.install_claude, "cursor": integ.install_cursor, "agents": integ.install_agents_md,
        "github": integ.install_github, "pre-commit": integ.install_pre_commit,
    }
    for name, enabled in chosen.items():
        if enabled:
            for line in installers[name](root):
                print_success(line)
    if not any(chosen.values()):
        print_info("Add integrations with: fixmyslop init --claude | --cursor | --agents | --github | "
                   "--pre-commit | --all   (or --user for every project)")
    console.print("\nNow run [cyan]fixmyslop scan[/cyan]\n")


# ─── baseline ───────────────────────────────────────────────────────────────

@app.command()
def baseline(
    path: str = typer.Argument(".", help="Project root"),
    no_static: bool = typer.Option(False, "--no-static", help="Skip ruff/bandit/semgrep"),
):
    """Accept every current issue as pre-existing; later scans only report new ones."""
    from fixmyslop.core.slop.baseline import BASELINE_FILE, write_baseline

    print_banner(APP_NAME, APP_VERSION)
    try:
        with console.status("Scanning…", spinner="dots"):
            report, engine = run_scan([path], use_static=not no_static, min_severity="info", use_baseline=False)
    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(1) from None
    written = write_baseline(Path(report.repo_path), report.issues, engine.relpath)
    print_success(f"Baselined {len(report.issues)} existing issue(s) in {written.name}")
    print_info(f"Commit {BASELINE_FILE}. From now on `fixmyslop scan` (and CI) only reports new slop; "
               "`--no-baseline` shows everything.")


# ─── mcp ────────────────────────────────────────────────────────────────────

@app.command()
def mcp():
    """Run as an MCP server over stdio (claude mcp add fixmyslop -- fixmyslop mcp)."""
    from fixmyslop.core.mcp_server import serve
    serve()


# ─── rules ──────────────────────────────────────────────────────────────────

@app.command()
def rules(rule_id: Optional[str] = typer.Argument(None, help="Show details for one rule")):
    """List every rule, or explain one."""
    from rich.table import Table
    from fixmyslop.core.slop import RULES
    from fixmyslop.core.slop.fixers import FIXERS

    if rule_id:
        found = RULES.get(rule_id)
        if not found:
            print_error(f"Unknown rule '{rule_id}'. Run `fixmyslop rules` for the list.")
            raise typer.Exit(1)
        console.print(f"\n[bold]{escape(found.id)}[/bold] — {escape(found.title)}  [dim]({found.severity}, {found.category})[/dim]\n")
        console.print(f"[bold]Why:[/bold] {escape(found.why)}\n")
        console.print(f"[bold]Fix:[/bold] {escape(found.fix)}\n")
        if found.id in FIXERS:
            console.print("[green]Auto-fixable[/green] with `fixmyslop fix --safe-only`\n")
        console.print(f"[dim]Silence one occurrence with a comment: {escape(f'fixmyslop-ignore[{found.id}]')}[/dim]\n")
        return
    table = Table(title=f"{APP_NAME} rules ({len(RULES)})", show_lines=False, header_style="bold")
    table.add_column("Rule", style="cyan", no_wrap=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("What it catches")
    table.add_column("Fix", justify="center")
    for item in sorted(RULES.values(), key=lambda r: (r.id.split("/")[0], SEVERITY_RANK.get(r.severity, 9), r.id)):
        table.add_row(item.id, item.severity, item.title, "auto" if item.id in FIXERS else "")
    console.print(table)


# ─── misc ───────────────────────────────────────────────────────────────────

@app.command()
def models(
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", "-b"),
):
    """List available models on running local LLM backends."""
    from fixmyslop.core.model_detector import ModelDetector
    detector = ModelDetector()
    backends = detector.detect_running_backends()
    if not backends:
        print_error("No running backends found. Start Ollama or llama.cpp server first.")
        raise typer.Exit(1)
    for backend, model_list in backends.items():
        typer.echo(f"\n{backend}:")
        for m in model_list:
            typer.echo(f"  - {m}")


@app.command()
def ui(
    path: Optional[str] = typer.Argument(None, help="Project folder to open (default: current directory)"),
    port: int = typer.Option(7777, "--port", help="Port on 127.0.0.1 (falls back to a free one if busy)"),
    no_open: bool = typer.Option(False, "--no-open", help="Don't open a browser tab"),
):
    """Open the FixMySlop app in your browser (local only)."""
    from fixmyslop.web.server import serve
    root = Path(path or ".").resolve()
    if not root.is_dir():
        print_error(f"Not a folder: {root}")
        raise typer.Exit(1)
    serve(root, port=port, open_browser=not no_open)


@app.command(hidden=True)
def gui(
    path: Optional[str] = typer.Argument(None),
    port: int = typer.Option(7777, "--port"),
):
    """Alias for `fixmyslop ui`."""
    ui(path=path, port=port, no_open=False)


@app.command()
def version():
    """Show FixMySlop version (and whether a newer one is out)."""
    from fixmyslop.utils import update_check
    typer.echo(f"{APP_NAME} v{APP_VERSION}")
    _print_update_notice(update_check.available_update())


def _print_update_notice(latest: Optional[str]) -> None:
    """One dim line when a newer version is on PyPI (set FIXMYSLOP_NO_UPDATE_CHECK=1 to turn off)."""
    if latest:
        from rich.markup import escape
        from fixmyslop.utils import update_check
        console.print(f"[dim]{escape(update_check.notice(latest))}[/dim]")


# Kept for backwards compatibility with code importing the old helper.
__all__ = ["app", "run_scan", "print_report"]


if __name__ == "__main__":
    app()

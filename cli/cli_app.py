"""
FixMySlop CLI — fully functional without the GUI.
Run: python -m cli.cli_app scan ./myrepo --model qwen2.5-coder:7b
"""
import typer
from pathlib import Path
from typing import Optional
from macros import (
    APP_NAME, APP_VERSION, DEFAULT_MODEL, DEFAULT_BASE_URL, DEFAULT_API_KEY,
    SCAN_MODE_TURBO, SCAN_MODE_DEEP, DEFAULT_SCAN_MODE,
)
from cli.cli_output import (
    print_banner, print_report, print_error, print_success,
    print_llm_warning, print_analyzing, print_scan_estimate,
)

app = typer.Typer(
    name="fixmyslop",
    help=f"{APP_NAME} — AI-powered code auditor and fixer.",
    add_completion=True,
)


@app.command()
def scan(
    path: str = typer.Argument(".", help="Repo or folder to scan"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", "-m", help="Model tag"),
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", "-b", help="Backend API URL"),
    api_key: str = typer.Option(DEFAULT_API_KEY, "--api-key", help="API key (use 'ollama' for Ollama)"),
    fix: bool = typer.Option(False, "--fix", help="Auto-apply suggested fixes"),
    output: str = typer.Option("markdown", "--output", "-o", help="Report format: markdown|html|json|csv|pdf"),
    save: Optional[str] = typer.Option(None, "--save", "-s", help="Save report to file"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Static analysis only, skip LLM"),
    retries: int = typer.Option(2, "--retries", help="Max LLM retries per file on parse failure"),
    mode: str = typer.Option(
        DEFAULT_SCAN_MODE,
        "--mode",
        help="Scan mode: turbo (fast, top issues) or deep (thorough)",
    ),
):
    """Scan a codebase for AI debt, bugs, and security issues."""
    from core.scanner import Scanner
    from core.analyzer import Analyzer
    from core.llm_client import LLMClient
    from core.report_builder import ReportBuilder
    from core.issue import Issue
    from utils.system_info import estimate_scan_time, _detect_gpu
    import time

    print_banner(APP_NAME, APP_VERSION)
    repo_path = Path(path).resolve()

    if not repo_path.exists():
        print_error(f"Path not found: {repo_path}")
        raise typer.Exit(1)

    scan_mode = mode.strip().lower()
    if scan_mode not in {SCAN_MODE_TURBO, SCAN_MODE_DEEP}:
        print_error("Invalid --mode. Use 'turbo' or 'deep'.")
        raise typer.Exit(1)

    client = None
    use_llm = not no_llm
    if not no_llm:
        client = LLMClient(
            base_url=base_url,
            api_key=api_key,
            model=model
        )
        if not client.is_available():
            from core.model_detector import get_best_available_model
            best = get_best_available_model(base_url)
            if best:
                typer.echo(
                    f"[INFO] Model '{model}' not found "
                    f"— auto-switching to '{best}'"
                )
                client = LLMClient(
                    base_url=base_url,
                    api_key=api_key,
                    model=best
                )
            else:
                print_error(
                    f"No LLM backend running at {base_url}.\n"
                    "Start Ollama first or use --no-llm flag."
                )
                raise typer.Exit(1)
        elif client.model != model:
            typer.echo(
                f"[INFO] Auto-switched model to '{client.model}'"
            )

    active_model = client.model if use_llm and client else model
    if use_llm:
        print_llm_warning(active_model, scan_mode)

    scanner = Scanner(str(repo_path))
    analyzer = Analyzer(
        llm_client=client,
        use_static_tools=True,
        max_retries=retries,
        scan_mode=scan_mode,
    )
    builder = ReportBuilder()
    all_issues: list[Issue] = []

    total = scanner.file_count

    # Show scan estimate for LLM mode
    if use_llm:
        gpu_info = _detect_gpu()
        # Calculate avg file size for chunking estimate
        avg_chars = 3000
        try:
            file_sizes = [f.stat().st_size for f in scanner._collect_files()]
            if file_sizes:
                avg_chars = sum(file_sizes) // len(file_sizes)
        except Exception:
            pass
        estimate = estimate_scan_time(
            total,
            active_model,
            gpu_info["vram_gb"],
            avg_chars,
            scan_mode=scan_mode,
            use_llm=use_llm,
        )
        print_scan_estimate(estimate, total, active_model)

    start = time.time()

    with typer.progressbar(length=total, label="Scanning") as progress:
        for file_path, content in scanner.scan():
            if use_llm:
                elapsed = time.time() - start
                print_analyzing(file_path.name, active_model, progress.pos + 1, total, elapsed)
            issues = analyzer.analyze_file(file_path, content)
            all_issues.extend(issues)
            progress.update(1)

    report = builder.build(
        repo_path=str(repo_path),
        issues=all_issues,
        total_files=total,
        scanned_files=total,
        scan_time_s=time.time() - start,
        model_used=client.model if use_llm and client else "static-only",
        scan_mode=scan_mode,
    )
    print_report(report)

    if save:
        if output == "pdf":
            builder.export_pdf(report, save)
        else:
            exported = builder.export(report, fmt=output)
            Path(save).write_text(exported, encoding="utf-8")
        print_success(f"Report saved to {save}")


@app.command()
def models(
    base_url: str = typer.Option(DEFAULT_BASE_URL, "--base-url", "-b"),
):
    """List available models on the running backend."""
    from core.model_detector import ModelDetector
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
def version():
    """Show FixMySlop version."""
    typer.echo(f"{APP_NAME} v{APP_VERSION}")


if __name__ == "__main__":
    app()

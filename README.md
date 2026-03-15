# FixMySlop

> **AI wrote your code. FixMySlop fixes it.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)]()

**FixMySlop** is a fully open-source, cross-platform desktop application that scans codebases (especially AI-generated code) for bugs, security vulnerabilities, technical debt, bad patterns, and missing tests. It generates a detailed audit report, suggests LLM-powered fixes with code diffs, and can optionally apply them.

**100% local.** No cloud, no subscriptions, no API key required after setup. Uses any Ollama/llama.cpp/vLLM compatible model.

---

## Features

- ⚡ **Turbo + Deep Modes** — Choose fast top-issue scanning or thorough full analysis
- 🔍 **Deep Code Scanning** — Walks your repo, respects `.gitignore`, analyzes every file
- 🛡️ **Security Analysis** — OWASP Top 10, injection, auth issues, exposed secrets (via Bandit + LLM)
- 🧹 **AI Smell Detection** — Hallucinated imports, broad try/except, missing validation
- 📊 **Slop Score** — 0-100 debt score showing overall code quality
- 🔧 **LLM-Powered Fixes** — Generates unified diff patches with one click
- 📄 **Export Reports** — Markdown, HTML, or JSON
- 🎨 **Dark & Light Themes** — Premium PyQt5 GUI with smooth UX
- 💻 **Full CLI** — Works without GUI via `fixmyslop scan ./myrepo`
- 🤖 **Auto Model Fallback** — Automatically switches to an installed backend model if configured model is missing
- 🪟 **Windows-safe CLI Output** — Handles PowerShell encoding edge cases gracefully
- 🏠 **100% Local** — Ollama, llama.cpp, vLLM — your data never leaves your machine

---

## Installation

### Prerequisites

- **Python 3.10+**
- **Ollama** (or any OpenAI-compatible local backend) — [Install Ollama](https://ollama.ai)

### Quick Start

```bash
# Clone the repo
git clone https://github.com/MrSpideyNihal/FixMySlop.git
cd FixMySlop

# Install dependencies
pip install -r requirements.txt

# Pull a model (using Ollama, example)
ollama pull qwen2.5-coder:3b

# Launch GUI
python main.py

# Or use CLI
python main.py scan ./your-project --mode turbo
```

FixMySlop can auto-detect a working local model from your backend,
so manual model configuration is optional in many setups.

### Optional Tools

For enhanced static analysis, install these tools:

```bash
pip install ruff bandit    # Included in requirements.txt
pip install semgrep        # Optional, heavyweight
```

---

## Usage

### GUI Mode

```bash
python main.py
```

This launches the full desktop application with:
- **Home** — Quick-start actions and recent scans
- **Scan** — Select folder, choose model, configure analysis
- **Report** — View issues sorted by severity with file tree
- **Fix** — Generate and apply LLM-powered fixes with diff viewer
- **Settings** — Configure backend, model, theme

### CLI Mode

```bash
# Scan a repository
python main.py scan ./myproject

# Turbo mode (fast, top issues)
python main.py scan ./myproject --mode turbo

# Deep mode (thorough)
python main.py scan ./myproject --mode deep

# Scan with a specific model
python main.py scan ./myproject --model qwen2.5-coder:3b --mode turbo

# Static analysis only (no LLM)
python main.py scan ./myproject --no-llm

# Save report to file
python main.py scan ./myproject --save report.md --output markdown

# List available models
python main.py models

# Show version
python main.py version
```

### Scan Modes

| Mode | Focus | Typical per-file estimate |
|------|-------|---------------------------|
| `turbo` | Top critical issues quickly | `~20-40s per file` |
| `deep` | Full, thorough issue discovery | `~15-30s per file` |
| `--no-llm` | Static analysis only | `< 1s per file` |

Notes:
- Turbo prioritizes highest-impact findings and keeps output concise.
- Deep is intended for complete analysis and broader issue coverage.
- Exact times vary by backend model, machine load, and file complexity.

---

## Configuration

Config file: `~/.fixmyslop/config.yaml`

```yaml
model: ""
base_url: http://localhost:11434/v1
api_key: ollama
temperature: 0.2
theme: dark
use_ruff: true
use_bandit: true
use_semgrep: false
auto_backup: true
```

If `model` is empty, FixMySlop attempts to auto-select the best available model from your running local backend.

---

## Supported Languages

Python, JavaScript, TypeScript, Go, Rust, Java, C++, C, C#, Ruby, PHP, Swift, Kotlin

---

## Architecture

```
FixMySlop/
├── macros.py           # All constants (single source of truth)
├── main.py             # Entry point (GUI / CLI router)
├── core/               # Pure logic — NO UI imports
│   ├── scanner.py      # Repo walker
│   ├── analyzer.py     # Static + LLM analysis orchestrator
│   ├── llm_client.py   # OpenAI-compatible API client
│   ├── fix_engine.py   # LLM fix generator
│   └── ...
├── ui/                 # PyQt5 GUI
│   ├── panels/         # Home, Scan, Report, Fix, Settings, About
│   ├── widgets/        # Reusable components
│   └── assets/         # QSS themes, icons, fonts
├── cli/                # Standalone CLI (works without PyQt5)
├── utils/              # Shared helpers
└── tests/              # Full test suite
```

**Key design rules:**
- `core/` never imports from `ui/` — logic and UI are fully separated
- All constants live in `macros.py` — never hardcoded
- All heavy work runs in `QThread` — UI never freezes
- Cross-platform: `pathlib.Path` everywhere, no OS-specific code

---

## Running Tests

```bash
pytest tests/ -v
```

---

## License

MIT — free forever, fully open source.

---



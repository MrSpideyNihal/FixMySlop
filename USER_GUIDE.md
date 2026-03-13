# FixMySlop — User Guide

> **AI wrote your code. FixMySlop fixes it.**

---

## 1. What is FixMySlop?

FixMySlop is a desktop application that scans your codebases for bugs, security vulnerabilities, technical debt, and AI-generated code smells. It combines **static analysis tools** (Ruff, Bandit, Semgrep) with **local LLM deep analysis** to find issues that traditional linters miss.

**Key highlights:**
- 🔍 Deep code scanning with AI-powered analysis
- 🛡️ Security checks (OWASP Top 10, injection, exposed secrets)
- 📊 Slop Score — a single 0-100 number showing code health
- 🔧 One-click LLM-powered fix generation with diff previews
- 💻 Works as both a GUI app and CLI tool
- 🏠 Runs **100% locally** — your code never leaves your machine

---

## 2. Requirements

| Requirement | Details |
|---|---|
| **Python** | 3.10 or newer |
| **LLM Backend** | [Ollama](https://ollama.ai), llama.cpp, or vLLM |
| **OS** | Windows, macOS, or Linux |
| **RAM** | 8 GB minimum (16 GB recommended for larger models) |

---

## 3. Installation

```bash
# Clone the repo
git clone https://github.com/nihalrodge/fixmyslop.git
cd fixmyslop

# Install Python dependencies
pip install -r requirements.txt

# Install and pull an LLM model (using Ollama)
# Visit https://ollama.ai to install Ollama first
ollama pull qwen2.5-coder:7b
```

That's it — you're ready to scan.

---

## 4. Quick Start — CLI

Open a terminal and run:

```bash
# Scan a folder (static analysis + LLM)
python main.py scan ./your-project --model qwen2.5-coder:7b

# Scan without LLM (fast, static-only)
python main.py scan ./your-project --no-llm

# Scan a single file
python main.py scan buggy_code.py --no-llm

# Save report to a file
python main.py scan ./your-project --save report.md --output markdown

# List available models on your backend
python main.py models

# Check version
python main.py version
```

---

## 5. Quick Start — GUI

1. **Launch** — Run `python main.py` (no arguments)
2. **Home** — You'll see the welcome screen with quick-action cards
3. **Scan** — Click "Scan Repository" or navigate to the Scan tab
   - Click **Browse** to select a folder
   - Choose your **LLM model** from the dropdown (click Refresh to load models)
   - Check/uncheck analysis tools (Ruff, Bandit, Semgrep, LLM)
   - Click **Start Scan**
4. **Report** — After scanning, you'll land on the Report tab
   - Left side: file tree with issue counts per file
   - Right side: expandable issue cards sorted by severity
   - Use the severity filter dropdown to focus on specific levels
5. **Fix** — Click "Generate Fix" on any issue to get an LLM-suggested fix
   - Review the side-by-side diff
   - Click **Apply Fix** to patch the file (a `.bak` backup is created)
   - Click **Reject** to discard the fix
6. **Settings** — Configure your backend URL, model, theme, and preferences

---

## 6. Understanding the Slop Score

The **Slop Score** is a 0-100 number that represents the overall "debt level" of your codebase.

| Score | Meaning |
|-------|---------|
| **0-20** | 🟢 Clean — minimal issues, well-maintained code |
| **21-40** | 🟡 Acceptable — some debt, but manageable |
| **41-60** | 🟠 Concerning — significant issues need attention |
| **61-80** | 🔴 Poor — high debt, security risks likely present |
| **81-100** | 🚨 Critical — immediate remediation recommended |

The score is calculated from issue count, severity weights, and file coverage.

---

## 7. Understanding Severity Levels

| Level | Color | Meaning | Example |
|-------|-------|---------|---------|
| **CRITICAL** | 🔴 Red | Exploitable vulnerability or crash | SQL injection, RCE |
| **HIGH** | 🟠 Orange | Serious bug or security risk | Unsafe deserialization, `eval()` |
| **MEDIUM** | 🟡 Yellow | Code smell or moderate risk | Broad `except:`, missing validation |
| **LOW** | 🔵 Cyan | Minor issue or style concern | Missing docstring, unused import |
| **INFO** | ⚪ Gray | Informational / suggestion | Naming convention, refactor hint |

---

## 8. Supported Languages

FixMySlop can scan files with these extensions:

| Language | Extensions |
|----------|-----------|
| Python | `.py` |
| JavaScript | `.js`, `.jsx` |
| TypeScript | `.ts`, `.tsx` |
| Go | `.go` |
| Rust | `.rs` |
| Java | `.java` |
| C/C++ | `.c`, `.cpp` |
| C# | `.cs` |
| Ruby | `.rb` |
| PHP | `.php` |
| Swift | `.swift` |
| Kotlin | `.kt` |

> **Note:** Static tools (Ruff, Bandit) are Python-specific. For other languages, LLM analysis provides the primary coverage.

---

## 9. How to Configure Your LLM Model

### Option A: Settings Panel (GUI)

Go to **Settings → LLM Backend** and configure:
- **Backend**: Select Ollama, llama.cpp, or vLLM
- **API URL**: Usually `http://localhost:11434/v1` for Ollama
- **Model**: Enter the model tag (e.g., `qwen2.5-coder:7b`)
- **Temperature**: Lower = more deterministic (0.2 recommended)

### Option B: Config File

Edit `~/.fixmyslop/config.yaml`:

```yaml
model: qwen2.5-coder:7b
base_url: http://localhost:11434/v1
api_key: ollama
temperature: 0.2
```

### Option C: CLI Flags

```bash
python main.py scan ./project --model codellama:13b --base-url http://localhost:11434/v1
```

### Recommended Models

| Model | Size | Best For |
|-------|------|----------|
| `qwen2.5-coder:7b` | ~4 GB | Good balance of speed and quality |
| `codellama:13b` | ~7 GB | Stronger analysis, slower |
| `llama3:latest` | ~4 GB | General purpose, decent code understanding |
| `deepseek-coder:6.7b` | ~4 GB | Fast, good for Python |

---

## 10. FAQ

### Q: Do I need an internet connection?
**No.** FixMySlop runs 100% locally. Once you've downloaded your model, everything works offline.

### Q: Why is LLM scanning slow?
LLM analysis sends each file to your local model for deep review. Speed depends on your hardware (GPU helps significantly). Use `--no-llm` for quick static-only scans when you need speed.

### Q: Can I scan non-Python projects?
**Yes.** FixMySlop supports 13 languages. However, the static tools (Ruff, Bandit) only work on Python. For other languages, LLM analysis provides the primary issue detection.

### Q: Will applying a fix break my code?
FixMySlop always creates a `.bak` backup before applying any fix. If something goes wrong, your original file is preserved as `filename.py.bak` in the same directory.

### Q: How do I switch between dark and light themes?
Go to **Settings → Appearance → Theme** and select your preference. The change applies immediately.

---

*Made by **Nihal Rodge** — FixMySlop is MIT licensed.*

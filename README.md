# FixMySlop

[![PyPI](https://img.shields.io/pypi/v/fixmyslop)](https://pypi.org/project/fixmyslop/)
[![npm](https://img.shields.io/npm/v/fixmyslop)](https://www.npmjs.com/package/fixmyslop)
[![CI](https://github.com/MrSpideyNihal/FixMySlop/actions/workflows/python-package.yml/badge.svg)](https://github.com/MrSpideyNihal/FixMySlop/actions/workflows/python-package.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![FixMySlop grade](https://fix-my-slop.vercel.app/badge/MrSpideyNihal/FixMySlop)](https://fix-my-slop.vercel.app/r/MrSpideyNihal/FixMySlop)

**The slop linter for the AI-agent era.** FixMySlop catches the things AI coding agents get wrong — the
purple-gradient landing page, the `// ... existing code ...` that silently deleted half a file, the npm
package that doesn't exist, the OpenAI key in `NEXT_PUBLIC_` — in milliseconds, without an LLM. Then it
hands a precise fix list to the agent you already use (Claude Code, Codex, Cursor, Gemini) and re-scans to
prove it's fixed.

**Try it without installing:** paste any public GitHub repo at **[fix-my-slop.vercel.app](https://fix-my-slop.vercel.app)**.

![fixmyslop scan output: 31 issues across UI slop, accessibility, code slop, security and dependencies, slop score 100, grade F](screenshots/cli.svg)

## Why this exists when you already have a frontier model

Frontier models are great at fixing slop and bad at noticing their own. They write the purple gradient
because it's the statistical default; they elide code when an edit gets long; they import packages that
sound right. FixMySlop is the other half of the loop:

| | Your agent | FixMySlop |
|---|---|---|
| Speed | seconds–minutes per review | ~0.5s for a 10k-line repo |
| Determinism | different answer each run | same input → same findings, stable rule IDs |
| Cost | tokens on every review | free, offline, no API key |
| Good at | *fixing* code | *finding* the tells, every time, in CI |

So: FixMySlop **finds**, your agent **fixes**, FixMySlop **verifies**. The old "local LLM reviews your code"
mode still exists (`--llm`), but it's optional — the rules engine is the product.

## Install

```bash
pipx install fixmyslop            # or: pip install fixmyslop
npx fixmyslop scan                # JavaScript projects: no install step (runs via uvx/pipx)
```

`npx` needs Python 3.10+ plus [uv](https://docs.astral.sh/uv/) or pipx on the machine; it always runs the
FixMySlop version that matches the npm package.

Optional: `pip install "fixmyslop[analysis]"` adds Ruff + Bandit findings for Python.

## 30 seconds

```bash
fixmyslop scan                    # whole repo
fixmyslop scan --changed          # only what changed vs main (+ uncommitted)
fixmyslop baseline                # existing codebase: accept today's issues, report only new ones
fixmyslop ui                      # the app: browse issues, apply fixes, copy prompts for your agent
fixmyslop scan --open             # one-off interactive HTML report
fixmyslop fix --safe-only         # behavior-preserving auto-fixes
fixmyslop fix                     # safe fixes → hand the rest to your agent → re-scan
fixmyslop init --claude           # make Claude Code check its own work, live
```

Try it on the bundled demos: `fixmyslop ui examples/slop-app` (classic purple-gradient slop) and
`fixmyslop scan examples/slop-2026` (the newer dark, glowing, aphorism-heavy look).

## For AI agents

If a user asks you to set up or run FixMySlop, these are the exact commands (all exist in the CLI; `fixmyslop <command> --help` shows every option):

```bash
pip install fixmyslop                  # needs internet access to PyPI (sandboxes without network can't install it)
fixmyslop init --all                   # config + agent rules + skill + MCP + Claude hook + CI + pre-commit
fixmyslop scan . -f compact            # one line per issue, token-efficient
fixmyslop scan . -f prompt             # full fix brief: issues, exact fixes, the project's design tokens
fixmyslop fix . --safe-only            # behavior-preserving auto-fixes only
fixmyslop scan . --fail-on medium      # exit 1 while CRITICAL/HIGH/MEDIUM issues remain
fixmyslop rules <rule-id>              # why a rule exists and how to fix it
```

Loop: scan → fix what the brief says → re-scan until clean. Report the before/after slop score to the user.
Supported files: Python, JS/TS, JSX/TSX, Vue, Svelte, Astro, HTML, CSS/SCSS/Less (full rule set), plus Go, Java, Kotlin,
Groovy, C#, Swift, PHP, Scala, Dart, Rust, C/C++ and Ruby (language-specific and general checks). Details:
[Supported languages](#supported-languages).

## On the web

**[fix-my-slop.vercel.app](https://fix-my-slop.vercel.app)**: paste a public GitHub repository and get the report,
with PDF and Markdown downloads and a README badge (`/badge/<owner>/<repo>`). It downloads the code, reads it,
and deletes it; nothing is executed. The source is in [site/](site/) and deploys to Vercel as-is: see
[site/README.md](site/README.md).

## The app

`fixmyslop ui` opens FixMySlop in your browser. It runs only on your machine (127.0.0.1, per-session token,
no external requests) and uses the same engine as the CLI:

- **Overview**: slop score with the change since your last scan, what to fix first, and three steps to fix it
- **Issues**: filter and search every finding, see the exact code, and copy a fix prompt for your agent
- **Rules**: turn rules on or off for the project (saved to `.fixmyslop.yml`)
- **Setup**: one-click install for Claude Code, Cursor, AGENTS.md, GitHub Actions and pre-commit

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="screenshots/app-overview-dark.png">
  <img alt="FixMySlop app overview: slop score 100, grade F, three fix steps, issues by category and the most affected files" src="screenshots/app-overview-light.png">
</picture>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="screenshots/app-issues-dark.png">
  <img alt="FixMySlop issues view: findings grouped by file, with the explanation, highlighted code and the exact fix for the selected issue" src="screenshots/app-issues-light.png">
</picture>

## What it catches

**UI slop** — the visual and copy tells of generated frontends (React, Vue, Svelte, Astro, HTML, CSS, Tailwind)

| Rule | Catches |
|---|---|
| `ui/ai-gradient` | `from-purple-600 to-pink-500`, `#667eea → #764ba2` |
| `ui/gradient-text` | `bg-clip-text text-transparent` headlines |
| `ui/emoji-icons` | 🚀 ⚡ ✨ used as feature icons |
| `ui/marketing-slop` | "Revolutionize", "Unlock the power of", "seamless", "next-gen" |
| `ui/fake-social-proof` | "10,000+ happy users", "99.9% uptime", testimonials from "Sarah Johnson" |
| `ui/placeholder-copy` | Lorem ipsum, "Your Company Name" |
| `ui/glassmorphism`, `ui/blur-blobs`, `ui/hover-scale`, `ui/heavy-shadows`, `ui/gimmick-animation` | the template aesthetic |
| `ui/rainbow-palette`, `ui/palette-sprawl`, `ui/arbitrary-color`, `ui/arbitrary-values` | no design system: 9 accent hues, 40 hex codes, `w-[347px]` |
| `ui/default-font`, `ui/z-index-war`, `ui/important-abuse` | Inter-everywhere, `z-index: 9999`, `!important` piles |
| `ui/aphorism-copy` | the newer AI voice: "Make space for what matters", "Intentional by design", "Less X. More Y." |
| `ui/neon-glow`, `ui/two-tone-headline`, `ui/eyebrow-labels` | glowing orbs in any hue, accent-colored second line, uppercase micro-labels on every section |
| `ui/fake-chart` | sparklines drawn from hard-coded heights, often right next to a "0" |

**Accessibility** — `a11y/img-alt`, `a11y/clickable-div`, `a11y/icon-button`, `a11y/focus-removed`, `a11y/dead-link`

**Code slop** — `slop/elided-code` (`// ... existing code ...`), `slop/placeholder-impl` ("in a real app you would…"),
`slop/stub-function`, `slop/swallowed-exception`, `slop/empty-catch`, `slop/bare-except`, `slop/narrating-comment`,
`slop/step-comments`, `slop/debugger`, `slop/console-log`, `slop/emoji-log`, `slop/ts-any`, `slop/ts-ignore`,
`slop/blanket-suppression`, `slop/placeholder-credential`, `slop/ai-voice`

**Backend** — `slop/empty-test` (tests that assert nothing — pytest, Jest, Vitest, Mocha), `slop/duplicate-function`
(the same body copy-pasted across files, names ignored), `slop/pointless-wrapper`, `slop/catch-rethrow`,
Go `slop/ignored-error` (`if err != nil { return nil }`), Java/Kotlin `slop/print-stacktrace`, and empty `catch {}`
in JS/TS, Java, C#, Kotlin, Swift, PHP and Dart

**Dependencies** — `deps/phantom-import`: imports that aren't stdlib, local, declared, or installed (hallucinated
packages are what [slopsquatting](https://en.wikipedia.org/wiki/Slopsquatting) attacks register).
`--online` confirms against PyPI / npm. `deps/undeclared-import`: works on your machine, breaks in CI.

**Security** — `sec/leaked-key` (OpenAI/Anthropic/AWS/GitHub/Stripe/Google key formats, private keys — always
redacted in output), `sec/env-secret` (a `.env` with real keys that git will commit), `sec/public-env-secret` (`NEXT_PUBLIC_*SECRET*`, `VITE_*OPENAI*`), `sec/hardcoded-credential`,
`sec/sql-injection`, `sec/cors-wildcard`, `sec/tls-disabled`, `sec/raw-html`, `sec/eval`

**Docs** — READMEs and Markdown docs. Checked against the real repo: `docs/missing-script` (`npm run test` when
package.json has no `test` script), `docs/dead-link` (links and images to files that don't exist, a LICENSE that
isn't there), `docs/placeholder` (`git clone https://github.com/yourusername/...`), `docs/chatbot-residue` <!-- fixmyslop-ignore[docs/placeholder]: example -->
("Certainly! Here's a comprehensive README", "[Insert screenshot here]"). Style: `docs/emoji-headings`
(`## 🚀 Features`, `## 🛠️ Tech Stack`) and `docs/hype-copy` ("seamless", "cutting-edge", "Made with ❤️").

Plus Ruff, Bandit and Semgrep findings when installed. `fixmyslop rules` lists everything;
`fixmyslop rules ui/ai-gradient` explains one.

## Supported languages

Depth varies by language. Frontend and Python/JS/TS backends get the full rule set; other languages get the
checks that look the same in any syntax.

| Language | Files | What runs |
|---|---|---|
| **React, Next.js, Vue, Svelte, Astro, HTML** | `.jsx` `.tsx` `.vue` `.svelte` `.astro` `.html` `.htm` | Everything: all UI and accessibility rules (Tailwind classes, inline styles and `<style>` blocks), plus the JS/TS checks below for the script parts |
| **CSS** | `.css` `.scss` `.sass` `.less` | UI style rules: AI gradients, glassmorphism, glow, shadows, default fonts, z-index wars, `!important`, palette sprawl (CSS variables count as design tokens) |
| **JavaScript, TypeScript** | `.js` `.mjs` `.cjs` `.ts` `.mts` `.cts` | Code slop, `any` / `@ts-ignore`, empty tests (Jest, Vitest, Mocha, `node:test`, chai), duplicate functions, catch-and-rethrow, hallucinated or undeclared npm imports, security |
| **Python** | `.py` | Code slop, stub functions, swallowed exceptions, bare `except`, empty tests (pytest, unittest), duplicate functions, pointless wrappers, hallucinated or undeclared PyPI imports, security. Optional Ruff and Bandit |
| **Go** | `.go` | Ignored errors (`if err != nil { return nil }`) plus the general checks |
| **Java, Kotlin, Groovy** | `.java` `.kt` `.kts` `.groovy` | Empty `catch`, `printStackTrace()`-only handlers, plus the general checks |
| **C#, Swift, PHP, Scala, Dart** | `.cs` `.swift` `.php` `.scala` `.dart` | Empty `catch` plus the general checks |
| **Rust, C, C++, Ruby** | `.rs` `.c` `.h` `.cpp` `.hpp` `.rb` | The general checks |
| **Env files** | `.env` `.env.local` `.env.production` ... | Real secrets in an env file git doesn't ignore (already committed, or the next `git add .` will be), leaked key formats, secrets behind `NEXT_PUBLIC_`/`VITE_` prefixes. A properly ignored `.env` and `.env.example` placeholders stay quiet |
| **Markdown docs** | `.md` `.mdx` `.markdown` | The docs rules above, on READMEs, root-level docs and anything under `docs/` or `.github/`. Blog posts and other Markdown content are left alone |

**General checks** (every language above): elided code (`// ... existing code ...`), placeholder
implementations, narrating and step-by-step comments, chatbot voice in comments, leaked keys and hardcoded
credentials, SQL built from strings, disabled TLS verification, CORS `*`, blanket lint suppression.

Package checks (`deps/*`) read `package.json`, `requirements*.txt`, `pyproject.toml`, `setup.py`/`setup.cfg`,
`Pipfile` and `environment.yml`; `go.mod`, `Cargo.toml` and Maven/Gradle aren't checked yet. Minified bundles,
generated files, lockfiles and `node_modules`/`.venv`/`dist` are skipped.

## What it can't catch

FixMySlop finds the *tells* that AI-written code leaves behind. It doesn't understand what your code is meant to
do, so it won't catch:

- logic that is wrong but looks normal, or a fix for the symptom instead of the cause
- a test that asserts the wrong thing (it only catches tests that assert nothing)
- a change much bigger than the task needed, or a rewrite of a helper that already existed elsewhere
- design quality beyond the patterns above: it can tell you the page has the AI look, not that the layout is good

A clean scan means "none of the known tells", not "this code is correct". Keep code review and tests; use
FixMySlop so reviewers stop spending their time on the obvious stuff.

## Use it with your agent

### Claude Code

```bash
fixmyslop init --claude
```

This installs four things, all idempotent:

- a **skill** (`.claude/skills/fixmyslop/SKILL.md`) so Claude reaches for FixMySlop on its own when it builds UI or finishes a task
- an **MCP server** in `.mcp.json` with `check_slop`, `fix_safe`, `explain_rule`, `slop_guide` tools
- a **PostToolUse hook** — every file Claude writes is checked instantly; only the lines it just wrote are reported, and Claude is told to fix them before moving on
- anti-slop rules in **CLAUDE.md**

`fixmyslop init --user` installs the skill for every project on your machine.

### Cursor, Codex, Gemini, Windsurf, anything with MCP

```bash
fixmyslop init --cursor          # .cursor/rules + .cursor/mcp.json
fixmyslop init --agents          # AGENTS.md (Codex, Gemini, Jules, Copilot agents)
claude mcp add fixmyslop -- fixmyslop mcp     # or register the MCP server anywhere
```

MCP config for JSON-configured clients (Cursor, Windsurf, Claude Desktop):

```json
{ "mcpServers": { "fixmyslop": { "command": "npx", "args": ["-y", "fixmyslop", "mcp"] } } }
```

### Hand off a fix

```bash
fixmyslop fix                          # auto-detects claude / codex / gemini on PATH
fixmyslop fix --agent claude --yes
fixmyslop fix --agent-cmd "aider --message-file {brief} --yes"
fixmyslop fix --agent llm -b https://openrouter.ai/api/v1 -m <model>   # any OpenAI-compatible API, incl. Ollama
fixmyslop scan -f prompt > brief.md    # or paste the brief yourself
```

`fix` applies safe deterministic fixes first, writes a brief to `.fixmyslop/brief.md` (file-by-file checklist with
a concrete fix for every rule plus UI design direction), runs the agent, re-scans, and repeats for up to `--rounds`.
It ends with the before/after score.

## Existing codebase? Baseline it

```bash
fixmyslop baseline          # accept today's issues (writes .fixmyslop-baseline.json — commit it)
fixmyslop scan --fail-on high   # from now on only NEW slop is reported and fails CI
fixmyslop scan --no-baseline    # see everything again
```

Fingerprints ignore line numbers, so editing code above an old issue doesn't bring it back. Also available in the
app under Setup.

## CI

```yaml
# .github/workflows/fixmyslop.yml   (or: fixmyslop init --github)
on: [pull_request]
permissions: { contents: read, security-events: write }
jobs:
  slop:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: MrSpideyNihal/FixMySlop@v0.6.8
        with: { fail-on: high, changed-only: true }
```

Findings show up as inline PR annotations (SARIF). Also on the [GitHub Marketplace](https://github.com/marketplace/actions/fixmyslop-ai-slop-linter). pre-commit:

```yaml
repos:
  - repo: https://github.com/MrSpideyNihal/FixMySlop
    rev: v0.6.8
    hooks: [{ id: fixmyslop }]
```

## Configure

`.fixmyslop.yml` (or `[tool.fixmyslop]` in pyproject.toml), created by `fixmyslop init`:

```yaml
exclude: ["legacy/**", "**/*.generated.ts"]
disable: ["ui/default-font"]           # ids or groups: ui, a11y, slop, sec, deps
severity: {"slop/console-log": "INFO"}
fail_on: high
hook: { min_severity: MEDIUM }
```

Silence one finding with a reason: `// fixmyslop-ignore[ui/gradient-text] brand guideline`.
Skip a file: `fixmyslop-ignore-file` in its first lines. Paths passed explicitly are always scanned.

**Updates.** `fixmyslop scan` (text output), `fixmyslop version` and the app tell you when a newer version is on
PyPI, at most once a day. Nothing is installed for you. The check is skipped in CI and in machine-readable output
(`-f json`, `compact`, the pre-commit hook), and `FIXMYSLOP_NO_UPDATE_CHECK=1` turns it off. `npx`, `uvx` and the
website always run the latest version; pip, pre-commit and the GitHub Action stay pinned until you upgrade.

## Output formats

`-f text` (default) · `compact` (one line per issue, for agents) · `prompt` (fix brief) · `sarif` · `json` ·
`markdown` · `html` · `csv` · `pdf`. Save with `-s report.pdf` (format inferred from the extension).

```bash
fixmyslop scan -s report.pdf      # score, summary, findings by file, how to fix each rule (no extra installs)
fixmyslop scan -s report.md       # same structure, for PRs, issues and docs
fixmyslop scan --open             # interactive HTML report
```

The HTML report and the app (`fixmyslop ui`) both have an **Export** menu: PDF, Markdown, CSV, JSON (and HTML/SARIF
in the app). Shared reports show the project name, never your local path.

Exit codes: `0` clean, `1` issues at/above `--fail-on`, `2` usage error.

## How accurate is it?

On a pinned corpus of 9 AI-built apps and 4 hand-built repos, **95% of findings were correct** in a random,
hand-reviewed sample of 80, and AI-built apps averaged about 2× more findings per 1,000 lines. Method, raw labels,
per-repo grades and limitations: [benchmarks/BENCHMARK.md](benchmarks/BENCHMARK.md). Reproduce with
`python benchmarks/run.py`.

Docs rules were checked separately on 130 READMEs and 59 cloned repos: none of 20 well-known hand-written
READMEs (React, Django, Vite, FastAPI...) was flagged, and every missing-script, dead-link and placeholder finding
was correct on review. `docs/emoji-headings` is a style signal, not proof: some older human READMEs use it too.

## Slop score

0 (clean) to 100, from severity-weighted findings per 1,000 lines, so a 500-line app and a 500k-line monorepo
are comparable. Grades: A < 10 ≤ B < 25 ≤ C < 45 ≤ D < 65 ≤ F. FixMySlop's own repo is scanned in CI and holds an A.

## Optional: LLM review

`fixmyslop scan --llm` adds a model review pass over each file (Ollama, llama.cpp, vLLM, LM Studio, or any
OpenAI-compatible endpoint via `--base-url`/`--api-key`/`--model`, or `FIXMYSLOP_*` env vars). It's slow and
non-deterministic, so it's off by default — every check above works without it.

## Development

```bash
pip install -e ".[analysis,dev]"
pytest -q
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --extend-exclude=examples,test_bait.py
fixmyslop scan . --fail-on medium     # the repo must stay clean
python screenshots/make_screenshots.py   # regenerate README screenshots
```

Adding a rule: write a check in `fixmyslop/core/slop/rules_*.py` with the `@rule` decorator (or `line_rule` for a regex),
then add a sloppy + clean pair to `tests/test_slop_rules.py`. Every rule needs a `why` and an actionable `fix` —
the fix text is what agents follow.

## Security and changes

See [SECURITY.md](SECURITY.md) for how FixMySlop handles your code (local, offline by default, secrets redacted)
and how to report a vulnerability, and [CHANGELOG.md](CHANGELOG.md) for what changed in each release.

## License

MIT

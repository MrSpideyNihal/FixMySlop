"""
FixMySlop macros — single source of truth for all constants.
Import this at the top of every module that needs a constant.
Never hardcode values anywhere else.
"""

# ─── App Identity ───────────────────────────────────────────────────────────
APP_NAME = "FixMySlop"
APP_VERSION = "0.2.2"
APP_DESCRIPTION = "AI wrote your code. FixMySlop fixes it."
APP_AUTHOR = "Nihal Rodge"
APP_LICENSE = "MIT"
APP_URL = "https://github.com/nihalrodge/fixmyslop"
APP_DOCS_URL = "https://fixmyslop.dev/docs"

# ─── Paths ───────────────────────────────────────────────────────────────────
from pathlib import Path

ROOT_DIR = Path(__file__).parent
CONFIG_DIR = Path.home() / ".fixmyslop"
CONFIG_FILE = CONFIG_DIR / "config.yaml"
LOG_FILE = CONFIG_DIR / "fixmyslop.log"
CACHE_DIR = CONFIG_DIR / "cache"
REPORTS_DIR = CONFIG_DIR / "reports"
USER_GUIDE_PATH = ROOT_DIR / "USER_GUIDE.md"

# ─── Defaults ────────────────────────────────────────────────────────────────
DEFAULT_MODEL = ""
DEFAULT_BASE_URL = "http://localhost:11434/v1"
DEFAULT_API_KEY = "ollama"
DEFAULT_TEMPERATURE = 0.2
DEFAULT_MAX_TOKENS = 1024
DEFAULT_THEME = "dark"
DEFAULT_FONT_SIZE = 14
MIN_FONT_SIZE = 11
MAX_FONT_SIZE = 20
DEFAULT_LANGUAGE = "en"
DEFAULT_MAX_FILE_SIZE_KB = 500
DEFAULT_SCAN_TIMEOUT_S = 300

# ─── Scan Modes ──────────────────────────────────────────────────────────────
SCAN_MODE_TURBO = "turbo"
SCAN_MODE_DEEP = "deep"
DEFAULT_SCAN_MODE = SCAN_MODE_TURBO

TURBO_MAX_TOKENS = 800
TURBO_MAX_ISSUES = 10
TURBO_CHUNK_SIZE = 15000

DEEP_MAX_TOKENS = 4096
DEEP_MAX_ISSUES = 50
DEEP_CHUNK_SIZE = 8000

# ─── Severity Levels ─────────────────────────────────────────────────────────
SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_HIGH = "HIGH"
SEVERITY_MEDIUM = "MEDIUM"
SEVERITY_LOW = "LOW"
SEVERITY_INFO = "INFO"

SEVERITY_ORDER = [
    SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
    SEVERITY_LOW, SEVERITY_INFO,
]

SEVERITY_COLORS = {
    SEVERITY_CRITICAL: "#FF4444",
    SEVERITY_HIGH: "#FF8C00",
    SEVERITY_MEDIUM: "#FFD700",
    SEVERITY_LOW: "#4FC3F7",
    SEVERITY_INFO: "#90A4AE",
}

# ─── Issue Categories ────────────────────────────────────────────────────────
CATEGORY_SECURITY = "Security"
CATEGORY_DEBT = "Technical Debt"
CATEGORY_PERFORMANCE = "Performance"
CATEGORY_MAINTAINABILITY = "Maintainability"
CATEGORY_TESTING = "Missing Tests"
CATEGORY_AI_SMELL = "AI Smell"

# ─── Supported File Extensions ───────────────────────────────────────────────
SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".java", ".cpp", ".c",
    ".cs", ".rb", ".php", ".swift", ".kt",
}

# ─── Static Tool Names ───────────────────────────────────────────────────────
TOOL_RUFF = "ruff"
TOOL_BANDIT = "bandit"
TOOL_SEMGREP = "semgrep"

# ─── UI Dimensions ───────────────────────────────────────────────────────────
WINDOW_MIN_WIDTH = 1100
WINDOW_MIN_HEIGHT = 700
SIDEBAR_WIDTH = 220
PANEL_PADDING = 24

# ─── Backend Types ───────────────────────────────────────────────────────────
BACKEND_OLLAMA = "ollama"
BACKEND_LLAMACPP = "llama.cpp"
BACKEND_VLLM = "vLLM"
BACKEND_OPENAI = "OpenAI-compatible"

KNOWN_BACKENDS = {
    BACKEND_OLLAMA: "http://localhost:11434/v1",
    BACKEND_LLAMACPP: "http://localhost:8080/v1",
    BACKEND_VLLM: "http://localhost:8000/v1",
}

# ─── Report Formats ──────────────────────────────────────────────────────────
REPORT_FORMAT_MARKDOWN = "markdown"
REPORT_FORMAT_HTML = "html"
REPORT_FORMAT_JSON = "json"
REPORT_FORMAT_CSV = "csv"
REPORT_FORMAT_PDF = "pdf"

# ─── Signals / Events (string keys for Qt signal data) ───────────────────────
EVENT_SCAN_STARTED = "scan_started"
EVENT_SCAN_PROGRESS = "scan_progress"
EVENT_SCAN_COMPLETE = "scan_complete"
EVENT_SCAN_FAILED = "scan_failed"
EVENT_FIX_APPLIED = "fix_applied"
EVENT_FIX_REJECTED = "fix_rejected"

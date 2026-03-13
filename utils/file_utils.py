"""
File utilities — safe reading, encoding detection, gitignore parsing.
All path operations use pathlib.Path — no os.sep, no hardcoded slashes.
"""
from pathlib import Path
from typing import Optional
from utils.logger import get_logger

logger = get_logger(__name__)


def read_file_safe(path: Path, max_size_kb: int = 500) -> Optional[str]:
    """
    Read a text file safely. Returns None on binary/oversized/unreadable files.
    Tries UTF-8 first, then latin-1 as fallback.
    """
    try:
        if path.stat().st_size > max_size_kb * 1024:
            logger.debug("Skipping oversized file: %s", path)
            return None
    except OSError as e:
        logger.warning("Could not stat %s: %s", path, e)
        return None

    for enc in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.warning("Could not read %s: %s", path, e)
            return None
    return None


def parse_gitignore(gitignore_path: Path) -> list[str]:
    """Parse .gitignore and return list of patterns. Returns [] if file missing."""
    if not gitignore_path.exists():
        return []
    try:
        lines = gitignore_path.read_text(encoding="utf-8").splitlines()
        return [line.strip() for line in lines if line.strip() and not line.startswith("#")]
    except Exception as e:
        logger.warning("Could not parse .gitignore at %s: %s", gitignore_path, e)
        return []


def get_language_from_extension(path: Path) -> str:
    """Map a file extension to a language label."""
    mapping = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".jsx": "JavaScript", ".tsx": "TypeScript",
        ".go": "Go", ".rs": "Rust", ".java": "Java",
        ".cpp": "C++", ".c": "C", ".cs": "C#",
        ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
        ".kt": "Kotlin",
    }
    return mapping.get(path.suffix.lower(), "Unknown")

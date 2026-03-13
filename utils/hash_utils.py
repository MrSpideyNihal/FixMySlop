"""
Hash utilities — file hashing for change detection.
Uses SHA-256 for reliable content fingerprinting.
"""
import hashlib
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


def hash_file(file_path: Path, algorithm: str = "sha256") -> str:
    """
    Compute the hash digest of a file's contents.
    Returns hex digest string, or empty string on error.
    """
    try:
        h = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        logger.warning("Could not hash file %s: %s", file_path, e)
        return ""


def hash_string(content: str, algorithm: str = "sha256") -> str:
    """Compute the hash digest of a string. Returns hex digest."""
    h = hashlib.new(algorithm)
    h.update(content.encode("utf-8"))
    return h.hexdigest()


def files_are_identical(path_a: Path, path_b: Path) -> bool:
    """Check if two files have identical content by comparing their hashes."""
    return hash_file(path_a) == hash_file(path_b)

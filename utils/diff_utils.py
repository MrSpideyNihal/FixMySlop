"""
Diff utilities — unified diff creation and patch formatting.
Used by fix_engine and patch_applier to create and display diffs.
"""
import difflib
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


def create_unified_diff(
    original: str,
    modified: str,
    file_path: str,
    context_lines: int = 3,
) -> str:
    """
    Create a unified diff string between original and modified content.
    Returns an empty string if both are identical.
    """
    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        n=context_lines,
    )
    return "".join(diff)


def parse_diff_hunks(diff_text: str) -> list[dict]:
    """
    Parse a unified diff into a list of hunk dictionaries.
    Each hunk contains: start_line, end_line, added_lines, removed_lines.
    """
    hunks = []
    current_hunk = None

    for line in diff_text.splitlines():
        if line.startswith("@@"):
            if current_hunk:
                hunks.append(current_hunk)
            # Parse @@ -start,count +start,count @@
            parts = line.split("@@")[1].strip()
            try:
                old_part, new_part = parts.split(" ")
                old_start = int(old_part.split(",")[0].lstrip("-"))
                new_start = int(new_part.split(",")[0].lstrip("+"))
            except (ValueError, IndexError):
                old_start, new_start = 0, 0
            current_hunk = {
                "old_start": old_start,
                "new_start": new_start,
                "added": [],
                "removed": [],
                "context": [],
            }
        elif current_hunk is not None:
            if line.startswith("+") and not line.startswith("+++"):
                current_hunk["added"].append(line[1:])
            elif line.startswith("-") and not line.startswith("---"):
                current_hunk["removed"].append(line[1:])
            else:
                current_hunk["context"].append(line)

    if current_hunk:
        hunks.append(current_hunk)
    return hunks


def format_diff_for_display(diff_text: str) -> list[tuple[str, str]]:
    """
    Format diff into a list of (line_type, content) tuples for display.
    line_type is one of: 'header', 'hunk', 'add', 'remove', 'context'.
    """
    result = []
    for line in diff_text.splitlines():
        if line.startswith("---") or line.startswith("+++"):
            result.append(("header", line))
        elif line.startswith("@@"):
            result.append(("hunk", line))
        elif line.startswith("+"):
            result.append(("add", line))
        elif line.startswith("-"):
            result.append(("remove", line))
        else:
            result.append(("context", line))
    return result

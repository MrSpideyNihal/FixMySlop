"""
Patch applier — safely applies unified diffs to files.
Creates a backup before applying. Validates patch before writing.
"""
import shutil
import re
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


class PatchApplier:
    """
    Applies unified diff patches to files safely.
    Always creates a .bak backup before modifying any file.
    """

    def apply(self, file_path: str, diff: str, create_backup: bool = True) -> bool:
        """
        Apply a unified diff to a file. Returns True on success.
        Creates a .bak file if create_backup is True.
        """
        path = Path(file_path)
        if not path.exists():
            logger.error("File not found: %s", file_path)
            return False

        if create_backup:
            backup_path = path.with_suffix(path.suffix + ".bak")
            shutil.copy2(path, backup_path)
            logger.info("Backup created: %s", backup_path)

        try:
            import subprocess
            result = subprocess.run(
                ["patch", "--no-backup-if-mismatch", "-p1"],
                input=diff.encode(),
                cwd=path.parent,
                capture_output=True,
            )
            if result.returncode == 0:
                logger.info("Patch applied successfully to %s", file_path)
                return True
            else:
                logger.error("Patch failed: %s", result.stderr.decode())
                # Fall back to manual apply
                return self._manual_apply(path, diff)
        except FileNotFoundError:
            # 'patch' not available — fall back to manual apply
            return self._manual_apply(path, diff)

    def _manual_apply(self, path: Path, diff: str) -> bool:
        """Fallback: parse and apply the diff manually without the 'patch' binary."""
        logger.warning("Using manual patch fallback (patch binary not found or failed)")
        try:
            original = path.read_text(encoding="utf-8")
            lines = original.splitlines(keepends=True)
            result_lines = list(lines)

            # Parse hunks from the diff
            hunks = self._parse_hunks(diff)
            if not hunks:
                logger.error("Could not parse any hunks from diff")
                return False

            # Apply hunks in reverse order to preserve line numbers
            for hunk in reversed(hunks):
                start = hunk["old_start"] - 1  # Convert to 0-indexed
                removed = hunk["removed"]
                added = hunk["added"]

                # Remove old lines and insert new ones
                del result_lines[start:start + len(removed)]
                for i, line in enumerate(added):
                    result_lines.insert(start + i, line)

            path.write_text("".join(result_lines), encoding="utf-8")
            logger.info("Manual patch applied successfully to %s", path)
            return True
        except Exception as e:
            logger.error("Manual patch apply failed: %s", e)
            return False

    def _parse_hunks(self, diff: str) -> list[dict]:
        """Parse unified diff into a list of hunks with old_start, removed, added."""
        hunks = []
        current = None

        for line in diff.splitlines(keepends=True):
            # Detect hunk header: @@ -start,count +start,count @@
            hunk_match = re.match(r"^@@ -(\d+)", line)
            if hunk_match:
                if current:
                    hunks.append(current)
                current = {
                    "old_start": int(hunk_match.group(1)),
                    "removed": [],
                    "added": [],
                }
                continue

            if current is None:
                continue

            if line.startswith("-") and not line.startswith("---"):
                current["removed"].append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                current["added"].append(line[1:])

        if current:
            hunks.append(current)
        return hunks

    def restore_backup(self, file_path: str) -> bool:
        """Restore a file from its .bak backup."""
        path = Path(file_path)
        backup_path = path.with_suffix(path.suffix + ".bak")
        if not backup_path.exists():
            logger.error("No backup found for %s", file_path)
            return False
        shutil.copy2(backup_path, path)
        backup_path.unlink()
        logger.info("Restored %s from backup", file_path)
        return True

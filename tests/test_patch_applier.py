"""Tests for core/patch_applier.py."""
from pathlib import Path
from core.patch_applier import PatchApplier


class TestPatchApplier:
    """Tests for the PatchApplier class."""

    def test_apply_creates_backup(self, tmp_path):
        """Should create a .bak backup file before applying."""
        test_file = tmp_path / "test.py"
        test_file.write_text("original content\n", encoding="utf-8")

        applier = PatchApplier()
        # Even if patch fails, backup should exist
        applier.apply(str(test_file), "invalid diff", create_backup=True)
        backup = tmp_path / "test.py.bak"
        assert backup.exists()
        assert backup.read_text(encoding="utf-8") == "original content\n"

    def test_apply_nonexistent_file(self):
        """Should return False for a non-existent file."""
        applier = PatchApplier()
        result = applier.apply("/nonexistent/file.py", "diff")
        assert result is False

    def test_restore_backup(self, tmp_path):
        """Should restore file from .bak backup."""
        test_file = tmp_path / "test.py"
        test_file.write_text("modified\n", encoding="utf-8")

        backup = tmp_path / "test.py.bak"
        backup.write_text("original\n", encoding="utf-8")

        applier = PatchApplier()
        result = applier.restore_backup(str(test_file))
        assert result is True
        assert test_file.read_text(encoding="utf-8") == "original\n"
        assert not backup.exists()

    def test_restore_backup_no_backup(self, tmp_path):
        """Should return False when no backup exists."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content\n", encoding="utf-8")

        applier = PatchApplier()
        result = applier.restore_backup(str(test_file))
        assert result is False

    def test_parse_hunks(self):
        """Should parse basic unified diff hunks."""
        applier = PatchApplier()
        diff = (
            "--- a/test.py\n"
            "+++ b/test.py\n"
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            "-old_line\n"
            "+new_line\n"
            " line3\n"
        )
        hunks = applier._parse_hunks(diff)
        assert len(hunks) == 1
        assert hunks[0]["old_start"] == 1
        assert "old_line\n" in hunks[0]["removed"]
        assert "new_line\n" in hunks[0]["added"]

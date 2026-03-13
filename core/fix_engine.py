"""
Fix engine — takes an Issue and generates a unified diff fix using the LLM.
Handles streaming for live display in the UI.
"""
from pathlib import Path
from typing import Generator
from core.issue import Issue
from core.llm_client import LLMClient
from core.prompts import FIX_SYSTEM, FIX_USER_TEMPLATE
from utils.file_utils import read_file_safe
from utils.logger import get_logger

logger = get_logger(__name__)


class FixEngine:
    """
    Generates code fixes for detected issues using the LLM.
    Returns unified diff patches ready for display and application.
    """

    def __init__(self, llm_client: LLMClient):
        """Initialize fix engine with an LLM client."""
        self.llm = llm_client

    def generate_fix(self, issue: Issue) -> str:
        """Generate a unified diff fix for a single issue. Returns diff string."""
        full_code = read_file_safe(Path(issue.file_path)) or ""
        language = Path(issue.file_path).suffix.lstrip(".")

        prompt = FIX_USER_TEMPLATE.format(
            file_path=issue.file_path,
            title=issue.title,
            description=issue.description,
            severity=issue.severity,
            line_start=issue.line_start,
            line_end=issue.line_end,
            evidence=issue.evidence,
            language=language,
            full_code=full_code[:10000],
        )
        diff = self.llm.chat(FIX_SYSTEM, prompt, temperature=0.1)
        issue.diff = diff
        logger.info("Fix generated for: %s (%s)", issue.title, issue.file_path)
        return diff

    def generate_fix_stream(self, issue: Issue) -> Generator[str, None, None]:
        """Stream fix generation — yields tokens for live UI display."""
        full_code = read_file_safe(Path(issue.file_path)) or ""
        language = Path(issue.file_path).suffix.lstrip(".")

        prompt = FIX_USER_TEMPLATE.format(
            file_path=issue.file_path,
            title=issue.title,
            description=issue.description,
            severity=issue.severity,
            line_start=issue.line_start,
            line_end=issue.line_end,
            evidence=issue.evidence,
            language=language,
            full_code=full_code[:10000],
        )
        full_diff = ""
        for token in self.llm.chat_stream(FIX_SYSTEM, prompt, temperature=0.1):
            full_diff += token
            yield token
        issue.diff = full_diff
        logger.info("Streamed fix generated for: %s", issue.title)

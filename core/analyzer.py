"""
Analyzer — orchestrates static tools + LLM to produce issues for one file.
Takes a file path + content, returns a list of Issue objects.
"""
import json
import re
from pathlib import Path
from typing import Optional
from core.issue import Issue
from core.llm_client import LLMClient
from core.static_tools import StaticToolRunner
from core.prompts import SYSTEM_AUDIT, AUDIT_USER_TEMPLATE
from utils.logger import get_logger
from macros import SEVERITY_HIGH

logger = get_logger(__name__)


def _repair_and_parse(raw: str) -> list:
    """Best-effort parse of LLM JSON output.

    Handles common LLM defects:
    - Markdown fences wrapping
    - Trailing commas before ] or }
    - Truncated JSON (model ran out of tokens mid-array)
    - Extra text before/after the JSON array
    - Mid-stream corruption (extracts valid objects individually)
    Returns a list of dicts, or [] on failure.
    """
    if not raw or not raw.strip():
        return []

    text = raw.strip()

    # 1. Try direct parse (clean JSON)
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        pass

    # 2. Strip markdown fences
    text = re.sub(r"```(?:json)?\s*", "", text).strip().rstrip("`").strip()

    # 3. Extract from first [ to last ]
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return []
    text = text[start:end + 1]

    # 4. Fix trailing commas:  ,] or ,}
    text = re.sub(r",\s*([}\]])", r"\1", text)

    # 5. Try parsing the cleaned text
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        pass

    # 6. Truncated JSON — find last complete object and close the array
    last_brace = text.rfind("}")
    if last_brace > start:
        truncated = text[: last_brace + 1] + "]"
        truncated = re.sub(r",\s*([}\]])", r"\1", truncated)
        try:
            result = json.loads(truncated)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            pass

    # 7. Object-by-object extraction — salvage valid objects from corrupted array
    objects = _extract_objects(text)
    if objects:
        logger.info("Salvaged %d valid objects from corrupted JSON", len(objects))
    return objects


def _extract_objects(text: str) -> list[dict]:
    """Extract individual JSON objects from a malformed array using brace matching."""
    results = []
    i = 0
    while i < len(text):
        if text[i] == '{':
            # Find matching closing brace using depth counting
            depth = 0
            in_string = False
            escape = False
            j = i
            while j < len(text):
                ch = text[j]
                if escape:
                    escape = False
                elif ch == '\\':
                    escape = True
                elif ch == '"':
                    in_string = not in_string
                elif not in_string:
                    if ch == '{':
                        depth += 1
                    elif ch == '}':
                        depth -= 1
                        if depth == 0:
                            # Found complete {...} block
                            candidate = text[i:j + 1]
                            try:
                                obj = json.loads(candidate)
                                if isinstance(obj, dict):
                                    results.append(obj)
                            except json.JSONDecodeError:
                                # Try fixing trailing commas in this object
                                fixed = re.sub(r",\s*([}\]])", r"\1", candidate)
                                try:
                                    obj = json.loads(fixed)
                                    if isinstance(obj, dict):
                                        results.append(obj)
                                except json.JSONDecodeError:
                                    pass  # Skip this corrupted object
                            i = j + 1
                            break
                j += 1
            else:
                break  # Unclosed brace, stop
        else:
            i += 1
    return results


class Analyzer:
    """
    Combines static analysis (Ruff, Bandit, Semgrep) with LLM-based
    deep analysis to produce a complete list of issues for a file.
    """

    def __init__(self, llm_client: Optional[LLMClient] = None,
                 use_static_tools: bool = True, max_retries: int = 2):
        """Initialize analyzer with optional LLM client, static tool toggle, and retry count."""
        self.llm = llm_client
        self.static = StaticToolRunner() if use_static_tools else None
        self.max_retries = max_retries

    def analyze_file(self, file_path: Path, content: str) -> list[Issue]:
        """
        Run all analysis passes on a single file.
        Returns deduplicated, merged list of Issue objects.
        """
        issues: list[Issue] = []
        language = self._detect_language(file_path)

        # Pass 1: Static tools (fast, deterministic)
        if self.static:
            try:
                static_issues = self.static.run(file_path, content, language)
                issues.extend(static_issues)
                logger.debug(
                    "Static tools found %d issues in %s",
                    len(static_issues), file_path.name,
                )
            except Exception as e:
                logger.warning("Static tools failed for %s: %s", file_path.name, e)

        # Pass 2: LLM deep analysis
        if self.llm:
            try:
                llm_issues = self._llm_analyze(file_path, content, language)
                issues.extend(llm_issues)
                logger.debug(
                    "LLM found %d issues in %s",
                    len(llm_issues), file_path.name,
                )
            except Exception as e:
                logger.warning("LLM analysis failed for %s: %s", file_path.name, e)

        return self._deduplicate(issues)

    def _llm_analyze(self, file_path: Path, content: str, language: str) -> list[Issue]:
        """Send file to LLM for analysis, chunking only very large files."""
        CHUNK_SIZE = 8000
        OVERLAP = 500

        if len(content) <= CHUNK_SIZE:
            return self._llm_analyze_chunk(file_path, content, language)

        # Split into overlapping chunks for large files
        logger.info(
            "File %s is %d chars — splitting into chunks of %d",
            file_path.name, len(content), CHUNK_SIZE,
        )
        all_issues: list[Issue] = []
        offset = 0
        chunk_num = 0
        while offset < len(content):
            chunk = content[offset:offset + CHUNK_SIZE]
            chunk_num += 1
            logger.debug("Analyzing chunk %d (offset %d) of %s", chunk_num, offset, file_path.name)
            issues = self._llm_analyze_chunk(file_path, chunk, language)
            all_issues.extend(issues)
            offset += CHUNK_SIZE - OVERLAP

        return self._deduplicate(all_issues)

    def _llm_analyze_chunk(self, file_path: Path, code: str, language: str) -> list[Issue]:
        """Analyze a single chunk of code with retry on parse failure."""
        for attempt in range(1, self.max_retries + 1):
            try:
                if attempt == 1:
                    prompt = AUDIT_USER_TEMPLATE.format(
                        language=language,
                        file_path=str(file_path),
                        code=code,
                    )
                else:
                    prompt = (
                        f"Analyze this {language} code for bugs and security issues.\n"
                        f"File: {file_path}\n\n"
                        f"```{language}\n{code}\n```\n\n"
                        "You MUST respond with ONLY a JSON array. No text before or after.\n"
                        "Each object must have: line_start, line_end, severity, "
                        "category, rule_id, title, description, evidence.\n"
                        "If no issues found, return: []\n"
                        "Response:"
                    )
                    logger.info(
                        "Retry %d/%d for %s with simplified prompt",
                        attempt, self.max_retries, file_path.name,
                    )

                raw = self.llm.chat(SYSTEM_AUDIT, prompt)
                data = _repair_and_parse(raw)

                if not data:
                    logger.warning(
                        "LLM returned no parseable issues for %s (len=%d), attempt %d",
                        file_path.name, len(raw), attempt,
                    )

                if data:
                    return self._build_issues(data, file_path)

                if attempt < self.max_retries:
                    logger.info("LLM returned 0 issues on attempt %d, retrying...", attempt)
                    continue
                return []

            except Exception as e:
                if attempt < self.max_retries:
                    logger.warning(
                        "LLM analysis attempt %d failed for %s: %s — retrying",
                        attempt, file_path.name, e,
                    )
                    continue
                logger.warning("LLM analysis failed after %d attempts for %s: %s",
                               self.max_retries, file_path.name, e)
                return []

        return []

    def _build_issues(self, data: list[dict], file_path: Path) -> list[Issue]:
        """Convert parsed JSON dicts into Issue objects."""
        issues = []
        for item in data:
            if not isinstance(item, dict):
                continue
            issues.append(Issue(
                file_path=str(file_path),
                line_start=item.get("line_start", 0),
                line_end=item.get("line_end", 0),
                severity=item.get("severity", SEVERITY_HIGH),
                category=item.get("category", "AI Smell"),
                rule_id=item.get("rule_id", "llm_detected"),
                title=item.get("title", "Issue detected"),
                description=item.get("description", ""),
                evidence=item.get("evidence", ""),
                source_tool="llm",
            ))
        return issues

    def _detect_language(self, file_path: Path) -> str:
        """Map file extension to language name for prompt context."""
        ext_map = {
            ".py": "python", ".js": "javascript", ".ts": "typescript",
            ".jsx": "javascript", ".tsx": "typescript", ".go": "go",
            ".rs": "rust", ".java": "java", ".cpp": "cpp",
            ".c": "c", ".cs": "csharp", ".rb": "ruby",
            ".php": "php", ".swift": "swift", ".kt": "kotlin",
        }
        return ext_map.get(file_path.suffix.lower(), "code")

    def _deduplicate(self, issues: list[Issue]) -> list[Issue]:
        """Remove near-duplicate issues (same file + line + rule)."""
        seen = set()
        unique = []
        for issue in issues:
            key = (issue.file_path, issue.line_start, issue.rule_id)
            if key not in seen:
                seen.add(key)
                unique.append(issue)
        return unique

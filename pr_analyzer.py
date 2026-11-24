"""
Rationale — GitHub Pull Request Diff Analyzer (Step 5).

Analyzes changed Python code in public GitHub Pull Requests to identify
known deprecated Flask API usage by reusing the AST-based `code_scanner`.

Features:
  - Validates and parses public GitHub PR URLs.
  - Fetches PR metadata and changed files using GitHub REST API.
  - Inspects added and modified code lines from available patch diffs.
  - Distinguishes newly introduced (added) deprecations from existing context lines.
  - Avoids treating deleted lines as current code.
  - Handles network failures, rate limiting, missing patches, non-Python files gracefully.
  - Reuses code_scanner.py without duplicating AST scanning logic.
  - Public unauthenticated access by default; respects GITHUB_TOKEN if configured.
"""

import os
import re
import textwrap
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Tuple
import requests

import code_scanner


# Maximum number of files processed per PR to prevent hanging on huge monorepos
MAX_PR_FILES = 100

# Regex for parsing public GitHub Pull Request URLs
PR_URL_PATTERN = re.compile(
    r"^(?:https?://)?(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)/pull/(-?[0-9]+)(?:[/?#].*)?$",
    re.IGNORECASE
)

# Regex for unified diff hunk header: @@ -old_start,old_count +new_start,new_count @@
HUNK_HEADER_PATTERN = re.compile(
    r"^@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@"
)


@dataclass
class PRFinding:
    """Represents a deprecated API pattern found in a PR patch diff."""
    symbol: str
    file_path: str
    line_number: Optional[int]       # Real line number in new file, or None if unreliable
    change_type: str                 # "added" (newly introduced in PR) or "context" (unchanged existing line)
    detection_type: str              # "decorator", "attribute_access", "call_argument"
    dep_version: Optional[str]
    rem_version: Optional[str]
    status: str                      # Lifecycle status or target-version status
    explanation: str
    evidence_url: Optional[str]
    snippet: str                     # The code line text
    confidence: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FileAnalysisSummary:
    """Summary of a file encountered in a Pull Request."""
    filename: str
    status: str                      # "analyzed" or "skipped"
    reason: Optional[str]            # e.g. "Analyzed Python patch", "Non-Python file (.md)", "Patch unavailable"
    additions: int = 0
    deletions: int = 0
    findings_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PRAnalysisResult:
    """Overall outcome of analyzing a Pull Request diff."""
    success: bool
    owner: str = ""
    repo: str = ""
    pr_number: int = 0
    pr_title: str = ""
    pr_url: str = ""
    pr_state: str = ""
    author: str = ""
    total_files_changed: int = 0
    python_files_count: int = 0
    analyzed_files: List[FileAnalysisSummary] = field(default_factory=list)
    skipped_files: List[FileAnalysisSummary] = field(default_factory=list)
    findings: List[PRFinding] = field(default_factory=list)
    error: Optional[str] = None
    target_version: Optional[str] = None

    @property
    def total_findings(self) -> int:
        return len(self.findings)

    @property
    def added_findings_count(self) -> int:
        return sum(1 for f in self.findings if f.change_type == "added")

    @property
    def context_findings_count(self) -> int:
        return sum(1 for f in self.findings if f.change_type == "context")

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["total_findings"] = self.total_findings
        data["added_findings_count"] = self.added_findings_count
        data["context_findings_count"] = self.context_findings_count
        return data


def parse_pr_url(url: str) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[str]]:
    """Validates and parses a public GitHub Pull Request URL.

    Returns:
        (owner, repo, pr_number, error_message)
    """
    if not url or not isinstance(url, str):
        return None, None, None, "Please provide a valid GitHub Pull Request URL."

    cleaned_url = url.strip()
    match = PR_URL_PATTERN.match(cleaned_url)
    if not match:
        return None, None, None, "Invalid GitHub Pull Request URL. Example format: https://github.com/owner/repo/pull/123"

    owner, repo, pr_str = match.groups()
    try:
        pr_number = int(pr_str)
        if pr_number <= 0:
            return None, None, None, "Invalid Pull Request number: must be greater than zero."
    except ValueError:
        return None, None, None, "Invalid Pull Request number format."

    # Strip any trailing .git from repository name if present
    if repo.lower().endswith(".git"):
        repo = repo[:-4]

    return owner, repo, pr_number, None


def _get_github_headers(token: Optional[str] = None) -> Dict[str, str]:
    """Prepares safe GitHub API headers without exposing credentials."""
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "Rationale-PR-Analyzer",
    }
    # Optional token from parameter or environment
    auth_token = token or os.getenv("GITHUB_TOKEN")
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


def fetch_pr_data(
    owner: str,
    repo: str,
    pr_number: int,
    token: Optional[str] = None,
    timeout: int = 15,
    session: Optional[requests.Session] = None
) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]], Optional[str]]:
    """Fetches PR metadata and changed files list from GitHub REST API.

    Returns:
        (pr_metadata, files_list, error_message)
    """
    http = session or requests
    headers = _get_github_headers(token)

    pr_endpoint = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
    files_endpoint = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files?per_page={MAX_PR_FILES}"

    try:
        # 1. Fetch PR metadata
        meta_resp = http.get(pr_endpoint, headers=headers, timeout=timeout)
        if meta_resp.status_code == 404:
            return None, None, f"Pull Request #{pr_number} was not found on {owner}/{repo}. Verify that the repository is public."
        elif meta_resp.status_code in (403, 429):
            msg = meta_resp.json().get("message", "Rate limit exceeded") if meta_resp.headers.get("content-type", "").startswith("application/json") else "Rate limit exceeded"
            return None, None, f"GitHub API rate limit exceeded: {msg}. Please wait before making further requests."
        elif meta_resp.status_code == 401:
            return None, None, "GitHub API authorization failed. Check configured credentials."
        elif meta_resp.status_code != 200:
            return None, None, f"GitHub API returned HTTP {meta_resp.status_code} while fetching PR #{pr_number}."

        pr_meta = meta_resp.json()

        # 2. Fetch changed files
        files_resp = http.get(files_endpoint, headers=headers, timeout=timeout)
        if files_resp.status_code != 200:
            return None, None, f"GitHub API returned HTTP {files_resp.status_code} while fetching PR files."

        files_data = files_resp.json()
        if not isinstance(files_data, list):
            return None, None, "Unexpected response format for PR files list."

        return pr_meta, files_data, None

    except requests.exceptions.Timeout:
        return None, None, "GitHub API request timed out. Please check your internet connection and try again."
    except requests.exceptions.ConnectionError:
        return None, None, "Failed to connect to GitHub API. Network connection error."
    except Exception as e:
        return None, None, f"Error communicating with GitHub API ({type(e).__name__}: {str(e)})"


def parse_patch_hunks(patch_text: str) -> List[Dict[str, Any]]:
    """Parses a unified diff patch text into structured hunks with line mappings.

    Each hunk contains:
      - new_start: Starting line number in the new file (or None if header is missing)
      - line_entries: List of dicts: {'code': line_text, 'real_line': int or None, 'type': 'added'|'context', 'raw': line}
    """
    if not patch_text or not isinstance(patch_text, str):
        return []

    hunks: List[Dict[str, Any]] = []
    current_hunk: Optional[Dict[str, Any]] = None
    current_new_line: Optional[int] = None

    for raw_line in patch_text.splitlines():
        header_match = HUNK_HEADER_PATTERN.match(raw_line)
        if header_match:
            if current_hunk and current_hunk["line_entries"]:
                hunks.append(current_hunk)
            try:
                new_start = int(header_match.group(2))
            except (IndexError, ValueError):
                new_start = None

            current_new_line = new_start
            current_hunk = {
                "new_start": new_start,
                "line_entries": []
            }
            continue

        if current_hunk is None:
            # Lines before first hunk header (e.g., git metadata)
            continue

        if raw_line.startswith("+"):
            # Added line in PR
            code_line = raw_line[1:]
            current_hunk["line_entries"].append({
                "code": code_line,
                "real_line": current_new_line,
                "type": "added",
                "raw": raw_line
            })
            if current_new_line is not None:
                current_new_line += 1
        elif raw_line.startswith("-"):
            # Deleted line: Do NOT include in new code representation
            # "Avoid treating deleted lines as current code."
            pass
        elif raw_line.startswith(" "):
            # Context line (unchanged)
            code_line = raw_line[1:]
            current_hunk["line_entries"].append({
                "code": code_line,
                "real_line": current_new_line,
                "type": "context",
                "raw": raw_line
            })
            if current_new_line is not None:
                current_new_line += 1
        elif raw_line.startswith("\\"):
            # "\ No newline at end of file"
            pass

    if current_hunk and current_hunk["line_entries"]:
        hunks.append(current_hunk)

    return hunks


def analyze_python_patch(
    file_path: str,
    patch_text: str,
    target_version: Optional[str] = None
) -> Tuple[List[PRFinding], bool]:
    """Analyzes a Python file diff patch for deprecated Flask APIs.

    Reuses `code_scanner.scan_code` to ensure exact, verified AST detection
    without duplicating visitor logic.

    Returns:
        A tuple of (findings_list, had_incomplete_snippets).
        had_incomplete_snippets is True when at least one hunk could not be
        fully parsed as a whole block and required statement-level fallback,
        meaning findings from that hunk have reduced confidence.
    """
    hunks = parse_patch_hunks(patch_text)
    findings: List[PRFinding] = []
    seen_findings = set()
    had_incomplete_snippets = False

    for hunk in hunks:
        entries = hunk["line_entries"]
        if not entries:
            continue

        # Build reconstructed snippet of the file's new state in this hunk
        raw_code = "\n".join(e["code"] for e in entries)
        dedented_code = textwrap.dedent(raw_code)

        # 1. Primary Strategy: Scan the dedented hunk block with code_scanner
        scan_res = code_scanner.scan_code(
            source_code=dedented_code,
            file_name=file_path,
            target_version=target_version
        )

        if scan_res.success and scan_res.findings:
            # Map findings back to hunk lines
            for f in scan_res.findings:
                # 1-based snippet line index
                line_idx = f.line - 1
                if 0 <= line_idx < len(entries):
                    entry = entries[line_idx]
                    real_line = entry["real_line"]
                    change_type = entry["type"]
                    snippet_text = entry["code"].strip()
                else:
                    real_line = None
                    change_type = "added"
                    snippet_text = f.symbol

                dedup_key = (f.symbol, file_path, real_line, change_type)
                if dedup_key not in seen_findings:
                    seen_findings.add(dedup_key)
                    findings.append(PRFinding(
                        symbol=f.symbol,
                        file_path=file_path,
                        line_number=real_line,
                        change_type=change_type,
                        detection_type=f.detection_type,
                        dep_version=f.dep_version,
                        rem_version=f.rem_version,
                        status=f.status,
                        explanation=f.explanation,
                        evidence_url=f.evidence_url,
                        snippet=snippet_text,
                        confidence=f.confidence,
                    ))
        elif scan_res.success and not scan_res.findings:
            # Hunk parsed successfully but contained no findings — fully analyzed, nothing to flag
            pass

        elif not scan_res.success:
            # 2. Fallback Strategy: If dedented hunk has a SyntaxError because it's a
            # partial fragment (e.g. cutting through an inner block or unclosed header),
            # scan candidate lines individually with statement completion.
            # Mark the file as having incomplete snippets.
            had_incomplete_snippets = True

            for entry in entries:
                stmt = entry["code"].strip()
                if not stmt or stmt.startswith("#"):
                    continue

                # Prepare standalone statement for AST parsing
                stmt_to_scan = stmt
                if stmt.endswith(":"):
                    stmt_to_scan = stmt + "\n    pass"
                elif stmt.startswith("@"):
                    stmt_to_scan = stmt + "\ndef _dummy():\n    pass"

                single_res = code_scanner.scan_code(
                    source_code=stmt_to_scan,
                    file_name=file_path,
                    target_version=target_version
                )
                if single_res.success and single_res.findings:
                    for f in single_res.findings:
                        real_line = entry["real_line"]
                        change_type = entry["type"]
                        dedup_key = (f.symbol, file_path, real_line, change_type)
                        if dedup_key not in seen_findings:
                            seen_findings.add(dedup_key)
                            findings.append(PRFinding(
                                symbol=f.symbol,
                                file_path=file_path,
                                line_number=real_line,
                                change_type=change_type,
                                detection_type=f.detection_type,
                                dep_version=f.dep_version,
                                rem_version=f.rem_version,
                                status=f.status,
                                explanation=f.explanation,
                                evidence_url=f.evidence_url,
                                snippet=entry["code"].strip(),
                                confidence="medium (partial hunk context)",
                            ))

    # Sort deterministically: added lines first (highest priority), then by line number
    findings.sort(key=lambda x: (0 if x.change_type == "added" else 1, x.line_number or 999999))
    return findings, had_incomplete_snippets


def is_python_file(filename: str) -> bool:
    """Checks whether a file path points to a Python source file."""
    if not filename:
        return False
    lower = filename.lower()
    return lower.endswith(".py") or lower.endswith(".pyi") or lower.endswith(".pyw")


def analyze_pr(
    pr_url: str,
    target_version: Optional[str] = None,
    token: Optional[str] = None,
    timeout: int = 15,
    session: Optional[requests.Session] = None
) -> PRAnalysisResult:
    """End-to-end analyzer for a public GitHub Pull Request.

    Args:
        pr_url: Public GitHub PR URL.
        target_version: Optional target Flask version string (e.g. '2.3.0').
        token: Optional GitHub API token.
        timeout: Request timeout in seconds.
        session: Optional requests.Session (useful for test mocking).

    Returns:
        PRAnalysisResult with structured metadata, file breakdown, and findings.
    """
    # 1. Validate and parse PR URL
    owner, repo, pr_number, err = parse_pr_url(pr_url)
    if err:
        return PRAnalysisResult(success=False, pr_url=pr_url, error=err)

    # 2. Fetch PR metadata and changed files
    pr_meta, files_list, fetch_err = fetch_pr_data(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        token=token,
        timeout=timeout,
        session=session
    )
    if fetch_err:
        return PRAnalysisResult(
            success=False,
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            pr_url=pr_url,
            error=fetch_err
        )

    # 3. Extract PR high-level metadata
    pr_title = pr_meta.get("title", "")
    pr_state = pr_meta.get("state", "open")
    author = pr_meta.get("user", {}).get("login", "")
    html_url = pr_meta.get("html_url", pr_url)
    total_files_count = len(files_list)

    analyzed_summaries: List[FileAnalysisSummary] = []
    skipped_summaries: List[FileAnalysisSummary] = []
    all_findings: List[PRFinding] = []
    python_files_count = 0

    # 4. Process each changed file
    for f in files_list:
        fname = f.get("filename", "")
        adds = f.get("additions", 0)
        dels = f.get("deletions", 0)
        status = f.get("status", "modified")

        if not is_python_file(fname):
            ext = os.path.splitext(fname)[1] or "no extension"
            skipped_summaries.append(FileAnalysisSummary(
                filename=fname,
                status="skipped",
                reason=f"Non-Python file ({ext})",
                additions=adds,
                deletions=dels,
            ))
            continue

        python_files_count += 1
        patch_text = f.get("patch")

        if not patch_text:
            # File is Python, but GitHub provided no patch
            reason = "Patch unavailable from GitHub"
            if status == "removed":
                reason = "File deleted; no new code introduced"
            elif status == "renamed" and adds == 0:
                reason = "File renamed without changes"
            elif f.get("changes", 0) > 3000:
                reason = "Diff exceeds GitHub size threshold"

            skipped_summaries.append(FileAnalysisSummary(
                filename=fname,
                status="skipped",
                reason=reason,
                additions=adds,
                deletions=dels,
            ))
            continue

        # 5. Scan available Python patch
        file_findings, had_incomplete = analyze_python_patch(
            file_path=fname,
            patch_text=patch_text,
            target_version=target_version
        )

        all_findings.extend(file_findings)

        if had_incomplete:
            file_status = "partially_analyzed"
            file_reason = "Partially analyzed: diff hunk contains incomplete syntax or missing outer context"
        else:
            file_status = "analyzed"
            file_reason = "Analyzed changed Python patch"

        analyzed_summaries.append(FileAnalysisSummary(
            filename=fname,
            status=file_status,
            reason=file_reason,
            additions=adds,
            deletions=dels,
            findings_count=len(file_findings),
        ))

    return PRAnalysisResult(
        success=True,
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        pr_title=pr_title,
        pr_url=html_url,
        pr_state=pr_state,
        author=author,
        total_files_changed=total_files_count,
        python_files_count=python_files_count,
        analyzed_files=analyzed_summaries,
        skipped_files=skipped_summaries,
        findings=all_findings,
        error=None,
        target_version=target_version
    )

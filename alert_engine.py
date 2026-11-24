"""
Rationale — Actionable Findings and Alert System (Step 6).

Converts scanner and PR analyzer findings into a consistent, prioritized
alert format.  Severity is strictly rule-based using verified lifecycle
metadata — no guesses, no security-vulnerability labels.

Accepts findings from:
  - code_scanner.ScanFinding  (local AST scan)
  - pr_analyzer.PRFinding     (GitHub PR diff analysis)
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

from packaging.version import Version, InvalidVersion


# ── Severity constants ────────────────────────────────────────────────────────

SEVERITY_CRITICAL = "Critical"
SEVERITY_HIGH = "High"
SEVERITY_MEDIUM = "Medium"
SEVERITY_INFO = "Informational"

SEVERITY_ORDER = {
    SEVERITY_CRITICAL: 0,
    SEVERITY_HIGH: 1,
    SEVERITY_MEDIUM: 2,
    SEVERITY_INFO: 3,
}

# ── Detection source labels ──────────────────────────────────────────────────

SOURCE_LOCAL_SCAN = "Local Code Scan"
SOURCE_GITHUB_PR = "GitHub PR"

# ── Verified recommended actions (only for known curated decisions) ───────────
# These are sourced from the verified rationale and migration guidance in the
# curated dataset; they are NOT fabricated suggestions.

VERIFIED_ACTIONS = {
    "app.before_first_request": (
        "Move initialisation logic into the application factory or "
        "use app.app_context() during setup instead of @app.before_first_request."
    ),
    "got_first_request": None,  # No verified replacement API exists in primary sources
    "test_client.as_tuple": (
        "Replace as_tuple=True in test client calls with direct attribute "
        "access on the response object (response.status, response.headers, response.data)."
    ),
}


# ── Alert dataclass ───────────────────────────────────────────────────────────

@dataclass
class Alert:
    """A single prioritised, actionable alert derived from a scanner finding."""

    alert_id: str
    symbol: str
    severity: str
    status: str                           # "New", "Needs Review", or "Resolved"
    file_path: str
    line_number: Optional[int]
    source: str                           # SOURCE_LOCAL_SCAN or SOURCE_GITHUB_PR
    description: str
    dep_version: Optional[str]
    rem_version: Optional[str]
    evidence_url: Optional[str]
    recommended_action: Optional[str]
    confidence: str = "high"
    change_type: Optional[str] = None     # For PR findings: "added" or "context"
    detection_type: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlertReport:
    """Aggregated alert report with counts and grouping helpers."""

    alerts: List[Alert] = field(default_factory=list)
    source_label: str = ""
    target_version: Optional[str] = None
    error: Optional[str] = None

    # ── Counts ────────────────────────────────────────────────────────────

    @property
    def total(self) -> int:
        return len(self.alerts)

    @property
    def critical_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == SEVERITY_CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == SEVERITY_HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == SEVERITY_MEDIUM)

    @property
    def info_count(self) -> int:
        return sum(1 for a in self.alerts if a.severity == SEVERITY_INFO)

    # ── Grouping ──────────────────────────────────────────────────────────

    def by_severity(self) -> Dict[str, List[Alert]]:
        """Returns alerts grouped by severity in priority order."""
        groups: Dict[str, List[Alert]] = {}
        for sev in (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_INFO):
            matching = [a for a in self.alerts if a.severity == sev]
            if matching:
                groups[sev] = matching
        return groups

    def filter(
        self,
        severity: Optional[str] = None,
        source: Optional[str] = None,
        symbol: Optional[str] = None,
    ) -> List[Alert]:
        """Returns a filtered view of alerts."""
        result = list(self.alerts)
        if severity:
            result = [a for a in result if a.severity == severity]
        if source:
            result = [a for a in result if a.source == source]
        if symbol:
            result = [a for a in result if a.symbol == symbol]
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "critical": self.critical_count,
            "high": self.high_count,
            "medium": self.medium_count,
            "informational": self.info_count,
            "source_label": self.source_label,
            "target_version": self.target_version,
            "error": self.error,
            "alerts": [a.to_dict() for a in self.alerts],
        }


# ── Severity assignment ──────────────────────────────────────────────────────

def _parse_version_safe(v: Optional[str]) -> Optional[Version]:
    """Parse a version string, returning None on failure."""
    if not v:
        return None
    cleaned = str(v).strip()
    if cleaned.lower().startswith("flask "):
        cleaned = cleaned[6:].strip()
    try:
        return Version(cleaned)
    except InvalidVersion:
        return None


def compute_severity(
    dep_version: Optional[str],
    rem_version: Optional[str],
    target_version: Optional[str],
    status_text: str = "",
) -> str:
    """Determines alert severity using transparent, rule-based logic.

    Rules:
      1. Critical  — removal version known AND target >= removal version.
      2. High      — removal version known but target is not supplied or
                     cannot be compared (the API *will* break eventually).
      3. Medium    — API is deprecated but not confirmed removed for the
                     selected target version.
      4. Info      — lifecycle information available but no direct compat
                     conclusion can be made.
    """
    parsed_target = _parse_version_safe(target_version)
    parsed_rem = _parse_version_safe(rem_version)
    parsed_dep = _parse_version_safe(dep_version)

    # Also consult the status text from version_checker when available
    status_lower = (status_text or "").strip().lower()

    # Rule 1: Confirmed removed for target version
    if parsed_rem and parsed_target and parsed_target >= parsed_rem:
        return SEVERITY_CRITICAL
    # Also handle status text from check_status
    if "removed" in status_lower and parsed_target:
        return SEVERITY_CRITICAL

    # Rule 2: Removal version known but target missing or below removal
    if parsed_rem:
        if parsed_target is None:
            return SEVERITY_HIGH
        # Target is below removal — still deprecated range
        if parsed_dep and parsed_target >= parsed_dep:
            return SEVERITY_MEDIUM
        # Target is below deprecation too
        if parsed_dep and parsed_target < parsed_dep:
            return SEVERITY_INFO
        # dep unknown, target below removal
        return SEVERITY_MEDIUM

    # Rule 3: Only deprecated, no removal version
    if parsed_dep:
        if parsed_target and parsed_target >= parsed_dep:
            return SEVERITY_MEDIUM
        return SEVERITY_INFO

    # Rule 4: No lifecycle milestones at all
    return SEVERITY_INFO


# ── Alert ID generation ──────────────────────────────────────────────────────

def _make_alert_id(symbol: str, file_path: str, line: Optional[int], source: str) -> str:
    """Deterministic, short hash-based alert ID for deduplication."""
    raw = f"{symbol}|{file_path}|{line}|{source}"
    return "ALR-" + hashlib.sha256(raw.encode()).hexdigest()[:10].upper()


# ── Build description ─────────────────────────────────────────────────────────

def _build_description(
    symbol: str,
    severity: str,
    dep_version: Optional[str],
    rem_version: Optional[str],
    target_version: Optional[str],
) -> str:
    """Human-readable, one-line description of why this alert was raised."""
    if severity == SEVERITY_CRITICAL:
        return (
            f"`{symbol}` was removed in Flask {rem_version} and the target "
            f"version ({target_version}) is at or beyond that release."
        )
    if severity == SEVERITY_HIGH:
        return (
            f"`{symbol}` has a known removal in Flask {rem_version}. "
            f"No target version was provided, so compatibility cannot be confirmed."
        )
    if severity == SEVERITY_MEDIUM:
        dep_str = f" (deprecated in Flask {dep_version})" if dep_version else ""
        return (
            f"`{symbol}` is deprecated{dep_str} but not confirmed removed "
            f"for the selected target version."
        )
    # Informational
    if dep_version:
        return (
            f"`{symbol}` has lifecycle information (deprecated in Flask "
            f"{dep_version}) but no direct compatibility impact can be determined."
        )
    return f"`{symbol}` was detected but insufficient lifecycle data is available."


# ── Public conversion functions ───────────────────────────────────────────────

def normalize_scan_finding(f: Any) -> Dict[str, Any]:
    """Normalizes a scanner finding from a dataclass, object, or dict into a standard dict.

    Ensures robust ingestion regardless of whether findings are preserved as
    code_scanner.ScanFinding dataclasses, plain dictionaries, or serialized state.
    """
    if isinstance(f, dict):
        symbol = str(f.get("symbol", "") or "")
        file_name = str(f.get("file_name") or f.get("file_path") or "<input>")
        line = f.get("line") if f.get("line") is not None else f.get("line_number")
        dep_v = f.get("dep_version")
        rem_v = f.get("rem_version")
        status = str(f.get("status", "") or "")
        evidence_url = f.get("evidence_url")
        confidence = str(f.get("confidence", "high") or "high")
        detection_type = str(f.get("detection_type", "") or "")
        explanation = str(f.get("explanation", "") or "")
        rec_action = f.get("recommended_action") or VERIFIED_ACTIONS.get(symbol)
    else:
        symbol = str(getattr(f, "symbol", "") or "")
        file_name = str(getattr(f, "file_name", None) or getattr(f, "file_path", None) or "<input>")
        line = getattr(f, "line", None) if getattr(f, "line", None) is not None else getattr(f, "line_number", None)
        dep_v = getattr(f, "dep_version", None)
        rem_v = getattr(f, "rem_version", None)
        status = str(getattr(f, "status", "") or "")
        evidence_url = getattr(f, "evidence_url", None)
        confidence = str(getattr(f, "confidence", "high") or "high")
        detection_type = str(getattr(f, "detection_type", "") or "")
        explanation = str(getattr(f, "explanation", "") or "")
        rec_action = getattr(f, "recommended_action", None) or VERIFIED_ACTIONS.get(symbol)

    return {
        "symbol": symbol,
        "file_name": file_name,
        "line": line,
        "dep_version": dep_v,
        "rem_version": rem_v,
        "status": status,
        "evidence_url": evidence_url,
        "confidence": confidence,
        "detection_type": detection_type,
        "explanation": explanation,
        "recommended_action": rec_action,
    }


def alerts_from_scan_findings(
    findings: Any,
    target_version: Optional[str] = None,
) -> AlertReport:
    """Convert code_scanner.ScanFinding objects (or dictionaries) into an AlertReport.

    Args:
        findings: List of ScanFinding dataclass instances or finding dicts.
        target_version: Optional Flask version string.

    Returns:
        AlertReport with deduplicated, severity-sorted alerts.
    """
    seen_ids: Set[str] = set()
    alerts: List[Alert] = []

    if findings is None:
        raw_list = []
    elif isinstance(findings, (list, tuple, set)):
        raw_list = list(findings)
    else:
        raw_list = [findings]

    for raw_f in raw_list:
        norm = normalize_scan_finding(raw_f)
        symbol = norm["symbol"]
        file_name = norm["file_name"]
        line = norm["line"]
        dep_v = norm["dep_version"]
        rem_v = norm["rem_version"]
        status = norm["status"]

        severity = compute_severity(
            dep_version=dep_v,
            rem_version=rem_v,
            target_version=target_version,
            status_text=status,
        )
        alert_id = _make_alert_id(symbol, file_name, line, SOURCE_LOCAL_SCAN)
        if alert_id in seen_ids:
            continue
        seen_ids.add(alert_id)

        alerts.append(Alert(
            alert_id=alert_id,
            symbol=symbol,
            severity=severity,
            status="New",
            file_path=file_name,
            line_number=line,
            source=SOURCE_LOCAL_SCAN,
            description=_build_description(
                symbol, severity, dep_v, rem_v, target_version
            ),
            dep_version=dep_v,
            rem_version=rem_v,
            evidence_url=norm["evidence_url"],
            recommended_action=norm["recommended_action"],
            confidence=norm["confidence"],
            detection_type=norm["detection_type"],
        ))

    # Sort: critical first, then by file+line
    alerts.sort(key=lambda a: (
        SEVERITY_ORDER.get(a.severity, 99),
        a.file_path,
        a.line_number or 999999,
    ))

    return AlertReport(
        alerts=alerts,
        source_label=SOURCE_LOCAL_SCAN,
        target_version=target_version,
    )


def alerts_from_pr_findings(
    findings: list,
    target_version: Optional[str] = None,
) -> AlertReport:
    """Convert a list of pr_analyzer.PRFinding objects into an AlertReport.

    Args:
        findings: List of PRFinding dataclass instances.
        target_version: Optional Flask version string.

    Returns:
        AlertReport with deduplicated, severity-sorted alerts.
    """
    seen_ids: Set[str] = set()
    alerts: List[Alert] = []

    for f in findings:
        severity = compute_severity(
            dep_version=f.dep_version,
            rem_version=f.rem_version,
            target_version=target_version,
            status_text=f.status,
        )
        alert_id = _make_alert_id(f.symbol, f.file_path, f.line_number, SOURCE_GITHUB_PR)
        if alert_id in seen_ids:
            continue
        seen_ids.add(alert_id)

        alerts.append(Alert(
            alert_id=alert_id,
            symbol=f.symbol,
            severity=severity,
            status="New",
            file_path=f.file_path,
            line_number=f.line_number,
            source=SOURCE_GITHUB_PR,
            description=_build_description(
                f.symbol, severity, f.dep_version, f.rem_version, target_version
            ),
            dep_version=f.dep_version,
            rem_version=f.rem_version,
            evidence_url=f.evidence_url,
            recommended_action=VERIFIED_ACTIONS.get(f.symbol),
            confidence=f.confidence,
            change_type=f.change_type,
            detection_type=f.detection_type,
        ))

    alerts.sort(key=lambda a: (
        SEVERITY_ORDER.get(a.severity, 99),
        a.file_path,
        a.line_number or 999999,
    ))

    return AlertReport(
        alerts=alerts,
        source_label=SOURCE_GITHUB_PR,
        target_version=target_version,
    )


def merge_reports(*reports: AlertReport) -> AlertReport:
    """Merge multiple AlertReports, deduplicating by alert_id.

    When alerts from different sources share the same symbol+file+line,
    they are kept as separate alerts (different sources = different alert IDs).
    """
    seen_ids: Set[str] = set()
    merged: List[Alert] = []
    target_v = None
    sources: List[str] = []

    for report in reports:
        if report.target_version and not target_v:
            target_v = report.target_version
        if report.source_label and report.source_label not in sources:
            sources.append(report.source_label)
        for alert in report.alerts:
            if alert.alert_id not in seen_ids:
                seen_ids.add(alert.alert_id)
                merged.append(alert)

    merged.sort(key=lambda a: (
        SEVERITY_ORDER.get(a.severity, 99),
        a.file_path,
        a.line_number or 999999,
    ))

    return AlertReport(
        alerts=merged,
        source_label=" + ".join(sources) if sources else "",
        target_version=target_v,
    )


def apply_status_overrides(report: AlertReport, status_map: Dict[str, str]) -> AlertReport:
    """Applies session-based status overrides to alerts (e.g. 'Needs Review', 'Resolved').
    
    Status tracking is session-based and strictly maintained for the current session.
    """
    if not status_map:
        return report
    valid_statuses = {"New", "Needs Review", "Resolved"}
    for alert in report.alerts:
        override = status_map.get(alert.alert_id)
        if override and override in valid_statuses:
            alert.status = override
    return report


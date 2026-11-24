"""
Rationale — Evidence-Backed Migration Guidance (Step 7).

Provides verified, source-backed migration guidance for known deprecated and
removed Flask APIs.

Guarantees:
  1. Every migration recommendation is backed strictly by verified project
     data and primary maintainer sources (Pallets GitHub Issues, PRs, and changelogs).
  2. Does NOT invent replacement APIs, code snippets, or generic architectural claims.
  3. Where no verified replacement exists (e.g. `got_first_request`), explicitly states:
     "No verified replacement guidance is currently available for this API."
  4. Illustrative before/after code examples are only provided when explicitly
     supported by reliable primary evidence (e.g. Issue #4605, PR #4417).
  5. Version-aware lifecycle evaluation reuses `version_checker.py`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from packaging.version import Version, InvalidVersion
from version_checker import load_decisions, get_verified_versions, check_status


DATA_FILE = Path(__file__).parent / "decisions.json"

# Verified primary source links and official metadata
PRIMARY_SOURCES = {
    "app.before_first_request": [
        {
            "label": "GitHub Issue #4605 (Deprecation proposal & rationale)",
            "url": "https://github.com/pallets/flask/issues/4605",
            "type": "issue",
            "ref": 4605,
        },
        {
            "label": "GitHub Pull Request #4995 (Removal implementation)",
            "url": "https://github.com/pallets/flask/pull/4995",
            "type": "pr",
            "ref": 4995,
        },
    ],
    "got_first_request": [
        {
            "label": "GitHub Pull Request #4997 (Deprecation & rationale)",
            "url": "https://github.com/pallets/flask/pull/4997",
            "type": "pr",
            "ref": 4997,
        },
        {
            "label": "GitHub Pull Request #5223 (Removal implementation)",
            "url": "https://github.com/pallets/flask/pull/5223",
            "type": "pr",
            "ref": 5223,
        },
    ],
    "test_client.as_tuple": [
        {
            "label": "GitHub Pull Request #4341 (Deprecation in Flask/Werkzeug)",
            "url": "https://github.com/pallets/flask/pull/4341",
            "type": "pr",
            "ref": 4341,
        },
        {
            "label": "GitHub Pull Request #4417 (Removal implementation)",
            "url": "https://github.com/pallets/flask/pull/4417",
            "type": "pr",
            "ref": 4417,
        },
    ],
}

# Verified migration records directly backed by primary source quotes & PRs
VERIFIED_MIGRATION_REGISTRY: Dict[str, Dict[str, Any]] = {
    "app.before_first_request": {
        "has_verified_replacement": True,
        "recommended_approach": (
            "Perform application setup during application creation, preferably in an application factory function "
            "(create_app()). Operations requiring an active application context should use 'with app.app_context():'."
        ),
        "why_migration_required": (
            "The @app.before_first_request decorator was deprecated in Flask 2.2.0 and removed in Flask 2.3.0. "
            "Running setup on the first incoming request introduces race conditions in multi-threaded/multi-worker "
            "deployments and defers initialization errors to runtime."
        ),
        "limitations": (
            "The application factory pattern is recommended by maintainers, but exact setup structure depends on the "
            "project architecture. There is no drop-in universal one-line replacement."
        ),
        "has_code_example": True,
        "before_code": """# Deprecated approach (Flask < 2.3)
from flask import Flask

app = Flask(__name__)

@app.before_first_request
def setup():
    init_database()""",
        "after_code": """# Verified approach: Application factory (Flask 2.3+)
from flask import Flask

def create_app():
    app = Flask(__name__)
    # Standard setup runs directly during app creation
    init_extensions(app)

    # Use explicit context only when required (e.g. DB initialization)
    with app.app_context():
        init_database()

    return app

app = create_app()""",
    },
    "got_first_request": {
        "has_verified_replacement": False,
        "recommended_approach": None,
        "why_migration_required": (
            "The app.got_first_request boolean property was deprecated in Flask 2.3.0 and removed in Flask 3.0.0. "
            "As documented in PR #4997, this property was missed when deprecating before_first_request."
        ),
        "limitations": (
            "No official replacement guidance is currently available for this API. Maintainers did not provide a replacement "
            "property because applications should not conditionally branch based on whether requests have started."
        ),
        "has_code_example": False,
        "before_code": None,
        "after_code": None,
    },
    "test_client.as_tuple": {
        "has_verified_replacement": True,
        "recommended_approach": (
            "Remove as_tuple=True from test client calls. In Flask 2.1+, test client calls consistently return a "
            "TestResponse object. The WSGI environment can be accessed directly from response.request.environ."
        ),
        "why_migration_required": (
            "The as_tuple parameter was deprecated in Werkzeug 2.0 / Flask 2.0.3 and removed in Werkzeug 2.1 / Flask 2.1.0 "
            "(PR #4417). Calling test client methods with as_tuple in Flask 2.1+ will fail."
        ),
        "limitations": (
            "Applies to Werkzeug and Flask test client calls. response.request.environ is appropriate for inspecting the "
            "WSGI environment that was previously returned as the first element of the tuple. It does not claim to be an "
            "exact drop-in replacement in every situation: test code that structurally unpacks tuples (e.g. environ, res = ...) "
            "or passes the tuple downstream must be refactored to consume the TestResponse object directly."
        ),
        "has_code_example": True,
        "before_code": """# Deprecated approach (Flask < 2.1 / Werkzeug < 2.1)
with app.test_client() as client:
    environ, response = client.get('/', as_tuple=True)
    status = response.status_code
    server = environ.get('SERVER_NAME')""",
        "after_code": """# Verified approach: Direct TestResponse (Flask 2.1+)
with app.test_client() as client:
    response = client.get('/')
    status = response.status_code
    # Access WSGI environment directly from the response if needed
    environ = response.request.environ
    server = environ.get('SERVER_NAME')""",
    },
}


@dataclass
class MigrationGuidance:
    """Structured, verified migration guidance for a Flask API."""

    symbol: str
    dep_version: Optional[str]
    rem_version: Optional[str]
    has_verified_replacement: bool
    replacement: Optional[str]                        # Verified replacement or approach (or None)
    why_migration_required: str                      # Explanation of why migration is required
    version_status: str                              # Human-readable version status
    target_version: Optional[str] = None
    target_version_evaluated: bool = False
    target_version_notice: Optional[str] = None
    evidence_links: List[Dict[str, Any]] = field(default_factory=list)
    source_quote: Optional[str] = None
    source_ref: Optional[int] = None
    evidence_completeness: str = "complete"          # "complete", "partial", "unavailable"
    limitations: Optional[str] = None
    has_code_example: bool = False
    before_code: Optional[str] = None
    after_code: Optional[str] = None
    is_supported: bool = True

    @property
    def display_replacement(self) -> str:
        """Returns the verified replacement or the exact standard unavailable notice."""
        if self.has_verified_replacement and self.replacement:
            return self.replacement
        return "No verified replacement guidance is currently available for this API."

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["display_replacement"] = self.display_replacement
        return data


def _canonicalize_symbol(symbol: str, decisions: List[Dict[str, Any]]) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Finds canonical entity name and decision dict for a query symbol or alias."""
    if not symbol or not isinstance(symbol, str):
        return None, None

    cleaned = symbol.strip()

    # Exact entity match
    for d in decisions:
        if d.get("entity") == cleaned:
            return d["entity"], d

    # Alias match
    cleaned_lower = cleaned.lower()
    for d in decisions:
        entity = d.get("entity", "")
        if entity.lower() == cleaned_lower:
            return entity, d
        for alias in d.get("aliases", []):
            if alias.lower() == cleaned_lower:
                return entity, d

    return None, None


def _extract_milestones(decision: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Extracts deprecation and removal version milestones from decision events."""
    dep_v = None
    rem_v = None
    for ev in decision.get("events", []):
        if ev.get("type") == "deprecated":
            dep_v = ev.get("version")
        elif ev.get("type") == "removed":
            rem_v = ev.get("version")
    return dep_v, rem_v


def get_migration_guidance(
    symbol: str,
    target_version: Optional[str] = None,
    decisions: Optional[List[Dict[str, Any]]] = None,
) -> Optional[MigrationGuidance]:
    """Retrieves verified migration guidance for a given Flask API symbol.

    Args:
        symbol: The API or symbol name (e.g. 'app.before_first_request', 'before_first_request', 'as_tuple').
        target_version: Optional target Flask version string (e.g. '2.3.0', '3.0.0').
        decisions: Optional pre-loaded decisions list (defaults to decisions.json).

    Returns:
        MigrationGuidance dataclass if symbol is a supported curated API, or None if unknown/unsupported.
    """
    if decisions is None:
        try:
            decisions = load_decisions()
        except Exception:
            decisions = []

    canonical_name, decision = _canonicalize_symbol(symbol, decisions)
    if not canonical_name or not decision:
        return None

    dep_v, rem_v = _extract_milestones(decision)

    # Extract source quote from rationale
    rationale = decision.get("rationale")
    source_quote = None
    source_ref = None
    if isinstance(rationale, dict):
        source_quote = rationale.get("quote")
        source_ref = rationale.get("ref")
    elif isinstance(rationale, str):
        source_quote = rationale

    # Evidence links from catalog or primary sources
    evidence_links = PRIMARY_SOURCES.get(canonical_name, [])

    # Migration registry details
    reg_entry = VERIFIED_MIGRATION_REGISTRY.get(canonical_name, {})
    has_replacement = reg_entry.get("has_verified_replacement", False)
    recommended_approach = reg_entry.get("recommended_approach")
    why_required = reg_entry.get("why_migration_required", "")
    limitations = reg_entry.get("limitations")
    has_code_ex = reg_entry.get("has_code_example", False)
    before_code = reg_entry.get("before_code")
    after_code = reg_entry.get("after_code")

    # Evaluate Version Status
    version_status = ""
    target_evaluated = False
    target_notice = None

    if target_version:
        v_clean = str(target_version).strip()
        if v_clean.lower().startswith("flask "):
            v_clean = v_clean[6:].strip()

        try:
            parsed_target = Version(v_clean)
            verified_versions = get_verified_versions(decisions)

            if parsed_target not in verified_versions:
                sorted_vers = ", ".join(sorted(str(v) for v in verified_versions))
                target_evaluated = False
                target_notice = (
                    f"Unavailable version evidence: Flask {v_clean} is not among the verified milestones "
                    f"({sorted_vers}). Lifecycle status cannot be established without verified data."
                )
                version_status = f"Status unverified for Flask {v_clean}"
            else:
                status_res = check_status(decision, parsed_target)
                target_evaluated = True
                status_label = status_res.get("status", "Unknown")
                event = status_res.get("event")
                ev_ver = event.get("version") if event else None

                if status_label == "Removed":
                    version_status = f"Removed in Flask {ev_ver or rem_v} (Incompatible with target Flask {v_clean})"
                elif status_label == "Deprecated":
                    version_status = f"Deprecated in Flask {ev_ver or dep_v} (Target Flask {v_clean})"
                elif status_label == "Not yet deprecated":
                    version_status = f"Not yet deprecated in Flask {v_clean} (Deprecated later in {dep_v})"
                else:
                    version_status = f"Lifecycle status: {status_label}"
        except InvalidVersion:
            target_evaluated = False
            target_notice = f"Invalid version format: '{target_version}'. Expected format: X.Y.Z (e.g. 2.3.0)."
            version_status = "Invalid target version format"
    else:
        # No target version specified
        target_evaluated = False
        target_notice = None
        if rem_v and dep_v:
            version_status = f"Removed in Flask {rem_v} (Deprecated in Flask {dep_v})"
        elif rem_v:
            version_status = f"Removed in Flask {rem_v}"
        elif dep_v:
            version_status = f"Deprecated in Flask {dep_v}"
        else:
            version_status = "Lifecycle milestone evidence unavailable"

    # Evidence completeness assessment
    if source_quote and evidence_links:
        completeness = "complete"
    elif evidence_links or source_quote:
        completeness = "partial"
    else:
        completeness = "unavailable"

    return MigrationGuidance(
        symbol=canonical_name,
        dep_version=dep_v,
        rem_version=rem_v,
        has_verified_replacement=has_replacement,
        replacement=recommended_approach,
        why_migration_required=why_required,
        version_status=version_status,
        target_version=target_version,
        target_version_evaluated=target_evaluated,
        target_version_notice=target_notice,
        evidence_links=evidence_links,
        source_quote=source_quote,
        source_ref=source_ref,
        evidence_completeness=completeness,
        limitations=limitations,
        has_code_example=has_code_ex,
        before_code=before_code,
        after_code=after_code,
        is_supported=True,
    )

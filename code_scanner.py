"""
Rationale — Python AST-Based Deprecated Flask API Scanner (Step 4).

Statically inspects Python source code using Python's built-in `ast` module to
detect known deprecated and removed Flask APIs from the verified catalogue:
  1. app.before_first_request
  2. got_first_request
  3. test_client.as_tuple

Security Guarantee:
  Never executes user-submitted Python code. No eval(), exec(), or runtime imports.
"""

import ast
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any, Set, Tuple
from packaging.version import Version, InvalidVersion

from version_checker import load_decisions, check_status


# Maximum source code size accepted for static scanning (1 MB / ~25,000 lines)
MAX_CODE_SIZE_BYTES = 1_000_000

# Verified evidence links for the 3 curated decisions
VERIFIED_EVIDENCE_MAP = {
    "app.before_first_request": "https://github.com/pallets/flask/issues/4605",
    "got_first_request": "https://github.com/pallets/flask/pull/4997",
    "test_client.as_tuple": "https://github.com/pallets/flask/pull/4417",
}


@dataclass
class ScanFinding:
    """Represents a single detected deprecated/removed Flask API pattern."""
    symbol: str
    file_name: str
    line: int
    col: int
    detection_type: str
    dep_version: Optional[str]
    rem_version: Optional[str]
    explanation: str
    evidence_url: Optional[str]
    status: str
    confidence: str = "high"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScanResult:
    """Result of scanning a Python source code text."""
    success: bool
    findings: List[ScanFinding] = field(default_factory=list)
    error: Optional[str] = None
    target_version: Optional[str] = None
    file_name: str = "<input>"
    lines_scanned: int = 0

    @property
    def total_findings(self) -> int:
        return len(self.findings)


def _get_decision_metadata(symbol: str) -> Dict[str, Any]:
    """Retrieves verified lifecycle metadata from decisions.json for a symbol."""
    try:
        decisions = load_decisions()
    except Exception:
        decisions = []

    for d in decisions:
        if d.get("entity") == symbol:
            return d
    return {}


def _extract_version_milestones(decision: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """Extracts deprecation and removal version strings from decision events."""
    dep_v = None
    rem_v = None
    for ev in decision.get("events", []):
        if ev.get("type") == "deprecated":
            dep_v = ev.get("version")
        elif ev.get("type") == "removed":
            rem_v = ev.get("version")
    return dep_v, rem_v


class FlaskDeprecationVisitor(ast.NodeVisitor):
    """AST NodeVisitor that identifies verified deprecated Flask patterns."""

    def __init__(self, file_name: str, decisions_map: Dict[str, Dict[str, Any]], parsed_target_version: Optional[Version]):
        self.file_name = file_name
        self.decisions_map = decisions_map
        self.parsed_target_version = parsed_target_version
        self.findings: List[ScanFinding] = []
        # Track (line, col, symbol) to avoid duplicate reporting when an AST node is visited through multiple paths
        self._seen: Set[Tuple[int, int, str]] = set()

    def _create_finding(
        self,
        symbol: str,
        line: int,
        col: int,
        detection_type: str,
    ) -> None:
        key = (line, col, symbol)
        if key in self._seen:
            return
        self._seen.add(key)

        decision = self.decisions_map.get(symbol, {})
        dep_v, rem_v = _extract_version_milestones(decision)

        explanation = ""
        rationale_meta = decision.get("rationale")
        if isinstance(rationale_meta, dict):
            explanation = rationale_meta.get("quote", "")
        elif isinstance(rationale_meta, str):
            explanation = rationale_meta

        evidence_url = VERIFIED_EVIDENCE_MAP.get(symbol)

        # Determine version-aware status
        if self.parsed_target_version and decision:
            status_info = check_status(decision, self.parsed_target_version)
            status = status_info.get("status", "Unknown")
        else:
            if rem_v:
                status = f"Removed in Flask {rem_v} (Deprecated in {dep_v or 'earlier'})"
            elif dep_v:
                status = f"Deprecated in Flask {dep_v}"
            else:
                status = "Known Deprecated/Removed API"

        self.findings.append(ScanFinding(
            symbol=symbol,
            file_name=self.file_name,
            line=line,
            col=col,
            detection_type=detection_type,
            dep_version=dep_v,
            rem_version=rem_v,
            explanation=explanation,
            evidence_url=evidence_url,
            status=status,
            confidence="high",
        ))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._check_decorators(node.decorator_list)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._check_decorators(node.decorator_list)
        self.generic_visit(node)

    def _check_decorators(self, decorator_list: List[ast.expr]) -> None:
        for dec in decorator_list:
            # e.g., @app.before_first_request or @bp.before_app_first_request
            attr_node = None
            if isinstance(dec, ast.Attribute):
                attr_node = dec
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                attr_node = dec.func

            if attr_node and attr_node.attr in ("before_first_request", "before_app_first_request"):
                self._create_finding(
                    symbol="app.before_first_request",
                    line=dec.lineno,
                    col=getattr(dec, "col_offset", 0),
                    detection_type="decorator",
                )

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Pattern 1: app.before_first_request outside decorators (e.g., app.before_first_request(handler))
        if node.attr in ("before_first_request", "before_app_first_request"):
            self._create_finding(
                symbol="app.before_first_request",
                line=node.lineno,
                col=getattr(node, "col_offset", 0),
                detection_type="attribute_access",
            )

        # Pattern 2: app.got_first_request attribute access
        elif node.attr == "got_first_request":
            self._create_finding(
                symbol="got_first_request",
                line=node.lineno,
                col=getattr(node, "col_offset", 0),
                detection_type="attribute_access",
            )

        # Pattern 3: test_client.as_tuple attribute access (e.g. client.as_tuple or test_client.as_tuple)
        elif node.attr == "as_tuple":
            # Avoid flagging arbitrary point.as_tuple or geometry.as_tuple
            is_client_access = False
            if isinstance(node.value, ast.Name) and "client" in node.value.id.lower():
                is_client_access = True
            elif isinstance(node.value, ast.Attribute) and "client" in node.value.attr.lower():
                is_client_access = True
            elif isinstance(node.value, ast.Call) and isinstance(node.value.func, ast.Attribute) and "test_client" in node.value.func.attr.lower():
                is_client_access = True

            if is_client_access:
                self._create_finding(
                    symbol="test_client.as_tuple",
                    line=node.lineno,
                    col=getattr(node, "col_offset", 0),
                    detection_type="attribute_access",
                )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Pattern 3 (Call argument): client.get('/', as_tuple=True)
        # Check if any keyword argument is 'as_tuple'
        for kw in node.keywords:
            if kw.arg == "as_tuple":
                # Ensure the call is relevant to test client (e.g. HTTP methods or client object)
                is_client_call = False
                if isinstance(node.func, ast.Attribute):
                    method_name = node.func.attr.lower()
                    http_methods = {"get", "post", "put", "delete", "patch", "head", "options", "open"}
                    if method_name in http_methods:
                        is_client_call = True
                    elif isinstance(node.func.value, ast.Name) and "client" in node.func.value.id.lower():
                        is_client_call = True
                    elif isinstance(node.func.value, ast.Attribute) and "client" in node.func.value.attr.lower():
                        is_client_call = True
                    elif isinstance(node.func.value, ast.Call) and isinstance(node.func.value.func, ast.Attribute) and "test_client" in node.func.value.func.attr.lower():
                        is_client_call = True

                if is_client_call:
                    self._create_finding(
                        symbol="test_client.as_tuple",
                        line=getattr(kw, "lineno", node.lineno),
                        col=getattr(kw, "col_offset", getattr(node, "col_offset", 0)),
                        detection_type="call_argument",
                    )

        self.generic_visit(node)


def scan_code(
    source_code: str,
    file_name: str = "<input>",
    target_version: Optional[str] = None
) -> ScanResult:
    """Statically scans Python source code text for known deprecated Flask APIs.

    Args:
        source_code: Python source code string.
        file_name: File name reported in findings (default: '<input>').
        target_version: Optional target Flask version string (e.g. '2.2.0', 'Flask 2.3.0').

    Returns:
        ScanResult containing success flag, list of ScanFinding objects, or error message.
    """
    if source_code is None:
        return ScanResult(success=True, findings=[], file_name=file_name, lines_scanned=0)

    # 1. Size guard: refuse inputs that exceed safety thresholds
    encoded_bytes = len(source_code.encode("utf-8", errors="replace"))
    if encoded_bytes > MAX_CODE_SIZE_BYTES:
        return ScanResult(
            success=False,
            findings=[],
            error=f"Source code exceeds maximum size limit of {MAX_CODE_SIZE_BYTES // 1000} KB.",
            file_name=file_name,
            lines_scanned=0,
        )

    # 2. Empty input handling
    stripped = source_code.strip()
    if not stripped:
        return ScanResult(success=True, findings=[], file_name=file_name, lines_scanned=0)

    lines_count = len(source_code.splitlines())

    # 3. Parse target Flask version if provided
    parsed_v = None
    if target_version:
        v_clean = str(target_version).strip()
        if v_clean.lower().startswith("flask "):
            v_clean = v_clean[6:].strip()
        try:
            parsed_v = Version(v_clean)
        except InvalidVersion:
            # We don't crash, but we note that version couldn't be parsed
            pass

    # 4. Safe AST parsing — NEVER execute code
    try:
        tree = ast.parse(source_code, filename=file_name)
    except SyntaxError as e:
        err_msg = f"Python SyntaxError at line {e.lineno}, col {e.offset}: {e.msg}"
        return ScanResult(
            success=False,
            findings=[],
            error=err_msg,
            file_name=file_name,
            target_version=str(parsed_v) if parsed_v else target_version,
            lines_scanned=lines_count,
        )
    except Exception as e:
        return ScanResult(
            success=False,
            findings=[],
            error=f"Failed to parse source code ({type(e).__name__}: {str(e)})",
            file_name=file_name,
            target_version=str(parsed_v) if parsed_v else target_version,
            lines_scanned=lines_count,
        )

    # 5. Build decision lookup cache
    try:
        decisions = load_decisions()
        decisions_map = {d.get("entity"): d for d in decisions if d.get("entity")}
    except Exception:
        decisions_map = {}

    # 6. Traverse AST with visitor
    visitor = FlaskDeprecationVisitor(
        file_name=file_name,
        decisions_map=decisions_map,
        parsed_target_version=parsed_v,
    )
    visitor.visit(tree)

    # Sort findings deterministically by line and column
    visitor.findings.sort(key=lambda f: (f.line, f.col))

    return ScanResult(
        success=True,
        findings=visitor.findings,
        error=None,
        target_version=str(parsed_v) if parsed_v else target_version,
        file_name=file_name,
        lines_scanned=lines_count,
    )

import os
import html
import base64
import requests
from PIL import Image
import streamlit as st
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
from typing import import Optional
import code_scanner
import pr_analyzer
import alert_engine
import migration_guidance
import importlib

# Ensure fresh module imports under long-running Streamlit servers
if not hasattr(code_scanner, "get_last_scan_result"):
    try:
        importlib.reload(code_scanner)
    except Exception:
        pass


def get_last_scan_result_safe():
    """Safely retrieve the last scan result without raising AttributeError."""
    fn = getattr(code_scanner, "get_last_scan_result", None)
    if callable(fn):
        return fn()
    return getattr(code_scanner, "_LAST_SCAN_RESULT", None)

load_dotenv()

# ── Paths & Config ───────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(__file__)
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
FAVICON_PATH = LOGO_PATH if os.path.exists(LOGO_PATH) else os.path.join(BASE_DIR, "assets", "favicon.png")
BG_PATH = os.path.join(BASE_DIR, "assets", "bg.png") if os.path.exists(os.path.join(BASE_DIR, "assets", "bg.png")) else os.path.join(BASE_DIR, "assets", "image.png")

# Load Favicon
favicon_img = Image.open(FAVICON_PATH) if os.path.exists(FAVICON_PATH) else None

st.set_page_config(
    page_title="Rationale",
    page_icon=favicon_img,
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Base64 Assets for CSS & Favicon Injection ────────────────────────────────

@st.cache_data
def get_asset_b64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

def clean_html(html_str: str) -> str:
    """Removes leading indentation and blank lines so Markdown parsers
    never treat indented HTML as code blocks.
    """
    return "\n".join(line.strip() for line in html_str.splitlines() if line.strip())


def status_badge_class(status) -> str:
    """Return a safe, status-specific CSS class for decision badges."""
    normalized = str(status or "unknown").strip().lower().replace(" ", "-")
    allowed_statuses = {"removed", "deprecated", "active", "retained", "unknown"}
    if normalized not in allowed_statuses:
        normalized = "unknown"
    return f"pill-status pill-status-{normalized}"


def severity_badge_class(severity: str) -> str:
    """Return CSS class for rule-based alert severity pills."""
    s = str(severity or "").strip().lower()
    if "critical" in s:
        return "pill-status severity-pill-critical"
    elif "high" in s:
        return "pill-status severity-pill-high"
    elif "medium" in s:
        return "pill-status severity-pill-medium"
    return "pill-status severity-pill-informational"


def alert_status_badge_class(status: str) -> str:
    """Return CSS class for alert workflow status (New, Needs Review, Resolved)."""
    s = str(status or "").strip().lower()
    if "resolved" in s:
        return "pill-status alert-status-resolved"
    elif "review" in s:
        return "pill-status alert-status-needs-review"
    return "pill-status alert-status-new"

bg_b64 = get_asset_b64(BG_PATH)
logo_b64 = get_asset_b64(LOGO_PATH)

# ── Neo4j Config ─────────────────────────────────────────────────────────────

def get_config(key):
    value = os.getenv(key)
    if value:
        return value
    try:
        return st.secrets.get(key)
    except Exception:
        return None


URL = get_config("NEO4J_HTTP_URL")
USER = get_config("NEO4J_USERNAME")
PASSWORD = get_config("NEO4J_PASSWORD")
DATABASE = get_config("NEO4J_DATABASE")
ENDPOINT = f"{URL}/db/{DATABASE}/query/v2" if URL and DATABASE else None

# Verified Reference Metadata (Official Pallets Issues and PRs)
VERIFIED_REF_METADATA = {
    4605: {"label": "GitHub Issue #4605", "url": "https://github.com/pallets/flask/issues/4605", "type": "issue"},
    4995: {"label": "Pull Request #4995", "url": "https://github.com/pallets/flask/pull/4995", "type": "pr"},
    4997: {"label": "Pull Request #4997", "url": "https://github.com/pallets/flask/pull/4997", "type": "pr"},
    5223: {"label": "Pull Request #5223", "url": "https://github.com/pallets/flask/pull/5223", "type": "pr"},
    4341: {"label": "Pull Request #4341", "url": "https://github.com/pallets/flask/pull/4341", "type": "pr"},
    4417: {"label": "Pull Request #4417", "url": "https://github.com/pallets/flask/pull/4417", "type": "pr"},
}

# Curated Fallback Data (100% consistent with verified decisions.json records)
CURATED_DATA = {
    "app.before_first_request": {
        "entity": "app.before_first_request",
        "category": "Flask — Lifecycle Hook",
        "status": "removed",
        "dep_version": "v2.2.0",
        "rem_version": "v2.3.0",
        "subtitle": "Deprecated in Flask 2.2.0",
        "aliases": ["before_first_request", "before_app_first_request", "app.before_first_request"],
        "rationale": "Configuration should be done before _running_ the application, during the actual setup phase. Preferably, it should be done in a factory function.",
        "evidence": [
            {"label": "GitHub Issue #4605", "url": "https://github.com/pallets/flask/issues/4605", "type": "issue"},
            {"label": "Pull Request #4995", "url": "https://github.com/pallets/flask/pull/4995", "type": "pr"}
        ],
        "events": [
            {"type": "deprecated", "version": "2.2.0", "ref": 4605, "merged_at": None},
            {"type": "removed", "version": "2.3.0", "ref": 4995, "merged_at": "2023-02-23T16:45:39Z"}
        ]
    },
    "got_first_request": {
        "entity": "got_first_request",
        "category": "Flask — Request State",
        "status": "removed",
        "dep_version": "v2.3.0",
        "rem_version": "v3.0.0",
        "subtitle": "Deprecated in Flask 2.3.0",
        "aliases": ["got_first_request"],
        "rationale": "This property was missed when deprecating `before_first_request`.",
        "evidence": [
            {"label": "Pull Request #4997", "url": "https://github.com/pallets/flask/pull/4997", "type": "pr"},
            {"label": "Pull Request #5223", "url": "https://github.com/pallets/flask/pull/5223", "type": "pr"}
        ],
        "events": [
            {"type": "deprecated", "version": "2.3.0", "ref": 4997, "merged_at": None},
            {"type": "removed", "version": "3.0.0", "ref": 5223, "merged_at": "2023-08-16T22:08:53Z"}
        ]
    },
    "test_client.as_tuple": {
        "entity": "test_client.as_tuple",
        "category": "Flask — Test Client",
        "status": "removed",
        "dep_version": "v2.0.3",
        "rem_version": "v2.1.0",
        "subtitle": "Deprecated in Flask 2.0.3",
        "aliases": ["test_client.as_tuple", "as_tuple", "test_client as_tuple"],
        "rationale": "This was deprecated in Werkzeug 2.0, and is no longer supported in Werkzeug 2.1 or Flask 2.1.",
        "evidence": [
            {"label": "Pull Request #4341", "url": "https://github.com/pallets/flask/pull/4341", "type": "pr"},
            {"label": "Pull Request #4417", "url": "https://github.com/pallets/flask/pull/4417", "type": "pr"}
        ],
        "events": [
            {"type": "deprecated", "version": "2.0.3", "ref": 4341, "merged_at": "2021-11-15T21:24:49Z"},
            {"type": "removed", "version": "2.1.0", "ref": 4417, "merged_at": "2022-01-14T17:38:02Z"}
        ]
    }
}

# Verified Migration Guidance
MIGRATION_DATA = {
    "app.before_first_request": {
        "official_guidance": "Configuration should be done before _running_ the application, during the actual setup phase. Preferably, it should be done in a factory function. (Source: Pallets / Flask GitHub Issue #4605)",
        "explanation": "The @app.before_first_request hook was deprecated in Flask 2.2.0 and removed in Flask 2.3.0. Application setup should occur explicitly during application creation, preferably within an application factory function (create_app()). Standard setup tasks (registering blueprints, loading config, initializing extensions via .init_app()) run directly on the app instance without an application context. An application context (with app.app_context():) is only needed for operations that explicitly require active context access (such as creating database tables with db.create_all() or inspecting current_app).",
        "compatibility": "Deprecated in Flask 2.2.0; removed in Flask 2.3.0. Calling @app.before_first_request in Flask 2.3+ will raise an AttributeError.",
        "before_code": """# Illustrative Example: Deprecated approach (Flask < 2.3)
from flask import Flask

app = Flask(__name__)

@app.before_first_request
def setup_app():
    # Misused as deferred setup hook on first request
    init_db()""",
        "after_code": """# Illustrative Example: Recommended migration (Flask 2.3+)
from flask import Flask

def create_app():
    app = Flask(__name__)
    app.config.from_prefixed_env()

    # 1. Standard setup runs directly on the app instance (no context needed)
    init_extensions(app)
    register_blueprints(app)

    # 2. Only tasks requiring active app context use 'with app.app_context():'
    # (e.g. creating tables in standalone scripts or inspecting current_app)
    with app.app_context():
        init_db()

    return app

app = create_app()"""
    },
    "got_first_request": {
        "official_guidance": "No official replacement documented in the sources reviewed.",
        "explanation": "The app.got_first_request attribute was deprecated in Flask 2.3.0 and removed in Flask 3.0.0. As documented in PR #4997, it was missed during the earlier deprecation of before_first_request. Modern Flask applications avoid stateful checks on whether requests have started; all setup should happen before the server begins serving.",
        "compatibility": "Deprecated in Flask 2.3.0; removed in Flask 3.0.0. Accessing app.got_first_request in Flask 3.0+ will raise an AttributeError.",
        "before_code": """# Illustrative Example: Deprecated approach (Flask < 3.0)
if not app.got_first_request:
    # State check for whether a request has occurred
    perform_startup_check()""",
        "after_code": """# No official replacement documented in the sources reviewed.
# Refactor architecture to perform startup checks before serving,
# or use application context / explicit health-check routes."""
    },
    "test_client.as_tuple": {
        "official_guidance": "The test client's as_tuple parameter is deprecated and will be removed in Werkzeug 2.1. It is now also deprecated in Flask, to be removed in Flask 2.1, while remaining compatible with both in 2.0.x. Use response.request.environ instead. (Source: PR #4341, PR #4417, CHANGES.rst)",
        "explanation": "In Werkzeug < 2.1 and Flask < 2.1, calling the test client with as_tuple=True returned a (environ, response) 2-tuple. The parameter was removed so test client calls consistently return a TestResponse object. The WSGI environment is accessible directly via response.request.environ.",
        "compatibility": "Deprecated in Werkzeug 2.0 / Flask 2.0.3; removed in Werkzeug 2.1 / Flask 2.1.0.",
        "before_code": """# Illustrative Example: Deprecated approach (Flask < 2.1)
with app.test_client() as client:
    environ, response = client.get('/', as_tuple=True)
    status = response.status_code
    server = environ.get('SERVER_NAME')""",
        "after_code": """# Illustrative Example: Recommended migration (Flask 2.1+)
with app.test_client() as client:
    response = client.get('/')
    status = response.status_code
    # Access WSGI environment from response.request.environ
    server = response.request.environ.get('SERVER_NAME')"""
    }
}

# Generic search terms disbarred from accidental short/generic matching
GENERIC_TERMS = {
    "a", "an", "the", "app", "flask", "why", "what", "how", "code",
    "function", "method", "test", "client", "request", "is", "like", "this"
}

# ── Data Query Helpers ───────────────────────────────────────────────────────

def run_query(statement, parameters=None):
    """Executes a Cypher query against Neo4j HTTP endpoint with safe error handling."""
    if not ENDPOINT or not USER or not PASSWORD:
        return None, "Database endpoint or credentials not configured"
    try:
        response = requests.post(
            ENDPOINT,
            auth=HTTPBasicAuth(USER, PASSWORD),
            json={"statement": statement, "parameters": parameters or {}},
            timeout=15
        )
        response.raise_for_status()
        result = response.json()
        if result.get("errors"):
            return None, f"Neo4j query error: {result['errors']}"
        return result.get("data", {}).get("values", []), None
    except requests.exceptions.RequestException as e:
        # Diagnostic message without exposing credentials
        return None, f"Neo4j connection error ({type(e).__name__})"
    except Exception as e:
        return None, f"Database error ({type(e).__name__})"

def query_neo4j_decision(question):
    """Queries Neo4j first for a matching decision, change events, and evidence."""
    query = """
    MATCH (d:Decision)
    WHERE toLower($question) CONTAINS toLower(d.entity)
       OR any(alias IN d.aliases WHERE toLower($question) CONTAINS toLower(alias))
    OPTIONAL MATCH (d)-[:HAS_EVENT]->(ev:ChangeEvent)
    OPTIONAL MATCH (d)-[:SUPPORTED_BY]->(e:Evidence)
    RETURN d.entity, d.status, d.aliases,
           collect(DISTINCT {type: ev.type, version: ev.version, ref: ev.ref, merged_at: ev.merged_at}) AS events,
           collect(DISTINCT {quote: e.quote, url: e.url, ref: e.ref}) AS evidence
    """
    rows, err = run_query(query, {"question": question})
    if err:
        return None, err
    if not rows:
        return None, None

    entity, status, aliases, events, evidence = rows[0]

    dep_v = "Unknown"
    rem_v = "Unknown"
    for ev in events:
        v_str = str(ev.get("version") or "").strip()
        if not v_str:
            continue
        v_fmt = v_str if v_str.startswith("v") else f"v{v_str}"
        if ev.get("type") == "deprecated":
            dep_v = v_fmt
        elif ev.get("type") == "removed":
            rem_v = v_fmt

    quote = None
    for it in evidence:
        if it.get("quote") and str(it["quote"]).strip():
            quote = str(it["quote"]).strip()
            break

    # Strictly avoid fallback that invents or fabricates a rationale when evidence quote is missing
    has_rationale = bool(quote)
    rationale = quote if has_rationale else None

    ev_list = []
    seen_urls = set()
    for it in evidence:
        u = it.get("url")
        ref_num = it.get("ref")
        if u and u not in seen_urls:
            seen_urls.add(u)
            meta = VERIFIED_REF_METADATA.get(ref_num, {})
            label = meta.get("label", f"Evidence #{ref_num}")
            ev_list.append({"label": label, "url": u, "type": meta.get("type", "pr"), "ref": ref_num})

    for ev in events:
        ref_num = ev.get("ref")
        if ref_num in VERIFIED_REF_METADATA:
            meta = VERIFIED_REF_METADATA[ref_num]
            if meta["url"] not in seen_urls:
                seen_urls.add(meta["url"])
                ev_list.append({"label": meta["label"], "url": meta["url"], "type": meta["type"], "ref": ref_num})

    category = CURATED_DATA.get(entity, {}).get("category", "Flask — Decision")

    return {
        "entity": entity,
        "category": category,
        "status": status or "removed",
        "dep_version": dep_v,
        "rem_version": rem_v,
        "subtitle": f"Deprecated in Flask {dep_v.lstrip('v')}",
        "rationale": rationale,
        "has_rationale": has_rationale,
        "rationale_status": "verified" if has_rationale else "missing_evidence",
        "evidence": ev_list,
        "events": events,
        "source": "Neo4j"
    }, None

def is_generic_query(question):
    """Checks if a query is empty, too short, or a generic term."""
    if not question:
        return True
    q_clean = question.strip().lower()
    return len(q_clean) < 3 or q_clean in GENERIC_TERMS

def find_decision(question):
    """Retrieval flow:
    1. Guard against empty/too short/generic queries.
    2. Query Neo4j first for matching decision.
    3. If Neo4j is unavailable or no record exists, fallback to CURATED_DATA.
    4. Return None for unknown queries.
    """
    if is_generic_query(question):
        return None
    q_clean = question.strip().lower()

    # Step 1: Query Neo4j FIRST
    neo_result, neo_error = query_neo4j_decision(question)
    if neo_result:
        return neo_result

    # Step 2: Fallback to CURATED_DATA with strict matching
    for key, val in CURATED_DATA.items():
        key_matches = (
            key.lower() == q_clean 
            or key.lower() in q_clean 
            or any(alias.lower() == q_clean or alias.lower() in q_clean for alias in val.get("aliases", []))
        )
        if key_matches:
            result = dict(val)
            rat = result.get("rationale")
            has_rat = bool(rat and str(rat).strip())
            result["has_rationale"] = has_rat
            result["rationale"] = str(rat).strip() if has_rat else None
            result["rationale_status"] = "verified" if has_rat else "missing_evidence"
            result["source"] = "Local fallback"
            result["db_note"] = neo_error or "Neo4j returned no matching record; showing bundled data."
            return result

    return None

def render_migration_guidance_component(symbol: str, target_version: Optional[str] = None):
    """Renders evidence-backed migration guidance for a detected API (Step 7)."""
    guidance = migration_guidance.get_migration_guidance(symbol, target_version=target_version)
    if not guidance:
        st.markdown(clean_html("""
        <div style="font-size: 0.88rem; color: var(--text-muted); padding: 0.85rem 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin: 0.8rem 0;">
            <strong style="color: var(--text-secondary);">No verified migration guidance available:</strong> This symbol is not present in the currently supported curated Flask dataset. Rationale refuses to infer or fabricate replacement guidance.
        </div>
        """), unsafe_allow_html=True)
        return

    st.markdown(clean_html("""
    <div class="migration-header-wrap" style="margin-top: 0.6rem; margin-bottom: 0.6rem;">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8B6FD6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M16 3h5v5"></path>
            <path d="M4 20L21 3"></path>
            <path d="M21 16v5h-5"></path>
            <path d="M15 15l6 6"></path>
            <path d="M4 4l5 5"></path>
        </svg>
        <span class="detail-section-title" style="margin:0;">Verified Migration Guidance</span>
        <span class="illustrative-pill">Primary Evidence</span>
    </div>
    """), unsafe_allow_html=True)

    # 1. Verified replacement or explicit refusal notice
    if guidance.has_verified_replacement and guidance.replacement:
        st.markdown(clean_html(f"""
        <div class="alert-rec-box" style="margin-bottom: 0.8rem;">
            <strong>Verified Replacement / Approach:</strong> {html.escape(guidance.replacement)}
        </div>
        """), unsafe_allow_html=True)
    else:
        st.markdown(clean_html("""
        <div style="font-size: 0.88rem; color: #FCA5A5; padding: 0.75rem 1rem; background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 8px; margin-bottom: 0.8rem;">
            <strong>No verified replacement guidance is currently available for this API.</strong>
        </div>
        """), unsafe_allow_html=True)

    # 2. Why migration is required
    st.markdown(clean_html(f"""
    <div class="rationale-quote-box" style="margin-bottom: 0.8rem;">
        <div style="font-size: 0.8rem; color: #C4B5FD; font-weight: 600; margin-bottom: 0.35rem; text-transform: uppercase; letter-spacing: 0.05em;">Why Migration Is Required</div>
        <div style="color: var(--text-secondary); font-size: 0.88rem; line-height: 1.6;">{html.escape(guidance.why_migration_required)}</div>
    </div>
    """), unsafe_allow_html=True)

    # 3. Version status & target notice if present
    if guidance.target_version_notice:
        st.caption(f"⚠️ {guidance.target_version_notice}")
    elif guidance.version_status:
        st.caption(f"**Lifecycle Status:** {guidance.version_status}")

    # 4. Verified maintainer quote if available
    if guidance.source_quote:
        ref_label = f" (Ref: #{guidance.source_ref})" if guidance.source_ref else ""
        st.markdown(clean_html(f"""
        <div style="font-size: 0.84rem; color: #E2E8F0; font-style: italic; padding: 0.6rem 0.9rem; background: rgba(255,255,255,0.03); border-left: 3px solid #8B6FD6; border-radius: 4px; margin: 0.6rem 0;">
            "{html.escape(guidance.source_quote)}"{ref_label}
        </div>
        """), unsafe_allow_html=True)

    # 5. Primary source links
    if guidance.evidence_links:
        ev_items = []
        for ev in guidance.evidence_links:
            ev_items.append(f'<a href="{ev["url"]}" target="_blank" style="color:#C4B5FD; text-decoration:underline; font-size:0.83rem; margin-right:1rem;">{html.escape(ev["label"])}</a>')
        st.markdown(clean_html(f"""
        <div style="margin: 0.5rem 0 0.8rem;">
            <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase;">Primary Sources: </span>
            {''.join(ev_items)}
        </div>
        """), unsafe_allow_html=True)

    # 6. Limitations notice if present
    if guidance.limitations:
        st.caption(f"ℹ️ **Note & Limitations:** {guidance.limitations}")

    # 7. Optional code example (ONLY if explicitly supported by reliable evidence)
    if guidance.has_code_example and guidance.before_code and guidance.after_code:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        col_b, col_a = st.columns(2)
        with col_b:
            st.markdown("**Before** *(Illustrative example)*")
            st.code(guidance.before_code, language="python")
        with col_a:
            st.markdown("**After** *(Verified approach)*")
            st.code(guidance.after_code, language="python")


def get_events_for_symbol(symbol: str) -> list:
    """Finds verified change events for an API symbol from CURATED_DATA."""
    if not symbol:
        return []
    sym_clean = symbol.strip().lower()
    for k, v in CURATED_DATA.items():
        if k.lower() == sym_clean or k.lower() in sym_clean or sym_clean in k.lower():
            return v.get("events", [])
        aliases = [a.lower() for a in v.get("aliases", [])]
        if any(a == sym_clean or a in sym_clean or sym_clean in a for a in aliases):
            return v.get("events", [])
    return []


def render_lifecycle_events_component(events_or_symbol, title: str = "Lifecycle Change Events"):
    """Renders verified Change Events (HAS_EVENT) in a responsive glass grid."""
    if isinstance(events_or_symbol, str):
        events = get_events_for_symbol(events_or_symbol)
    else:
        events = events_or_symbol or []

    if not events:
        return

    sorted_events = sorted(events, key=lambda ev: (0 if ev.get("type") == "deprecated" else 1))

    cards_html = ""
    for ev in sorted_events:
        ev_type = str(ev.get("type", "")).lower()
        badge_cls = "event-type-deprecated" if ev_type == "deprecated" else "event-type-removed"
        ev_type_label = "Deprecated Event" if ev_type == "deprecated" else "Removal Event"
        ev_ver = ev.get("version", "N/A")
        ev_ref = ev.get("ref", "")
        ev_date = ev.get("merged_at", "")
        date_str = f"Merged: {ev_date[:10]}" if ev_date else "Recorded in official Flask repo"
        ref_meta = VERIFIED_REF_METADATA.get(ev_ref, {})
        ref_label = ref_meta.get("label", f"Ref #{ev_ref}")
        ref_url = ref_meta.get("url", "")

        ref_link_html = f'<a href="{ref_url}" target="_blank" class="event-ref-link">{github_svg}<span>{ref_label}</span>{ext_arrow_svg}</a>' if ref_url else f'<span class="event-ref-label">{ref_label}</span>'

        cards_html += f"""
        <div class="event-card">
            <div class="event-card-header">
                <span class="event-type-badge {badge_cls}">{ev_type_label}</span>
                <span class="event-version-pill">Flask {ev_ver}</span>
            </div>
            <div class="event-meta-row" style="margin-top: 0.45rem;">
                <span>Reference:</span>
                {ref_link_html}
            </div>
            <div class="event-meta-row" style="color: var(--text-muted); font-size: 0.74rem;">
                <span>Milestone Date:</span>
                <span>{date_str}</span>
            </div>
        </div>
        """

    st.markdown(clean_html(f"""
    <div style="margin: 1.2rem 0 0.8rem 0;">
        <div class="detail-section-title" style="margin-bottom: 0.6rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            <span>{title}</span>
            <span class="step-tag" style="margin-left: 0.4rem; font-size: 0.68rem;">HAS_EVENT</span>
        </div>
        <div class="lifecycle-events-grid">
            {cards_html}
        </div>
    </div>
    """), unsafe_allow_html=True)


def log_workflow_event(event_type: str, entity: str, detail: str, source: str = "User Action", new_status: Optional[str] = None):
    """Logs and dispatches an event in session state for audit trail & workflow management."""
    import datetime
    if "event_log" not in st.session_state:
        st.session_state["event_log"] = []

    now_str = datetime.datetime.now().strftime("%H:%M:%S")
    entry = {
        "time": now_str,
        "type": event_type,
        "entity": entity,
        "detail": detail,
        "source": source,
        "new_status": new_status,
    }
    st.session_state["event_log"].append(entry)


def render_event_audit_log_component():
    """Renders an interactive Event Management & Audit Log panel."""
    events = st.session_state.get("event_log", [])
    with st.expander(f"🛡️ Event Management & Session Audit Trail ({len(events)} events recorded)", expanded=False):
        col_act1, col_act2 = st.columns([3, 1])
        with col_act1:
            st.caption("Real-time event handling system tracking API lifecycle triggers, scan events, and alert state transitions.")
        with col_act2:
            if st.button("Clear Event Log", key="clear_events_btn", use_container_width=True):
                st.session_state["event_log"] = []
                st.rerun()

        if not events:
            st.markdown(clean_html("""
            <div style="padding: 1rem; text-align: center; color: var(--text-muted); font-size: 0.85rem;">
                No workflow events recorded in the current session. Perform a scan or update an alert status to trigger events.
            </div>
            """), unsafe_allow_html=True)
        else:
            rows_html = ""
            for ev in reversed(events[-20:]):
                type_cls = "source-neo4j" if "STATUS" in ev["type"] else "source-fallback"
                rows_html += f"""
                <tr>
                    <td><code>{ev['time']}</code></td>
                    <td><span class="source-badge {type_cls}" style="font-size:0.7rem; padding:0.15rem 0.5rem;">{html.escape(ev['type'])}</span></td>
                    <td><strong>{html.escape(ev['entity'])}</strong></td>
                    <td>{html.escape(ev['detail'])}</td>
                    <td><span style="color:var(--text-muted); font-size:0.75rem;">{html.escape(ev['source'])}</span></td>
                </tr>
                """
            st.markdown(clean_html(f"""
            <div style="overflow-x: auto; width: 100%;">
                <table class="events-audit-table">
                    <thead>
                        <tr>
                            <th>Time</th>
                            <th>Event Type</th>
                            <th>Target Entity</th>
                            <th>Event Details</th>
                            <th>Source</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows_html}
                    </tbody>
                </table>
            </div>
            """), unsafe_allow_html=True)


def render_migration_and_timeline(decision_data):
    """Renders migration guidance (Before vs After) and historical timeline using clean Streamlit components."""
    entity = decision_data.get("entity", "")
    has_rationale = decision_data.get("has_rationale", True) and bool(decision_data.get("rationale"))
    if not has_rationale:
        st.markdown(clean_html("""
        <div style="font-size: 0.88rem; color: var(--text-muted); padding: 0.85rem 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 8px; margin-bottom: 1.2rem;">
            <strong style="color: var(--text-secondary);">Migration Guidance Refusal:</strong> No verified replacement or migration guidance is documented for this decision. This system refuses to invent or infer migration recommendations without verified sources.
        </div>
        """), unsafe_allow_html=True)
    else:
        render_migration_guidance_component(entity)

    events = decision_data.get("events", [])
    if events:
        render_lifecycle_events_component(events, title="Historical Change Events")

# ── Session State Handling ───────────────────────────────────────────────────

# Sync with query params
query_params = st.query_params
if "page" in query_params:
    st.session_state.nav = query_params["page"]
elif "nav" not in st.session_state:
    st.session_state.nav = "home"

if "decision" in query_params:
    st.session_state.selected_decision = query_params["decision"]
elif "selected_decision" not in st.session_state:
    st.session_state.selected_decision = "app.before_first_request"

if "search_query" not in st.session_state:
    st.session_state.search_query = ""

# ── SaaS Developer-Tool Design System & CSS ───────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    --bg-dark: #0A0A0F;
    --surface: rgba(22, 18, 36, 0.72);
    --surface-card: rgba(26, 21, 42, 0.75);
    --surface-hover: rgba(38, 30, 60, 0.65);
    --surface-solid: #13101E;
    --border: rgba(196, 181, 253, 0.14);
    --border-hover: rgba(167, 139, 250, 0.45);
    --accent: #A78BFA;
    --accent-hover: #C4B5FD;
    --accent-muted: rgba(167, 139, 250, 0.12);
    --accent-border: rgba(167, 139, 250, 0.32);
    --accent-glow: rgba(143, 120, 217, 0.25);
    --text-primary: #FFFFFF;
    --text-secondary: #E2E8F0;
    --text-muted: #94A3B8;
    --text-lavender: #DDD6FE;
    --glass-blur: blur(16px);
    --glass-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
}

* {
    box-sizing: border-box;
}

/* 1. Global Typography */
html, body, .stApp, h1, h2, h3, p, label, button, input {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

html, body, [data-testid="stApp"] {
    color: var(--text-primary);
    background-color: var(--bg-dark);
}

/* Clean dark background: no harsh white lines on pure black */
[data-testid="stApp"] {
    background-color: #0A0A0F;
    background-image: none !important;
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
}

/* Hide Streamlit heading anchor links / chain icons */
[data-testid="stHeaderActionElements"],
h1 a, h2 a, h3 a,
.hero-title a,
a[data-testid="stHeaderActionElements"],
div[data-testid="stHeaderActionElements"],
.stHeading a,
a.anchorjs-link {
    display: none !important;
    visibility: hidden !important;
    opacity: 0 !important;
    pointer-events: none !important;
    width: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

/* 2. ZERO OUT TOP NAVBAR GAP COMPLETELY */
header[data-testid="stHeader"], [data-testid="stHeader"] {
    display: none !important;
    height: 0px !important;
    min-height: 0px !important;
    max-height: 0px !important;
    padding: 0 !important;
    margin: 0 !important;
    visibility: hidden !important;
}

[data-testid="stDecoration"], [data-testid="stToolbar"], div.stAppDeployButton {
    display: none !important;
    height: 0px !important;
    margin: 0 !important;
    padding: 0 !important;
}

.main, [data-testid="stAppViewContainer"], [data-testid="stMain"], section[data-testid="stMain"] {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

.main .block-container, 
[data-testid="stAppViewContainer"] .block-container, 
[data-testid="stAppViewBlockContainer"],
[data-testid="stMainBlockContainer"],
.block-container {
    max-width: 100% !important;
    padding-left: 5% !important;
    padding-right: 5% !important;
    padding-top: 0.15rem !important;
    margin-top: 0 !important;
    padding-bottom: 4rem !important;
    position: relative !important;
    z-index: 1 !important;
}

[data-testid="stVerticalBlock"] {
    gap: 0.6rem !important;
}

[data-testid="stVerticalBlock"]:first-child,
[data-testid="stVerticalBlock"] > div:first-child,
div[data-testid="stElementContainer"]:first-child {
    padding-top: 0 !important;
    margin-top: 0 !important;
}

/* Collapse empty Streamlit markdown/style/script containers that add gap */
div[data-testid="stElementContainer"]:has(script),
div[data-testid="stElementContainer"]:has(style),
div[data-testid="stElementContainer"]:has([data-testid="stMarkdownContainer"]:empty),
div[data-testid="stMarkdownContainer"]:empty {
    display: none !important;
    margin: 0 !important;
    padding: 0 !important;
    height: 0 !important;
    position: absolute !important;
}

/* Default for other pages: simple black without home hero glow */
.block-container::before {
    content: none !important;
}

#MainMenu, footer {
    display: none !important;
}

/* 3. Link Overrides (No default Streamlit blue) */
a, a:visited {
    text-decoration: none !important;
    color: inherit !important;
}

.brand-container, .brand-container:visited {
    color: #F4F2FA !important;
}

.decision-badge, .decision-badge:visited {
    color: #8B6FD6 !important;
}

/* ── Motion & Keyframes ───────────────────────────────────────────────────── */
@keyframes fade-up {
    from {
        opacity: 0;
        transform: translateY(24px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.hero-container, .feature-card, .detail-panel, .decision-card-item, .methodology-card, .glass-box {
    animation: fade-up 0.7s ease forwards;
}

@media (prefers-reduced-motion: reduce) {
    *, .hero-container, .feature-card, .detail-panel, .decision-card-item, .methodology-card, .home-section, .cta-panel, .home-footer, .glass-box {
        animation: none !important;
        transition: none !important;
    }
}


/* ── Home / About content sections (stacked, glass) ───────────────────────── */
.home-section {
    width: 100%;
    max-width: 980px;
    margin: 6rem auto 0;
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 1.4rem;
    animation: fade-up 0.7s ease both;
}
.sec-head { text-align: center; display: flex; flex-direction: column; align-items: center; gap: 1rem; }
.sec-pill {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem; font-weight: 500; letter-spacing: 0.14em; text-transform: uppercase;
    color: #D4C9F7; background: rgba(196,181,253,0.10);
    border: 1px solid rgba(196,181,253,0.30); border-radius: 9999px; padding: 0.38rem 0.95rem;
}
.sec-title {
    font-size: clamp(1.9rem, 4vw, 3rem); font-weight: 300; line-height: 1.15; letter-spacing: -0.03em; margin: 0;
    background: linear-gradient(180deg, #FFFFFF 0%, #F3F0FE 50%, #E2D9FD 100%);
    -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; color: #fff;
}
.sec-sub { font-size: 1.02rem; line-height: 1.7; color: rgba(235,229,252,0.72); max-width: 680px; margin: 0; }
.glass-box {
    background: linear-gradient(145deg, rgba(255,255,255,0.075), rgba(255,255,255,0.025));
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(196,181,253,0.18); border-radius: 22px; padding: 1.6rem 1.9rem;
    box-shadow: 0 10px 40px rgba(10,6,24,0.35), inset 0 1px 0 rgba(255,255,255,0.08);
    transition: transform .25s ease, border-color .25s ease;
}
.glass-box:hover { transform: translateY(-2px); border-color: rgba(196,181,253,0.38); }
.glass-box h4 { padding:0 !important; margin: 0 0 .4rem !important; font-size: 1.08rem; font-weight: 600; color: #fff; letter-spacing: -0.01em; }
.glass-box p { margin: 0 !important; padding:0 !important; font-size: .96rem; line-height: 1.7; color: rgba(235,229,252,0.76); }
.glass-row { display: flex; align-items: flex-start; gap: 1.1rem; }
.glass-ico {
    flex: 0 0 auto; width: 44px; height: 44px; border-radius: 12px; display: flex; align-items: center; justify-content: center;
    color: #D4C9F7; background: rgba(196,181,253,0.12); border: 1px solid rgba(196,181,253,0.28);
}
.step-tag { font-family: 'JetBrains Mono', monospace; font-size: .74rem; letter-spacing: .14em; color: #C4B5FD; margin-bottom: .35rem; display:block; }
.flow-link { display:flex; justify-content:center; height: 26px; }
.flow-link::before { content:""; width:1px; height:100%; background: linear-gradient(to bottom, rgba(196,181,253,0.7), rgba(196,181,253,0.1)); }
.code-win {
    background: rgba(8,6,16,0.78); border: 1px solid rgba(196,181,253,0.2); border-radius: 16px; overflow: hidden;
    backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
}
.code-win-bar { display:flex; align-items:center; gap:7px; padding: .7rem 1rem; border-bottom: 1px solid rgba(255,255,255,0.08); background: rgba(255,255,255,0.035); }
.code-win-bar i { width:10px; height:10px; border-radius:50%; background: rgba(255,255,255,0.22); display:block; }
.code-win-bar span { margin-left: .6rem; font-family:'JetBrains Mono',monospace; font-size:.76rem; color: rgba(235,229,252,0.66); }
.code-win pre { margin:0 !important; padding: 1.2rem 1.4rem !important; font-family:'JetBrains Mono',monospace; font-size:.86rem; line-height:1.75; color:#E8E2FB; overflow-x:auto; white-space:pre; background:transparent; border:none; }
.code-win .kw { color:#C4B5FD; } .code-win .err { color:#F5B5C8; } .code-win .str { color:#B8E0C8; }
.q-line { border-left: 3px solid #C4B5FD; padding: .35rem 0 .35rem 1.1rem; font-size: 1.04rem; color: rgba(245,242,255,0.92); }
.closing-line { text-align:center; font-size: 1.12rem; color:#E2D9FD; font-weight:500; margin-top:.4rem; }
.check-list { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:.75rem; }
.check-list li { display:flex; gap:.7rem; align-items:flex-start; color: rgba(245,242,255,0.88); font-size:.98rem; line-height:1.55; }
.check-list li svg { flex:0 0 auto; margin-top:3px; color:#C4B5FD; }
.mono-chip { font-family:'JetBrains Mono',monospace; font-size:.82rem; color:#D4C9F7; }
.note-muted { text-align:center; font-size:.9rem; color: rgba(235,229,252,0.62); font-style: italic; margin: .4rem auto 0; max-width: 620px; line-height:1.6; }
.road-step { text-align:center; }
.road-step .glass-ico { margin: 0 auto .8rem; }
.road-step h4 { font-size: 1rem; }
.road-tag { font-family:'JetBrains Mono',monospace; font-size:.72rem; color:#C4B5FD; letter-spacing:.12em; }

/* FAQ expanders as glass cards */
.faq-wrap { width:100%; max-width:980px; margin: 1.4rem auto 0; }
.st-key-faq_block [data-testid="stExpander"] {
    background: linear-gradient(145deg, rgba(255,255,255,0.075), rgba(255,255,255,0.025)) !important;
    backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
    border: 1px solid rgba(196,181,253,0.18) !important; border-radius: 18px !important; margin-bottom: .8rem; overflow: hidden;
}
.st-key-faq_block [data-testid="stExpander"] details, .st-key-faq_block [data-testid="stExpander"] summary { background: transparent !important; }
.st-key-faq_block [data-testid="stExpander"] summary { padding: 1rem 1.4rem !important; }
.st-key-faq_block [data-testid="stExpander"] summary p { color:#fff !important; font-weight:500; font-size:1.02rem; }
.st-key-faq_block [data-testid="stExpander"] [data-testid="stExpanderDetails"] p { color: rgba(235,229,252,0.80) !important; line-height:1.7; }
.st-key-faq_block { max-width: 980px; margin: 0 auto; }

/* CTA panel + footer */
.cta-panel {
    position: relative; width: 100%; max-width: 980px; margin: 6rem auto 0; padding: 4.2rem 1.5rem 5.2rem; text-align:center; overflow:hidden;
    border: 1px solid rgba(255,255,255,0.10); border-radius: 36px;
    background: radial-gradient(ellipse 90% 120% at 50% 0%, #0D0B12 0%, #0D0B12 40%, #1E1630 55%, #382760 66%, #4E3588 74%, #745CB4 82%, #9381CE 90%, #D2CDE8 97%, #FFFFFF 100%), #0D0B12;
    animation: fade-up 0.7s ease both;
}
.cta-panel h2 { font-size: clamp(2rem, 4.4vw, 3.4rem); font-weight:300; letter-spacing:-0.04em; line-height:1.12; margin:0 0 2rem; color:#fff; -webkit-text-fill-color:#fff; }
.cta-btns { display:flex; flex-wrap:wrap; justify-content:center; gap:1rem; }
.cta-btn-white, .cta-btn-glass { display:inline-block; padding: .95rem 2rem; border-radius:9999px; font-size:1.02rem; font-weight:500; text-decoration:none !important; transition: transform .2s ease; }
.cta-btn-white, .cta-btn-white:visited, .cta-btn-white:hover { background:#fff; color:#000 !important; }
.cta-btn-glass { background: rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.35); color:#fff !important; backdrop-filter: blur(10px); }
.cta-btn-white:hover, .cta-btn-glass:hover { transform: translateY(-2px); }
.home-footer { width:111.1111%; margin: 5rem 0 0 -5.5556%; padding: 3.2rem 0 1.6rem; border-top: 1px solid rgba(255,255,255,0.10); background: #0A0A0F; animation: fade-up 0.7s ease both; }
.foot-inner { max-width: 1100px; margin: 0 auto; padding: 0 1.5rem; display:flex; flex-wrap:wrap; justify-content:space-between; gap: 2.5rem; text-align:left; }
.foot-brand { display:flex; flex-direction:column; gap:.9rem; max-width: 300px; }
.foot-brand-row { display:flex; align-items:center; gap:.7rem; font-size:1.25rem; font-weight:600; color:#fff; letter-spacing:-0.02em; }
.foot-brand-row img { height: 30px; width:auto; filter: invert(1); mix-blend-mode: screen; }
.foot-brand p { margin:0; font-size:.9rem; line-height:1.6; color: rgba(235,229,252,0.62); }
.foot-cols { display:flex; flex-wrap:wrap; gap: 4.5rem; }
.foot-group { display:flex; flex-direction:column; gap:.7rem; align-items:flex-start; }
.foot-title { font-size:.92rem; font-weight:600; color:#fff; }
.foot-group a { font-size:.9rem; color: rgba(235,229,252,0.68) !important; text-decoration:none !important; }
.foot-group a:hover { color:#fff !important; text-decoration:underline !important; }
.foot-bottom { max-width:1100px; margin: 2.6rem auto 0; padding: 1.3rem 1.5rem 0; border-top: 1px solid rgba(255,255,255,0.08); display:flex; flex-wrap:wrap; justify-content:space-between; gap:.6rem 2rem; font-size:.84rem; color: rgba(235,229,252,0.58); }
.foot-bottom a { color: rgba(235,229,252,0.68) !important; text-decoration:none !important; }
.foot-bottom a:hover { color:#fff !important; }
@media (max-width: 640px) { .foot-cols { gap: 2.5rem; } }
@media (max-width: 640px) {
    .home-section, .cta-panel { margin-top: 4.5rem; }
    .glass-box { padding: 1.3rem 1.2rem; }
    .glass-row { flex-direction: column; }
}

/* ── Top Navigation Bar (Flat 3-Column SaaS Layout right at top) ─────────── */
.top-navbar {
    display: grid !important;
    grid-template-columns: 1fr auto 1fr !important;
    align-items: center !important;
    width: auto !important;
    height: 56px !important;
    padding: 0 28px !important;
    /* edge-to-edge bar: cancels the page's 5% side padding */
    margin: 0 -5.5556% 6px -5.5556% !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
}

.brand-container {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    text-decoration: none !important;
    justify-self: start;
}

.brand-logo { height: 30px; width: auto; display: block; filter: invert(1); mix-blend-mode: screen; }
.brand-title {
    font-size: 22px;
    font-weight: 600;
    color: #FFFFFF !important;
    letter-spacing: -0.03em;
    font-family: "Plus Jakarta Sans", sans-serif;
}

.nav-pill-group {
    display: flex;
    align-items: center;
    gap: 52px;
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    justify-self: center;
}

.nav-link {
    display: inline-flex;
    align-items: center;
    padding: 0.4rem 0.2rem;
    font-size: 16px !important;
    font-weight: 500 !important;
    letter-spacing: -0.02em;
    color: rgba(255, 255, 255, 0.78) !important;
    text-decoration: none !important;
    background: transparent !important;
    border: none !important;
    transition: color 0.15s ease;
}

.nav-link:visited {
    color: rgba(255, 255, 255, 0.78) !important;
}

.nav-link:hover, .nav-link.active {
    color: #FFFFFF !important;
    background: transparent !important;
    font-weight: 500 !important;
}

.nav-right-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    justify-self: end;
}

.nav-login-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.45rem 1.25rem !important;
    background: rgba(255, 255, 255, 0.08) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    border-radius: 9999px !important;
    font-size: 0.88rem !important;
    font-weight: 500 !important;
}

.nav-login-btn:visited {
    color: #FFFFFF !important;
}

.nav-login-btn:hover {
    background: rgba(255, 255, 255, 0.15) !important;
    color: #FFFFFF !important;
}

.nav-signup-btn {
    gap: 8px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    height: 35px;
    padding: 0 16px;
    background: #FFFFFF !important;
    color: #0A0A0F !important;
    border: none !important;
    border-radius: 9999px !important;
    font-size: 13.5px !important;
    font-weight: 600 !important;
    text-decoration: none !important;
    transition: all 0.2s ease;
}

.nav-signup-btn:visited {
    color: #0A0A0F !important;
}

.nav-signup-btn:hover {
    background: #F4F2FA !important;
    color: #0A0A0F !important;
    box-shadow: 0 0 16px rgba(255, 255, 255, 0.35);
}

/* ── Mobile 3-Dots Navbar Menu ────────────────────────────────────────────── */
.mobile-nav-wrapper {
    display: none;
}

.mobile-menu-checkbox {
    display: none !important;
}

.mobile-dots-btn {
    display: none;
}

.mobile-dropdown-menu {
    display: none;
}

/* ── Tool Page Modern Header ─────────────────────────────────────────────── */
.tool-page-header {
    margin-bottom: 2rem !important;
    width: 100% !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 0.75rem !important;
}

.tool-header-top-meta {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    gap: 1rem !important;
    flex-wrap: wrap !important;
    width: 100% !important;
}

.tool-page-title {
    font-size: clamp(2rem, 3.5vw, 2.75rem) !important;
    font-weight: 700 !important;
    color: #FFFFFF !important;
    letter-spacing: -0.035em !important;
    line-height: 1.2 !important;
    margin: 0 !important;
    padding: 0 !important;
    background: linear-gradient(180deg, #FFFFFF 0%, #F5F3FF 50%, #DDD6FE 100%) !important;
    -webkit-background-clip: text !important;
    background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

.tool-page-subtitle {
    font-size: 1rem !important;
    color: rgba(255, 255, 255, 0.72) !important;
    line-height: 1.6 !important;
    margin: 0 !important;
    max-width: 820px !important;
}

/* ── Stacked Glass Card Box Headers & Elements ────────────────────────────── */
.stacked-box-header {
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    flex-wrap: wrap !important;
    gap: 0.75rem !important;
    margin-bottom: 0.5rem !important;
}

.stacked-box-title-group {
    display: flex !important;
    align-items: center !important;
    gap: 0.75rem !important;
}

.stacked-box-title {
    font-size: 1.15rem !important;
    font-weight: 600 !important;
    color: #FFFFFF !important;
    letter-spacing: -0.015em !important;
}

.stacked-box-tag {
    display: inline-flex !important;
    align-items: center !important;
    font-size: 0.76rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    color: #C4B5FD !important;
    background: rgba(167, 139, 250, 0.12) !important;
    border: 1px solid rgba(167, 139, 250, 0.28) !important;
    border-radius: 9999px !important;
    padding: 0.25rem 0.75rem !important;
}

.stacked-box-desc {
    font-size: 0.88rem !important;
    color: rgba(255, 255, 255, 0.64) !important;
    line-height: 1.55 !important;
    margin-bottom: 1.1rem !important;
}

.scope-pill {
    display: inline-flex !important;
    align-items: center !important;
    font-size: 0.78rem !important;
    font-family: 'JetBrains Mono', monospace !important;
    color: #E2E8F0 !important;
    background: rgba(255, 255, 255, 0.06) !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    border-radius: 6px !important;
    padding: 0.22rem 0.6rem !important;
}

.step-indicator {
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--accent);
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 9999px;
    padding: 0.35rem 0.85rem;
}

/* ── Hero Section (Home) ──────────────────────────────────────────────────── */
.hero-container {
    text-align: center;
    padding: 70px 1rem 1.8rem;
    max-width: 960px;
    margin: 0 auto;
    position: relative;
}

/* Connected Circular Nodes (Double Size, Black Fill, White Boundary, No Node Glow) */
.hero-nodes-row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0;
    margin: 0 auto 0;
    position: relative;
    z-index: 1;
}

.hero-glass-node {
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    background: #0A0A0F !important;
    border: 0.5px solid rgba(255, 255, 255, 0.15) !important;
    color: #FFFFFF !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    -webkit-backdrop-filter: none !important;
    position: relative;
    z-index: 1;
}

.hero-node-small {
    width: 46px !important;
    height: 46px !important;
}

.hero-node-center {
    width: 58px !important;
    height: 58px !important;
    border: 0.5px solid rgba(255, 255, 255, 0.18) !important;
}
.hero-node-small svg { width: 21px; height: 21px; }
.hero-node-center svg { width: 27px; height: 27px; }

.hero-connector-line {
    width: 46px;
    height: 1.5px;
    background: rgba(255, 255, 255, 0.25);
}

/* ── Travelling light: logo 1 -> logo 2 -> logo 3, soft dark-purple glow, circle swells slightly ── */
.hero-connector-line { position: relative; overflow: visible; }
.hero-connector-line::after {
    content: ""; position: absolute; top: -0.25px; left: 0; width: 20px; height: 2px; border-radius: 2px; opacity: 0;
    background: linear-gradient(90deg, transparent, rgba(139,111,214,0.9) 60%, rgba(196,181,253,0.9), transparent);
}
.hero-line-left::after  { animation: streak-1 6s ease-in-out infinite; }
.hero-line-right::after { animation: streak-2 6s ease-in-out infinite; }
.hero-glass-node::before {
    content: ""; position: absolute; inset: -26px; border-radius: 50%; z-index: -1; opacity: 0; pointer-events: none;
    background: radial-gradient(circle at 50% 50%, rgba(74,48,150,0.55) 0%, rgba(58,38,120,0.32) 38%, rgba(40,26,86,0.12) 62%, transparent 76%);
    filter: blur(5px);
}
.hero-node-left   { animation: swell-1 6s ease-in-out infinite; }
.hero-node-center { animation: swell-2 6s ease-in-out infinite; }
.hero-node-right  { animation: swell-3 6s ease-in-out infinite; }
.hero-node-left::before   { animation: glow-1 6s ease-in-out infinite; }
.hero-node-center::before { animation: glow-2 6s ease-in-out infinite; }
.hero-node-right::before  { animation: glow-3 6s ease-in-out infinite; }
@keyframes streak-1 { 0%,6%{transform:translateX(-20px);opacity:0} 9%{opacity:1} 24%{transform:translateX(46px);opacity:1} 26%,100%{transform:translateX(46px);opacity:0} }
@keyframes streak-2 { 0%,30%{transform:translateX(-20px);opacity:0} 33%{opacity:1} 48%{transform:translateX(46px);opacity:1} 50%,100%{transform:translateX(46px);opacity:0} }
@keyframes glow-1 { 0%{opacity:0} 4%{opacity:1} 14%,100%{opacity:0} }
@keyframes glow-2 { 0%,22%{opacity:0} 28%{opacity:1} 40%,100%{opacity:0} }
@keyframes glow-3 { 0%,46%{opacity:0} 52%{opacity:1} 68%,100%{opacity:0} }
@keyframes swell-1 { 0%{transform:scale(1)} 4%{transform:scale(1.1)} 14%,100%{transform:scale(1)} }
@keyframes swell-2 { 0%,22%{transform:scale(1)} 28%{transform:scale(1.1)} 40%,100%{transform:scale(1)} }
@keyframes swell-3 { 0%,46%{transform:scale(1)} 52%{transform:scale(1.1)} 68%,100%{transform:scale(1)} }
@media (prefers-reduced-motion: reduce) { .hero-connector-line::after, .hero-glass-node::before, .hero-glass-node { animation: none !important; } }

.hero-node-right-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}

/* Purple half-disc glow behind the right icon */
.hero-purple-halfdisc {
    position: absolute;
    width: 140px;
    height: 75px;
    top: -24px;
    left: 50%;
    transform: translateX(-50%);
    background: radial-gradient(ellipse at 50% 100%, rgba(143, 120, 217, 0.45) 0%, rgba(91, 63, 181, 0.25) 50%, transparent 80%);
    border-radius: 140px 140px 0 0;
    filter: blur(14px);
    z-index: 0;
    pointer-events: none;
}

.get-started-pill,
.get-started-pill:link,
.get-started-pill:visited,
.get-started-pill:hover,
.get-started-pill:active,
.get-started-pill:focus,
.get-started-pill * {
    color: #0A0A0F !important;
    text-decoration: none !important;
    background: #FFFFFF !important;
}

.hero-nodes-row, .hero-title, .hero-subtitle, [data-testid="stForm"], .chips-row {
    position: relative;
    z-index: 1;
}

.mobile-hero-cta {
    display: none;
}

/* Hero Title ~92px, font-weight 300, white to muted lavender gradient */
.hero-title, .hero-title * {
    font-weight: 300 !important;
}

.hero-title {
    font-size: clamp(2.6rem, 5vw, 96px) !important;
    line-height: 1.13 !important;
    letter-spacing: -0.05em !important;
    margin: 56px auto 2px !important;
    text-align: center !important;
    max-width: 1100px !important;
    /* line 1: pure white */
    background: linear-gradient(180deg, #FFFFFF 0%, #F6F4FE 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

.hero-title-gradient, .hero-title-accent {
    display: block !important;
    font-weight: 300 !important;
    /* line 2: soft lavender-white, same as the reference */
    background: linear-gradient(180deg, #F3F0FE 0%, #E2D9FD 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

/* Centered Hero Subtitle (~21px, muted lavender) */
.hero-subtitle {
    font-size: clamp(1rem, 1.1vw, 21px) !important;
    font-weight: 400 !important;
    letter-spacing: -0.02em !important;
    color: rgba(235, 229, 252, 0.62) !important;
    line-height: 1.6 !important;
    max-width: 640px !important;
    margin-left: auto !important;
    margin-right: auto !important;
    margin-bottom: 56px !important;
    text-align: center !important;
}

/* Headings on all pages (Selective gradient for major titles, solid white for card/sub headings) */
.section-heading, .sec-title, .hero-title-gradient, .hero-title-accent {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-weight: 300 !important;
    letter-spacing: -0.04em !important;
    background: linear-gradient(180deg, #FFFFFF 0%, #F5F3FF 45%, #C4B5FD 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
}

.feature-title, .detail-title, h1, h2, h3, h4 {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #FFFFFF !important;
    -webkit-text-fill-color: initial !important;
}

/* ── Form & Input Styling (White Search Bar with Black Text & Matching Button Height) ── */
[data-testid="stForm"] {
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    width: 100%;
    max-width: 680px;
    margin: 0 auto;
}

[data-testid="stTextInput"] {
    margin-bottom: 0 !important;
}

[data-baseweb="base-input"] {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

[data-baseweb="input"] {
    background: #FFFFFF !important;
    border-radius: 9999px !important;
    border: 1px solid #FFFFFF !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
    height: 52px !important;
    min-height: 52px !important;
}

[data-baseweb="input"]:focus-within {
    border-color: #8F78D9 !important;
    box-shadow: 0 0 0 3px rgba(143, 120, 217, 0.35), 0 4px 24px rgba(0, 0, 0, 0.3) !important;
}

[data-testid="stTextInputRootElement"] {
    background: #FFFFFF !important;
    border-radius: 9999px !important;
    border: 1px solid #FFFFFF !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
    height: 52px !important;
    min-height: 52px !important;
}

[data-testid="stTextInputRootElement"]:focus-within {
    border-color: #8F78D9 !important;
    box-shadow: 0 0 0 3px rgba(143, 120, 217, 0.35), 0 4px 24px rgba(0, 0, 0, 0.3) !important;
}

[data-testid="stTextInput"] input {
    background: transparent !important;
    border: none !important;
    color: #0A0A0F !important;
    font-size: 0.98rem !important;
    font-weight: 500 !important;
    padding: 0 1.5rem !important;
    height: 52px !important;
}

[data-testid="stTextInput"] input::placeholder {
    color: rgba(10, 10, 15, 0.55) !important;
    font-weight: 400 !important;
}

/* Home Search Form Submit Button */
[data-testid="stForm"] button[kind="primaryFormSubmit"] {
    background: #0A0A0F !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 0.96rem !important;
    height: 52px !important;
    min-height: 52px !important;
    padding: 0 2rem !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 9999px !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35) !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    white-space: nowrap !important;
    overflow: visible !important;
    min-width: 105px !important;
}

[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover {
    background: #1C1A27 !important;
    border-color: #8F78D9 !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45) !important;
}

/* General Primary Buttons: Sleek Purple Gradient & Glow */
button[kind="primary"], button[kind="primaryFormSubmit"] {
    background: linear-gradient(135deg, #7C3AED 0%, #6D28D9 100%) !important;
    color: #FFFFFF !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    border: 1px solid rgba(196, 181, 253, 0.35) !important;
    border-radius: 9999px !important;
    box-shadow: 0 4px 18px rgba(109, 40, 217, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
    cursor: pointer !important;
}

button[kind="primary"]:hover, button[kind="primaryFormSubmit"]:hover {
    background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%) !important;
    border-color: rgba(196, 181, 253, 0.6) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 26px rgba(124, 58, 237, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
}

/* Secondary Buttons: Translucent Glass & Subtle Lavender Border */
button[kind="secondary"] {
    border-radius: 9999px !important;
    background: rgba(255, 255, 255, 0.05) !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    border: 1px solid rgba(196, 181, 253, 0.22) !important;
    color: #EDE9FE !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    transition: all 0.2s ease !important;
}

button[kind="secondary"]:hover {
    background: rgba(167, 139, 250, 0.15) !important;
    border-color: rgba(167, 139, 250, 0.5) !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(139, 111, 214, 0.2) !important;
}

/* Full-width Glass Containers for Explore Decisions */
[class*="st-key-explore_card_"] {
    background: linear-gradient(145deg, rgba(26, 21, 42, 0.82) 0%, rgba(14, 11, 24, 0.88) 100%) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(196, 181, 253, 0.18) !important;
    border-radius: 22px !important;
    padding: 2.2rem 2.4rem !important;
    margin-bottom: 2.2rem !important;
    box-shadow: 0 12px 42px rgba(0, 0, 0, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.09) !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
}

[class*="st-key-explore_card_"]:hover {
    border-color: rgba(196, 181, 253, 0.36) !important;
    box-shadow: 0 16px 48px rgba(124, 58, 237, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.12) !important;
}

/* Glass Panels for Inputs & Configuration (Stacked Cards) */
[class*="st-key-scanner_input_card"], [class*="st-key-pr_input_card"], [class*="st-key-alerts_config_card"],
[class*="st-key-scanner_source_box"], [class*="st-key-scanner_config_box"],
[class*="st-key-pr_input_box1"], [class*="st-key-pr_input_box2"],
[class*="st-key-alerts_input_box1"], [class*="st-key-alerts_input_box2"] {
    background: linear-gradient(145deg, rgba(24, 19, 38, 0.72) 0%, rgba(13, 10, 22, 0.78) 100%) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(196, 181, 253, 0.16) !important;
    border-radius: 18px !important;
    padding: 1.6rem 1.8rem !important;
    margin-bottom: 1.4rem !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
    transition: border-color 0.25s ease, box-shadow 0.25s ease !important;
}

[class*="st-key-scanner_source_box"]:hover, [class*="st-key-scanner_config_box"]:hover,
[class*="st-key-pr_input_box1"]:hover, [class*="st-key-pr_input_box2"]:hover,
[class*="st-key-alerts_input_box1"]:hover, [class*="st-key-alerts_input_box2"]:hover {
    border-color: rgba(196, 181, 253, 0.34) !important;
    box-shadow: 0 10px 36px rgba(124, 58, 237, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.1) !important;
}

[class*="st-key-pr_overview_panel"] {
    background: linear-gradient(145deg, rgba(26, 21, 42, 0.78) 0%, rgba(14, 11, 24, 0.82) 100%) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border: 1px solid rgba(196, 181, 253, 0.18) !important;
    border-radius: 20px !important;
    padding: 1.8rem 2rem !important;
    margin-bottom: 1.5rem !important;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08) !important;
}

/* Glass styling for Streamlit Text Areas & File Uploaders */
[data-testid="stTextArea"] textarea {
    background: rgba(16, 13, 26, 0.8) !important;
    border: 1px solid rgba(196, 181, 253, 0.18) !important;
    border-radius: 14px !important;
    color: #F8FAFC !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.88rem !important;
    line-height: 1.6 !important;
    backdrop-filter: blur(12px) !important;
    -webkit-backdrop-filter: blur(12px) !important;
    transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

[data-testid="stTextArea"] textarea:focus {
    border-color: #A78BFA !important;
    box-shadow: 0 0 0 2px rgba(167, 139, 250, 0.25) !important;
}

[data-testid="stFileUploader"] section {
    background: rgba(22, 17, 36, 0.5) !important;
    border: 1px dashed rgba(196, 181, 253, 0.25) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(12px) !important;
}

/* Glass Expanders */
[data-testid="stExpander"] {
    background: rgba(22, 18, 36, 0.65) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(196, 181, 253, 0.16) !important;
    border-radius: 16px !important;
    margin-bottom: 1rem !important;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
}

[data-testid="stExpander"] summary {
    border-radius: 16px !important;
    padding: 0.85rem 1.25rem !important;
}

[data-testid="stExpander"] summary:hover {
    background: rgba(255, 255, 255, 0.03) !important;
}

/* Glass Selectbox & Radio */
[data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: rgba(18, 14, 28, 0.85) !important;
    border: 1px solid rgba(196, 181, 253, 0.2) !important;
    border-radius: 12px !important;
    color: #F8FAFC !important;
}

/* Code Blocks Styling */
pre, code, [data-testid="stCode"] {
    border-radius: 10px !important;
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── 3 Feature Cards (Home) ───────────────────────────────────────────────── */
.feature-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.4rem;
    width: 100%;
    margin: 5.5rem auto 3rem !important;
}

.feature-card {
    background: var(--surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.6rem 1.5rem;
    display: flex;
    align-items: flex-start;
    gap: 1.1rem;
    transition: all 0.2s ease;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    min-width: 0;
    overflow: visible;
}

.feature-card:hover {
    border-color: var(--border-hover);
    transform: translateY(-2px);
}

.feature-icon-box {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 42px;
    height: 42px;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 10px;
    color: var(--accent);
    flex-shrink: 0;
}

.feature-title {
    font-size: 1.05rem;
    font-weight: 600;
    margin: 0 0 0.35rem;
}

.feature-desc {
    font-size: 0.86rem;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
    word-break: break-word;
}

/* ── Section Header Row ───────────────────────────────────────────────────── */
.section-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    gap: 1rem;
    width: 100%;
}

.section-title-wrap {
    display: flex;
    align-items: center;
    gap: 1rem;
}

.title-icon-box {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 10px;
    color: var(--accent);
    flex-shrink: 0;
}

.section-heading {
    font-size: 1.85rem;
    font-weight: 300;
    letter-spacing: -0.04em;
    line-height: 1.1;
    margin: 0;
}

.section-subtext {
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin: 0.25rem 0 0;
}

.counter-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border);
    border-radius: 9999px;
    padding: 0.45rem 1rem;
    font-size: 0.84rem;
    font-weight: 600;
    color: var(--text-primary);
}

/* ── Explore Left List ────────────────────────────────────────────────────── */
.decision-card-item {
    display: flex;
    align-items: center;
    gap: 1rem;
    background: var(--surface);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.15rem 1.3rem;
    margin-bottom: 0.85rem;
    text-decoration: none !important;
    color: var(--text-primary) !important;
    transition: all 0.2s ease;
    cursor: pointer;
    width: 100%;
    min-width: 0;
    overflow: visible;
}

.decision-card-item:hover {
    border-color: var(--border-hover);
    background: var(--surface-hover);
    transform: translateY(-1px);
}

.decision-card-item.active {
    background: var(--accent-muted);
    border: 1px solid var(--accent);
    box-shadow: 0 0 20px rgba(139, 111, 214, 0.25);
}

.card-code-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--accent);
    flex-shrink: 0;
}

.card-title-text {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.2rem;
    word-break: break-word;
}

.card-sub-text {
    font-size: 0.82rem;
    color: var(--text-secondary);
}

/* ── Decision Detail Panel ────────────────────────────────────────────────── */
.detail-panel {
    background: var(--surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 2rem 2.2rem;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
    width: 100%;
    word-break: break-word;
    overflow: visible;
}

.detail-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.8rem;
    gap: 1rem;
    flex-wrap: wrap;
    overflow: visible;
}

.detail-entity-wrap {
    display: flex;
    align-items: center;
    gap: 1.1rem;
    min-width: 0;
    overflow: visible;
}

.detail-code-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 10px;
    color: var(--accent);
    flex-shrink: 0;
}

.detail-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.25rem;
    word-break: break-word;
}

.detail-category {
    font-size: 0.88rem;
    color: var(--text-secondary);
    margin: 0;
}

.source-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.35rem 0.85rem;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}

.source-neo4j {
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    color: var(--accent);
}

.source-fallback {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    color: var(--text-secondary);
}

.decision-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.85rem;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.02em;
    white-space: nowrap;
}

/* ── Stats Grid & Item ────────────────────────────────────────────────────── */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.25rem;
    padding: 1.25rem 1.5rem;
    background: rgba(255, 255, 255, 0.015);
    border: 1px solid var(--border);
    border-radius: 14px;
    margin-bottom: 1.8rem;
    overflow: visible;
}

.stat-item {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    min-width: 0;
    overflow: visible;
}

.stat-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 9px;
    color: var(--accent);
    flex-shrink: 0;
}

.stat-meta-label {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin-bottom: 0.2rem;
    white-space: nowrap;
}

.stat-meta-val {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    word-break: break-word;
}

.pill-status {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    border: 1px solid var(--accent-border);
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}

.pill-status-removed {
    background: var(--accent-muted);
    border-color: var(--accent-border);
    color: var(--accent);
}

.pill-status-deprecated {
    background: rgba(245, 158, 11, 0.10);
    border-color: rgba(245, 158, 11, 0.35);
    color: #FBBF24;
}

.pill-status-active,
.pill-status-retained {
    background: rgba(34, 197, 94, 0.10);
    border-color: rgba(34, 197, 94, 0.35);
    color: #4ADE80;
}

.pill-status-unknown {
    background: rgba(148, 163, 184, 0.10);
    border-color: rgba(148, 163, 184, 0.30);
    color: #CBD5E1;
}

/* ── Rule-Based Severity & Alert Status Pills (Step 6) ──────────────────────── */
.severity-pill-critical {
    background: rgba(239, 68, 68, 0.15) !important;
    border-color: rgba(239, 68, 68, 0.40) !important;
    color: #F87171 !important;
}

.severity-pill-high {
    background: rgba(249, 115, 22, 0.15) !important;
    border-color: rgba(249, 115, 22, 0.40) !important;
    color: #FB923C !important;
}

.severity-pill-medium {
    background: rgba(245, 158, 11, 0.12) !important;
    border-color: rgba(245, 158, 11, 0.35) !important;
    color: #FBBF24 !important;
}

.severity-pill-informational {
    background: rgba(59, 130, 246, 0.12) !important;
    border-color: rgba(59, 130, 246, 0.35) !important;
    color: #60A5FA !important;
}

.alert-status-new {
    background: rgba(14, 165, 233, 0.15) !important;
    border-color: rgba(14, 165, 233, 0.35) !important;
    color: #38BDF8 !important;
}

.alert-status-needs-review {
    background: rgba(234, 179, 8, 0.15) !important;
    border-color: rgba(234, 179, 8, 0.35) !important;
    color: #FACC15 !important;
}

.alert-status-resolved {
    background: rgba(34, 197, 94, 0.15) !important;
    border-color: rgba(34, 197, 94, 0.35) !important;
    color: #4ADE80 !important;
}

.alert-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.4rem;
    margin-bottom: 1.1rem;
    transition: border-color 0.18s ease;
}

.alert-card:hover {
    border-color: var(--accent-border);
}

.alert-rec-box {
    background: rgba(34, 197, 94, 0.07);
    border: 1px solid rgba(34, 197, 94, 0.25);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin: 0.8rem 0;
    font-size: 0.86rem;
    line-height: 1.55;
    color: #D1FAE5;
}

/* ── Horizontal Timeline (Deprecated vX -> Removed vY) ─────────────────────── */
.horizontal-timeline-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.1rem 1.4rem;
    background: rgba(255, 255, 255, 0.015);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 1.8rem;
    gap: 1rem;
    flex-wrap: wrap;
}

.timeline-step-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}

.timeline-circle {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: var(--accent);
    box-shadow: 0 0 10px var(--accent);
}

.timeline-circle-removed {
    background: #C4B5FD;
    box-shadow: 0 0 10px #C4B5FD;
}

.timeline-connector {
    flex: 1;
    min-width: 40px;
    height: 1px;
    background: linear-gradient(90deg, var(--accent-border), rgba(255, 255, 255, 0.15));
}

.timeline-text-lbl {
    font-size: 0.74rem;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.06em;
}

.timeline-text-ver {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--text-primary);
}

.detail-section-title {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.98rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 1.6rem 0 0.85rem;
}

.rationale-quote-box {
    background: rgba(255, 255, 255, 0.02);
    border-left: 3px solid #8B6FD6;
    border-radius: 0 12px 12px 0;
    padding: 1.25rem 1.5rem;
    font-size: 0.95rem;
    color: var(--text-primary);
    line-height: 1.65;
    margin-bottom: 1.8rem;
    word-break: break-word;
    overflow: visible;
}

.evidence-btn-group {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    overflow: visible;
}

.evidence-pill-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid var(--border);
    border-radius: 9999px;
    padding: 0.6rem 1.15rem;
    font-size: 0.84rem;
    font-weight: 500;
    color: #C4B5FD !important;
    text-decoration: none !important;
    transition: all 0.15s ease;
    white-space: nowrap;
}

.evidence-pill-btn:visited {
    color: #C4B5FD !important;
}

.evidence-pill-btn:hover {
    background: var(--accent-muted);
    border-color: var(--accent-border);
    color: #fff !important;
    transform: translateY(-1px);
}

.migration-header-wrap {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    margin: 1.8rem 0 0.85rem;
}

.illustrative-pill {
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--text-muted);
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border);
    border-radius: 9999px;
    padding: 0.2rem 0.6rem;
    letter-spacing: 0.03em;
}

/* ── About / Technical Approach ───────────────────────────────────────────── */
.methodology-card {
    background: var(--surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 1.8rem 2rem;
    height: auto;
    overflow: visible;
}

.method-step-row {
    display: flex;
    align-items: flex-start;
    gap: 1.1rem;
    padding: 0.9rem 0;
    overflow: visible;
}

.step-num-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 9999px;
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
    flex-shrink: 0;
}

.step-content {
    flex: 1;
    min-width: 0;
    overflow: visible;
}

.step-heading {
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-size: 0.96rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 0.25rem;
}

.step-desc {
    font-size: 0.84rem;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
    word-break: break-word;
}

.step-arrow {
    text-align: center;
    color: var(--text-muted);
    font-size: 1rem;
    margin: -0.2rem 0;
}

.workflow-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    padding: 0.5rem 0;
    overflow: visible;
}

.wf-node {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    min-width: 105px;
    text-align: center;
    transition: all 0.15s ease;
}

.wf-node:hover {
    border-color: var(--accent-border);
    background: var(--accent-muted);
}

.wf-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    margin-bottom: 0.4rem;
}

.wf-label {
    font-size: 0.84rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.15rem;
}

.wf-sub {
    font-size: 0.72rem;
    color: var(--text-muted);
}

.wf-arrow {
    color: var(--text-muted);
    font-size: 1rem;
    flex-shrink: 0;
}

.schema-grid {
    display: grid;
    grid-template-columns: 1fr 1.5fr;
    gap: 2rem;
    align-items: start;
    overflow: visible;
}

.legend-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0;
    font-size: 0.85rem;
    color: var(--text-secondary);
}

.legend-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    flex-shrink: 0;
}

.legend-name {
    font-weight: 600;
    color: var(--text-primary);
}

.legend-example {
    font-size: 0.76rem;
    color: var(--text-muted);
    margin-left: 0.35rem;
}

.graph-canvas {
    background: rgba(14, 16, 22, 0.6);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: visible;
}

/* ── Form Section Headings & Inputs Formatting ────────────────────────── */
.form-section-title {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    font-size: 0.98rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0.5rem 0 0.85rem 0;
    letter-spacing: -0.01em;
}

/* ── Lifecycle Change Events & Event Management ──────────────────────── */
.lifecycle-events-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 0.9rem;
    margin: 0.85rem 0 1.2rem;
    width: 100%;
}

.event-card {
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 0.85rem 1.1rem;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
    transition: all 0.18s ease;
}

.event-card:hover {
    border-color: var(--accent-border);
    background: rgba(167, 139, 250, 0.04);
}

.event-card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
}

.event-type-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.72rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 0.22rem 0.6rem;
    border-radius: 9999px;
}

.event-type-deprecated {
    background: rgba(245, 158, 11, 0.15);
    color: #FBBF24;
    border: 1px solid rgba(245, 158, 11, 0.35);
}

.event-type-removed {
    background: rgba(167, 139, 250, 0.15);
    color: #C4B5FD;
    border: 1px solid rgba(167, 139, 250, 0.35);
}

.event-version-pill {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.84rem;
    color: var(--text-primary);
    font-weight: 600;
}

.event-meta-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    font-size: 0.78rem;
    color: var(--text-muted);
    flex-wrap: wrap;
    gap: 0.4rem;
}

.event-ref-link {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    color: #C4B5FD !important;
    text-decoration: none !important;
    font-size: 0.78rem;
    font-weight: 500;
    transition: color 0.15s ease;
}

.event-ref-link:hover {
    color: #FFFFFF !important;
    text-decoration: underline !important;
}

.event-ref-label {
    font-size: 0.78rem;
    color: var(--text-muted);
}

/* ── Audit Trail & Workflow Event Table ──────────────────────────────── */
.events-audit-table {
    width: 100%;
    border-collapse: collapse;
    margin-top: 0.75rem;
    font-size: 0.82rem;
}

.events-audit-table th {
    text-align: left;
    padding: 0.65rem 0.85rem;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    font-size: 0.72rem;
}

.events-audit-table td {
    padding: 0.7rem 0.85rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    color: var(--text-secondary);
}

.events-audit-table tr:hover td {
    background: rgba(255, 255, 255, 0.02);
}

/* ── Responsive adjustments (Desktop, Tablet, Mobile) ──────────────────── */
@media (max-width: 960px) {
    .main .block-container, [data-testid="stAppViewContainer"] .block-container, .block-container {
        padding-left: 4% !important;
        padding-right: 4% !important;
    }
    .nav-pill-group, .nav-right-actions {
        display: none !important;
    }
    .top-navbar {
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        position: relative !important;
        height: 56px !important;
        padding: 0 16px !important;
        margin: 0 -4.3478% 6px -4.3478% !important;
        background: transparent !important;
    }
    .brand-container {
        justify-self: start !important;
    }
    .mobile-nav-wrapper {
        display: block !important;
        position: relative !important;
    }
    .mobile-dots-btn {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        width: 38px !important;
        height: 38px !important;
        background: transparent !important;
        border: none !important;
        color: #FFFFFF !important;
        cursor: pointer !important;
        padding: 0 !important;
        transition: opacity 0.2s ease !important;
    }
    .mobile-dots-btn:hover {
        background: transparent !important;
        border: none !important;
        opacity: 0.8 !important;
    }
    .mobile-menu-checkbox:checked ~ .mobile-dropdown-menu {
        display: flex !important;
    }
    .mobile-dropdown-menu {
        display: none;
        position: absolute !important;
        top: calc(100% + 10px) !important;
        right: 0 !important;
        width: 250px !important;
        background: rgba(18, 13, 30, 0.96) !important;
        backdrop-filter: blur(24px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
        border: 1px solid rgba(196, 181, 253, 0.28) !important;
        border-radius: 16px !important;
        padding: 8px !important;
        flex-direction: column !important;
        gap: 3px !important;
        box-shadow: 0 16px 42px rgba(0, 0, 0, 0.75), 0 0 24px rgba(124, 58, 237, 0.22) !important;
        z-index: 999999 !important;
        animation: mobileMenuFade 0.18s ease-out !important;
    }
    @keyframes mobileMenuFade {
        from { opacity: 0; transform: translateY(-8px) scale(0.97); }
        to { opacity: 1; transform: translateY(0) scale(1); }
    }
    .mobile-dropdown-header {
        font-size: 11px !important;
        font-weight: 700 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.1em !important;
        color: rgba(196, 181, 253, 0.6) !important;
        padding: 6px 12px 4px !important;
        font-family: 'JetBrains Mono', monospace !important;
    }
    .mobile-nav-item {
        display: flex !important;
        align-items: center !important;
        gap: 12px !important;
        padding: 10px 12px !important;
        border-radius: 9px !important;
        font-size: 14.5px !important;
        font-weight: 500 !important;
        color: rgba(255, 255, 255, 0.82) !important;
        text-decoration: none !important;
        transition: all 0.15s ease !important;
    }
    .mobile-nav-item:hover {
        color: #FFFFFF !important;
        background: rgba(167, 139, 250, 0.18) !important;
    }
    .mobile-nav-item.active {
        color: #FFFFFF !important;
        background: rgba(167, 139, 250, 0.24) !important;
        font-weight: 600 !important;
        border-left: 3px solid #A78BFA !important;
    }
    .mobile-dropdown-divider {
        height: 1px !important;
        background: rgba(255, 255, 255, 0.08) !important;
        margin: 4px 6px !important;
    }
    .feature-grid {
        grid-template-columns: 1fr;
        gap: 1rem !important;
    }
    .hero-title {
        font-size: 2.8rem !important;
    }
    .stats-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1rem !important;
    }
    .schema-grid {
        grid-template-columns: 1fr;
    }
    .hero-container {
        padding-top: 50px !important;
    }
    [class*="st-key-explore_card_"], .detail-panel {
        padding: 1.6rem 1.6rem !important;
    }
}

@media (max-width: 640px) {
    .main .block-container, [data-testid="stAppViewContainer"] .block-container, .block-container {
        padding-left: 3% !important;
        padding-right: 3% !important;
    }
    .top-navbar {
        height: 52px !important;
        padding: 0 12px !important;
    }
    .hero-title {
        font-size: 2.1rem !important;
    }
    .hero-subtitle {
        font-size: 0.95rem !important;
        margin-bottom: 36px !important;
    }
    .stats-grid {
        grid-template-columns: 1fr !important;
        padding: 0.85rem !important;
        gap: 0.75rem !important;
    }
    .horizontal-timeline-bar {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 0.75rem !important;
        padding: 0.9rem !important;
    }
    .timeline-connector {
        display: none !important;
    }
    [class*="st-key-explore_card_"], .detail-panel {
        padding: 1.1rem 0.9rem !important;
        border-radius: 14px !important;
    }
    .detail-title {
        font-size: 1.15rem !important;
    }
    .section-heading {
        font-size: 1.45rem !important;
    }
    .section-header-row {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 0.75rem !important;
    }
    .counter-badge, .badge-count-pill {
        width: 100% !important;
        justify-content: center !important;
    }
    .detail-top-row {
        flex-direction: column !important;
        align-items: flex-start !important;
        gap: 0.75rem !important;
    }
    .detail-entity-wrap {
        width: 100% !important;
    }
    .evidence-pill-btn {
        width: 100% !important;
        justify-content: center !important;
    }
    .evidence-btn-group {
        width: 100% !important;
    }
    .lifecycle-events-grid {
        grid-template-columns: 1fr !important;
        gap: 0.65rem !important;
    }
    .alert-card {
        padding: 1rem 0.85rem !important;
    }
    pre, code, [data-testid="stCode"] {
        max-width: 100% !important;
        overflow-x: auto !important;
        -webkit-overflow-scrolling: touch !important;
        white-space: pre !important;
    }
    .stButton > button {
        width: 100% !important;
    }
}
</style>
""", unsafe_allow_html=True)

brand_logo_html = f'<img class="brand-logo" src="data:image/png;base64,{logo_b64}" alt="logo">' if logo_b64 else ""

# ── Render Universal Top Navigation Bar ───────────────────────────────────────

cur_page = st.session_state.nav

PROJECT_REPO_URL = ""   # put your own GitHub repo link here (falls back to the Flask repo)
TEAM_NAME = ""          # put your team name here (hidden when empty)
is_home = (cur_page == "home")
is_explore = (cur_page == "explore")
is_scanner = (cur_page == "scanner")
is_pr = (cur_page == "pr")
is_alerts = (cur_page == "alerts")
is_about = (cur_page == "about")

if not is_home and bg_b64:
    st.markdown(f"""
    <style>
    [data-testid="stApp"] {{
        background-color: #0A0A0F !important;
        background-image: 
            linear-gradient(rgba(10, 10, 15, 0.88), rgba(10, 10, 15, 0.94)),
            url("data:image/png;base64,{bg_b64}") !important;
        background-repeat: no-repeat !important;
        background-position: center top !important;
        background-size: cover !important;
        background-attachment: fixed !important;
    }}
    </style>
    """, unsafe_allow_html=True)

github_svg = """<svg height="15" width="15" viewBox="0 0 16 16" fill="currentColor">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
</svg>"""

ext_arrow_svg = """<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
</svg>"""

code_icon_svg = """<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
</svg>"""

db_icon_svg = """<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
</svg>"""

pkg_icon_svg = """<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"/><path d="m3.3 7 8.7 5 8.7-5"/><path d="M12 22V12"/>
</svg>"""

right_header_elem = """
<div class="nav-right-actions">
    <a href="https://github.com/pallets/flask" target="_blank" class="nav-signup-btn"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.69 1.25 3.35.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.39-5.25 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z"/></svg><span>GitHub</span></a>
</div>
"""

# ── Render Universal Top Navigation Bar ───────────────────────────────────────
st.markdown(clean_html(f"""
<div class="top-navbar">
    <a href="?page=home" target="_self" class="brand-container">
        {brand_logo_html}<span class="brand-title">Rationale</span>
    </a>
    <div class="nav-pill-group">
        <a href="?page=home" target="_self" class="nav-link {'active' if is_home else ''}">Home</a>
        <a href="?page=explore" target="_self" class="nav-link {'active' if is_explore else ''}">Explore Decisions</a>
        <a href="?page=scanner" target="_self" class="nav-link {'active' if is_scanner else ''}">Code Scanner</a>
        <a href="?page=pr" target="_self" class="nav-link {'active' if is_pr else ''}">PR Analyzer</a>
        <a href="?page=alerts" target="_self" class="nav-link {'active' if is_alerts else ''}">Alerts</a>
        <a href="?page=about" target="_self" class="nav-link {'active' if is_about else ''}">About</a>
    </div>
    {right_header_elem}

    <!-- Mobile Responsive Menu (Right Aligned on Mobile) -->
    <div class="mobile-nav-wrapper">
        <input type="checkbox" id="mobile-menu-toggle" class="mobile-menu-checkbox" aria-label="Toggle navigation" />
        <label for="mobile-menu-toggle" class="mobile-dots-btn" title="Navigation Menu">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round">
                <line x1="3" y1="8" x2="21" y2="8"></line>
                <line x1="3" y1="16" x2="21" y2="16"></line>
            </svg>
        </label>
        <div class="mobile-dropdown-menu">
            <div class="mobile-dropdown-header">Navigation Menu</div>
            <a href="?page=home" target="_self" class="mobile-nav-item {'active' if is_home else ''}">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>
                <span>Home</span>
            </a>
            <a href="?page=explore" target="_self" class="mobile-nav-item {'active' if is_explore else ''}">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></svg>
                <span>Explore Decisions</span>
            </a>
            <a href="?page=scanner" target="_self" class="mobile-nav-item {'active' if is_scanner else ''}">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
                <span>Code Scanner</span>
            </a>
            <a href="?page=pr" target="_self" class="mobile-nav-item {'active' if is_pr else ''}">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/></svg>
                <span>PR Analyzer</span>
            </a>
            <a href="?page=alerts" target="_self" class="mobile-nav-item {'active' if is_alerts else ''}">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
                <span>Alerts</span>
            </a>
            <a href="?page=about" target="_self" class="mobile-nav-item {'active' if is_about else ''}">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                <span>About</span>
            </a>
            <div class="mobile-dropdown-divider"></div>
            <a href="https://github.com/pallets/flask" target="_blank" class="mobile-nav-item">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M12 .5C5.65.5.5 5.65.5 12c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.56v-2c-3.2.7-3.87-1.37-3.87-1.37-.52-1.33-1.28-1.69-1.28-1.69-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.69 1.25 3.35.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.28 1.18-3.09-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.77 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.23 2.76.11 3.05.74.81 1.18 1.83 1.18 3.09 0 4.42-2.69 5.39-5.25 5.67.41.36.78 1.06.78 2.14v3.17c0 .31.21.67.8.56A11.5 11.5 0 0 0 23.5 12C23.5 5.65 18.35.5 12 .5z"/></svg>
                <span>GitHub Repository</span>
            </a>
        </div>
    </div>
</div>
"""), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: HOME
# ══════════════════════════════════════════════════════════════════════════════

if is_home:

    # Hero panel (same look as the reference): thin 1px outline + rounded corners, black half-sphere at the top,
    # muted violet -> lavender -> white at the outer corners, 60px grid that only shows on the purple.
    # Colours below were sampled from the reference screenshot (no blue-ish tones).
    st.markdown(clean_html("""
    <style>
    /* Streamlit wraps the panel and caps it at 100% width; widen the wrapper so the panel runs edge to edge */
    [data-testid="stLayoutWrapper"]:has(> .st-key-hero_panel) {
        width: 111.1111% !important;
        max-width: none !important;
        margin-left: -5.5556% !important;
        margin-bottom: 28px !important;
    }
    .st-key-hero_panel {
        position: relative !important;
        width: 100% !important;
        max-width: none !important;
        padding: 0 0 106px !important;
        gap: 0 !important;
        border: 1px solid rgba(255, 255, 255, 0.09) !important;
        border-radius: 5px !important;
        overflow: hidden !important;
        background-origin: border-box !important;
        background-repeat: repeat, repeat, no-repeat, no-repeat !important;
        background:
            linear-gradient(to right, rgba(255, 255, 255, 0.16) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.16) 1px, transparent 1px),
            radial-gradient(ellipse 82% 107% at 50% 0%,
                #0D0B12 0%,
                #0D0B12 52%,
                #14101F 58%,
                #1E1630 62.7%,
                #382760 66.6%,
                #4E3588 71%,
                #745CB4 76.4%,
                #9381CE 82.5%,
                #AEA1DB 89%,
                #D2CDE8 96%,
                #FFFFFF 100%
            ),
            #0D0B12 !important;
        background-size: 60px 60px, 60px 60px, 100% 100%, 100% 100% !important;
        background-origin: border-box !important;
        background-repeat: repeat, repeat, no-repeat, no-repeat !important;
        background-blend-mode: overlay, overlay, normal, normal !important;
    }
    @media (max-width: 960px) {
        [data-testid="stLayoutWrapper"]:has(> .st-key-hero_panel) {
            width: 100% !important;
            max-width: 100% !important;
            margin-left: 0 !important;
            margin-right: 0 !important;
            margin-bottom: 24px !important;
            display: flex !important;
            justify-content: center !important;
        }
        .st-key-hero_panel {
            width: 100% !important;
            max-width: 440px !important;
            margin: 10px auto 20px auto !important;
            padding: 42px 18px 48px !important;
            border-radius: 32px !important;
            border: 1px solid rgba(255, 255, 255, 0.14) !important;
            background:
                linear-gradient(to right, rgba(168, 85, 247, 0.18) 1px, transparent 1px),
                linear-gradient(to bottom, rgba(168, 85, 247, 0.18) 1px, transparent 1px),
                radial-gradient(ellipse 95% 108% at 50% 0%,
                    #0D0B12 0%,
                    #0D0B12 46%,
                    #151022 52%,
                    #22163B 58%,
                    #3E276E 64%,
                    #5C3D9E 70%,
                    #7F63C4 77%,
                    #A592DB 84%,
                    #D3CBEA 92%,
                    #FFFFFF 100%
                ),
                #0D0B12 !important;
            background-size: 38px 38px, 38px 38px, 100% 100%, 100% 100% !important;
            background-origin: border-box !important;
            background-repeat: repeat, repeat, no-repeat, no-repeat !important;
            background-blend-mode: overlay, overlay, normal, normal !important;
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.7), 0 0 32px rgba(124, 58, 237, 0.18) !important;
        }
        .hero-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        .hero-nodes-row {
            margin: 0 auto 28px auto !important;
        }
        .hero-node-small {
            width: 42px !important;
            height: 42px !important;
            background: #0D0B14 !important;
            border: 1px solid rgba(255, 255, 255, 0.16) !important;
        }
        .hero-node-center {
            width: 56px !important;
            height: 56px !important;
            background: #0D0B14 !important;
            border: 1px solid rgba(255, 255, 255, 0.22) !important;
            box-shadow: 0 0 24px rgba(139, 92, 246, 0.4) !important;
        }
        .hero-connector-line {
            width: 32px !important;
            background: rgba(255, 255, 255, 0.22) !important;
        }
        .hero-title {
            font-size: clamp(2rem, 7.5vw, 2.5rem) !important;
            font-weight: 500 !important;
            line-height: 1.18 !important;
            letter-spacing: -0.035em !important;
            margin: 0 auto 16px auto !important;
            text-align: center !important;
            color: #FFFFFF !important;
            background: none !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }
        .hero-title-gradient, .hero-title-accent {
            display: block !important;
            font-weight: 500 !important;
            color: #FFFFFF !important;
            background: none !important;
            -webkit-text-fill-color: #FFFFFF !important;
        }
        .hero-subtitle {
            font-size: 0.94rem !important;
            line-height: 1.58 !important;
            color: rgba(235, 229, 252, 0.74) !important;
            max-width: 330px !important;
            margin: 0 auto 28px auto !important;
            text-align: center !important;
        }
        .mobile-hero-cta {
            display: flex !important;
            justify-content: center !important;
            width: 100% !important;
            margin: 0 auto !important;
        }
        .mobile-get-started-btn {
            display: inline-flex !important;
            align-items: center !important;
            justify-content: center !important;
            background: #FFFFFF !important;
            color: #0A0A0F !important;
            font-size: 1rem !important;
            font-weight: 600 !important;
            padding: 13px 38px !important;
            border-radius: 9999px !important;
            text-decoration: none !important;
            box-shadow: 0 4px 18px rgba(0, 0, 0, 0.3) !important;
            transition: transform 0.2s ease, box-shadow 0.2s ease !important;
        }
        .mobile-get-started-btn:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.45) !important;
            color: #0A0A0F !important;
        }
        [data-testid="stForm"] {
            display: none !important;
        }
    }
    </style>
    """), unsafe_allow_html=True)

    with st.container(key="hero_panel"):
        # Hero Content (Sitting inside black / dark purple zone)
        st.markdown(clean_html("""
        <div class="hero-container" style="padding-bottom: 1.2rem;">
            <div class="hero-nodes-row">
                <!-- 1. Code Investigation (Stack / Layers icon) -->
                <div class="hero-glass-node hero-node-small hero-node-left" title="Code Investigation">
                    <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                        <polyline points="2 17 12 22 22 17"></polyline>
                        <polyline points="2 12 12 17 22 12"></polyline>
                    </svg>
                </div>
                <div class="hero-connector-line hero-line-left"></div>
                <!-- 2. Decision History (center, prominent, Stylized Emblem) -->
                <div class="hero-glass-node hero-node-center" title="Decision History">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/>
                    </svg>
                </div>
                <div class="hero-connector-line hero-line-right"></div>
                <!-- 3. Verified Evidence (shield with check) -->
                <div class="hero-glass-node hero-node-small hero-node-right" title="Verified Evidence">
                    <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                        <polyline points="9 12 11 14 15 10"></polyline>
                    </svg>
                </div>
            </div>
            <h1 class="hero-title">
                Why The Code<br>
                <span class="hero-title-gradient">Is Like This</span>
            </h1>
            <p class="hero-subtitle">
                Understand the architectural rationale, deprecation milestones, and official source evidence behind code changes.
            </p>
            <div class="mobile-hero-cta">
                <a href="?page=explore" target="_self" class="mobile-get-started-btn">Get Started</a>
            </div>
        </div>
        """), unsafe_allow_html=True)

        # Search Bar Form (White bar with black text, matching height search button)
        with st.form("home_search_form", clear_on_submit=False):
            col_inp, col_btn = st.columns([5, 1.2], gap="small")
            with col_inp:
                query_val = st.text_input(
                    "Search",
                    placeholder="Search a code symbol, method, or deprecation...",
                    value=st.session_state.search_query,
                    label_visibility="collapsed",
                )
            with col_btn:
                submitted = st.form_submit_button("Search", type="primary", use_container_width=True)

    if submitted and query_val:
        st.session_state.search_query = query_val
    # Show Search Results if Search is active
    if st.session_state.search_query:
        raw_query = st.session_state.search_query.strip()
        if is_generic_query(raw_query):
            st.markdown(clean_html(f"""
            <div style="text-align: center; margin: 2rem auto 3rem; padding: 2.2rem 1.8rem; background: var(--surface); border: 1px solid var(--border); border-radius: 16px;">
                <div style="display:inline-flex; align-items:center; justify-content:center; width:48px; height:48px; background:rgba(239,68,68,0.1); border:1px solid rgba(239,68,68,0.25); border-radius:12px; color:#EF4444; margin-bottom:0.75rem;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                </div>
                <div style="font-size: 1.15rem; font-weight: 600; color: var(--text-primary);">Query safely rejected: Too generic or short</div>
                <div style="font-size: 0.88rem; color: var(--text-muted); margin-top: 0.35rem; line-height: 1.6;">
                    The search term <code>{html.escape(raw_query)}</code> is too generic or under 3 characters. Generic queries are safely rejected to prevent ambiguous results. Please search for a specific symbol such as <code>before_first_request</code>, <code>got_first_request</code>, or <code>test_client.as_tuple</code>.
                </div>
            </div>
            """), unsafe_allow_html=True)
        else:
            matched = find_decision(raw_query)
            if matched:
                has_rat = matched.get("has_rationale", True) and bool(matched.get("rationale"))
                src_type = matched.get("source", "Local fallback")
                src_cls = "source-neo4j" if src_type == "Neo4j" else "source-fallback"
                src_icon_svg = db_icon_svg if src_type == "Neo4j" else pkg_icon_svg
                src_badge_html = f'<span class="source-badge {src_cls}">{src_icon_svg}<span>Source: {src_type}</span></span>'
                db_note_html = f'<div style="font-size:0.8rem; color:#A78BFA; background:rgba(167,139,250,0.08); border:1px solid rgba(167,139,250,0.25); border-radius:8px; padding:0.5rem 0.9rem; margin-bottom:1.2rem;">Notice: {matched["db_note"]}</div>' if matched.get("db_note") else ""

                ev_buttons = ""
                for ev in matched.get("evidence", []):
                    ev_buttons += f"""
                    <a href="{ev['url']}" target="_blank" class="evidence-pill-btn">
                        {github_svg}
                        <span>{ev['label']}</span>
                        {ext_arrow_svg}
                    </a>
                    """
                if not ev_buttons:
                    ev_buttons = '<span style="font-size:0.85rem; color:var(--text-muted);">No external evidence links recorded.</span>'

                if has_rat:
                    rationale_box_html = f"""
                    <div class="rationale-quote-box">
                        {matched['rationale']}
                    </div>
                    """
                else:
                    rationale_box_html = f"""
                    <div class="rationale-quote-box" style="border-left: 3px solid #F59E0B; background: rgba(245, 158, 11, 0.08);">
                        <div style="font-size: 0.85rem; font-weight: 600; color: #FBBF24; margin-bottom: 0.35rem;">
                            Verified Rationale Unavailable
                        </div>
                        <div style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.5;">
                            A decision record exists for <code>{html.escape(matched['entity'])}</code>, but verified rationale is unavailable in repository evidence. This system refuses to display fabricated or placeholder explanations.
                        </div>
                    </div>
                    """

                st.markdown(clean_html(f"""
                <div style="width: 100%; margin: 0 auto 1.5rem;">
                    <div class="detail-panel">
                        <div class="detail-top-row">
                            <div class="detail-entity-wrap">
                                <div class="detail-code-icon">
                                    {code_icon_svg}
                                </div>
                                <div>
                                    <div class="detail-title">{matched['entity']}</div>
                                    <div class="detail-category">{matched['category']}</div>
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
                                <span class="{status_badge_class(matched.get('status'))}">{matched.get('status', 'unknown')}</span>
                                {src_badge_html}
                                <a href="?page=explore&decision={matched['entity']}" target="_self" class="decision-badge">
                                    <span>Explorer</span>
                                    {ext_arrow_svg}
                                </a>
                            </div>
                        </div>
                        {db_note_html}
                        <div class="horizontal-timeline-bar">
                            <div class="timeline-step-item">
                                <div class="timeline-circle"></div>
                                <div>
                                    <div class="timeline-text-lbl">Deprecated</div>
                                    <div class="timeline-text-ver">{matched['dep_version']}</div>
                                </div>
                            </div>
                            <div class="timeline-connector"></div>
                            <div class="timeline-step-item">
                                <div class="timeline-circle timeline-circle-removed"></div>
                                <div>
                                    <div class="timeline-text-lbl">Removed</div>
                                    <div class="timeline-text-ver">{matched['rem_version']}</div>
                                </div>
                            </div>
                        </div>
                        <div class="detail-section-title">
                            <span>Why was it removed?</span>
                        </div>
                        {rationale_box_html}
                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
                            <span class="detail-section-title" style="margin:0;">Evidence</span>
                            <div class="evidence-btn-group">
                                {ev_buttons}
                            </div>
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)

                with st.container():
                    expander_label = "View Migration Guidance & Historical Timeline" if has_rat else "View Historical Timeline"
                    with st.expander(expander_label, expanded=True):
                        render_migration_and_timeline(matched)
            else:
                st.markdown(clean_html(f"""
                <div style="text-align: center; margin: 2rem auto 3rem; padding: 2.2rem 1.8rem; background: var(--surface); border: 1px solid var(--border); border-radius: 16px;">
                    <div style="display:inline-flex; align-items:center; justify-content:center; width:48px; height:48px; background:var(--accent-muted); border:1px solid var(--accent-border); border-radius:12px; color:var(--accent); margin-bottom:0.75rem;">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 600; color: var(--text-primary);">No matching decision found.</div>
                    <div style="font-size: 0.88rem; color: var(--text-muted); margin-top: 0.35rem; line-height: 1.6;">
                        The symbol <code>{html.escape(raw_query)}</code> is not present in the currently supported curated Flask dataset. This system follows an evidence-based refusal policy and will not generate or infer an unverified rationale. Try searching for <code>before_first_request</code>, <code>got_first_request</code>, or <code>test_client.as_tuple</code>.
                    </div>
                </div>
                """), unsafe_allow_html=True)

    # 4 Feature Cards (Clean SVG icons, SaaS style)
    st.markdown(clean_html("""
    <div class="feature-grid" style="grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));">
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">AST Code Scanner</h3>
                <p class="feature-desc">Statically inspect Python code to detect deprecated or removed APIs with zero execution.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">PR Diff Analyzer</h3>
                <p class="feature-desc">Inspect git diff patches in public PRs, isolating newly introduced breaking changes.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Prioritized Alerts</h3>
                <p class="feature-desc">Rule-based severity engine categorizing findings by target version milestones.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Decision Knowledge Graph</h3>
                <p class="feature-desc">Neo4j AuraDB graph linking decisions, version events, and verified quotes.</p>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # ═══ Home content sections (stacked, glassmorphism). Data pulled from CURATED_DATA, never hardcoded. ═══
    _ex = CURATED_DATA.get("app.before_first_request") or next(iter(CURATED_DATA.values()))
    _ex_ent = _ex["entity"]
    _ex_short = _ex_ent.split(".")[-1]
    _n_dec = len(CURATED_DATA)
    _ex_ev = _ex.get("evidence", [])
    _ex_url = _ex_ev[0]["url"] if _ex_ev else ""
    _ev_ev = next((e for e in _ex.get("events", []) if e["type"] == "deprecated"), None)
    _rm_ev = next((e for e in _ex.get("events", []) if e["type"] == "removed"), None)
    _repo_url = PROJECT_REPO_URL or "https://github.com/pallets/flask"

    st.markdown(clean_html(f"""
    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">THE PROBLEM</span><h2 class="sec-title">The error tells you what broke. Not why.</h2><p class="sec-sub">After an upgrade, developers see a failure but the reasoning behind the change is scattered across docs, changelogs, Issues and pull requests.</p></div>
        <div class="code-win"><div class="code-win-bar"><i></i><i></i><i></i><span>terminal</span></div>
<pre><span class="err">AttributeError:</span> 'Flask' object has no attribute '<span class="kw">{_ex_short}</span>'</pre></div>
        <div class="glass-box" style="display:flex;flex-direction:column;gap:.9rem;">
            <div class="q-line">Why was it removed?</div>
            <div class="q-line">Which version deprecated it, and which removed it?</div>
            <div class="q-line">Who proposed it, and what did maintainers say?</div>
            <div class="q-line">What should I use instead?</div>
        </div>
        <div class="closing-line">Today that means opening five tabs. We put the answer in one place.</div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">HOW IT WORKS</span><h2 class="sec-title">End-to-end intelligence for breaking changes.</h2></div>
        <div class="glass-box"><span class="step-tag">STEP 01</span><h4>Explore Verified Decisions</h4><p>Search an API symbol or method, like <span class="mono-chip">{_ex_ent}</span>. See deprecation milestones, maintainer quotes, and evidence links.</p></div>
        <div class="flow-link"></div>
        <div class="glass-box"><span class="step-tag">STEP 02</span><h4>Statically Scan Code</h4><p>Paste or upload Python files. The AST scanner identifies deprecated APIs, line numbers, and migration paths without running code.</p></div>
        <div class="flow-link"></div>
        <div class="glass-box"><span class="step-tag">STEP 03</span><h4>Analyze GitHub PR Diffs</h4><p>Input a public GitHub Pull Request URL. The engine isolates added lines from context and detects deprecated APIs before merge.</p></div>
        <div class="flow-link"></div>
        <div class="glass-box"><span class="step-tag">STEP 04</span><h4>Prioritize Actionable Alerts</h4><p>Aggregate findings into Critical, High, and Medium severity tiers based on your evaluation target version.</p></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">UNDER THE HOOD</span><h2 class="sec-title">A graph, not a pile of links.</h2></div>
        <div class="glass-box">
            <p style="margin-bottom:1.2rem !important;">Decisions, change events and evidence are stored as connected nodes in Neo4j, so one query returns the complete story.</p>
            <ul class="check-list">
                <li><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Decision → ChangeEvent <span class="mono-chip">(HAS_EVENT)</span></span></li>
                <li><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Decision → Evidence <span class="mono-chip">(SUPPORTED_BY)</span></span></li>
                <li><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Verified quotes from original GitHub records</span></li>
                <li><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg><span>Source label on every answer: Neo4j or Local fallback</span></li>
            </ul>
        </div>
        <div class="code-win"><div class="code-win-bar"><i></i><i></i><i></i><span>query.cypher</span></div>
<pre><span class="kw">MATCH</span> (d:Decision {{entity: <span class="str">'{_ex_ent}'</span>}})-[:HAS_EVENT]-&gt;(e:ChangeEvent)
<span class="kw">OPTIONAL MATCH</span> (d)-[:SUPPORTED_BY]-&gt;(ev:Evidence)
<span class="kw">RETURN</span> d.entity, e.type, e.version, ev.url</pre></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">WHO IT'S FOR</span><h2 class="sec-title">Built for people who inherit code.</h2></div>
        <div class="glass-box"><div class="glass-row"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg></div><div><h4>Developers upgrading dependencies</h4><p>Understand a breaking change before you rewrite code.</p></div></div></div>
<div class="glass-box"><div class="glass-row"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/></svg></div><div><h4>Open-source contributors</h4><p>Learn why a project works the way it does, from primary sources.</p></div></div></div>
<div class="glass-box"><div class="glass-row"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg></div><div><h4>Tech leads and reviewers</h4><p>Justify an upgrade or a migration plan with real evidence.</p></div></div></div>
<div class="glass-box"><div class="glass-row"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 10L12 5 2 10l10 5 10-5z"/><path d="M6 12v5c3 2 9 2 12 0v-5"/></svg></div><div><h4>Students and new hires</h4><p>Onboard faster by reading the reasoning behind the code.</p></div></div></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">TRUST BY DESIGN</span><h2 class="sec-title">No evidence, no answer.</h2><p class="sec-sub">This system does not generate explanations. It retrieves them.</p></div>
        <div class="glass-box"><div class="glass-row"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg></div><div><h4>Primary sources only</h4><p>Every reason comes from a GitHub Issue, pull request or changelog.</p></div></div></div>
<div class="glass-box"><div class="glass-row"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg></div><div><h4>Verified quotes</h4><p>Stored quotes are checked against the original record.</p></div></div></div>
<div class="glass-box"><div class="glass-row"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg></div><div><h4>Honest fallbacks</h4><p>If a record is missing, the app says so instead of guessing.</p></div></div></div>
        <div class="note-muted">Shipped developer suite: 4 integrated modules across Decision Intelligence, AST Code Scanning, PR Diff Analysis, and Rule-Based Alerts.</div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">ROADMAP</span><h2 class="sec-title">From architectural decisions to automated CI/CD.</h2></div>
        <div class="glass-box road-step"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg></div><span class="road-tag">SHIPPED · 01</span><h4>AST Code Scanner & PR Diff Engine</h4></div>
<div class="flow-link"></div>
<div class="glass-box road-step"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div><span class="road-tag">SHIPPED · 02</span><h4>Rule-Based Alert System</h4></div>
<div class="flow-link"></div>
<div class="glass-box road-step"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg></div><span class="road-tag">SHIPPED · 03</span><h4>Neo4j AuraDB Knowledge Graph</h4></div>
<div class="flow-link"></div>
<div class="glass-box road-step"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 0-3.16 19.5c.5.1.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.15-1.1-1.46-1.1-1.46-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.9.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02a9.5 9.5 0 0 1 5 0c1.9-1.29 2.74-1.02 2.74-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.94.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0 0 12 2z"/></svg></div><span class="road-tag">NEXT · 04</span><h4>CI/CD GitHub Actions & Pre-Commit Hooks</h4></div>
        <div class="note-muted">Active capabilities: 4 core modules deployed. Next expansion brings automated CI checks to repositories.</div>
    </div>

    <div class="home-section" style="margin-bottom:0;">
        <div class="sec-head"><span class="sec-pill">FAQ</span><h2 class="sec-title">Questions, answered.</h2></div>
    </div>
    """), unsafe_allow_html=True)

    with st.container(key="faq_block"):
        with st.expander("Does it use AI to write the reasons?"):
            st.write("No. Every explanation comes directly from original GitHub records. An LLM could later help summarise long discussions, but only with citations back to the source.")
        with st.expander("Does the scanner execute my code?"):
            st.write("Never. The scanner uses Python's native `ast` module to statically inspect code structure. Your code is never imported, run, or evaluated.")
        with st.expander("Which libraries and patterns are covered?"):
            st.write(f"The platform covers verified Flask decisions (@app.before_first_request, app.got_first_request, and test_client.as_tuple) with AST detection, PR diff analysis, and Neo4j graph nodes. The architecture is designed to scale across broader Python frameworks.")
        with st.expander("Where does the data come from?"):
            st.write("Public GitHub Issues and pull requests, plus official changelogs.")
        with st.expander("What if my API is not in the database?"):
            st.write('You will see "No verified evidence found." We never invent an answer.')
        with st.expander("Why Neo4j AuraDB?"):
            st.write("Decisions, events and evidence are connected, and a graph returns that connected history in one query.")

    st.markdown(clean_html(f"""
    <div class="cta-panel">
        <h2>Find the reason.<br>Fix your code.</h2>
        <div class="cta-btns">
            <a class="cta-btn-white" href="?page=explore" target="_self">Try the Explorer</a>
            <a class="cta-btn-glass" href="{_repo_url}" target="_blank" rel="noopener">View on GitHub</a>
        </div>
    </div>
    <div class="home-footer">
        <div class="foot-inner">
            <div class="foot-brand">
                <div class="foot-brand-row">{brand_logo_html}<span>Rationale</span></div>
                <p>Find the reason behind the code. Every answer comes from original GitHub records.</p>
            </div>
            <div class="foot-cols">
                <div class="foot-group"><span class="foot-title">Product</span>
                    <a href="?page=home" target="_self">Home</a><a href="?page=explore" target="_self">Explore Decisions</a><a href="?page=scanner" target="_self">Code Scanner</a><a href="?page=pr" target="_self">PR Analyzer</a><a href="?page=alerts" target="_self">Alerts</a><a href="?page=about" target="_self">About</a></div>
                <div class="foot-group"><span class="foot-title">Resources</span>
                    <a href="{_repo_url}" target="_blank" rel="noopener">GitHub repository</a><a href="https://github.com/pallets/flask" target="_blank" rel="noopener">Flask repository</a></div>
            </div>
        </div>
        <div class="foot-bottom"><span>© 2026 Rationale</span><span>Built with Python, Streamlit and Neo4j AuraDB.</span></div>
    </div>
    """), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: EXPLORE DECISIONS
# ══════════════════════════════════════════════════════════════════════════════

elif is_explore:

    # Spacing below navbar before content begins
    st.markdown('<div style="height: 1.2rem;"></div>', unsafe_allow_html=True)

    # Header Row
    st.markdown(clean_html(f"""
    <div class="section-header-row">
        <div class="section-title-wrap">
            <div class="title-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
                </svg>
            </div>
            <div>
                <h1 class="section-heading">Explore Code Decisions</h1>
                <p class="section-subtext">Browse verified decisions with deprecation milestones, rationale, and primary evidence.</p>
            </div>
        </div>
        <div class="counter-badge">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
            </svg>
            <span>{len(CURATED_DATA)} Verified Records</span>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # Display all 3 decisions vertically, one below another, in full-width glass containers
    for idx, (decision_key, fallback_val) in enumerate(CURATED_DATA.items()):
        # Query Neo4j first for each decision; fallback to CURATED_DATA
        retrieved = find_decision(decision_key)
        if retrieved:
            d_data = retrieved
        else:
            d_data = dict(fallback_val)
            d_data["source"] = "Local fallback"

        entity_name = d_data.get("entity", decision_key)
        cat_name = d_data.get("category", fallback_val.get("category", "Flask — Decision"))
        status_name = d_data.get("status", "removed")
        dep_v = d_data.get("dep_version", "Unknown")
        rem_v = d_data.get("rem_version", "Unknown")
        has_rat = d_data.get("has_rationale", True) and bool(d_data.get("rationale"))
        src_type = d_data.get("source", "Local fallback")
        src_cls = "source-neo4j" if src_type == "Neo4j" else "source-fallback"
        src_icon_svg = db_icon_svg if src_type == "Neo4j" else pkg_icon_svg
        src_badge_html = f'<span class="source-badge {src_cls}">{src_icon_svg}<span>Source: {src_type}</span></span>'
        db_note_html = f'<div style="font-size:0.8rem; color:#A78BFA; background:rgba(167,139,250,0.08); border:1px solid rgba(167,139,250,0.25); border-radius:8px; padding:0.5rem 0.9rem; margin-bottom:1.2rem;">Notice: {d_data["db_note"]}</div>' if d_data.get("db_note") else ""

        ev_buttons = ""
        for ev in d_data.get("evidence", []):
            ev_buttons += f"""
            <a href="{ev['url']}" target="_blank" class="evidence-pill-btn">
                {github_svg}
                <span>{ev['label']}</span>
                {ext_arrow_svg}
            </a>
            """
        if not ev_buttons:
            ev_buttons = '<span style="font-size:0.85rem; color:var(--text-muted);">No external evidence links recorded.</span>'

        if has_rat:
            rationale_html = f"""
            <div class="rationale-quote-box">
                {d_data['rationale']}
            </div>
            """
        else:
            rationale_html = f"""
            <div class="rationale-quote-box" style="border-left: 3px solid #F59E0B; background: rgba(245, 158, 11, 0.08);">
                <div style="font-size: 0.85rem; font-weight: 600; color: #FBBF24; margin-bottom: 0.35rem;">
                    Verified Rationale Unavailable
                </div>
                <div style="font-size: 0.9rem; color: var(--text-secondary); line-height: 1.5;">
                    A decision record exists for <code>{html.escape(entity_name)}</code>, but verified rationale is unavailable in repository evidence. This system refuses to display fabricated or placeholder explanations.
                </div>
            </div>
            """

        with st.container(key=f"explore_card_{idx}"):
            st.markdown(f'<div id="{html.escape(entity_name)}"></div>', unsafe_allow_html=True)
            st.markdown(clean_html(f"""
            <div class="detail-top-row">
                <div class="detail-entity-wrap">
                    <div class="detail-code-icon">
                        {code_icon_svg}
                    </div>
                    <div>
                        <div class="detail-title">{entity_name}</div>
                        <div class="detail-category">{cat_name}</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
                    <span class="{status_badge_class(status_name)}">{status_name}</span>
                    {src_badge_html}
                    <div class="decision-badge">Decision #{idx + 1}</div>
                </div>
            </div>
            {db_note_html}

            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Deprecated In</div>
                        <div class="stat-meta-val">{dep_v}</div>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Removed In</div>
                        <div class="stat-meta-val">{rem_v}</div>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z"/><path d="M7 7h.01"/>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Current Status</div>
                        <div><span class="{status_badge_class(status_name)}">{status_name.capitalize()}</span></div>
                    </div>
                </div>
            </div>

            <div class="horizontal-timeline-bar">
                <div class="timeline-step-item">
                    <div class="timeline-circle"></div>
                    <div>
                        <div class="timeline-text-lbl">Deprecated Milestone</div>
                        <div class="timeline-text-ver">{dep_v}</div>
                    </div>
                </div>
                <div class="timeline-connector"></div>
                <div class="timeline-step-item">
                    <div class="timeline-circle timeline-circle-removed"></div>
                    <div>
                        <div class="timeline-text-lbl">Removal Milestone</div>
                        <div class="timeline-text-ver">{rem_v}</div>
                    </div>
                </div>
            </div>

            <div class="detail-section-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span>Verified Maintainer Rationale</span>
            </div>
            {rationale_html}

            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; margin-bottom: 1.2rem;">
                <div class="detail-section-title" style="margin:0;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                    </svg>
                    <span>Primary Evidence Links</span>
                </div>
                <div class="evidence-btn-group">
                    {ev_buttons}
                </div>
            </div>
            """), unsafe_allow_html=True)

            # Render Migration Guidance (Before vs After) and Historical Timeline inside this full-width glass card
            render_migration_and_timeline(d_data)

        st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: CODE SCANNER (PYTHON STATIC AST ANALYSIS)
# ══════════════════════════════════════════════════════════════════════════════

elif is_scanner:

    st.markdown('<div style="height: 1.8rem;"></div>', unsafe_allow_html=True)

    # Header Row
    st.markdown(clean_html("""
    <div class="tool-page-header">
        <div class="tool-header-top-meta">
            <span class="sec-pill">STATIC CODE ANALYSIS</span>
            <div class="badge-count-pill">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
                </svg>
                <span>3 Verified Patterns</span>
            </div>
        </div>
        <h1 class="tool-page-title">Python Deprecated API Scanner</h1>
        <p class="tool-page-subtitle">Statically inspects Python source code using AST parsing to detect deprecated or removed Flask APIs. Never executes user code.</p>
    </div>
    """), unsafe_allow_html=True)

    # Box 1: Python Source Code Input
    with st.container(key="scanner_source_box"):
        st.markdown(clean_html("""
        <div class="stacked-box-header">
            <div class="stacked-box-title-group">
                <span class="step-num-pill">01</span>
                <span class="stacked-box-title">Python Source Code Input</span>
            </div>
            <span class="stacked-box-tag">Static AST (Safe, Zero-Execution)</span>
        </div>
        <div class="stacked-box-desc">Paste your Python code below or upload a <code>.py</code> file. AST parsing never executes, imports, or evaluates user code.</div>
        """), unsafe_allow_html=True)

        pasted_code = st.text_area(
            "Python Source Code",
            height=230,
            placeholder="""# Example: Paste Python source code here
from flask import Flask

app = Flask(__name__)

@app.before_first_request
def setup_app():
    pass

if not app.got_first_request:
    setup_app()

with app.test_client() as client:
    res, env = client.get('/', as_tuple=True)""",
            help="Code is parsed statically into an AST. It is never run or evaluated.",
            label_visibility="collapsed",
        )

        uploaded_file = st.file_uploader(
            "Or upload a Python (.py) file",
            type=["py"],
            help="Select a local Python source file to scan statically."
        )

    # Box 2: Scan Configuration & Scope
    with st.container(key="scanner_config_box"):
        st.markdown(clean_html("""
        <div class="stacked-box-header">
            <div class="stacked-box-title-group">
                <span class="step-num-pill">02</span>
                <span class="stacked-box-title">Scan Configuration & Target Version</span>
            </div>
            <span class="stacked-box-tag">Lifecycle Milestone Matching</span>
        </div>
        <div class="stacked-box-desc">Optionally specify your target Flask version to compare findings against verified deprecation and removal milestones.</div>
        """), unsafe_allow_html=True)

        col_v, col_scope = st.columns([1.2, 1.8], gap="medium")
        with col_v:
            target_v = st.text_input(
                "Target Flask Version (optional)",
                placeholder="e.g. 2.2.0, 2.3.0, 3.0.0",
                help="If provided, the scanner compares findings against verified lifecycle milestones to distinguish 'Deprecated' from 'Removed'."
            )
        with col_scope:
            st.markdown(clean_html("""
            <div style="font-size: 0.85rem; font-weight: 600; color: rgba(255, 255, 255, 0.9); margin-bottom: 0.4rem;">Supported Detection Scope:</div>
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                <span class="scope-pill">@app.before_first_request</span>
                <span class="scope-pill">app.got_first_request</span>
                <span class="scope-pill">test_client.as_tuple</span>
            </div>
            <div style="font-size: 0.78rem; color: rgba(255, 255, 255, 0.5); margin-top: 0.4rem;">AST detection is strictly scoped to verified catalogue patterns.</div>
            """), unsafe_allow_html=True)

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        scan_clicked = st.button("Scan Source Code", type="primary", use_container_width=True)

    # Determine code to scan
    source_to_scan = ""
    file_label = "<input>"
    if uploaded_file is not None:
        try:
            source_to_scan = uploaded_file.getvalue().decode("utf-8", errors="replace")
            file_label = uploaded_file.name
        except Exception as e:
            st.error(f"Failed to read uploaded file: {e}")
    elif pasted_code:
        source_to_scan = pasted_code
        file_label = "<pasted_code>"

    scan_res = None
    if scan_clicked:
        if not source_to_scan.strip():
            st.info("Please paste Python source code or upload a .py file to scan.")
        else:
            scan_res = code_scanner.scan_code(
                source_code=source_to_scan,
                file_name=file_label,
                target_version=target_v.strip() if target_v else None
            )
            st.session_state["scan_result"] = scan_res
            st.session_state["scan_findings"] = scan_res.findings
            st.session_state["scan_target_version"] = target_v.strip() if target_v else None
            st.session_state["scan_file_name"] = file_label
            log_workflow_event("SCAN_COMPLETED", file_label, f"Scanned {scan_res.lines_scanned} lines, detected {scan_res.total_findings} findings (Target: {scan_res.target_version or 'Unspecified'})", source="Code Scanner")
    elif "scan_result" in st.session_state and st.session_state["scan_result"] is not None:
        scan_res = st.session_state["scan_result"]
    else:
        last_scan = get_last_scan_result_safe()
        if last_scan and last_scan.findings:
            scan_res = last_scan
            st.session_state["scan_result"] = scan_res
            st.session_state["scan_findings"] = scan_res.findings
            st.session_state["scan_target_version"] = scan_res.target_version
            st.session_state["scan_file_name"] = scan_res.file_name

    if scan_res is not None:
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

        if not scan_res.success:
            st.error(f"Scanner Notice: {scan_res.error}")
        elif scan_res.total_findings == 0:
            st.session_state["scan_findings"] = []
            st.session_state["scan_target_version"] = target_v.strip() if target_v else None
            st.session_state["scan_file_name"] = file_label
            st.markdown(clean_html("""
            <div style="text-align: center; margin: 1.5rem auto 2.5rem; padding: 2.2rem 1.8rem; background: var(--surface); border: 1px solid var(--border); border-radius: 16px;">
                <div style="display:inline-flex; align-items:center; justify-content:center; width:48px; height:48px; background:rgba(34, 197, 94, 0.1); border:1px solid rgba(34, 197, 94, 0.25); border-radius:12px; color:#22C55E; margin-bottom:0.75rem;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </div>
                <div style="font-size: 1.15rem; font-weight: 600; color: var(--text-primary);">No known deprecated Flask API patterns detected by the current scanner.</div>
                <div style="font-size: 0.88rem; color: var(--text-muted); margin-top: 0.35rem; line-height: 1.6;">
                    This scanner strictly checks against the current verified Flask catalogue (<code>app.before_first_request</code>, <code>got_first_request</code>, and <code>test_client.as_tuple</code>). This does not claim or certify that the entire codebase is free from other deprecations or issues.
                </div>
            </div>
            """), unsafe_allow_html=True)
        else:
            st.session_state["scan_findings"] = scan_res.findings
            st.session_state["scan_target_version"] = target_v.strip() if target_v else None
            st.session_state["scan_file_name"] = file_label
            log_workflow_event("SCAN_COMPLETED", file_label, f"Scanned {scan_res.lines_scanned} lines, detected {scan_res.total_findings} findings (Target: {scan_res.target_version or 'Unspecified'})", source="Code Scanner")
            # Render summary header
            col_hdr_left, col_hdr_right = st.columns([2.2, 1.8], vertical_alignment="center")
            with col_hdr_left:
                st.markdown(clean_html(f"""
                <div style="display: flex; align-items: center; flex-wrap: wrap; gap: 0.6rem;">
                    <span class="detail-section-title" style="margin: 0;">Scan Results</span>
                    <span style="font-size: 0.88rem; color: var(--text-muted);">File: <code>{html.escape(scan_res.file_name)}</code> ({scan_res.lines_scanned} lines scanned)</span>
                    <span class="source-badge source-fallback"><span>Total Findings: {scan_res.total_findings}</span></span>
                </div>
                """), unsafe_allow_html=True)
            with col_hdr_right:
                if st.button("View Prioritized Alerts →", key="view_scanner_alerts_btn", type="secondary", use_container_width=True):
                    st.session_state.nav = "alerts"
                    st.query_params["page"] = "alerts"
                    st.rerun()

            st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)

            # Render each finding full-width
            for idx, finding in enumerate(scan_res.findings):
                badge_cls = status_badge_class(finding.status.split()[0].lower())
                ev_link_html = ""
                if finding.evidence_url:
                    ev_link_html = f"""
                    <a href="{finding.evidence_url}" target="_blank" class="evidence-pill-btn">
                        {github_svg}
                        <span>Verified Source</span>
                        {ext_arrow_svg}
                    </a>
                    """

                st.markdown(clean_html(f"""
                <div class="detail-panel" style="margin-bottom: 1.5rem;">
                    <div class="detail-top-row">
                        <div class="detail-entity-wrap">
                            <div class="detail-code-icon">
                                {code_icon_svg}
                            </div>
                            <div>
                                <div class="detail-title">{finding.symbol}</div>
                                <div class="detail-category"><code>{html.escape(finding.file_name)}</code> — Line {finding.line}, Column {finding.col} (Pattern: {finding.detection_type})</div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap;">
                            <span class="{badge_cls}">{finding.status}</span>
                            <a href="?page=explore&decision={finding.symbol}" target="_self" class="decision-badge">
                                <span>Explorer</span>
                                {ext_arrow_svg}
                            </a>
                        </div>
                    </div>

                    <div class="horizontal-timeline-bar" style="margin: 1rem 0;">
                        <div class="timeline-step-item">
                            <div class="timeline-circle"></div>
                            <div>
                                <div class="timeline-text-lbl">Deprecated</div>
                                <div class="timeline-text-ver">{finding.dep_version or 'N/A'}</div>
                            </div>
                        </div>
                        <div class="timeline-connector"></div>
                        <div class="timeline-step-item">
                            <div class="timeline-circle timeline-circle-removed"></div>
                            <div>
                                <div class="timeline-text-lbl">Removed</div>
                                <div class="timeline-text-ver">{finding.rem_version or 'N/A'}</div>
                            </div>
                        </div>
                    </div>

                    <div class="detail-section-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                        </svg>
                        <span>Verified Rationale</span>
                    </div>
                    <div class="rationale-quote-box">
                        {finding.explanation}
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; margin-top: 1rem;">
                        <span class="detail-section-title" style="margin:0;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                            </svg>
                            <span>Evidence</span>
                        </span>
                        <div class="evidence-btn-group">
                            {ev_link_html}
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)

                # Lifecycle Change Events (HAS_EVENT) for this detected finding
                render_lifecycle_events_component(finding.symbol, title=f"Lifecycle Change Events: {finding.symbol}")

                with st.expander(f"View Verified Migration Guidance: {finding.symbol}", expanded=False):
                    render_migration_guidance_component(finding.symbol, target_version=target_v.strip() if target_v else None)

            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            render_event_audit_log_component()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4: PULL REQUEST ANALYZER (DIFF INSPECTION)
# ══════════════════════════════════════════════════════════════════════════════

elif is_pr:

    st.markdown('<div style="height: 1.8rem;"></div>', unsafe_allow_html=True)

    # Header Row
    st.markdown(clean_html("""
    <div class="tool-page-header">
        <div class="tool-header-top-meta">
            <span class="sec-pill">GITHUB PR ANALYSIS</span>
            <div class="badge-count-pill">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="18" cy="18" r="3"></circle>
                    <circle cx="6" cy="6" r="3"></circle>
                    <path d="M13 6h3a2 2 0 0 1 2 2v7"></path>
                    <line x1="6" y1="9" x2="6" y2="21"></line>
                </svg>
                <span>Public PR Diff</span>
            </div>
        </div>
        <h1 class="tool-page-title">Pull Request Diff Analyzer</h1>
        <p class="tool-page-subtitle">Analyzes changed Python code in public GitHub Pull Requests to detect deprecated or removed Flask APIs. Distinguishes newly introduced code from surrounding context.</p>
    </div>
    """), unsafe_allow_html=True)

    # Box 1: Public GitHub PR URL Input
    with st.container(key="pr_input_box1"):
        st.markdown(clean_html("""
        <div class="stacked-box-header">
            <div class="stacked-box-title-group">
                <span class="step-num-pill">01</span>
                <span class="stacked-box-title">Public GitHub Pull Request URL</span>
            </div>
            <span class="stacked-box-tag">Public GitHub REST API</span>
        </div>
        <div class="stacked-box-desc">Enter a public GitHub PR URL. The analyzer fetches diff patches and metadata without requiring credentials.</div>
        """), unsafe_allow_html=True)

        pr_url_input = st.text_input(
            "Public GitHub Pull Request URL",
            placeholder="https://github.com/pallets/flask/pull/4997",
            help="Enter a public GitHub PR URL (e.g. https://github.com/owner/repo/pull/123)",
            label_visibility="collapsed"
        )
        st.caption("Example: `https://github.com/pallets/flask/pull/4997` (public unauthenticated GitHub REST API)")

    # Box 2: Target Version & Scope
    with st.container(key="pr_input_box2"):
        st.markdown(clean_html("""
        <div class="stacked-box-header">
            <div class="stacked-box-title-group">
                <span class="step-num-pill">02</span>
                <span class="stacked-box-title">Target Flask Version & Scope</span>
            </div>
            <span class="stacked-box-tag">Diff Ingestion</span>
        </div>
        <div class="stacked-box-desc">Optionally set a target Flask version to categorize breaking changes vs deprecation warnings in the PR diff.</div>
        """), unsafe_allow_html=True)

        col_pr_v, col_pr_info = st.columns([1.2, 1.8], gap="medium")
        with col_pr_v:
            pr_target_v = st.text_input(
                "Target Flask Version (optional)",
                placeholder="e.g. 2.2.0, 2.3.0, 3.0.0",
                help="If supplied, compares detected findings against verified milestones to distinguish 'Deprecated' from 'Removed'.",
                label_visibility="collapsed"
            )
        with col_pr_info:
            st.markdown(clean_html("""
            <div style="font-size: 0.85rem; font-weight: 600; color: rgba(255, 255, 255, 0.9); margin-bottom: 0.35rem;">Diff Analysis Capability:</div>
            <div style="font-size: 0.82rem; color: rgba(255, 255, 255, 0.65); line-height: 1.5;">
                Parses unified git diffs, isolates additions (<code>+</code>) from modifications, and runs AST checks only on active changes.
            </div>
            """), unsafe_allow_html=True)

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        analyze_btn = st.button("Analyze Pull Request", type="primary", use_container_width=True)

    if analyze_btn:
        if not pr_url_input.strip():
            st.info("Please enter a public GitHub Pull Request URL.")
        else:
            with st.spinner("Fetching PR metadata and diff patches from GitHub..."):
                pr_res = pr_analyzer.analyze_pr(
                    pr_url=pr_url_input.strip(),
                    target_version=pr_target_v.strip() if pr_target_v else None
                )

            st.markdown("<div style='height: 1.2rem;'></div>", unsafe_allow_html=True)

            if not pr_res.success:
                st.error(f"Analysis Notice: {pr_res.error}")
            else:
                # Save findings to session state for the Alerts system
                st.session_state["pr_findings"] = pr_res.findings
                st.session_state["pr_target_version"] = pr_target_v.strip() if pr_target_v else None
                st.session_state["pr_url"] = pr_res.pr_url
                st.session_state["pr_result"] = pr_res
                log_workflow_event("PR_ANALYZED", f"PR #{pr_res.pr_number}", f"Inspected {len(pr_res.analyzed_files)} files, found {pr_res.total_findings} findings (Repo: {pr_res.owner}/{pr_res.repo})", source="PR Analyzer")

    # Check if we have active PR result to display
    pr_res_to_display = None
    if "pr_result" in st.session_state and st.session_state["pr_result"] is not None:
        pr_res_to_display = st.session_state["pr_result"]

    if pr_res_to_display is not None:
        pr_res = pr_res_to_display
        # 1. PR Overview Card
        state_badge = '<span class="pill-status pill-status-active">Open</span>' if pr_res.pr_state == "open" else '<span class="pill-status pill-status-removed">Closed</span>'
        
        with st.container(key="pr_overview_panel"):
            col_pr_hdr_l, col_pr_hdr_r = st.columns([2.2, 1.8], vertical_alignment="center")
            with col_pr_hdr_l:
                st.markdown(clean_html(f"""
                <div class="detail-entity-wrap">
                    <div class="detail-code-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="18" cy="18" r="3"></circle>
                            <circle cx="6" cy="6" r="3"></circle>
                            <path d="M13 6h3a2 2 0 0 1 2 2v7"></path>
                            <line x1="6" y1="9" x2="6" y2="21"></line>
                        </svg>
                    </div>
                    <div>
                        <div class="detail-title">{html.escape(pr_res.owner)} / {html.escape(pr_res.repo)} #{pr_res.pr_number}</div>
                        <div class="detail-category">{html.escape(pr_res.pr_title)} (by @{html.escape(pr_res.author)})</div>
                    </div>
                </div>
                """), unsafe_allow_html=True)
            with col_pr_hdr_r:
                col_pra1, col_pra2 = st.columns([1, 1.4], vertical_alignment="center")
                with col_pra1:
                    st.markdown(clean_html(f"""
                    <div style="display:flex; align-items:center; gap:0.5rem; justify-content:flex-end;">
                        {state_badge}
                        <a href="{pr_res.pr_url}" target="_blank" class="evidence-pill-btn">
                            {github_svg}
                            <span>Open PR</span>
                            {ext_arrow_svg}
                        </a>
                    </div>
                    """), unsafe_allow_html=True)
                with col_pra2:
                    if st.button("View Prioritized Alerts →", key="view_pr_alerts_btn", type="secondary", use_container_width=True):
                        st.session_state.nav = "alerts"
                        st.query_params["page"] = "alerts"
                        st.rerun()

            st.markdown(clean_html(f"""
            <div class="stats-grid" style="margin-top: 1.2rem;">
                <div class="stat-item">
                    <div class="stat-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                            <polyline points="14 2 14 8 20 8"></polyline>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Files Changed</div>
                        <div class="stat-meta-val">{pr_res.total_files_changed}</div>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Python Files Analyzed</div>
                        <div class="stat-meta-val">{len(pr_res.analyzed_files)}</div>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-icon">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Total Findings</div>
                        <div class="stat-meta-val">{pr_res.total_findings} <span style="font-size:0.75rem; color:var(--text-muted);">({pr_res.added_findings_count} added, {pr_res.context_findings_count} context)</span></div>
                    </div>
                </div>
            </div>
            """), unsafe_allow_html=True)

        # 2. File Breakdown Expander
        with st.expander("View Analyzed & Skipped Files Breakdown", expanded=False):
            col_af, col_sf = st.columns(2)
            with col_af:
                st.markdown(f"**Analyzed Python Files ({len(pr_res.analyzed_files)})**")
                if not pr_res.analyzed_files:
                    st.caption("No Python files with available patches were analyzed.")
                for af in pr_res.analyzed_files:
                    partial_tag = " ⚠️ **[Partially Analyzed]**" if af.status == "partially_analyzed" else ""
                    st.markdown(f"- `+{af.additions} -{af.deletions}` **{af.filename}** ({af.findings_count} findings){partial_tag}")
                    if af.status == "partially_analyzed":
                        st.caption(f"  ↳ {af.reason}")
            with col_sf:
                st.markdown(f"**Skipped Files ({len(pr_res.skipped_files)})**")
                if not pr_res.skipped_files:
                    st.caption("No files were skipped.")
                for sf in pr_res.skipped_files:
                    st.markdown(f"- **{sf.filename}**: *{sf.reason}*")

        # 3. Findings Section
        if pr_res.total_findings == 0:
            st.markdown(clean_html("""
            <div style="text-align: center; margin: 1.5rem auto 2.5rem; padding: 2.2rem 1.8rem; background: var(--surface); border: 1px solid var(--border); border-radius: 16px;">
                <div style="display:inline-flex; align-items:center; justify-content:center; width:48px; height:48px; background:rgba(34, 197, 94, 0.1); border:1px solid rgba(34, 197, 94, 0.25); border-radius:12px; color:#22C55E; margin-bottom:0.75rem;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                </div>
                <div style="font-size: 1.15rem; font-weight: 600; color: var(--text-primary);">No known deprecated Flask API patterns were detected in the available changed Python code.</div>
                <div style="font-size: 0.88rem; color: var(--text-muted); margin-top: 0.35rem; line-height: 1.6;">
                    This analysis is strictly limited to the changed Python patch content for the 3 curated Flask decisions (<code>app.before_first_request</code>, <code>got_first_request</code>, and <code>test_client.as_tuple</code>). This does not claim or mean that the entire PR or repository is free of deprecated APIs.
                </div>
            </div>
            """), unsafe_allow_html=True)
        else:
            st.markdown(f"### Detected Findings ({pr_res.total_findings})")
            for finding in pr_res.findings:
                # Distinguish added vs context badge
                if finding.change_type == "added":
                    origin_badge = '<span class="pill-status pill-status-removed" style="background:rgba(239,68,68,0.15); color:#FCA5A5; border:1px solid rgba(239,68,68,0.3);">Added in PR</span>'
                else:
                    origin_badge = '<span class="pill-status pill-status-deprecated" style="background:rgba(148,163,184,0.12); color:#CBD5E1; border:1px solid rgba(148,163,184,0.25);">Existing Context</span>'

                line_str = f"Line {finding.line_number}" if finding.line_number is not None else "Line unavailable"
                badge_cls = status_badge_class(finding.status.split()[0].lower())

                # Confidence badge: distinguish high from partial/medium
                if finding.confidence and "medium" in finding.confidence.lower():
                    confidence_badge = '<span class="pill-status pill-status-deprecated" style="background:rgba(234,179,8,0.12); color:#FBBF24; border:1px solid rgba(234,179,8,0.3); font-size:0.72rem;">⚠ Partial Context</span>'
                else:
                    confidence_badge = '<span class="pill-status pill-status-active" style="font-size:0.72rem;">High Confidence</span>'

                ev_link_html = ""
                if finding.evidence_url:
                    ev_link_html = f"""
                    <a href="{finding.evidence_url}" target="_blank" class="evidence-pill-btn">
                        {github_svg}
                        <span>Verified Evidence</span>
                        {ext_arrow_svg}
                    </a>
                    """

                st.markdown(clean_html(f"""
                <div class="detail-panel" style="margin-bottom: 1.2rem;">
                    <div class="detail-top-row">
                        <div class="detail-entity-wrap">
                            <div class="detail-code-icon">
                                {code_icon_svg}
                            </div>
                            <div>
                                <div class="detail-title">{finding.symbol}</div>
                                <div class="detail-category"><code>{html.escape(finding.file_path)}</code> — {line_str} (Pattern: {finding.detection_type})</div>
                            </div>
                        </div>
                        <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
                            {origin_badge}
                            <span class="{badge_cls}">{finding.status}</span>
                            {confidence_badge}
                            <a href="?page=explore&decision={finding.symbol}" target="_self" class="decision-badge">
                                <span>Explorer</span>
                                {ext_arrow_svg}
                            </a>
                        </div>
                    </div>

                    <div style="margin: 0.8rem 0; padding: 0.6rem 0.9rem; background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 8px; font-family:'JetBrains Mono',monospace; font-size:0.85rem; color:#E2E8F0;">
                        {html.escape(finding.snippet)}
                    </div>

                    <div class="horizontal-timeline-bar" style="margin: 1rem 0;">
                        <div class="timeline-step-item">
                            <div class="timeline-circle"></div>
                            <div>
                                <div class="timeline-text-lbl">Deprecated</div>
                                <div class="timeline-text-ver">{finding.dep_version or 'N/A'}</div>
                            </div>
                        </div>
                        <div class="timeline-connector"></div>
                        <div class="timeline-step-item">
                            <div class="timeline-circle timeline-circle-removed"></div>
                            <div>
                                <div class="timeline-text-lbl">Removed</div>
                                <div class="timeline-text-ver">{finding.rem_version or 'N/A'}</div>
                            </div>
                        </div>
                    </div>

                    <div class="detail-section-title">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                        </svg>
                        <span>Verified Rationale</span>
                    </div>
                    <div class="rationale-quote-box">
                        {finding.explanation}
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; margin-top: 1rem;">
                        <span class="detail-section-title" style="margin:0;">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                            </svg>
                            <span>Evidence</span>
                        </span>
                        <div class="evidence-btn-group">
                            {ev_link_html}
                        </div>
                    </div>
                </div>
                """), unsafe_allow_html=True)

                # Lifecycle Change Events (HAS_EVENT) for this PR finding
                render_lifecycle_events_component(finding.symbol, title=f"Lifecycle Change Events: {finding.symbol}")

                with st.expander(f"View Verified Migration Guidance: {finding.symbol}", expanded=False):
                    render_migration_guidance_component(finding.symbol, target_version=pr_target_v.strip() if pr_target_v else None)

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        render_event_audit_log_component()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5: ACTIONABLE FINDINGS & ALERT SYSTEM (STEP 6)
# ══════════════════════════════════════════════════════════════════════════════

elif is_alerts:

    st.markdown('<div style="height: 1.8rem;"></div>', unsafe_allow_html=True)

    # Header Row
    st.markdown(clean_html("""
    <div class="tool-page-header">
        <div class="tool-header-top-meta">
            <span class="sec-pill">PRIORITIZED ALERTS</span>
            <div class="badge-count-pill">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
                <span>Rule-Based Prioritization</span>
            </div>
        </div>
        <h1 class="tool-page-title">Actionable Findings & Alert System</h1>
        <p class="tool-page-subtitle">Translates AST scanner and PR analyzer findings into transparent, rule-based alerts to prioritize what breaks first. Alerts are categorized strictly by verified lifecycle milestones (Critical, High, Medium, Informational).</p>
    </div>
    """), unsafe_allow_html=True)

    # 1. Source Data Gathering
    scan_findings = st.session_state.get("scan_findings", [])
    scan_target_v = st.session_state.get("scan_target_version")
    if not scan_findings:
        last_scan = get_last_scan_result_safe()
        if last_scan and last_scan.findings:
            scan_findings = last_scan.findings
            st.session_state["scan_findings"] = scan_findings
            if not scan_target_v:
                scan_target_v = last_scan.target_version
                st.session_state["scan_target_version"] = scan_target_v
            if not st.session_state.get("scan_file_name"):
                st.session_state["scan_file_name"] = last_scan.file_name
    pr_findings = st.session_state.get("pr_findings", [])
    pr_target_v = st.session_state.get("pr_target_version")

    # Box 1: Findings Detection Source
    with st.container(key="alerts_input_box1"):
        st.markdown(clean_html("""
        <div class="stacked-box-header">
            <div class="stacked-box-title-group">
                <span class="step-num-pill">01</span>
                <span class="stacked-box-title">Findings Detection Source</span>
            </div>
            <span class="stacked-box-tag">Pipeline Ingestion</span>
        </div>
        <div class="stacked-box-desc">Choose which detection sources to aggregate and prioritize into actionable alerts.</div>
        """), unsafe_allow_html=True)

        source_filter_choice = st.radio(
            "Select Findings Source",
            options=["All Active Sources (Merged)", "Local Code Scan", "GitHub PR Diff"],
            horizontal=True,
            help="Choose which detection source to inspect alerts for."
        )

    # Box 2: Target Version Severity Override & Thresholds
    with st.container(key="alerts_input_box2"):
        st.markdown(clean_html("""
        <div class="stacked-box-header">
            <div class="stacked-box-title-group">
                <span class="step-num-pill">02</span>
                <span class="stacked-box-title">Version Severity Override & Thresholds</span>
            </div>
            <span class="stacked-box-tag">Rule-Based Prioritization</span>
        </div>
        <div class="stacked-box-desc">Set or override the Flask target version to re-evaluate alert severities against verified lifecycle milestones.</div>
        """), unsafe_allow_html=True)

        col_ver, col_rules = st.columns([1.2, 1.8], gap="medium")
        with col_ver:
            alert_target_override = st.text_input(
                "Evaluation Target Version",
                value=scan_target_v or pr_target_v or "",
                placeholder="e.g. 2.2.0, 2.3.0, 3.0.0",
                help="Override or set the Flask target version to re-evaluate severity (Critical if target >= removal)."
            )
        with col_rules:
            st.markdown(clean_html("""
            <div style="font-size: 0.85rem; font-weight: 600; color: rgba(255, 255, 255, 0.9); margin-bottom: 0.35rem;">Severity Priority Matrix:</div>
            <div style="display: flex; gap: 0.45rem; flex-wrap: wrap;">
                <span class="pill-severity pill-severity-critical">Critical · Removed in Target</span>
                <span class="pill-severity pill-severity-high">High · Deprecated in Target</span>
                <span class="pill-severity pill-severity-medium">Medium · Deprecation Planned</span>
                <span class="pill-severity pill-severity-info">Info · Advisory</span>
            </div>
            """), unsafe_allow_html=True)

    eval_target_v = alert_target_override.strip() if alert_target_override else None

    # Sample data generator for quick evaluation/demo if no scan has been executed yet
    if not scan_findings and not pr_findings:
        st.markdown(clean_html("""
        <div style="margin: 1.2rem 0; padding: 1.2rem 1.4rem; background: rgba(59, 130, 246, 0.08); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: 12px;">
            <div style="font-weight: 600; color: #93C5FD; margin-bottom: 0.35rem;">No active scan or PR analysis findings in the current session.</div>
            <div style="font-size: 0.88rem; color: #CBD5E1; line-height: 1.55;">
                Run a scan on the <strong>Code Scanner</strong> page or inspect a pull request on the <strong>PR Analyzer</strong> page. Alternatively, click below to load a verified sample dataset to test alert prioritization.
            </div>
        </div>
        """), unsafe_allow_html=True)
        if st.button("Load Verified Sample Findings (Demo)", type="secondary"):
            sample_code = '''
# Sample Application
@app.before_first_request
def setup():
    pass

if not app.got_first_request:
    initialize()

def test_api(client):
    return client.get('/status', as_tuple=True)
'''
            demo_scan = code_scanner.scan_code(sample_code, file_name="demo_app.py", target_version="2.3.0")
            st.session_state["scan_findings"] = demo_scan.findings
            st.session_state["scan_target_version"] = "2.3.0"
            st.session_state["scan_file_name"] = "demo_app.py"
            st.rerun()

    # Build the report based on chosen source
    scan_report = alert_engine.alerts_from_scan_findings(scan_findings, target_version=eval_target_v)
    pr_report = alert_engine.alerts_from_pr_findings(pr_findings, target_version=eval_target_v)

    if source_filter_choice == "Local Code Scan":
        active_report = scan_report
    elif source_filter_choice == "GitHub PR Diff":
        active_report = pr_report
    else:
        active_report = alert_engine.merge_reports(scan_report, pr_report)

    # Initialize and apply session-based alert status overrides
    if "alert_statuses" not in st.session_state:
        st.session_state["alert_statuses"] = {}

    active_report = alert_engine.apply_status_overrides(active_report, st.session_state["alert_statuses"])

    # Notice about session status storage
    st.caption("ℹ️ *Alert statuses ('New', 'Needs Review', 'Resolved') and severity assessments are session-based (temporary state).*")

    # Metric Cards Grid
    st.markdown(clean_html(f"""
    <div class="stats-grid" style="margin: 1rem 0 1.5rem 0;">
        <div class="stat-item">
            <div class="stat-icon">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
            </div>
            <div>
                <div class="stat-meta-label">Total Alerts</div>
                <div class="stat-meta-val">{active_report.total}</div>
            </div>
        </div>
        <div class="stat-item">
            <div class="stat-icon" style="background: rgba(239, 68, 68, 0.15); color: #F87171;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>
            </div>
            <div>
                <div class="stat-meta-label">Critical (Removed)</div>
                <div class="stat-meta-val" style="color: #F87171;">{active_report.critical_count}</div>
            </div>
        </div>
        <div class="stat-item">
            <div class="stat-icon" style="background: rgba(249, 115, 22, 0.15); color: #FB923C;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line>
                </svg>
            </div>
            <div>
                <div class="stat-meta-label">High (Removal Slated)</div>
                <div class="stat-meta-val" style="color: #FB923C;">{active_report.high_count}</div>
            </div>
        </div>
        <div class="stat-item">
            <div class="stat-icon" style="background: rgba(245, 158, 11, 0.15); color: #FBBF24;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>
                </svg>
            </div>
            <div>
                <div class="stat-meta-label">Medium (Deprecated)</div>
                <div class="stat-meta-val" style="color: #FBBF24;">{active_report.medium_count}</div>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # Empty State Check
    if active_report.total == 0:
        st.markdown(clean_html("""
        <div style="text-align: center; margin: 2rem auto; padding: 2.5rem 1.8rem; background: var(--surface); border: 1px solid var(--border); border-radius: 16px;">
            <div style="display:inline-flex; align-items:center; justify-content:center; width:48px; height:48px; background:rgba(34, 197, 94, 0.1); border:1px solid rgba(34, 197, 94, 0.25); border-radius:12px; color:#22C55E; margin-bottom:0.75rem;">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
            </div>
            <div style="font-size: 1.15rem; font-weight: 600; color: var(--text-primary);">No active alerts detected.</div>
            <div style="font-size: 0.88rem; color: var(--text-muted); margin-top: 0.35rem; line-height: 1.6;">
                No known supported deprecated or removed Flask API patterns were detected in the selected findings source.
            </div>
        </div>
        """), unsafe_allow_html=True)
    else:
        # Filters Bar
        st.markdown(clean_html("""
        <div class="form-section-title" style="margin-top: 1.5rem; margin-bottom: 0.8rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
            </svg>
            <span>Filter & Prioritize Alerts</span>
        </div>
        """), unsafe_allow_html=True)
        f_col1, f_col2, f_col3, f_col4 = st.columns(4)

        with f_col1:
            sel_severity = st.selectbox(
                "Severity",
                options=["All", "Critical", "High", "Medium", "Informational"],
                index=0
            )
        with f_col2:
            sel_status = st.selectbox(
                "Status",
                options=["All", "New", "Needs Review", "Resolved"],
                index=0
            )
        with f_col3:
            all_symbols = sorted(list(set(a.symbol for a in active_report.alerts)))
            sel_symbol = st.selectbox(
                "API Symbol",
                options=["All"] + all_symbols,
                index=0
            )
        with f_col4:
            all_sources = sorted(list(set(a.source for a in active_report.alerts)))
            sel_source = st.selectbox(
                "Detection Source",
                options=["All"] + all_sources,
                index=0
            )

        # Apply user filters
        filtered_alerts = active_report.alerts
        if sel_severity != "All":
            filtered_alerts = [a for a in filtered_alerts if a.severity == sel_severity]
        if sel_status != "All":
            filtered_alerts = [a for a in filtered_alerts if a.status == sel_status]
        if sel_symbol != "All":
            filtered_alerts = [a for a in filtered_alerts if a.symbol == sel_symbol]
        if sel_source != "All":
            filtered_alerts = [a for a in filtered_alerts if a.source == sel_source]

        st.markdown(f"Showing **{len(filtered_alerts)}** of **{active_report.total}** alerts")

        if not filtered_alerts:
            st.info("No alerts match the chosen filter criteria.")
        else:
            # Group filtered alerts by severity in priority order
            grouped_alerts = {}
            for sev in [alert_engine.SEVERITY_CRITICAL, alert_engine.SEVERITY_HIGH, alert_engine.SEVERITY_MEDIUM, alert_engine.SEVERITY_INFO]:
                matching = [a for a in filtered_alerts if a.severity == sev]
                if matching:
                    grouped_alerts[sev] = matching

            severity_descriptions = {
                alert_engine.SEVERITY_CRITICAL: "Confirmed removed in target Flask version — code will fail immediately on import or invocation.",
                alert_engine.SEVERITY_HIGH: "Confirmed removal milestone known, but target version is unspecified or unestablished.",
                alert_engine.SEVERITY_MEDIUM: "Deprecated in target Flask version; removal scheduled in a subsequent release.",
                alert_engine.SEVERITY_INFO: "API lifecycle milestone information available, but no direct breaking conclusion is established.",
            }

            for sev_title, sev_alerts in grouped_alerts.items():
                sev_badge_cls = severity_badge_class(sev_title)
                st.markdown(clean_html(f"""
                <div style="display: flex; align-items: baseline; gap: 0.8rem; margin: 1.5rem 0 0.8rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem;">
                    <span class="{sev_badge_cls}" style="font-size: 0.82rem;">{sev_title} ({len(sev_alerts)})</span>
                    <span style="font-size: 0.85rem; color: var(--text-muted);">{severity_descriptions.get(sev_title, '')}</span>
                </div>
                """), unsafe_allow_html=True)

                for alert in sev_alerts:
                    line_str = f"Line {alert.line_number}" if alert.line_number is not None else "Line unavailable"
                    source_badge = '<span class="source-badge source-neo4j" style="font-size:0.72rem;">' + html.escape(alert.source) + '</span>'
                    status_badge = f'<span class="{alert_status_badge_class(alert.status)}" style="font-size:0.72rem;">{alert.status}</span>'
                    confidence_badge = f'<span class="pill-status pill-status-active" style="font-size:0.7rem;">{alert.confidence}</span>' if "high" in alert.confidence.lower() else f'<span class="pill-status pill-status-deprecated" style="font-size:0.7rem;">{alert.confidence}</span>'

                    ev_html = ""
                    if alert.evidence_url:
                        ev_html = f'''<a href="{alert.evidence_url}" target="_blank" class="evidence-pill-btn">{github_svg}<span>Verified Evidence</span>{ext_arrow_svg}</a>'''
                    else:
                        ev_html = '<span style="font-size:0.8rem; color:var(--text-muted); font-style:italic;">Evidence reference unavailable</span>'

                    rec_html = ""
                    if alert.recommended_action:
                        rec_html = f'''
                        <div class="alert-rec-box">
                            <strong>Recommended Action:</strong> {html.escape(alert.recommended_action)}
                        </div>
                        '''
                    else:
                        rec_html = '<div style="font-size:0.82rem; color:var(--text-muted); margin: 0.5rem 0;">No verified recommendation recorded for this symbol.</div>'

                    # Alert Box
                    st.markdown(clean_html(f"""
                    <div class="alert-card">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:0.6rem; margin-bottom:0.6rem;">
                            <div>
                                <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap; margin-bottom:0.3rem;">
                                    <span class="{severity_badge_class(alert.severity)}">{alert.severity}</span>
                                    <span style="font-weight:700; font-size:1.05rem; color:var(--text-primary);">{html.escape(alert.symbol)}</span>
                                    {status_badge}
                                    <code style="font-size:0.75rem; color:var(--text-muted);">{alert.alert_id}</code>
                                </div>
                                <div style="font-size:0.85rem; color:var(--text-muted);">
                                    <code>{html.escape(alert.file_path)}</code> — <strong>{line_str}</strong> | {source_badge} | {confidence_badge}
                                </div>
                            </div>
                            <div style="display:flex; align-items:center; gap:0.5rem;">
                                <a href="?page=explore&decision={alert.symbol}" target="_self" class="decision-badge">
                                    <span>Explorer</span>
                                    {ext_arrow_svg}
                                </a>
                            </div>
                        </div>

                        <div style="font-size:0.88rem; color:#E2E8F0; margin:0.5rem 0 0.7rem; line-height:1.55;">
                            {html.escape(alert.description)}
                        </div>

                        {rec_html}

                        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.8rem; margin-top:0.8rem; padding-top:0.6rem; border-top:1px solid rgba(255,255,255,0.06);">
                            <div style="font-size:0.82rem; color:var(--text-muted);">
                                Deprecated: <code>{alert.dep_version or 'N/A'}</code> | Removed: <code>{alert.rem_version or 'N/A'}</code>
                            </div>
                            <div>
                                {ev_html}
                            </div>
                        </div>
                    </div>
                    """), unsafe_allow_html=True)

                    # Lifecycle Change Events (HAS_EVENT) for this Alert symbol
                    render_lifecycle_events_component(alert.symbol, title=f"Lifecycle Change Events: {alert.symbol}")

                    # Quick 1-Click Event Handling Actions
                    col_ev1, col_ev2, col_ev3 = st.columns(3)
                    with col_ev1:
                        if st.button("✓ Mark Resolved", key=f"quick_res_{alert.alert_id}", use_container_width=True):
                            st.session_state["alert_statuses"][alert.alert_id] = "Resolved"
                            log_workflow_event("STATUS_RESOLVED", alert.symbol, f"Alert {alert.alert_id} marked as Resolved", source="Alert Actions", new_status="Resolved")
                            st.rerun()
                    with col_ev2:
                        if st.button("🔍 Flag Review", key=f"quick_rev_{alert.alert_id}", use_container_width=True):
                            st.session_state["alert_statuses"][alert.alert_id] = "Needs Review"
                            log_workflow_event("STATUS_NEEDS_REVIEW", alert.symbol, f"Alert {alert.alert_id} marked for review", source="Alert Actions", new_status="Needs Review")
                            st.rerun()
                    with col_ev3:
                        if st.button("⚡ Reset to New", key=f"quick_rst_{alert.alert_id}", use_container_width=True):
                            st.session_state["alert_statuses"][alert.alert_id] = "New"
                            log_workflow_event("STATUS_RESET", alert.symbol, f"Alert {alert.alert_id} reset to New", source="Alert Actions", new_status="New")
                            st.rerun()

                    # Workflow Status Management Expander
                    with st.expander(f"Manage Alert Workflow: {alert.alert_id} ({alert.status})", expanded=False):
                        w_col1, w_col2 = st.columns([1.5, 2])
                        with w_col1:
                            new_status = st.selectbox(
                                "Update Workflow Status",
                                options=["New", "Needs Review", "Resolved"],
                                index=["New", "Needs Review", "Resolved"].index(alert.status) if alert.status in ["New", "Needs Review", "Resolved"] else 0,
                                key=f"status_sel_{alert.alert_id}"
                            )
                            if new_status != alert.status:
                                st.session_state["alert_statuses"][alert.alert_id] = new_status
                                log_workflow_event(f"STATUS_{new_status.upper().replace(' ', '_')}", alert.symbol, f"Status updated to {new_status} via workflow dropdown", source="Alert Workflow", new_status=new_status)
                                st.rerun()
                        with w_col2:
                            st.caption(f"**Alert ID:** `{alert.alert_id}`")
                            st.caption(f"**API Symbol:** `{alert.symbol}`")
                            st.caption(f"**Detection Source:** {alert.source}")
                            st.caption("Status updates are preserved during your active browser session.")

                    with st.expander(f"View Verified Migration Guidance: {alert.symbol}", expanded=False):
                        render_migration_guidance_component(alert.symbol, target_version=eval_target_v)

            st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
            render_event_audit_log_component()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 6: TECHNICAL APPROACH / ABOUT
# ══════════════════════════════════════════════════════════════════════════════

elif is_about:

    # Spacing below navbar before content begins
    st.markdown('<div style="height: 1.8rem;"></div>', unsafe_allow_html=True)

    # Header Row
    st.markdown(clean_html("""
    <div class="section-header-row">
        <div class="section-title-wrap">
            <div class="title-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                    <polyline points="2 17 12 22 22 17"></polyline>
                    <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
            </div>
            <div>
                <h1 class="section-heading">Technical Approach</h1>
                <p class="section-subtext">From raw GitHub maintenance events to verifiable, graph-backed decision intelligence.</p>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    col_meth, col_right = st.columns([1, 1.8], gap="large")

    with col_meth:
        st.markdown(clean_html("""
        <div class="methodology-card">
            <div style="display:flex; align-items:center; gap:0.6rem; font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:1.4rem;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
                <span>System Pipeline</span>
            </div>

            <!-- Step 01 -->
            <div class="method-step-row">
                <span class="step-num-pill">01</span>
                <div class="step-content">
                    <div class="step-heading">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>
                        </svg>
                        <span>Data Curation</span>
                    </div>
                    <p class="step-desc">Extract deprecation and removal records from official Pallets repository issues and pull requests.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 02 -->
            <div class="method-step-row">
                <span class="step-num-pill">02</span>
                <div class="step-content">
                    <div class="step-heading">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                        </svg>
                        <span>Knowledge Modeling</span>
                    </div>
                    <p class="step-desc">Structure decisions, change events, versions, and evidence into an interconnected graph schema.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 03 -->
            <div class="method-step-row">
                <span class="step-num-pill">03</span>
                <div class="step-content">
                    <div class="step-heading">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
                        </svg>
                        <span>AST Static Inspection</span>
                    </div>
                    <p class="step-desc">Parse user Python source code into abstract syntax trees to locate deprecated calls without executing code.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 04 -->
            <div class="method-step-row">
                <span class="step-num-pill">04</span>
                <div class="step-content">
                    <div class="step-heading">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>
                        </svg>
                        <span>PR Diff Ingestion</span>
                    </div>
                    <p class="step-desc">Fetch and parse unified git diffs from public GitHub PRs, isolating newly introduced changes from context.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 05 -->
            <div class="method-step-row">
                <span class="step-num-pill">05</span>
                <div class="step-content">
                    <div class="step-heading">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                        </svg>
                        <span>Prioritized Alerts UI</span>
                    </div>
                    <p class="step-desc">Classify findings into transparent severity tiers (Critical, High, Medium, Info) and provide verified migration guidance.</p>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    with col_right:
        # End-to-End Workflow Card (Clean SVG icons, SaaS style)
        st.markdown(clean_html("""
        <div class="detail-panel" style="padding: 1.6rem 1.8rem; margin-bottom: 1.4rem;">
            <div style="display:flex; align-items:center; gap:0.6rem; font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:1.2rem;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
                </svg>
                <span>End-to-End Pipeline</span>
            </div>
            
            <div class="workflow-row">
                <div class="wf-node">
                    <div class="wf-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="18" cy="18" r="3"/><circle cx="6" cy="6" r="3"/><path d="M13 6h3a2 2 0 0 1 2 2v7"/><line x1="6" y1="9" x2="6" y2="21"/>
                        </svg>
                    </div>
                    <div class="wf-label">Source</div>
                    <div class="wf-sub">Pallets GitHub</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>
                        </svg>
                    </div>
                    <div class="wf-label">Curate</div>
                    <div class="wf-sub">Verify Citations</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                        </svg>
                    </div>
                    <div class="wf-label">Model</div>
                    <div class="wf-sub">Graph Schema</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                        </svg>
                    </div>
                    <div class="wf-label">Store</div>
                    <div class="wf-sub">Neo4j AuraDB</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                        </svg>
                    </div>
                    <div class="wf-label">Query</div>
                    <div class="wf-sub">Cypher Engine</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
                        </svg>
                    </div>
                    <div class="wf-label">Explain</div>
                    <div class="wf-sub">Streamlit UI</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

        # Knowledge Graph Design Card (Two-colour theme only, no emojis)
        st.markdown(clean_html("""
        <div class="detail-panel" style="padding: 1.6rem 1.8rem;">
            <div style="display:flex; align-items:center; gap:0.6rem; font-size:1.05rem; font-weight:700; color:var(--text-primary); margin-bottom:1.2rem;">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
                </svg>
                <span>Knowledge Graph Schema</span>
            </div>

            <div class="schema-grid">
                <!-- Left: Legend -->
                <div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Decision</span>
                            <div class="legend-example">app.before_first_request</div>
                        </div>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Change Event</span>
                            <div class="legend-example">Removed · Flask 2.3.0</div>
                        </div>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Evidence</span>
                            <div class="legend-example">Pallets Issue #4605, PR #4995</div>
                        </div>
                    </div>
                </div>

                <!-- Right: SVG Visual Diagram in Restrained Two-Colour SaaS Theme -->
                <div class="graph-canvas">
                    <svg viewBox="0 0 380 230" style="width:100%; height:auto; overflow:visible;">
                        <defs>
                            <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 8 5 L 0 9 z" fill="#64748B"/>
                            </marker>
                        </defs>

                        <!-- Lines -->
                        <!-- Decision to ChangeEvent (top) -->
                        <line x1="180" y1="95" x2="210" y2="48" stroke="#475569" stroke-width="1.6" marker-end="url(#arrow)"/>
                        <text x="215" y="74" font-size="8.5" fill="#94A3B8" font-family="'JetBrains Mono', monospace">HAS_EVENT</text>

                        <!-- Decision to Evidence (bottom) -->
                        <line x1="180" y1="135" x2="180" y2="180" stroke="#475569" stroke-width="1.6" marker-end="url(#arrow)"/>
                        <text x="215" y="160" font-size="8.5" fill="#94A3B8" text-anchor="middle" font-family="'JetBrains Mono', monospace">SUPPORTED_BY</text>

                        <!-- Top Node: ChangeEvent -->
                        <g transform="translate(170, 20)">
                            <rect x="0" y="0" width="125" height="28" rx="6" fill="#161922" stroke="#A78BFA" stroke-width="1.2"/>
                            <text x="62" y="18" font-size="11" font-weight="600" fill="#F8FAFC" text-anchor="middle" font-family="Inter, sans-serif">ChangeEvent</text>
                        </g>

                        <!-- Center Node: Decision -->
                        <g transform="translate(138, 99)">
                            <rect x="0" y="0" width="90" height="32" rx="6" fill="#A78BFA" stroke="#C4B5FD" stroke-width="1.2"/>
                            <text x="45" y="20" font-size="11.5" font-weight="700" fill="#111318" text-anchor="middle" font-family="Inter, sans-serif">Decision</text>
                        </g>

                        <!-- Bottom Node: Evidence -->
                        <g transform="translate(133, 185)">
                            <rect x="0" y="0" width="100" height="28" rx="6" fill="#161922" stroke="#A78BFA" stroke-width="1.2"/>
                            <text x="50" y="18" font-size="11" font-weight="600" fill="#F8FAFC" text-anchor="middle" font-family="Inter, sans-serif">Evidence</text>
                        </g>
                    </svg>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    # ═══ About extras (stacked, glass) ═══
    _n_dec = len(CURATED_DATA)
    st.markdown(clean_html(f"""
    <div class="home-section" style="margin-top:4.5rem;">
        <div class="sec-head"><span class="sec-pill">OUR STORY</span><h2 class="sec-title">Why this platform exists</h2></div>
        <div class="glass-box"><h4>The problem we picked</h4><p>When an API is deprecated or removed, the error only tells you what broke. The reasoning is spread across changelogs, GitHub Issues, pull requests and code diffs, so developers rebuild the story by hand every time.</p></div>
        <div class="glass-box"><h4>What we built</h4><p>An end-to-end developer intelligence platform: an Architectural Decision Explorer backed by Neo4j AuraDB, a Static AST Code Scanner, a GitHub PR Diff Analyzer, and a Rule-Based Prioritized Alert Engine. It connects breaking changes directly to primary GitHub evidence, explains why decisions were made, and provides actionable migration guidance with explicit refusal guarantees.</p></div>
        <div class="glass-box"><h4>Where the data comes from</h4><p>Only primary sources: official GitHub Issues and pull requests of the Flask repository, plus official release changelogs. Decisions include verified maintainer quotes and version milestone events.</p></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">PRINCIPLES</span><h2 class="sec-title">How we keep it honest</h2></div>
        <div class="glass-box"><span class="step-tag">PRINCIPLE 01</span><h4>No evidence, no answer</h4><p>If a record is missing or guidance is unavailable, the platform provides explicit refusal messages instead of inventing answers.</p></div>
        <div class="glass-box"><span class="step-tag">PRINCIPLE 02</span><h4>Every answer shows its source</h4><p>Each result is labelled Source: Neo4j AuraDB or Source: Local fallback, so you always know where it came from.</p></div>
        <div class="glass-box"><span class="step-tag">PRINCIPLE 03</span><h4>Zero-execution safety guarantee</h4><p>The code scanner statically parses AST without ever running, executing, or importing user code.</p></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">THE STACK</span><h2 class="sec-title">What it runs on</h2></div>
        <div class="glass-box"><h4>Python and Streamlit</h4><p>The high-contrast developer interface, AST parsing visitor, diff engine, and alert prioritization pipeline.</p></div>
        <div class="glass-box"><h4>Neo4j AuraDB</h4><p>A cloud graph database that stores decisions, change events and evidence as connected nodes, powering multi-hop queries.</p></div>
        <div class="glass-box"><h4>GitHub REST API</h4><p>Used to fetch public PR patches and diff metadata without requiring credentials.</p></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">WHAT'S NEXT</span><h2 class="sec-title">Where this goes from here</h2></div>
        <div class="glass-box"><span class="step-tag">PHASE 1 · SHIPPED</span><h4>Full Developer Suite</h4><p>4 core modules deployed: Decision Explorer, Static AST Code Scanner, GitHub PR Diff Analyzer, and Rule-Based Prioritized Alerts.</p></div>
        <div class="glass-box"><span class="step-tag">PHASE 2 · IN PROGRESS</span><h4>Automated CI/CD Integration</h4><p>GitHub Actions and pre-commit hooks to automatically flag deprecated APIs in pull requests.</p></div>
        <div class="glass-box"><span class="step-tag">PHASE 3 · FUTURE</span><h4>Multi-Framework Scaling</h4><p>Expanding the knowledge graph and AST visitors to Django, FastAPI, SQLAlchemy, and editor inline diagnostics.</p></div>
    </div>
    """), unsafe_allow_html=True)

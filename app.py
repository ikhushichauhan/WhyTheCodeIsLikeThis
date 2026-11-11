import os
import base64
import textwrap
import requests
from PIL import Image
import streamlit as st
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

# ── Paths & Config ───────────────────────────────────────────────────────────

BASE_DIR = os.path.dirname(__file__)
LOGO_PATH = os.path.join(BASE_DIR, "assets", "logo.png")
FAVICON_PATH = LOGO_PATH if os.path.exists(LOGO_PATH) else os.path.join(BASE_DIR, "assets", "favicon.png")
BG_PATH = os.path.join(BASE_DIR, "assets", "image.png")

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

bg_b64 = get_asset_b64(BG_PATH)
favicon_b64 = get_asset_b64(FAVICON_PATH)
logo_b64 = get_asset_b64(LOGO_PATH)

# Guarantee Favicon and Page Title in browser tab via JS
if favicon_b64:
    st.markdown(f"""
    <script>
        document.title = "Rationale";
        function setFavicon() {{
            try {{
                let link = document.querySelector("link[rel*='icon']") || document.createElement('link');
                link.type = 'image/png';
                link.rel = 'shortcut icon';
                link.href = 'data:image/png;base64,{favicon_b64}';
                document.getElementsByTagName('head')[0].appendChild(link);
                
                if (window.parent && window.parent.document) {{
                    window.parent.document.title = "Rationale";
                    let pLink = window.parent.document.querySelector("link[rel*='icon']") || window.parent.document.createElement('link');
                    pLink.type = 'image/png';
                    pLink.rel = 'shortcut icon';
                    pLink.href = 'data:image/png;base64,{favicon_b64}';
                    window.parent.document.getElementsByTagName('head')[0].appendChild(pLink);
                }}
            }} catch(e) {{}}
        }}
        setFavicon();
        setTimeout(setFavicon, 500);
    </script>
    """, unsafe_allow_html=True)

# ── Neo4j Config ─────────────────────────────────────────────────────────────

URL = os.getenv("NEO4J_HTTP_URL")
USER = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATABASE = os.getenv("NEO4J_DATABASE")
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

    dep_v = "v2.2.0"
    rem_v = "v2.3.0"
    for ev in events:
        v_str = str(ev.get("version", ""))
        v_fmt = v_str if v_str.startswith("v") else f"v{v_str}"
        if ev.get("type") == "deprecated":
            dep_v = v_fmt
        elif ev.get("type") == "removed":
            rem_v = v_fmt

    quote = None
    for it in evidence:
        if it.get("quote"):
            quote = it["quote"]
            break
    if not quote:
        if entity in CURATED_DATA:
            quote = CURATED_DATA[entity]["rationale"]
        else:
            quote = "Verified decision recorded from official Flask maintenance history."

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
        "rationale": quote,
        "evidence": ev_list,
        "events": events,
        "source": "Neo4j"
    }, None

def find_decision(question):
    """Retrieval flow:
    1. Guard against empty/too short/generic queries.
    2. Query Neo4j first for matching decision.
    3. If Neo4j is unavailable or no record exists, fallback to CURATED_DATA.
    4. Return None for unknown queries.
    """
    if not question:
        return None
    q_clean = question.strip().lower()
    if len(q_clean) < 3 or q_clean in GENERIC_TERMS:
        return None

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
            result["source"] = "Local fallback"
            if neo_error:
                result["db_note"] = neo_error
            return result

    return None

def render_migration_and_timeline(decision_data):
    """Renders migration guidance (Before vs After) and historical timeline using clean Streamlit components."""
    entity = decision_data.get("entity", "")
    mig = MIGRATION_DATA.get(entity)
    if mig:
        st.markdown(clean_html("""
        <div class="migration-header-wrap">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8B6FD6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M16 3h5v5"></path>
                <path d="M4 20L21 3"></path>
                <path d="M21 16v5h-5"></path>
                <path d="M15 15l6 6"></path>
                <path d="M4 4l5 5"></path>
            </svg>
            <span class="detail-section-title" style="margin:0;">Migration Guidance</span>
            <span class="illustrative-pill">Illustrative example</span>
        </div>
        """), unsafe_allow_html=True)

        st.markdown(clean_html(f"""
        <div class="rationale-quote-box" style="margin-bottom: 0.8rem;">
            <div style="font-size: 0.82rem; color: #C4B5FD; font-weight: 600; margin-bottom: 0.35rem; text-transform: uppercase; letter-spacing: 0.05em;">Official Guidance</div>
            <div>{mig['official_guidance']}</div>
            <div style="margin-top: 0.5rem; color: var(--text-secondary); font-size: 0.88rem; line-height: 1.6;">{mig['explanation']}</div>
        </div>
        """), unsafe_allow_html=True)

        if mig.get("compatibility"):
            st.caption(f"**Compatibility Note:** {mig['compatibility']}")

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        col_b, col_a = st.columns(2)
        with col_b:
            st.markdown("**Before** *(Illustrative example)*")
            st.code(mig["before_code"], language="python")
        with col_a:
            st.markdown("**After** *(Illustrative example)*")
            st.code(mig["after_code"], language="python")

    events = decision_data.get("events", [])
    if events:
        st.markdown(clean_html("""
        <div class="detail-section-title" style="margin-top: 1.8rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8B6FD6" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
            </svg>
            Historical Timeline
        </div>
        """), unsafe_allow_html=True)

        sorted_events = sorted(events, key=lambda ev: (0 if ev.get("type") == "deprecated" else 1))
        t_cols = st.columns(len(sorted_events))
        for idx, ev in enumerate(sorted_events):
            with t_cols[idx]:
                ev_type = str(ev.get("type", "")).capitalize()
                ev_ver = ev.get("version", "")
                ev_ref = ev.get("ref", "")
                ev_date = ev.get("merged_at", "")
                date_str = f"Merged: {ev_date[:10]}" if ev_date else "Recorded in Flask issue history"
                ref_meta = VERIFIED_REF_METADATA.get(ev_ref, {})
                ref_label = ref_meta.get("label", f"Ref #{ev_ref}")
                ref_url = ref_meta.get("url", "")

                st.markdown(f"**• {ev_type}**")
                st.markdown(f"Version: `Flask {ev_ver}`")
                if ref_url:
                    st.markdown(f"[{ref_label} ↗]({ref_url})")
                else:
                    st.markdown(f"`{ref_label}`")
                st.caption(date_str)

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
    --surface: rgba(255, 255, 255, 0.02);
    --surface-solid: #121218;
    --surface-hover: rgba(255, 255, 255, 0.04);
    --border: rgba(255, 255, 255, 0.08);
    --border-hover: rgba(143, 120, 217, 0.4);
    --accent: #8F78D9;
    --accent-hover: #D4C9F7;
    --accent-muted: rgba(143, 120, 217, 0.12);
    --accent-border: rgba(143, 120, 217, 0.3);
    --text-primary: #F4F2FA;
    --text-secondary: #A09EB5;
    --text-muted: #6C6A80;
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
    gap: 0.75rem;
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
    text-decoration: none !important;
    transition: all 0.15s ease;
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
    padding: 0 26px !important;
    background: #FFFFFF !important;
    color: #0A0A0F !important;
    border: 1px solid #FFFFFF !important;
    border-radius: 9999px !important;
    font-size: 16px !important;
    font-weight: 500 !important;
    letter-spacing: -0.02em;
    text-decoration: none !important;
    box-shadow: none !important;
    transition: all 0.15s ease;
}

.nav-signup-btn:visited {
    color: #0A0A0F !important;
}

.nav-signup-btn:hover {
    background: #F4F2FA !important;
    color: #0A0A0F !important;
    transform: translateY(-1px);
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

/* Headings on all pages (Same font style as Hero: Plus Jakarta Sans, 300 weight, white-to-lavender gradient) */
.section-heading, .feature-title, h1, h2 {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    font-weight: 300 !important;
    letter-spacing: -0.04em !important;
    background: linear-gradient(180deg, #FFFFFF 0%, #FFFFFF 50%, #D4C9F7 100%) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
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

/* Newer Streamlit versions put the input inside stTextInputRootElement (no data-baseweb), so style it the same way */
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

/* Matching Search Button (Exact same 52px height as search bar) */
button[kind="primaryFormSubmit"], button[kind="primary"] {
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

button[kind="primaryFormSubmit"] *,
button[kind="primary"] * {
    color: #FFFFFF !important;
    font-weight: 600 !important;
    white-space: nowrap !important;
}

button[kind="primaryFormSubmit"]:hover, button[kind="primary"]:hover {
    background: #1C1A27 !important;
    border-color: #8F78D9 !important;
    color: #FFFFFF !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.45) !important;
}

button[kind="secondary"] {
    border-radius: 9999px !important;
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    color: #F4F2FA !important;
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

.pill-status-removed {
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.75rem;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 9999px;
    color: var(--accent);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
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

/* ── Responsive adjustments ──────────────────────────────────────────────── */
@media (max-width: 960px) {
    .main .block-container, [data-testid="stAppViewContainer"] .block-container, .block-container {
        padding-left: 4% !important;
        padding-right: 4% !important;
    }
    .feature-grid {
        grid-template-columns: 1fr;
    }
    .hero-title {
        font-size: 2.6rem !important;
    }
    .stats-grid {
        grid-template-columns: 1fr;
    }
    .schema-grid {
        grid-template-columns: 1fr;
    }
    .top-navbar {
        grid-template-columns: 1fr !important;
        gap: 0.8rem;
        text-align: center;
        height: auto !important;
        padding: 12px 16px !important;
        margin: 0 -4.3478% 6px -4.3478% !important;
    }
    .hero-container {
        padding-top: 64px !important;
    }
    .brand-container {
        justify-self: center;
    }
    .nav-right-actions {
        justify-self: center !important;
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
is_about = (cur_page == "about")

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
        <a href="?page=about" target="_self" class="nav-link {'active' if is_about else ''}">About</a>
    </div>
    {right_header_elem}
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
        border-radius: 40px !important;
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
            width: 108.6957% !important;
            margin-left: -4.3478% !important;
        }
        .st-key-hero_panel {
            padding-bottom: 64px !important;
            border-radius: 28px !important;
        }
    }
    </style>
    """), unsafe_allow_html=True)

    with st.container(key="hero_panel"):
        # Hero Content (Sitting inside black / dark purple zone)
        st.markdown(clean_html("""
        <div class="hero-container" style="padding-bottom: 1.2rem;">
            <div class="hero-nodes-row">
                <!-- 1. Code Investigation (double size, white logo, white boundary, black inside, no glow) -->
                <div class="hero-glass-node hero-node-small hero-node-left" title="Code Investigation">
                    <svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="7"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                        <polyline points="9.5 9 7.5 11 9.5 13"></polyline>
                        <polyline points="12.5 9 14.5 11 12.5 13"></polyline>
                    </svg>
                </div>
                <div class="hero-connector-line hero-line-left"></div>
                <!-- 2. Decision History (center, prominent, double size, white logo, white boundary, black inside) -->
                <div class="hero-glass-node hero-node-center" title="Decision History">
                    <svg width="27" height="27" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="7" cy="17" r="2.5"></circle>
                        <circle cx="17" cy="9" r="2.5"></circle>
                        <line x1="7" y1="5" x2="7" y2="14.5"></line>
                        <path d="M7 17c3.5 0 6.5-1 7.5-5"></path>
                    </svg>
                </div>
                <div class="hero-connector-line hero-line-right"></div>
                <!-- 3. Verified Evidence (no glow, same style as others) -->
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

    # Check chip query param
    if "q" in query_params:
        st.session_state.search_query = query_params["q"]

    # Show Search Results if Search is active
    if st.session_state.search_query:
        matched = find_decision(st.session_state.search_query)
        if matched:
            src_type = matched.get("source", "Local fallback")
            src_cls = "source-neo4j" if src_type == "Neo4j" else "source-fallback"
            src_icon_svg = db_icon_svg if src_type == "Neo4j" else pkg_icon_svg
            src_badge_html = f'<span class="source-badge {src_cls}">{src_icon_svg}<span>Source: {src_type}</span></span>'
            db_note_html = f'<div style="font-size:0.8rem; color:#A78BFA; background:rgba(167,139,250,0.08); border:1px solid rgba(167,139,250,0.25); border-radius:8px; padding:0.5rem 0.9rem; margin-bottom:1.2rem;">Notice: {matched["db_note"]}</div>' if matched.get("db_note") else ""

            ev_buttons = ""
            for ev in matched["evidence"]:
                ev_buttons += f"""
                <a href="{ev['url']}" target="_blank" class="evidence-pill-btn">
                    {github_svg}
                    <span>{ev['label']}</span>
                    {ext_arrow_svg}
                </a>
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
                            <span class="pill-status-removed">{matched.get('status', 'removed')}</span>
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
                    <div class="rationale-quote-box">
                        {matched['rationale']}
                    </div>
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
                with st.expander("View Migration Guidance & Historical Timeline", expanded=True):
                    render_migration_and_timeline(matched)
        else:
            st.markdown(clean_html("""
            <div style="text-align: center; margin: 2rem auto 3rem; padding: 2.2rem 1.8rem; background: var(--surface); border: 1px solid var(--border); border-radius: 16px;">
                <div style="display:inline-flex; align-items:center; justify-content:center; width:48px; height:48px; background:var(--accent-muted); border:1px solid var(--accent-border); border-radius:12px; color:var(--accent); margin-bottom:0.75rem;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                </div>
                <div style="font-size: 1.15rem; font-weight: 600; color: var(--text-primary);">No verified evidence found.</div>
                <div style="font-size: 0.88rem; color: var(--text-muted); margin-top: 0.35rem;">
                    This system refuses to generate unverified explanations. Try searching for <code>before_first_request</code>, <code>got_first_request</code>, or <code>test_client.as_tuple</code>.
                </div>
            </div>
            """), unsafe_allow_html=True)

    # 3 Feature Cards (Clean SVG icons, SaaS style)
    st.markdown(clean_html("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="11" cy="11" r="7"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    <polyline points="9.5 9 7.5 11 9.5 13"></polyline>
                    <polyline points="12.5 9 14.5 11 12.5 13"></polyline>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Code Investigation</h3>
                <p class="feature-desc">Find the original reason behind deprecated code.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="7" cy="17" r="2.5"></circle>
                    <circle cx="17" cy="9" r="2.5"></circle>
                    <line x1="7" y1="5" x2="7" y2="14.5"></line>
                    <path d="M7 17c3.5 0 6.5-1 7.5-5"></path>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Decision History</h3>
                <p class="feature-desc">Connect GitHub Issues, PRs and version changes.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
                    <polyline points="9 12 11 14 15 10"></polyline>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Verified Evidence</h3>
                <p class="feature-desc">Show source-backed explanations, not invented answers.</p>
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
        <div class="sec-head"><span class="sec-pill">HOW IT WORKS</span><h2 class="sec-title">Three steps. Every answer traceable.</h2></div>
        <div class="glass-box"><span class="step-tag">STEP 01</span><h4>Search an API</h4><p>Type a method or symbol, like <span class="mono-chip">{_ex_ent}</span>. Aliases are recognised.</p></div>
        <div class="flow-link"></div>
        <div class="glass-box"><span class="step-tag">STEP 02</span><h4>See the evidence chain</h4><p>Deprecated version, removal version, the maintainers' reasoning, and links to the original Issue and PR.</p></div>
        <div class="flow-link"></div>
        <div class="glass-box"><span class="step-tag">STEP 03</span><h4>Migrate with context</h4><p>Sourced migration guidance, with clearly labelled illustrative Before / After code.</p></div>
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
        <div class="note-muted">Current prototype: {_n_dec} curated Flask decisions. The discovery pipeline below shows how it scales.</div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">ROADMAP</span><h2 class="sec-title">From {_n_dec} decisions to any repository.</h2></div>
        <div class="glass-box road-step"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a10 10 0 0 0-3.16 19.5c.5.1.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.45-1.15-1.1-1.46-1.1-1.46-.9-.62.07-.6.07-.6 1 .07 1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.9.83.09-.65.35-1.09.63-1.34-2.22-.25-4.55-1.11-4.55-4.94 0-1.09.39-1.98 1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02a9.5 9.5 0 0 1 5 0c1.9-1.29 2.74-1.02 2.74-1.02.55 1.37.2 2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.69-4.57 4.94.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0 0 12 2z"/></svg></div><span class="road-tag">STEP 01</span><h4>GitHub API</h4></div>
<div class="flow-link"></div>
<div class="glass-box road-step"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg></div><span class="road-tag">STEP 02</span><h4>Filter deprecations</h4></div>
<div class="flow-link"></div>
<div class="glass-box road-step"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="12" r="3"/><circle cx="18" cy="12" r="3"/><line x1="9" y1="12" x2="15" y2="12"/></svg></div><span class="road-tag">STEP 03</span><h4>Link Issue to PR</h4></div>
<div class="flow-link"></div>
<div class="glass-box road-step"><div class="glass-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg></div><span class="road-tag">STEP 04</span><h4>Verify and load to Neo4j</h4></div>
        <div class="note-muted">Planned. Not part of the current prototype.</div>
    </div>

    <div class="home-section" style="margin-bottom:0;">
        <div class="sec-head"><span class="sec-pill">FAQ</span><h2 class="sec-title">Questions, answered.</h2></div>
    </div>
    """), unsafe_allow_html=True)

    with st.container(key="faq_block"):
        with st.expander("Does it use AI to write the reasons?"):
            st.write("No. Every explanation comes from original GitHub records. An LLM could later help summarise long discussions, but only with citations back to the source.")
        with st.expander("Which libraries are covered?"):
            st.write(f"The prototype covers {_n_dec} Flask decisions. The architecture is built to add more repositories.")
        with st.expander("Where does the data come from?"):
            st.write("Public GitHub Issues and pull requests, plus official changelogs.")
        with st.expander("What if my API is not in the database?"):
            st.write('You will see "No verified evidence found." We never invent an answer.')
        with st.expander("Why Neo4j?"):
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
                    <a href="?page=home" target="_self">Home</a><a href="?page=explore" target="_self">Explore Decisions</a><a href="?page=about" target="_self">About</a></div>
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
    st.markdown('<div style="height: 1.8rem;"></div>', unsafe_allow_html=True)

    # Header Row
    st.markdown(clean_html("""
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
            <span>3 Verified Records</span>
        </div>
    </div>
    """), unsafe_allow_html=True)

    # Selected Decision (Neo4j with fallback)
    selected_key = st.session_state.selected_decision
    if selected_key not in CURATED_DATA:
        selected_key = "app.before_first_request"

    # Query Neo4j first for selected decision; fallback to CURATED_DATA only if needed
    retrieved = find_decision(selected_key)
    if retrieved:
        decision_data = retrieved
    else:
        decision_data = dict(CURATED_DATA.get(selected_key, CURATED_DATA["app.before_first_request"]))
        decision_data["source"] = "Local fallback"

    # Split Layout: Left list (32%) / Right details (68%)
    col_list, col_detail = st.columns([1, 2.1], gap="large")

    with col_list:
        cards_html = ""
        for k, v in CURATED_DATA.items():
            is_sel = (k == selected_key)
            active_cls = "active" if is_sel else ""
            cards_html += f"""
            <a href="?page=explore&decision={k}" target="_self" class="decision-card-item {active_cls}">
                <div class="card-code-icon">
                    {code_icon_svg}
                </div>
                <div>
                    <div class="card-title-text">{v['entity']}</div>
                    <div class="card-sub-text">{v['subtitle']}</div>
                </div>
            </a>
            """
        st.markdown(clean_html(cards_html), unsafe_allow_html=True)

    with col_detail:
        ev_buttons = ""
        for ev in decision_data["evidence"]:
            ev_buttons += f"""
            <a href="{ev['url']}" target="_blank" class="evidence-pill-btn">
                {github_svg}
                <span>{ev['label']}</span>
                {ext_arrow_svg}
            </a>
            """

        src_type = decision_data.get("source", "Local fallback")
        src_cls = "source-neo4j" if src_type == "Neo4j" else "source-fallback"
        src_icon_svg = db_icon_svg if src_type == "Neo4j" else pkg_icon_svg
        src_badge_html = f'<span class="source-badge {src_cls}">{src_icon_svg}<span>Source: {src_type}</span></span>'
        db_note_html = f'<div style="font-size:0.8rem; color:#A78BFA; background:rgba(167,139,250,0.08); border:1px solid rgba(167,139,250,0.25); border-radius:8px; padding:0.5rem 0.9rem; margin-bottom:1.2rem;">Notice: {decision_data["db_note"]}</div>' if decision_data.get("db_note") else ""

        st.markdown(clean_html(f"""
        <div class="detail-panel">
            <div class="detail-top-row">
                <div class="detail-entity-wrap">
                    <div class="detail-code-icon">
                        {code_icon_svg}
                    </div>
                    <div>
                        <div class="detail-title">{decision_data['entity']}</div>
                        <div class="detail-category">{decision_data['category']}</div>
                    </div>
                </div>
                <div style="display:flex; align-items:center; gap:0.6rem; flex-wrap:wrap;">
                    <span class="pill-status-removed">{decision_data.get('status', 'removed')}</span>
                    {src_badge_html}
                    <div class="decision-badge">Verified Decision</div>
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
                        <div class="stat-meta-val">{decision_data['dep_version']}</div>
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
                        <div class="stat-meta-val">{decision_data['rem_version']}</div>
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
                        <div><span class="pill-status-removed">Removed</span></div>
                    </div>
                </div>
            </div>

            <div class="detail-section-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                <span>Why was it removed?</span>
            </div>
            <div class="rationale-quote-box">
                {decision_data['rationale']}
            </div>

            <div class="detail-section-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                </svg>
                <span>Primary Evidence</span>
            </div>
            <div class="evidence-btn-group">
                {ev_buttons}
            </div>
        </div>
        """), unsafe_allow_html=True)

        # Render Migration Guidance (Before vs After) and Historical Timeline
        render_migration_and_timeline(decision_data)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: TECHNICAL APPROACH / ABOUT
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
                            <ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
                        </svg>
                        <span>Graph Storage</span>
                    </div>
                    <p class="step-desc">Store and index the entities in Neo4j AuraDB with cypher-searchable properties.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 04 -->
            <div class="method-step-row">
                <span class="step-num-pill">04</span>
                <div class="step-content">
                    <div class="step-heading">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
                        </svg>
                        <span>Query & Retrieval</span>
                    </div>
                    <p class="step-desc">Execute parameterized Cypher queries to retrieve verified citations, change events, and source links.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 05 -->
            <div class="method-step-row">
                <span class="step-num-pill">05</span>
                <div class="step-content">
                    <div class="step-heading">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
                        </svg>
                        <span>Interactive UI</span>
                    </div>
                    <p class="step-desc">Provide a high-contrast SaaS dashboard in Streamlit with migration comparisons and explicit refusal mechanics.</p>
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
                            <span class="legend-name">Method / Function</span>
                            <div class="legend-example">app.before_first_request</div>
                        </div>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Change Event</span>
                            <div class="legend-example">Deprecated, Removed</div>
                        </div>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Version</span>
                            <div class="legend-example">Flask v2.2.0, v2.3.0</div>
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
                        <!-- Method to Decision -->
                        <line x1="85" y1="115" x2="135" y2="115" stroke="#475569" stroke-width="1.6" marker-end="url(#arrow)"/>
                        <text x="110" y="106" font-size="8.5" fill="#94A3B8" text-anchor="middle" font-family="'JetBrains Mono', monospace">OF</text>

                        <!-- Decision to ChangeEvent (top) -->
                        <line x1="180" y1="95" x2="210" y2="48" stroke="#475569" stroke-width="1.6" marker-end="url(#arrow)"/>
                        <text x="215" y="74" font-size="8.5" fill="#94A3B8" font-family="'JetBrains Mono', monospace">HAS_CHANGE</text>

                        <!-- Decision to Version (right) -->
                        <line x1="225" y1="115" x2="275" y2="115" stroke="#475569" stroke-width="1.6" marker-end="url(#arrow)"/>
                        <text x="250" y="106" font-size="8.5" fill="#94A3B8" text-anchor="middle" font-family="'JetBrains Mono', monospace">IN_VERSION</text>

                        <!-- Decision to Evidence (bottom) -->
                        <line x1="180" y1="135" x2="180" y2="180" stroke="#475569" stroke-width="1.6" marker-end="url(#arrow)"/>
                        <text x="215" y="160" font-size="8.5" fill="#94A3B8" text-anchor="middle" font-family="'JetBrains Mono', monospace">SUPPORTED_BY</text>

                        <!-- Top Node: ChangeEvent -->
                        <g transform="translate(170, 20)">
                            <rect x="0" y="0" width="125" height="28" rx="6" fill="#161922" stroke="#A78BFA" stroke-width="1.2"/>
                            <text x="62" y="18" font-size="11" font-weight="600" fill="#F8FAFC" text-anchor="middle" font-family="Inter, sans-serif">ChangeEvent</text>
                        </g>

                        <!-- Left Node: Method -->
                        <g transform="translate(10, 101)">
                            <rect x="0" y="0" width="80" height="28" rx="6" fill="#161922" stroke="#A78BFA" stroke-width="1.2"/>
                            <text x="40" y="18" font-size="11" font-weight="600" fill="#F8FAFC" text-anchor="middle" font-family="Inter, sans-serif">Method</text>
                        </g>

                        <!-- Center Node: Decision -->
                        <g transform="translate(138, 99)">
                            <rect x="0" y="0" width="90" height="32" rx="6" fill="#A78BFA" stroke="#C4B5FD" stroke-width="1.2"/>
                            <text x="45" y="20" font-size="11.5" font-weight="700" fill="#111318" text-anchor="middle" font-family="Inter, sans-serif">Decision</text>
                        </g>

                        <!-- Right Node: Version -->
                        <g transform="translate(280, 101)">
                            <rect x="0" y="0" width="85" height="28" rx="6" fill="#161922" stroke="#A78BFA" stroke-width="1.2"/>
                            <text x="42" y="18" font-size="11" font-weight="600" fill="#F8FAFC" text-anchor="middle" font-family="Inter, sans-serif">Version</text>
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
        <div class="sec-head"><span class="sec-pill">OUR STORY</span><h2 class="sec-title">Why this project exists</h2></div>
        <div class="glass-box"><h4>The problem we picked</h4><p>When an API is deprecated or removed, the error only tells you what broke. The reasoning is spread across changelogs, GitHub Issues, pull requests and code diffs, so developers rebuild the story by hand every time.</p></div>
        <div class="glass-box"><h4>What we built</h4><p>A small explorer that connects a decision, its change events and its evidence in one graph. Search an API, see when it was deprecated and removed, read the maintainers' reasoning, and open the original sources.</p></div>
        <div class="glass-box"><h4>Where the data comes from</h4><p>Only primary sources: public GitHub Issues and pull requests of the Flask repository, plus official changelogs. The prototype currently holds {_n_dec} curated decisions, each with verified quotes.</p></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">PRINCIPLES</span><h2 class="sec-title">How we keep it honest</h2></div>
        <div class="glass-box"><span class="step-tag">PRINCIPLE 01</span><h4>No evidence, no answer</h4><p>If a record is missing, the app says "No verified evidence found." instead of guessing.</p></div>
        <div class="glass-box"><span class="step-tag">PRINCIPLE 02</span><h4>Every answer shows its source</h4><p>Each result is labelled Source: Neo4j or Source: Local fallback, so you always know where it came from.</p></div>
        <div class="glass-box"><span class="step-tag">PRINCIPLE 03</span><h4>Illustrative code is labelled</h4><p>Before / After migration snippets are marked as illustrative. Reasons and versions are never invented.</p></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">THE STACK</span><h2 class="sec-title">What it runs on</h2></div>
        <div class="glass-box"><h4>Python and Streamlit</h4><p>The interface and the lookup logic. Light, fast to deploy, easy for a small team to maintain.</p></div>
        <div class="glass-box"><h4>Neo4j AuraDB</h4><p>A graph database that stores decisions, change events and evidence as connected nodes, so one Cypher query returns the whole story.</p></div>
        <div class="glass-box"><h4>GitHub API</h4><p>Used to collect the original Issues and pull requests that justify each decision.</p></div>
    </div>

    <div class="home-section">
        <div class="sec-head"><span class="sec-pill">WHAT'S NEXT</span><h2 class="sec-title">Where this goes from here</h2></div>
        <div class="glass-box"><span class="step-tag">PHASE 1 · NOW</span><h4>Curated prototype</h4><p>{_n_dec} verified Flask decisions, a Neo4j graph and a Streamlit explorer.</p></div>
        <div class="glass-box"><span class="step-tag">PHASE 2 · NEXT</span><h4>Automated discovery</h4><p>Planned: pull deprecations from GitHub, link each Issue to its PR, verify quotes, then load them into Neo4j.</p></div>
        <div class="glass-box"><span class="step-tag">PHASE 3 · LATER</span><h4>Beyond one repository</h4><p>Planned: more libraries, and hints inside developer tools when a deprecation warning appears. Phases 2 and 3 are plans, not shipped features.</p></div>
    </div>
    """), unsafe_allow_html=True)
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
FAVICON_PATH = os.path.join(BASE_DIR, "assets", "favicon.png")
BG_PATH = os.path.join(BASE_DIR, "assets", "image.png")

# Load Favicon
favicon_img = Image.open(FAVICON_PATH) if os.path.exists(FAVICON_PATH) else None

st.set_page_config(
    page_title="Why The Code Is Like This",
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

# Guarantee Favicon and Page Title in browser tab via JS
if favicon_b64:
    st.markdown(f"""
    <script>
        document.title = "Why The Code Is Like This";
        function setFavicon() {{
            try {{
                let link = document.querySelector("link[rel*='icon']") || document.createElement('link');
                link.type = 'image/png';
                link.rel = 'shortcut icon';
                link.href = 'data:image/png;base64,{favicon_b64}';
                document.getElementsByTagName('head')[0].appendChild(link);
                
                if (window.parent && window.parent.document) {{
                    window.parent.document.title = "Why The Code Is Like This";
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
        <div class="detail-section-title" style="margin-top: 1.8rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M16 3h5v5"></path>
                <path d="M4 20L21 3"></path>
                <path d="M21 16v5h-5"></path>
                <path d="M15 15l6 6"></path>
                <path d="M4 4l5 5"></path>
            </svg>
            Migration Guidance
        </div>
        """), unsafe_allow_html=True)

        st.info(f"**Official Source Recommendation:**\n\n{mig['official_guidance']}")
        st.markdown(f"**Explanation:** {mig['explanation']}")
        st.caption(f"**Compatibility Note:** {mig['compatibility']}")

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
        col_b, col_a = st.columns(2)
        with col_b:
            st.markdown("**Deprecated Pattern** *(Illustrative Example)*")
            st.code(mig["before_code"], language="python")
        with col_a:
            st.markdown("**Recommended Pattern** *(Illustrative Example)*")
            st.code(mig["after_code"], language="python")

    events = decision_data.get("events", [])
    if events:
        st.markdown(clean_html("""
        <div class="detail-section-title" style="margin-top: 1.8rem;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
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

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
    --bg-dark: #111318;
    --surface: rgba(22, 25, 34, 0.75);
    --surface-solid: #161922;
    --surface-hover: rgba(28, 32, 44, 0.85);
    --border: rgba(255, 255, 255, 0.08);
    --border-hover: rgba(167, 139, 250, 0.35);
    --accent: #A78BFA;
    --accent-hover: #C4B5FD;
    --accent-muted: rgba(167, 139, 250, 0.12);
    --accent-border: rgba(167, 139, 250, 0.28);
    --text-primary: #F8FAFC;
    --text-secondary: #94A3B8;
    --text-muted: #64748B;
}}

* {{
    box-sizing: border-box;
}}

html, body, [data-testid="stApp"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-primary);
    background-color: var(--bg-dark);
}}

[data-testid="stApp"] {{
    background-color: var(--bg-dark);
    min-height: 100vh;
    position: relative;
    overflow-x: hidden;
}}

/* Very subtle low-opacity backdrop image */
[data-testid="stApp"]::before {{
    content: "";
    position: fixed;
    inset: 0;
    background: url("data:image/png;base64,{bg_b64}") center center / cover no-repeat fixed;
    opacity: 0.04;
    pointer-events: none;
    z-index: 0;
}}

/* Professional full-width SaaS layout with 6% left/right margins */
.block-container {{
    max-width: 100% !important;
    padding-left: 6% !important;
    padding-right: 6% !important;
    padding-top: 1.25rem !important;
    padding-bottom: 4rem !important;
    position: relative;
    z-index: 1;
}}

#MainMenu, footer, header[data-testid="stHeader"] {{
    display: none !important;
}}

a {{
    text-decoration: none !important;
    color: inherit;
}}

/* ── Top Navigation Bar ───────────────────────────────────────────────────── */
.top-navbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    padding: 0.8rem 1.4rem;
    margin-bottom: 2.2rem;
    background: var(--surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    flex-wrap: wrap;
    gap: 1rem;
}}

.brand-container {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    text-decoration: none !important;
}}

.brand-icon {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 8px;
    color: var(--accent);
}}

.brand-title {{
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -0.01em;
}}

.nav-pill-group {{
    display: flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    padding: 0.25rem 0.35rem;
    border-radius: 9px;
    flex-wrap: wrap;
}}

.nav-link {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 1rem;
    border-radius: 7px;
    font-size: 0.86rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-decoration: none !important;
    transition: all 0.15s ease;
}}

.nav-link:hover {{
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.05);
}}

.nav-link.active {{
    color: var(--text-primary);
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    font-weight: 600;
}}

.github-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.45rem 1rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text-primary);
    font-size: 0.85rem;
    font-weight: 500;
    text-decoration: none !important;
    transition: all 0.15s ease;
}}

.github-btn:hover {{
    background: rgba(255, 255, 255, 0.07);
    border-color: var(--border-hover);
    color: #fff;
}}

.step-indicator {{
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--accent);
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 6px;
    padding: 0.35rem 0.75rem;
}}

/* ── Hero Section (Home) ──────────────────────────────────────────────────── */
.hero-container {{
    text-align: center;
    padding: 2.8rem 1rem 1.8rem;
    max-width: 860px;
    margin: 0 auto;
}}

.hero-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 9999px;
    padding: 0.35rem 1rem;
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--accent);
    margin-bottom: 1.4rem;
}}

.hero-title {{
    font-size: 3.2rem;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -0.03em;
    color: var(--text-primary);
    margin: 0 0 0.8rem;
}}

.hero-title-accent {{
    color: var(--accent);
}}

.hero-subtitle {{
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0 0 0.6rem;
}}

.hero-desc {{
    font-size: 0.98rem;
    color: var(--text-secondary);
    line-height: 1.6;
    max-width: 680px;
    margin: 0 auto 2.2rem;
}}

/* ── Form & Input Styling ─────────────────────────────────────────────────── */
[data-testid="stForm"] {{
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    width: 100%;
    max-width: 760px;
    margin: 0 auto;
}}

[data-testid="stTextInput"] {{
    margin-bottom: 0 !important;
}}

[data-testid="stTextInput"] input {{
    background: var(--surface-solid) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text-primary) !important;
    font-size: 0.95rem !important;
    padding: 0.8rem 1.25rem !important;
    transition: all 0.2s ease !important;
}}

[data-testid="stTextInput"] input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(167, 139, 250, 0.2) !important;
}}

button[kind="primaryFormSubmit"], button[kind="primary"] {{
    background: var(--accent) !important;
    color: #111318 !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 1.5rem !important;
    border: none !important;
    border-radius: 10px !important;
    transition: all 0.2s ease !important;
    cursor: pointer !important;
}}

button[kind="primaryFormSubmit"]:hover, button[kind="primary"]:hover {{
    background: var(--accent-hover) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 14px rgba(167, 139, 250, 0.25) !important;
}}

/* ── Search Chips ─────────────────────────────────────────────────────────── */
.chips-row {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.65rem;
    flex-wrap: wrap;
    margin: 1.4rem auto 3rem;
    font-size: 0.88rem;
    color: var(--text-muted);
}}

.chip-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.4rem 0.95rem;
    font-size: 0.82rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-secondary);
    text-decoration: none !important;
    transition: all 0.15s ease;
}}

.chip-btn:hover {{
    color: var(--text-primary);
    background: var(--accent-muted);
    border-color: var(--accent-border);
    transform: translateY(-1px);
}}

/* ── 3 Feature Cards (Home) ───────────────────────────────────────────────── */
.feature-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.4rem;
    width: 100%;
    margin: 0 auto;
}}

.feature-card {{
    background: var(--surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.6rem 1.5rem;
    display: flex;
    align-items: flex-start;
    gap: 1.1rem;
    transition: all 0.2s ease;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
    min-width: 0;
    overflow: visible;
}}

.feature-card:hover {{
    border-color: var(--border-hover);
    transform: translateY(-2px);
}}

.feature-icon-box {{
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
}}

.feature-title {{
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.35rem;
}}

.feature-desc {{
    font-size: 0.86rem;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
    word-break: break-word;
}}

/* ── Section Header Row ───────────────────────────────────────────────────── */
.section-header-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 2rem;
    flex-wrap: wrap;
    gap: 1rem;
    width: 100%;
}}

.section-title-wrap {{
    display: flex;
    align-items: center;
    gap: 1rem;
}}

.title-icon-box {{
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
}}

.section-heading {{
    font-size: 1.65rem;
    font-weight: 800;
    color: var(--text-primary);
    letter-spacing: -0.02em;
    margin: 0;
}}

.section-subtext {{
    font-size: 0.9rem;
    color: var(--text-secondary);
    margin: 0.25rem 0 0;
}}

.counter-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.45rem 1rem;
    font-size: 0.84rem;
    font-weight: 600;
    color: var(--text-primary);
}}

/* ── Explore Left List ────────────────────────────────────────────────────── */
.decision-card-item {{
    display: flex;
    align-items: center;
    gap: 1rem;
    background: var(--surface);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.15rem 1.3rem;
    margin-bottom: 0.85rem;
    text-decoration: none !important;
    color: var(--text-primary) !important;
    transition: all 0.2s ease;
    cursor: pointer;
    width: 100%;
    min-width: 0;
    overflow: visible;
}}

.decision-card-item:hover {{
    border-color: var(--border-hover);
    background: var(--surface-hover);
    transform: translateY(-1px);
}}

.decision-card-item.active {{
    background: var(--accent-muted);
    border: 1px solid var(--accent);
    box-shadow: 0 0 16px rgba(167, 139, 250, 0.2);
}}

.card-code-icon {{
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
}}

.card-title-text {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 0.2rem;
    word-break: break-word;
}}

.card-sub-text {{
    font-size: 0.82rem;
    color: var(--text-secondary);
}}

/* ── Decision Detail Panel ────────────────────────────────────────────────── */
.detail-panel {{
    background: var(--surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 2rem 2.2rem;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.25);
    width: 100%;
    word-break: break-word;
    overflow: visible;
}}

.detail-top-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.8rem;
    gap: 1rem;
    flex-wrap: wrap;
    overflow: visible;
}}

.detail-entity-wrap {{
    display: flex;
    align-items: center;
    gap: 1.1rem;
    min-width: 0;
    overflow: visible;
}}

.detail-code-icon {{
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
}}

.detail-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.35rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.25rem;
    word-break: break-word;
}}

.detail-category {{
    font-size: 0.88rem;
    color: var(--text-secondary);
    margin: 0;
}}

.source-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.35rem 0.85rem;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    white-space: nowrap;
}}

.source-neo4j {{
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    color: var(--accent);
}}

.source-fallback {{
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    color: var(--text-secondary);
}}

.decision-badge {{
    display: inline-flex;
    align-items: center;
    padding: 0.35rem 0.85rem;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    color: var(--accent);
    letter-spacing: 0.02em;
    white-space: nowrap;
}}

/* ── Stats Grid (Full Visibility, No Cut-Off) ────────────────────────────── */
.stats-grid {{
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.25rem;
    padding: 1.25rem 1.5rem;
    background: rgba(255, 255, 255, 0.02);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin-bottom: 1.8rem;
    overflow: visible;
}}

.stat-item {{
    display: flex;
    align-items: center;
    gap: 0.9rem;
    min-width: 0;
    overflow: visible;
}}

.stat-icon {{
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
}}

.stat-meta-label {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-muted);
    margin-bottom: 0.2rem;
    white-space: nowrap;
}}

.stat-meta-val {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    word-break: break-word;
}}

.pill-status-removed {{
    display: inline-flex;
    align-items: center;
    padding: 0.25rem 0.65rem;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 6px;
    color: var(--accent);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}

.detail-section-title {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.98rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 1.6rem 0 0.85rem;
}}

.rationale-quote-box {{
    background: rgba(255, 255, 255, 0.025);
    border-left: 3px solid var(--accent);
    border-radius: 0 10px 10px 0;
    padding: 1.25rem 1.5rem;
    font-size: 0.95rem;
    color: var(--text-primary);
    line-height: 1.65;
    margin-bottom: 1.8rem;
    word-break: break-word;
    overflow: visible;
}}

.evidence-btn-group {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    overflow: visible;
}}

.evidence-pill-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem 1.1rem;
    font-size: 0.84rem;
    font-weight: 500;
    color: var(--text-primary);
    text-decoration: none !important;
    transition: all 0.15s ease;
    white-space: nowrap;
}}

.evidence-pill-btn:hover {{
    background: var(--accent-muted);
    border-color: var(--accent-border);
    color: #fff;
    transform: translateY(-1px);
}}

/* ── About / Technical Approach ───────────────────────────────────────────── */
.methodology-card {{
    background: var(--surface);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.8rem 2rem;
    height: auto;
    overflow: visible;
}}

.method-step-row {{
    display: flex;
    align-items: flex-start;
    gap: 1.1rem;
    padding: 0.9rem 0;
    overflow: visible;
}}

.step-num-pill {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: var(--accent-muted);
    border: 1px solid var(--accent-border);
    border-radius: 8px;
    color: var(--accent);
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
    flex-shrink: 0;
}}

.step-content {{
    flex: 1;
    min-width: 0;
    overflow: visible;
}}

.step-heading {{
    display: flex;
    align-items: center;
    gap: 0.55rem;
    font-size: 0.96rem;
    font-weight: 700;
    color: var(--text-primary);
    margin: 0 0 0.25rem;
}}

.step-desc {{
    font-size: 0.84rem;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
    word-break: break-word;
}}

.step-arrow {{
    text-align: center;
    color: var(--text-muted);
    font-size: 1rem;
    margin: -0.2rem 0;
}}

.workflow-row {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    flex-wrap: wrap;
    padding: 0.5rem 0;
    overflow: visible;
}}

.wf-node {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.9rem 1rem;
    min-width: 105px;
    text-align: center;
    transition: all 0.15s ease;
}}

.wf-node:hover {{
    border-color: var(--accent-border);
    background: var(--accent-muted);
}}

.wf-icon {{
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--accent);
    margin-bottom: 0.4rem;
}}

.wf-label {{
    font-size: 0.84rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.15rem;
}}

.wf-sub {{
    font-size: 0.72rem;
    color: var(--text-muted);
}}

.wf-arrow {{
    color: var(--text-muted);
    font-size: 1rem;
    flex-shrink: 0;
}}

.schema-grid {{
    display: grid;
    grid-template-columns: 1fr 1.5fr;
    gap: 2rem;
    align-items: start;
    overflow: visible;
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0;
    font-size: 0.85rem;
    color: var(--text-secondary);
}}

.legend-dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--accent);
    flex-shrink: 0;
}}

.legend-name {{
    font-weight: 600;
    color: var(--text-primary);
}}

.legend-example {{
    font-size: 0.76rem;
    color: var(--text-muted);
    margin-left: 0.35rem;
}}

.graph-canvas {{
    background: rgba(14, 16, 22, 0.6);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: visible;
}}

/* ── Responsive adjustments ──────────────────────────────────────────────── */
@media (max-width: 960px) {{
    .block-container {{
        padding-left: 4% !important;
        padding-right: 4% !important;
    }}
    .feature-grid {{
        grid-template-columns: 1fr;
    }}
    .hero-title {{
        font-size: 2.2rem;
    }}
    .stats-grid {{
        grid-template-columns: 1fr;
    }}
    .schema-grid {{
        grid-template-columns: 1fr;
    }}
    .top-navbar {{
        flex-direction: column;
        align-items: stretch;
    }}
}}
</style>
""", unsafe_allow_html=True)

# ── Render Universal Top Navigation Bar ───────────────────────────────────────

cur_page = st.session_state.nav

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

right_header_elem = f"""
<a href="https://github.com/pallets/flask" target="_blank" class="github-btn">
    {github_svg}
    <span>GitHub</span>
    {ext_arrow_svg}
</a>
"""

if is_about:
    right_header_elem = f"""
    <div style="display:flex; align-items:center; gap:0.6rem;">
        <span class="step-indicator">v1.0 Architecture</span>
        {right_header_elem}
    </div>
    """

# ── Render Universal Top Navigation Bar ───────────────────────────────────────
st.markdown(clean_html(f"""
<div class="top-navbar">
    <a href="?page=home" target="_self" class="brand-container">
        <span class="brand-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
        </span>
        <span class="brand-title">Why The Code Is Like This</span>
    </a>
    <div class="nav-pill-group">
        <a href="?page=home" target="_self" class="nav-link {'active' if is_home else ''}">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
            <span>Home</span>
        </a>
        <a href="?page=explore" target="_self" class="nav-link {'active' if is_explore else ''}">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
            </svg>
            <span>Explore Decisions</span>
        </a>
        <a href="?page=about" target="_self" class="nav-link {'active' if is_about else ''}">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>
            </svg>
            <span>About</span>
        </a>
    </div>
    {right_header_elem}
</div>
"""), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: HOME
# ══════════════════════════════════════════════════════════════════════════════

if is_home:

    # Hero Content
    st.markdown(clean_html("""
    <div class="hero-container">
        <div class="hero-badge">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
            </svg>
            <span>Code Decision Intelligence</span>
        </div>
        <h1 class="hero-title">Why The <span class="hero-title-accent">Code</span> Is Like This.</h1>
        <div class="hero-subtitle">Understand the decisions behind your codebase.</div>
        <p class="hero-desc">
            Explore why specific methods and functions were deprecated or removed, backed by
            verified version history, original maintainer rationale, and primary source evidence.
        </p>
    </div>
    """), unsafe_allow_html=True)

    # Search Bar Form
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
            submitted = st.form_submit_button("Search  →", type="primary", use_container_width=True)

    if submitted and query_val:
        st.session_state.search_query = query_val

    # Interactive Try Searching Chips (Lucide SVG, No emojis)
    st.markdown(clean_html(f"""
    <div class="chips-row">
        <span>Try searching:</span>
        <a href="?page=home&q=app.before_first_request" target="_self" class="chip-btn">
            {code_icon_svg} app.before_first_request
        </a>
        <a href="?page=home&q=got_first_request" target="_self" class="chip-btn">
            {code_icon_svg} got_first_request
        </a>
        <a href="?page=home&q=test_client.as_tuple" target="_self" class="chip-btn">
            {code_icon_svg} test_client.as_tuple
        </a>
    </div>
    """), unsafe_allow_html=True)

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
                            {src_badge_html}
                            <a href="?page=explore&decision={matched['entity']}" target="_self" class="decision-badge">
                                <span>Explorer</span>
                                {ext_arrow_svg}
                            </a>
                        </div>
                    </div>
                    {db_note_html}
                    <div class="rationale-quote-box">
                        {matched['rationale']}
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem;">
                        <span style="font-size:0.86rem; color:var(--text-secondary);">
                            Deprecated in <strong style="color:var(--accent);">{matched['dep_version']}</strong> · 
                            Removed in <strong style="color:var(--text-primary);">{matched['rem_version']}</strong>
                        </span>
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
            <div style="text-align: center; margin: 2rem auto 3rem; color: var(--text-secondary);">
                <div style="display:inline-flex; align-items:center; justify-content:center; width:48px; height:48px; background:var(--accent-muted); border:1px solid var(--accent-border); border-radius:12px; color:var(--accent); margin-bottom:0.75rem;">
                    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
                    </svg>
                </div>
                <div style="font-size: 1.05rem; font-weight: 700; color: var(--text-primary);">No verified decision record found</div>
                <div style="font-size: 0.88rem; color: var(--text-muted); margin-top: 0.25rem;">
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
                    <circle cx="12" cy="12" r="4"/><line x1="1.05" y1="12" x2="7" y2="12"/><line x1="17.01" y1="12" x2="22.96" y2="12"/>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Version History</h3>
                <p class="feature-desc">Track precise deprecation milestones, removal releases, and commit timeline history.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Evidence-Backed</h3>
                <p class="feature-desc">Direct citations and links to primary GitHub issues, maintainer pull requests, and changelogs.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"></path>
                    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"></path>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Developer Context</h3>
                <p class="feature-desc">Understand original architectural reasoning and migration pathways without hallucinated explanations.</p>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: EXPLORE DECISIONS
# ══════════════════════════════════════════════════════════════════════════════

elif is_explore:

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
                <span>Verified Rationale</span>
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

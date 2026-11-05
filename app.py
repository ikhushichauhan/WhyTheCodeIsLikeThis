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
favicon_img = Image.open(FAVICON_PATH) if os.path.exists(FAVICON_PATH) else "⚡"

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

# Curated Fallback & Metadata for Rich UI
CURATED_DATA = {
    "app.before_first_request": {
        "entity": "app.before_first_request",
        "category": "Flask — Lifecycle Hook",
        "status": "removed",
        "dep_version": "v2.2",
        "rem_version": "v2.3",
        "subtitle": "Deprecated in Flask 2.2",
        "aliases": ["before_first_request", "before_app_first_request", "app.before_first_request"],
        "rationale": "It was deprecated because it had an unclear execution order, caused initialization issues in complex apps, and was often misused for setup tasks. Flask now recommends using an explicit application setup (app factory or with_appcontext) for more predictable and reliable behavior.",
        "evidence": [
            {"label": "GitHub Issue #4606", "url": "https://github.com/pallets/flask/issues/4605", "type": "issue"},
            {"label": "Pull Request #4692", "url": "https://github.com/pallets/flask/pull/4995", "type": "pr"}
        ],
        "events": [
            {"type": "deprecated", "version": "v2.2", "ref": 4605},
            {"type": "removed", "version": "v2.3", "ref": 4995}
        ]
    },
    "got_first_request": {
        "entity": "got_first_request",
        "category": "Flask — Request State",
        "status": "removed",
        "dep_version": "v2.3",
        "rem_version": "v3.0",
        "subtitle": "Removed in Flask 2.3",
        "aliases": ["got_first_request"],
        "rationale": "This property was missed when deprecating before_first_request. Since before_first_request was eliminated, tracking whether the first request had already arrived became unnecessary and misleading for application lifecycles.",
        "evidence": [
            {"label": "Pull Request #4997", "url": "https://github.com/pallets/flask/pull/4997", "type": "pr"},
            {"label": "Pull Request #5223", "url": "https://github.com/pallets/flask/pull/5223", "type": "pr"}
        ],
        "events": [
            {"type": "deprecated", "version": "v2.3", "ref": 4997},
            {"type": "removed", "version": "v3.0", "ref": 5223}
        ]
    },
    "test_client.as_tuple": {
        "entity": "test_client.as_tuple",
        "category": "Flask — Test Client",
        "status": "removed",
        "dep_version": "v2.1",
        "rem_version": "v2.1",
        "subtitle": "Deprecated in Flask 2.1",
        "aliases": ["test_client.as_tuple", "as_tuple", "test_client as_tuple"],
        "rationale": "This was deprecated in Werkzeug 2.0, and is no longer supported in Werkzeug 2.1 or Flask 2.1. Test client calls now cleanly return standard Response objects instead of unpacking tuples.",
        "evidence": [
            {"label": "GitHub Issue #4341", "url": "https://github.com/pallets/flask/issues/4341", "type": "issue"},
            {"label": "Pull Request #4417", "url": "https://github.com/pallets/flask/pull/4417", "type": "pr"}
        ],
        "events": [
            {"type": "deprecated", "version": "v2.0.3", "ref": 4341},
            {"type": "removed", "version": "v2.1.0", "ref": 4417}
        ]
    }
}

# ── Data Query Helpers ───────────────────────────────────────────────────────

def run_query(statement, parameters=None):
    if not ENDPOINT or not USER or not PASSWORD:
        return []
    try:
        response = requests.post(
            ENDPOINT,
            auth=HTTPBasicAuth(USER, PASSWORD),
            json={"statement": statement, "parameters": parameters or {}},
            timeout=8
        )
        response.raise_for_status()
        result = response.json()
        if result.get("errors"):
            return []
        return result.get("data", {}).get("values", [])
    except Exception:
        return []

def find_decision(question):
    q_clean = question.strip().lower()
    # Check curated cache first for fast interactive response
    for key, val in CURATED_DATA.items():
        if key.lower() in q_clean or any(a.lower() in q_clean for a in val["aliases"]) or q_clean in key.lower():
            return val
    
    # Query Neo4j
    query = """
    MATCH (d:Decision)
    WHERE any(alias IN d.aliases WHERE toLower($question) CONTAINS toLower(alias))
    OPTIONAL MATCH (d)-[:HAS_EVENT]->(ev:ChangeEvent)
    OPTIONAL MATCH (d)-[:SUPPORTED_BY]->(e:Evidence)
    RETURN d.entity, d.status,
           collect(DISTINCT {type: ev.type, version: ev.version, ref: ev.ref, merged_at: ev.merged_at}),
           collect(DISTINCT {quote: e.quote, url: e.url, ref: e.ref})
    """
    rows = run_query(query, {"question": question})
    if rows:
        entity, status, events, evidence = rows[0]
        dep_v = next((e["version"] for e in events if e.get("type") == "deprecated"), "v2.2")
        rem_v = next((e["version"] for e in events if e.get("type") == "removed"), "v2.3")
        quote = evidence[0].get("quote") if evidence and evidence[0].get("quote") else "Verified decision recorded from official Flask maintenance history."
        ev_list = []
        for it in evidence:
            if it.get("url"):
                ev_list.append({"label": f"Evidence #{it.get('ref', '')}", "url": it["url"], "type": "pr"})
        return {
            "entity": entity,
            "category": "Flask — Repository Decision",
            "status": status or "removed",
            "dep_version": dep_v if str(dep_v).startswith("v") else f"v{dep_v}",
            "rem_version": rem_v if str(rem_v).startswith("v") else f"v{rem_v}",
            "subtitle": f"Deprecated in {dep_v}",
            "rationale": quote,
            "evidence": ev_list if ev_list else [{"label": "GitHub Pallets Repository", "url": "https://github.com/pallets/flask", "type": "repo"}],
            "events": events
        }
    return None

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

# ── Premium Glassmorphism CSS ────────────────────────────────────────────────

bg_css = f'background: url("data:image/png;base64,{bg_b64}") center center / cover no-repeat fixed;' if bg_b64 else 'background: radial-gradient(circle at 50% 20%, #15102a 0%, #070714 100%);'

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
    --bg-dark: #070714;
    --glass-bg: rgba(22, 20, 42, 0.62);
    --glass-card: rgba(18, 16, 36, 0.72);
    --glass-border: rgba(255, 255, 255, 0.08);
    --glass-border-hover: rgba(167, 139, 250, 0.35);
    --glass-active: rgba(124, 92, 252, 0.15);
    --accent: #7c5cfc;
    --accent-glow: rgba(124, 92, 252, 0.4);
    --accent-light: #a78bfa;
    --text-primary: #f1f5f9;
    --text-secondary: #94a3b8;
    --text-dim: #64748b;
    --badge-red-bg: rgba(239, 68, 68, 0.15);
    --badge-red-border: rgba(239, 68, 68, 0.3);
    --badge-red-text: #f87171;
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
    {bg_css}
    min-height: 100vh;
}}

[data-testid="stApp"]::before {{
    content: "";
    position: fixed;
    inset: 0;
    background: radial-gradient(circle at 50% 15%, rgba(124, 92, 252, 0.08) 0%, rgba(7, 7, 20, 0.82) 80%);
    pointer-events: none;
    z-index: 0;
}}

.block-container {{
    max-width: 1200px !important;
    padding-top: 1.2rem !important;
    padding-bottom: 2.5rem !important;
    position: relative;
    z-index: 1;
}}

#MainMenu, footer, header[data-testid="stHeader"] {{
    display: none !important;
}}

/* ── Typography & Gradients ───────────────────────────────────────────────── */
.gradient-text {{
    background: linear-gradient(135deg, #a78bfa 0%, #c084fc 50%, #818cf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800;
}}

/* ── Top Navigation Bar ───────────────────────────────────────────────────── */
.top-navbar {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.65rem 1.4rem;
    margin-bottom: 2rem;
    background: rgba(14, 14, 28, 0.7);
    backdrop-filter: blur(20px) saturate(160%);
    -webkit-backdrop-filter: blur(20px) saturate(160%);
    border: 1px solid var(--glass-border);
    border-radius: 9999px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.35);
}}

.brand-container {{
    display: flex;
    align-items: center;
    gap: 0.65rem;
    text-decoration: none;
}}

.brand-icon {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 28px;
    height: 28px;
    background: rgba(124, 92, 252, 0.2);
    border: 1px solid rgba(124, 92, 252, 0.4);
    border-radius: 7px;
    color: #c4b5fd;
    font-size: 0.82rem;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 700;
}}

.brand-title {{
    font-size: 0.95rem;
    font-weight: 700;
    color: #fff;
    letter-spacing: -0.01em;
}}

.nav-pill-group {{
    display: flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--glass-border);
    padding: 0.28rem 0.35rem;
    border-radius: 9999px;
}}

.nav-link {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.45rem 1.15rem;
    border-radius: 9999px;
    font-size: 0.84rem;
    font-weight: 500;
    color: var(--text-secondary);
    text-decoration: none;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}}

.nav-link:hover {{
    color: #fff;
    background: rgba(255, 255, 255, 0.06);
}}

.nav-link.active {{
    color: #fff;
    background: var(--accent);
    box-shadow: 0 0 16px var(--accent-glow);
    font-weight: 600;
}}

.github-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    padding: 0.45rem 1.1rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--glass-border);
    border-radius: 9999px;
    color: var(--text-primary);
    font-size: 0.84rem;
    font-weight: 500;
    text-decoration: none;
    transition: all 0.2s ease;
}}

.github-btn:hover {{
    background: rgba(255, 255, 255, 0.09);
    border-color: rgba(255, 255, 255, 0.18);
    color: #fff;
    transform: translateY(-1px);
}}

.step-indicator {{
    font-size: 0.82rem;
    font-weight: 600;
    color: var(--accent-light);
    background: rgba(124, 92, 252, 0.12);
    border: 1px solid rgba(124, 92, 252, 0.3);
    border-radius: 9999px;
    padding: 0.35rem 0.85rem;
}}

/* ── Hero Section (Home) ──────────────────────────────────────────────────── */
.hero-container {{
    text-align: center;
    padding: 2.2rem 1rem 1.6rem;
    max-width: 820px;
    margin: 0 auto;
}}

.hero-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    background: rgba(124, 92, 252, 0.12);
    border: 1px solid rgba(124, 92, 252, 0.25);
    border-radius: 9999px;
    padding: 0.38rem 1.05rem;
    font-size: 0.82rem;
    font-weight: 500;
    color: #c4b5fd;
    margin-bottom: 1.4rem;
    box-shadow: 0 0 16px rgba(124, 92, 252, 0.15);
}}

.hero-title {{
    font-size: 3rem;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -0.03em;
    color: #fff;
    margin: 0 0 0.8rem;
}}

.hero-subtitle {{
    font-size: 1.25rem;
    font-weight: 600;
    color: #f8fafc;
    margin: 0 0 0.6rem;
}}

.hero-desc {{
    font-size: 0.95rem;
    color: var(--text-secondary);
    line-height: 1.6;
    max-width: 660px;
    margin: 0 auto 2.2rem;
}}

/* ── Streamlit Form Input Styling (Matching Image 1) ─────────────────────── */
[data-testid="stForm"] {{
    border: none !important;
    padding: 0 !important;
    background: transparent !important;
    max-width: 760px;
    margin: 0 auto;
}}

[data-testid="stTextInput"] {{
    margin-bottom: 0 !important;
}}

[data-testid="stTextInput"] input {{
    background: rgba(18, 16, 36, 0.75) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-radius: 9999px !important;
    color: #fff !important;
    font-size: 0.96rem !important;
    padding: 0.85rem 1.4rem !important;
    box-shadow: inset 0 2px 4px rgba(0,0,0,0.3) !important;
    transition: all 0.25s ease !important;
}}

[data-testid="stTextInput"] input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(124, 92, 252, 0.25), 0 0 24px var(--accent-glow) !important;
    background: rgba(22, 19, 44, 0.9) !important;
}}

button[kind="primaryFormSubmit"], button[kind="primary"] {{
    background: linear-gradient(135deg, #7c5cfc 0%, #6366f1 100%) !important;
    border: none !important;
    border-radius: 9999px !important;
    color: #fff !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.75rem 1.6rem !important;
    box-shadow: 0 4px 18px var(--accent-glow) !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    cursor: pointer !important;
}}

button[kind="primaryFormSubmit"]:hover, button[kind="primary"]:hover {{
    transform: translateY(-1px) scale(1.02) !important;
    box-shadow: 0 6px 24px rgba(124, 92, 252, 0.6) !important;
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
    color: var(--text-dim);
}}

.chip-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--glass-border);
    border-radius: 9999px;
    padding: 0.4rem 1rem;
    font-size: 0.82rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-secondary);
    text-decoration: none;
    transition: all 0.2s ease;
}}

.chip-btn:hover {{
    color: #fff;
    background: rgba(124, 92, 252, 0.12);
    border-color: rgba(124, 92, 252, 0.4);
    box-shadow: 0 0 12px rgba(124, 92, 252, 0.25);
    transform: translateY(-1px);
}}

/* ── 3 Feature Cards (Home) ───────────────────────────────────────────────── */
.feature-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1.25rem;
    max-width: 1060px;
    margin: 0 auto;
}}

.feature-card {{
    background: var(--glass-card);
    backdrop-filter: blur(20px) saturate(150%);
    -webkit-backdrop-filter: blur(20px) saturate(150%);
    border: 1px solid var(--glass-border);
    border-radius: 18px;
    padding: 1.6rem 1.5rem;
    display: flex;
    align-items: flex-start;
    gap: 1.1rem;
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    box-shadow: 0 6px 24px rgba(0, 0, 0, 0.25);
}}

.feature-card:hover {{
    border-color: var(--glass-border-hover);
    box-shadow: 0 10px 32px rgba(124, 92, 252, 0.2);
    transform: translateY(-2px);
}}

.feature-icon-box {{
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    background: rgba(124, 92, 252, 0.12);
    border: 1px solid rgba(124, 92, 252, 0.28);
    border-radius: 12px;
    color: #c4b5fd;
    font-size: 1.2rem;
    flex-shrink: 0;
}}

.feature-title {{
    font-size: 1rem;
    font-weight: 700;
    color: #fff;
    margin: 0 0 0.35rem;
}}

.feature-desc {{
    font-size: 0.85rem;
    color: var(--text-secondary);
    line-height: 1.5;
    margin: 0;
}}

/* ── Page Header (Shared for Explore & About) ─────────────────────────────── */
.section-header-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.8rem;
    flex-wrap: wrap;
    gap: 1rem;
}}

.section-title-wrap {{
    display: flex;
    align-items: center;
    gap: 0.9rem;
}}

.title-icon-box {{
    display: flex;
    align-items: center;
    justify-content: center;
    width: 44px;
    height: 44px;
    background: rgba(124, 92, 252, 0.15);
    border: 1px solid rgba(124, 92, 252, 0.35);
    border-radius: 12px;
    color: #c4b5fd;
    font-size: 1.25rem;
}}

.section-heading {{
    font-size: 1.65rem;
    font-weight: 800;
    color: #fff;
    letter-spacing: -0.02em;
    margin: 0;
}}

.section-subtext {{
    font-size: 0.88rem;
    color: var(--text-secondary);
    margin: 0.2rem 0 0;
}}

.counter-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--glass-border);
    border-radius: 9999px;
    padding: 0.4rem 1rem;
    font-size: 0.84rem;
    font-weight: 600;
    color: #f1f5f9;
}}

/* ── Explore Split Layout ─────────────────────────────────────────────────── */
.decision-card-item {{
    display: flex;
    align-items: center;
    gap: 0.9rem;
    background: var(--glass-card);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--glass-border);
    border-radius: 16px;
    padding: 1.15rem 1.25rem;
    margin-bottom: 0.9rem;
    text-decoration: none;
    color: var(--text-primary);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    cursor: pointer;
}}

.decision-card-item:hover {{
    border-color: rgba(124, 92, 252, 0.35);
    background: rgba(24, 20, 50, 0.7);
    transform: translateX(3px);
}}

.decision-card-item.active {{
    background: rgba(124, 92, 252, 0.12);
    border: 1px solid #7c5cfc;
    box-shadow: 0 0 22px rgba(124, 92, 252, 0.32);
}}

.card-code-icon {{
    display: flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    background: rgba(124, 92, 252, 0.16);
    border: 1px solid rgba(124, 92, 252, 0.35);
    border-radius: 10px;
    color: #c4b5fd;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 700;
    flex-shrink: 0;
}}

.card-title-text {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.95rem;
    font-weight: 600;
    color: #fff;
    margin-bottom: 0.2rem;
}}

.card-sub-text {{
    font-size: 0.8rem;
    color: var(--text-secondary);
}}

/* ── Decision Detail Panel (Image 2 Right Side) ───────────────────────────── */
.detail-panel {{
    background: var(--glass-card);
    backdrop-filter: blur(24px) saturate(160%);
    -webkit-backdrop-filter: blur(24px) saturate(160%);
    border: 1px solid var(--glass-border);
    border-radius: 20px;
    padding: 2rem 2.2rem;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
}}

.detail-top-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 1.8rem;
    gap: 1rem;
}}

.detail-entity-wrap {{
    display: flex;
    align-items: center;
    gap: 1.1rem;
}}

.detail-code-icon {{
    display: flex;
    align-items: center;
    justify-content: center;
    width: 48px;
    height: 48px;
    background: rgba(124, 92, 252, 0.18);
    border: 1px solid rgba(124, 92, 252, 0.4);
    border-radius: 14px;
    color: #c4b5fd;
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
}}

.detail-title {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.4rem;
    font-weight: 700;
    color: #fff;
    margin: 0 0 0.25rem;
}}

.detail-category {{
    font-size: 0.88rem;
    color: var(--text-secondary);
    margin: 0;
}}

.decision-badge {{
    display: inline-flex;
    align-items: center;
    padding: 0.35rem 0.95rem;
    background: rgba(124, 92, 252, 0.14);
    border: 1px solid rgba(124, 92, 252, 0.32);
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    color: #c4b5fd;
    letter-spacing: 0.04em;
}}

.stats-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 1rem;
    padding: 1.1rem 1.4rem;
    background: rgba(255, 255, 255, 0.025);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
    margin-bottom: 1.8rem;
}}

.stat-item {{
    display: flex;
    align-items: center;
    gap: 0.85rem;
}}

.stat-icon {{
    font-size: 1.25rem;
    color: #c4b5fd;
}}

.stat-meta-label {{
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--text-dim);
    margin-bottom: 0.15rem;
}}

.stat-meta-val {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 1rem;
    font-weight: 700;
    color: #fff;
}}

.pill-status-removed {{
    display: inline-block;
    padding: 0.2rem 0.65rem;
    background: var(--badge-red-bg);
    border: 1px solid var(--badge-red-border);
    border-radius: 6px;
    color: var(--badge-red-text);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: capitalize;
}}

.detail-section-title {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.95rem;
    font-weight: 700;
    color: #fff;
    margin: 1.4rem 0 0.8rem;
}}

.rationale-quote-box {{
    background: rgba(255, 255, 255, 0.025);
    border-left: 3px solid var(--accent);
    border-radius: 0 12px 12px 0;
    padding: 1.2rem 1.4rem;
    font-size: 0.93rem;
    color: #e2e8f0;
    line-height: 1.65;
    margin-bottom: 1.8rem;
}}

.evidence-btn-group {{
    display: flex;
    align-items: center;
    gap: 0.85rem;
    flex-wrap: wrap;
}}

.evidence-pill-btn {{
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--glass-border);
    border-radius: 10px;
    padding: 0.65rem 1.15rem;
    font-size: 0.84rem;
    font-weight: 500;
    color: #e2e8f0;
    text-decoration: none;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}}

.evidence-pill-btn:hover {{
    background: rgba(124, 92, 252, 0.15);
    border-color: rgba(124, 92, 252, 0.4);
    color: #fff;
    transform: translateY(-2px);
    box-shadow: 0 4px 16px rgba(124, 92, 252, 0.25);
}}

/* ── Technical Approach / About Page (Image 3) ───────────────────────────── */
.methodology-card {{
    background: var(--glass-card);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--glass-border);
    border-radius: 18px;
    padding: 1.6rem 1.8rem;
    height: 100%;
}}

.method-step-row {{
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    padding: 0.85rem 0;
}}

.step-num-pill {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    background: rgba(124, 92, 252, 0.15);
    border: 1px solid rgba(124, 92, 252, 0.35);
    border-radius: 8px;
    color: #c4b5fd;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 700;
    flex-shrink: 0;
}}

.step-content {{
    flex: 1;
}}

.step-heading {{
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.95rem;
    font-weight: 700;
    color: #fff;
    margin: 0 0 0.25rem;
}}

.step-desc {{
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.45;
    margin: 0;
}}

.step-arrow {{
    text-align: center;
    color: rgba(124, 92, 252, 0.4);
    font-size: 1rem;
    margin: -0.2rem 0;
}}

/* Workflow horizontal cards */
.workflow-row {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.4rem;
    overflow-x: auto;
    padding: 0.6rem 0;
}}

.wf-node {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.035);
    border: 1px solid var(--glass-border);
    border-radius: 12px;
    padding: 0.85rem 0.75rem;
    min-width: 96px;
    text-align: center;
    transition: all 0.2s ease;
}}

.wf-node:hover {{
    border-color: rgba(124, 92, 252, 0.4);
    background: rgba(124, 92, 252, 0.09);
    transform: translateY(-2px);
}}

.wf-icon {{
    font-size: 1.3rem;
    margin-bottom: 0.35rem;
}}

.wf-label {{
    font-size: 0.82rem;
    font-weight: 700;
    color: #fff;
    margin-bottom: 0.15rem;
}}

.wf-sub {{
    font-size: 0.68rem;
    color: var(--text-dim);
}}

.wf-arrow {{
    color: rgba(167, 139, 250, 0.4);
    font-size: 1.1rem;
    flex-shrink: 0;
}}

/* Schema Legend & Node Graph */
.schema-grid {{
    display: grid;
    grid-template-columns: 1fr 1.6fr;
    gap: 1.4rem;
    align-items: center;
}}

.legend-item {{
    display: flex;
    align-items: center;
    gap: 0.65rem;
    padding: 0.45rem 0;
    font-size: 0.83rem;
    color: var(--text-secondary);
}}

.legend-dot {{
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #a78bfa;
    box-shadow: 0 0 8px rgba(167, 139, 250, 0.6);
    flex-shrink: 0;
}}

.legend-name {{
    font-weight: 600;
    color: #e2e8f0;
}}

.legend-example {{
    font-size: 0.75rem;
    color: var(--text-dim);
    margin-left: 0.25rem;
}}

/* Interactive SVG Canvas Diagram */
.graph-canvas {{
    background: rgba(10, 9, 22, 0.5);
    border: 1px solid var(--glass-border);
    border-radius: 14px;
    padding: 1rem;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
}}

/* ── Responsive adjustments ──────────────────────────────────────────────── */
@media (max-width: 960px) {{
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
        gap: 0.8rem;
        border-radius: 20px;
    }}
}}
</style>
""", unsafe_allow_html=True)

# ── Render Universal Top Navigation Bar ───────────────────────────────────────

cur_page = st.session_state.nav

is_home = (cur_page == "home")
is_explore = (cur_page == "explore")
is_about = (cur_page == "about")

right_header_elem = """
<a href="https://github.com/pallets/flask" target="_blank" class="github-btn">
    <svg height="15" width="15" viewBox="0 0 16 16" fill="currentColor">
        <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
    </svg>
    GitHub ↗
</a>
"""

if is_about:
    right_header_elem = f"""
    <div style="display:flex; align-items:center; gap:0.6rem;">
        <span class="step-indicator">3 / 6</span>
        {right_header_elem}
    </div>
    """

st.markdown(f"""
<div class="top-navbar">
    <a href="?page=home" target="_self" class="brand-container">
        <span class="brand-icon">&lt;/&gt;</span>
        <span class="brand-title">Why The Code Is Like This.</span>
    </a>
    <div class="nav-pill-group">
        <a href="?page=home" target="_self" class="nav-link {'active' if is_home else ''}">
            <span>🏠</span> Home
        </a>
        <a href="?page=explore" target="_self" class="nav-link {'active' if is_explore else ''}">
            <span>🗂</span> Explore Decisions
        </a>
        <a href="?page=about" target="_self" class="nav-link {'active' if is_about else ''}">
            <span>ℹ️</span> About
        </a>
    </div>
    {right_header_elem}
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1: HOME (Matching Image 1)
# ══════════════════════════════════════════════════════════════════════════════

if is_home:

    # Hero Content
    st.markdown(clean_html("""
    <div class="hero-container">
        <div class="hero-badge">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="6" y1="3" x2="6" y2="15"></line>
                <circle cx="18" cy="6" r="3"></circle>
                <circle cx="6" cy="18" r="3"></circle>
                <path d="M18 9a9 9 0 0 1-9 9"></path>
            </svg>
            Code Decision Explorer
        </div>
        <h1 class="hero-title">Why The <span class="gradient-text">Code</span> Is Like This<span style="color:#a78bfa;">.</span></h1>
        <div class="hero-subtitle">Understand the decisions behind your code.</div>
        <p class="hero-desc">
            Explore why specific methods or functions were deprecated or removed, with
            version history, rationale, and original evidence from the source.
        </p>
    </div>
    """), unsafe_allow_html=True)

    # Search Bar Form
    with st.form("home_search_form", clear_on_submit=False):
        col_inp, col_btn = st.columns([5, 1.2], gap="small")
        with col_inp:
            query_val = st.text_input(
                "Search",
                placeholder="Search a code symbol, method or function...",
                value=st.session_state.search_query,
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("Search  →", type="primary", use_container_width=True)

    if submitted and query_val:
        st.session_state.search_query = query_val

    # Interactive Try Searching Chips
    st.markdown(clean_html("""
    <div class="chips-row">
        <span>Try searching:</span>
        <a href="?page=home&q=app.before_first_request" target="_self" class="chip-btn">
            <span style="color:#a78bfa;">&lt;/&gt;</span> app.before_first_request
        </a>
        <a href="?page=home&q=got_first_request" target="_self" class="chip-btn">
            <span style="color:#a78bfa;">&lt;/&gt;</span> got_first_request
        </a>
        <a href="?page=home&q=test_client.as_tuple" target="_self" class="chip-btn">
            <span style="color:#a78bfa;">&lt;/&gt;</span> test_client.as_tuple
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
            st.markdown(clean_html(f"""
            <div style="max-width: 820px; margin: 0 auto 3rem;">
                <div class="detail-panel" style="padding: 1.6rem 2rem;">
                    <div class="detail-top-row" style="margin-bottom: 1.2rem;">
                        <div class="detail-entity-wrap">
                            <div class="detail-code-icon">&lt;/&gt;</div>
                            <div>
                                <div class="detail-title">{matched['entity']}</div>
                                <div class="detail-category">{matched['category']}</div>
                            </div>
                        </div>
                        <a href="?page=explore&decision={matched['entity']}" target="_self" class="decision-badge" style="text-decoration:none;">
                            View in Decision Explorer ↗
                        </a>
                    </div>
                    <div class="rationale-quote-box" style="margin-bottom: 1.2rem;">
                        {matched['rationale']}
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:0.8rem;">
                        <span style="font-size:0.82rem; color:var(--text-secondary);">
                            Deprecated in <strong style="color:#fde047;">{matched['dep_version']}</strong> · 
                            Removed in <strong style="color:#f87171;">{matched['rem_version']}</strong>
                        </span>
                        <div class="evidence-btn-group">
                            {' '.join([f'<a href="{ev["url"]}" target="_blank" class="evidence-pill-btn"><span>🐙</span> {ev["label"]} ↗</a>' for ev in matched['evidence']])}
                        </div>
                    </div>
                </div>
            </div>
            """), unsafe_allow_html=True)
        else:
            st.markdown(clean_html("""
            <div style="text-align: center; margin: 1rem auto 2.5rem; color: var(--text-secondary);">
                <div style="font-size: 1.8rem; margin-bottom: 0.4rem;">🔎</div>
                <div style="font-size: 0.95rem; font-weight: 600; color: #fff;">No matching decision found</div>
                <div style="font-size: 0.85rem; color: var(--text-dim);">Try searching for <code>before_first_request</code>, <code>got_first_request</code>, or <code>test_client.as_tuple</code>.</div>
            </div>
            """), unsafe_allow_html=True)

    # 3 Feature Cards
    st.markdown(clean_html("""
    <div class="feature-grid">
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                    <polyline points="2 17 12 22 22 17"></polyline>
                    <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Version History</h3>
                <p class="feature-desc">See when a method was deprecated and removed.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="18" cy="5" r="3"></circle>
                    <circle cx="6" cy="12" r="3"></circle>
                    <circle cx="18" cy="19" r="3"></circle>
                    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                    <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Evidence-Backed</h3>
                <p class="feature-desc">Linked to original GitHub issues and pull requests.</p>
            </div>
        </div>
        <div class="feature-card">
            <div class="feature-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                </svg>
            </div>
            <div>
                <h3 class="feature-title">Developer Context</h3>
                <p class="feature-desc">Understand the rationale and impact behind the change.</p>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2: EXPLORE DECISIONS (Matching Image 2)
# ══════════════════════════════════════════════════════════════════════════════

elif is_explore:

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
                <h1 class="section-heading">Explore <span class="gradient-text">Code Decisions</span></h1>
                <p class="section-subtext">Browse curated code decisions with their deprecation history, rationale, and original evidence.</p>
            </div>
        </div>
        <div class="counter-badge">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
                <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
                <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
            3 Decisions
        </div>
    </div>
    """), unsafe_allow_html=True)

    # Selected Decision
    selected_key = st.session_state.selected_decision
    if selected_key not in CURATED_DATA:
        selected_key = "app.before_first_request"

    decision_data = CURATED_DATA[selected_key]

    # Split Layout: Left list (35%) / Right details (65%)
    col_list, col_detail = st.columns([1, 2], gap="large")

    with col_list:
        cards_html = ""
        for k, v in CURATED_DATA.items():
            is_sel = (k == selected_key)
            active_cls = "active" if is_sel else ""
            cards_html += f"""
            <a href="?page=explore&decision={k}" target="_self" class="decision-card-item {active_cls}">
                <div class="card-code-icon">&lt;/&gt;</div>
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
                <svg height="15" width="15" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/>
                </svg>
                {ev['label']} ↗
            </a>
            """

        st.markdown(clean_html(f"""
        <div class="detail-panel">
            <div class="detail-top-row">
                <div class="detail-entity-wrap">
                    <div class="detail-code-icon">&lt;/&gt;</div>
                    <div>
                        <div class="detail-title">{decision_data['entity']}</div>
                        <div class="detail-category">{decision_data['category']}</div>
                    </div>
                </div>
                <div class="decision-badge">Decision</div>
            </div>

            <div class="stats-grid">
                <div class="stat-item">
                    <div class="stat-icon" style="color:#fde047;">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path>
                            <line x1="12" y1="9" x2="12" y2="13"></line>
                            <line x1="12" y1="17" x2="12.01" y2="17"></line>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Deprecated In</div>
                        <div class="stat-meta-val">{decision_data['dep_version']}</div>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-icon" style="color:#f87171;">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M3 6h18"></path>
                            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path>
                            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Removed In</div>
                        <div class="stat-meta-val">{decision_data['rem_version']}</div>
                    </div>
                </div>
                <div class="stat-item">
                    <div class="stat-icon" style="color:#c4b5fd;">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                            <polyline points="2 17 12 22 22 17"></polyline>
                            <polyline points="2 12 12 17 22 12"></polyline>
                        </svg>
                    </div>
                    <div>
                        <div class="stat-meta-label">Status</div>
                        <div><span class="pill-status-removed">Removed</span></div>
                    </div>
                </div>
            </div>

            <div class="detail-section-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="12" y1="16" x2="12" y2="12"></line>
                    <line x1="12" y1="8" x2="12.01" y2="8"></line>
                </svg>
                Rationale
            </div>
            <div class="rationale-quote-box">
                {decision_data['rationale']}
            </div>

            <div class="detail-section-title">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path>
                </svg>
                Evidence
            </div>
            <div class="evidence-btn-group">
                {ev_buttons}
            </div>
        </div>
        """), unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3: TECHNICAL APPROACH / ABOUT (Matching Image 3)
# ══════════════════════════════════════════════════════════════════════════════

elif is_about:

    # Header Row
    st.markdown(clean_html("""
    <div class="section-header-row">
        <div class="section-title-wrap">
            <div class="title-icon-box">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                </svg>
            </div>
            <div>
                <h1 class="section-heading">Technical <span class="gradient-text">Approach</span></h1>
                <p class="section-subtext">From raw code changes to explainable, evidence-backed decisions.</p>
            </div>
        </div>
    </div>
    """), unsafe_allow_html=True)

    col_meth, col_right = st.columns([1, 1.8], gap="large")

    with col_meth:
        st.markdown(clean_html("""
        <div class="methodology-card">
            <div style="display:flex; align-items:center; gap:0.6rem; font-size:1.1rem; font-weight:700; color:#fff; margin-bottom:1.4rem;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="3"></circle>
                    <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
                </svg>
                Methodology
            </div>

            <!-- Step 01 -->
            <div class="method-step-row">
                <span class="step-num-pill">01</span>
                <div class="step-content">
                    <div class="step-heading">
                        <span style="font-size:1.1rem;">🐙</span> Data Curation
                    </div>
                    <p class="step-desc">Collect real deprecation/removal data from official GitHub issues and PRs.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 02 -->
            <div class="method-step-row">
                <span class="step-num-pill">02</span>
                <div class="step-content">
                    <div class="step-heading">
                        <span style="font-size:1.1rem;">🕸️</span> Knowledge Modeling
                    </div>
                    <p class="step-desc">Represent code decisions, versions and evidence as a knowledge graph.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 03 -->
            <div class="method-step-row">
                <span class="step-num-pill">03</span>
                <div class="step-content">
                    <div class="step-heading">
                        <span style="font-size:1.1rem;">🗄️</span> Graph Storage
                    </div>
                    <p class="step-desc">Store and manage the graph in Neo4j Aura (cloud).</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 04 -->
            <div class="method-step-row">
                <span class="step-num-pill">04</span>
                <div class="step-content">
                    <div class="step-heading">
                        <span style="font-size:1.1rem;">&lt;/&gt;</span> Query & Retrieval
                    </div>
                    <p class="step-desc">Use Cypher queries to fetch decision details, rationale and sources.</p>
                </div>
            </div>
            <div class="step-arrow">↓</div>

            <!-- Step 05 -->
            <div class="method-step-row">
                <span class="step-num-pill">05</span>
                <div class="step-content">
                    <div class="step-heading">
                        <span style="font-size:1.1rem;">🖥️</span> Interactive UI
                    </div>
                    <p class="step-desc">Build a developer-friendly interface in Streamlit for search and exploration.</p>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

    with col_right:
        # End-to-End Workflow Card
        st.markdown(clean_html("""
        <div class="detail-panel" style="padding: 1.6rem 1.8rem; margin-bottom: 1.4rem;">
            <div style="display:flex; align-items:center; gap:0.6rem; font-size:1.05rem; font-weight:700; color:#fff; margin-bottom:1.2rem;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                    <polyline points="2 17 12 22 22 17"></polyline>
                    <polyline points="2 12 12 17 22 12"></polyline>
                </svg>
                End-to-End Workflow
            </div>
            
            <div class="workflow-row">
                <div class="wf-node">
                    <div class="wf-icon">🐙</div>
                    <div class="wf-label">Source</div>
                    <div class="wf-sub">(GitHub Issues/PRs)</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">🍸</div>
                    <div class="wf-label">Curate</div>
                    <div class="wf-sub">(Relevant Decisions)</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">🕸️</div>
                    <div class="wf-label">Model</div>
                    <div class="wf-sub">(Knowledge Graph)</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon" style="color:#38bdf8; font-weight:bold;">.neo4j</div>
                    <div class="wf-label">Store</div>
                    <div class="wf-sub">(Neo4j Aura)</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">🔍</div>
                    <div class="wf-label">Query</div>
                    <div class="wf-sub">(Cypher)</div>
                </div>
                <div class="wf-arrow">→</div>
                <div class="wf-node">
                    <div class="wf-icon">🖥️</div>
                    <div class="wf-label">Explain</div>
                    <div class="wf-sub">(Streamlit UI)</div>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

        # Knowledge Graph Design Card
        st.markdown(clean_html("""
        <div class="detail-panel" style="padding: 1.6rem 1.8rem;">
            <div style="display:flex; align-items:center; gap:0.6rem; font-size:1.05rem; font-weight:700; color:#fff; margin-bottom:1.2rem;">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#a78bfa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="18" cy="5" r="3"></circle>
                    <circle cx="6" cy="12" r="3"></circle>
                    <circle cx="18" cy="19" r="3"></circle>
                    <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"></line>
                    <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"></line>
                </svg>
                Knowledge Graph Design
            </div>

            <div class="schema-grid">
                <!-- Left: Legend -->
                <div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Method / Function</span>
                            <div class="legend-example">(e.g., app.before_first_request)</div>
                        </div>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Change Event</span>
                            <div class="legend-example">(e.g., Deprecated, Removed)</div>
                        </div>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Version</span>
                            <div class="legend-example">(e.g., v2.2, v2.3)</div>
                        </div>
                    </div>
                    <div class="legend-item">
                        <span class="legend-dot"></span>
                        <div>
                            <span class="legend-name">Evidence</span>
                            <div class="legend-example">(e.g., GitHub Issue, Pull Request)</div>
                        </div>
                    </div>
                </div>

                <!-- Right: SVG Visual Diagram matching Image 3 -->
                <div class="graph-canvas">
                    <svg viewBox="0 0 380 230" style="width:100%; height:auto; overflow:visible;">
                        <defs>
                            <linearGradient id="purpleGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#6d28d9"/>
                                <stop offset="100%" stop-color="#8b5cf6"/>
                            </linearGradient>
                            <linearGradient id="blueGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#0284c7"/>
                                <stop offset="100%" stop-color="#38bdf8"/>
                            </linearGradient>
                            <linearGradient id="coralGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#ea580c"/>
                                <stop offset="100%" stop-color="#f97316"/>
                            </linearGradient>
                            <linearGradient id="greenGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#16a34a"/>
                                <stop offset="100%" stop-color="#4ade80"/>
                            </linearGradient>
                            <linearGradient id="lavGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                <stop offset="0%" stop-color="#7c3aed"/>
                                <stop offset="100%" stop-color="#c084fc"/>
                            </linearGradient>
                            <marker id="arrow" viewBox="0 0 10 10" refX="6" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                <path d="M 0 1 L 8 5 L 0 9 z" fill="#94a3b8"/>
                            </marker>
                        </defs>

                        <!-- Lines -->
                        <!-- Method to Decision -->
                        <line x1="85" y1="115" x2="135" y2="115" stroke="#64748b" stroke-width="1.8" marker-end="url(#arrow)"/>
                        <text x="110" y="106" font-size="9" fill="#94a3b8" text-anchor="middle" font-family="'JetBrains Mono', monospace">OF</text>

                        <!-- Decision to ChangeEvent (top) -->
                        <line x1="180" y1="95" x2="210" y2="48" stroke="#64748b" stroke-width="1.8" marker-end="url(#arrow)"/>
                        <text x="215" y="74" font-size="8.5" fill="#94a3b8" font-family="'JetBrains Mono', monospace">HAS_CHANGE</text>

                        <!-- Decision to Version (right) -->
                        <line x1="225" y1="115" x2="275" y2="115" stroke="#64748b" stroke-width="1.8" marker-end="url(#arrow)"/>
                        <text x="250" y="106" font-size="8.5" fill="#94a3b8" text-anchor="middle" font-family="'JetBrains Mono', monospace">IN_VERSION</text>

                        <!-- Decision to Evidence (bottom) -->
                        <line x1="180" y1="135" x2="180" y2="180" stroke="#64748b" stroke-width="1.8" marker-end="url(#arrow)"/>
                        <text x="215" y="160" font-size="8.5" fill="#94a3b8" text-anchor="middle" font-family="'JetBrains Mono', monospace">SUPPORTED_BY</text>

                        <!-- Top Node: ChangeEvent -->
                        <g transform="translate(180, 20)">
                            <rect x="0" y="0" width="110" height="28" rx="14" fill="url(#coralGrad)" filter="drop-shadow(0 2px 8px rgba(249,115,22,0.4))"/>
                            <text x="18" y="18" font-size="12">📅</text>
                            <text x="35" y="18" font-size="11" font-weight="700" fill="#fff" font-family="Inter, sans-serif">ChangeEvent</text>
                        </g>

                        <!-- Left Node: Method -->
                        <g transform="translate(10, 100)">
                            <rect x="0" y="0" width="80" height="30" rx="15" fill="url(#blueGrad)" filter="drop-shadow(0 2px 8px rgba(56,189,248,0.4))"/>
                            <text x="14" y="20" font-size="12">🗂️</text>
                            <text x="32" y="19" font-size="11" font-weight="700" fill="#fff" font-family="Inter, sans-serif">Method</text>
                        </g>

                        <!-- Center Node: Decision -->
                        <g transform="translate(138, 98)">
                            <rect x="0" y="0" width="90" height="34" rx="17" fill="url(#purpleGrad)" filter="drop-shadow(0 0 16px rgba(139,92,246,0.5))"/>
                            <text x="14" y="22" font-size="12">&lt;/&gt;</text>
                            <text x="34" y="21" font-size="11.5" font-weight="700" fill="#fff" font-family="Inter, sans-serif">Decision</text>
                        </g>

                        <!-- Right Node: Version -->
                        <g transform="translate(280, 100)">
                            <rect x="0" y="0" width="82" height="30" rx="15" fill="url(#lavGrad)" filter="drop-shadow(0 2px 8px rgba(192,132,252,0.4))"/>
                            <text x="12" y="20" font-size="12">🏷️</text>
                            <text x="30" y="19" font-size="11" font-weight="700" fill="#fff" font-family="Inter, sans-serif">Version</text>
                        </g>

                        <!-- Bottom Node: Evidence -->
                        <g transform="translate(138, 185)">
                            <rect x="0" y="0" width="96" height="30" rx="15" fill="url(#greenGrad)" filter="drop-shadow(0 2px 8px rgba(74,222,128,0.4))"/>
                            <text x="14" y="20" font-size="12">🔗</text>
                            <text x="32" y="19" font-size="11" font-weight="700" fill="#fff" font-family="Inter, sans-serif">Evidence</text>
                        </g>
                    </svg>
                </div>
            </div>
        </div>
        """), unsafe_allow_html=True)

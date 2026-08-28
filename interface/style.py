"""Shared Streamlit look & feel — light pro + dark (black / orange)."""

from __future__ import annotations

import html

import streamlit as st

APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:wght@600;700&display=swap');

/* ---- Light (default) ---- */
:root, html[data-theme="light"] {
  --ink: #111827;
  --text: #1f2937;
  --muted: #6b7280;
  --bg: #f8fafc;
  --surface: #ffffff;
  --border: #e5e7eb;
  --border-strong: #d1d5db;
  --accent: #0b3a4a;
  --accent-2: #1565a8;
  --accent-soft: #e8f1f6;
  --accent-text: #ffffff;
  --danger: #991b1b;
  --danger-bg: #fef2f2;
  --warn: #92400e;
  --warn-bg: #fffbeb;
  --ok: #065f46;
  --ok-bg: #ecfdf5;
  --input-bg: #ffffff;
  --row-line: #f3f4f6;
  --radius: 8px;
}

/* ---- Dark: black + orange ---- */
html[data-theme="dark"] {
  --ink: #fafaf9;
  --text: #e7e5e4;
  --muted: #a8a29e;
  --bg: #0a0a0a;
  --surface: #141414;
  --border: #2a2a2a;
  --border-strong: #3f3f46;
  --accent: #ea580c;
  --accent-2: #fb923c;
  --accent-soft: #431407;
  --accent-text: #0a0a0a;
  --danger: #fb7185;
  --danger-bg: #3f1219;
  --warn: #fdba74;
  --warn-bg: #431407;
  --ok: #86efac;
  --ok-bg: #052e16;
  --input-bg: #1c1c1c;
  --row-line: #222222;
}

html, body, [class*="css"], .stMarkdown, .stText, label {
  font-family: "IBM Plex Sans", "Segoe UI", sans-serif !important;
  color: var(--text);
}

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section.main {
  background-color: var(--bg) !important;
  color: var(--text) !important;
}

[data-testid="stHeader"] {
  background: var(--bg) !important;
}

.page-header {
  border-bottom: 1px solid var(--border);
  padding: 0.25rem 0 1rem;
  margin-bottom: 1.25rem;
}
.page-kicker {
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted) !important;
  margin-bottom: 0.35rem;
}
html[data-theme="dark"] .page-kicker {
  color: var(--accent-2) !important;
}
.page-title {
  font-family: "IBM Plex Serif", Georgia, serif !important;
  font-size: 1.85rem;
  font-weight: 700;
  color: var(--ink) !important;
  line-height: 1.2;
  margin: 0;
}
.page-sub {
  margin-top: 0.35rem;
  color: var(--muted) !important;
  font-size: 0.95rem;
  max-width: 42rem;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.75rem;
  margin: 0 0 1.5rem;
}
@media (max-width: 900px) {
  .metric-strip { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
.metric-item {
  background: var(--surface) !important;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.9rem 1rem;
}
html[data-theme="dark"] .metric-item {
  border-top: 2px solid var(--accent);
}
.metric-item .label {
  color: var(--muted) !important;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.metric-item .value {
  font-family: "IBM Plex Serif", Georgia, serif;
  font-size: 1.65rem;
  font-weight: 700;
  color: var(--ink) !important;
  margin-top: 0.25rem;
  line-height: 1.1;
}
.metric-item .hint {
  margin-top: 0.25rem;
  font-size: 0.8rem;
  color: var(--muted) !important;
}

.panel {
  background: var(--surface) !important;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.15rem;
  margin-bottom: 1rem;
  height: 100%;
}
.panel h3, .panel-title {
  font-size: 0.8rem !important;
  font-weight: 700 !important;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted) !important;
  margin: 0 0 0.75rem !important;
  font-family: "IBM Plex Sans", sans-serif !important;
}
html[data-theme="dark"] .panel-title {
  color: var(--accent-2) !important;
}
.section-title {
  font-family: "IBM Plex Serif", Georgia, serif !important;
  font-size: 1.15rem !important;
  font-weight: 700 !important;
  color: var(--ink) !important;
  margin: 1.4rem 0 0.65rem !important;
  padding-bottom: 0.4rem;
  border-bottom: 1px solid var(--border);
}

.kv { display: grid; gap: 0.45rem; }
.kv-row {
  display: grid;
  grid-template-columns: 8.5rem 1fr;
  gap: 0.5rem;
  font-size: 0.9rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--row-line);
}
.kv-row:last-child { border-bottom: none; }
.kv-key { color: var(--muted) !important; font-weight: 500; }
.kv-val { color: var(--ink) !important; font-weight: 500; word-break: break-word; }

.badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  text-transform: uppercase;
}
.badge-critique { background: var(--danger-bg) !important; color: var(--danger) !important; border: 1px solid var(--danger); }
.badge-eleve { background: var(--warn-bg) !important; color: var(--warn) !important; border: 1px solid var(--warn); }
.badge-faible { background: var(--ok-bg) !important; color: var(--ok) !important; border: 1px solid var(--ok); }
.badge-na { background: var(--border) !important; color: var(--muted) !important; border: 1px solid var(--border-strong); }

.risk-line {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin: 0.5rem 0 1rem;
  padding: 0.75rem 1rem;
  background: var(--surface) !important;
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
html[data-theme="dark"] .risk-line {
  border-left: 3px solid var(--accent);
}
.risk-score {
  font-family: "IBM Plex Serif", Georgia, serif;
  font-size: 1.5rem;
  font-weight: 700;
  color: var(--ink) !important;
}
html[data-theme="dark"] .risk-score {
  color: var(--accent-2) !important;
}
.risk-meta { color: var(--muted) !important; font-size: 0.9rem; }
.risk-meta strong { color: var(--ink) !important; }

.message-box {
  white-space: pre-wrap;
  background: #0b1220;
  color: #f3f4f6 !important;
  border-radius: var(--radius);
  padding: 1rem 1.1rem;
  font-size: 0.9rem;
  line-height: 1.55;
  border: 1px solid #1f2937;
  font-family: "IBM Plex Sans", monospace;
}
html[data-theme="dark"] .message-box {
  background: #000000 !important;
  border: 1px solid var(--accent);
  color: #fafaf9 !important;
}

.steps {
  margin: 0;
  padding-left: 1.1rem;
  color: var(--text) !important;
  font-size: 0.92rem;
  line-height: 1.55;
}
.steps li { margin-bottom: 0.35rem; color: var(--text) !important; }
.steps strong { color: var(--ink) !important; }

div[data-testid="stSidebar"],
div[data-testid="stSidebar"] > div:first-child {
  background: var(--surface) !important;
  border-right: 1px solid var(--border);
}
html[data-theme="dark"] div[data-testid="stSidebar"],
html[data-theme="dark"] div[data-testid="stSidebar"] > div:first-child {
  background: #000000 !important;
  border-right: 1px solid #2a2a2a;
}
div[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
div[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
div[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
div[data-testid="stSidebar"] label,
div[data-testid="stSidebar"] span {
  color: var(--text) !important;
}
div[data-testid="stSidebar"] .stMarkdown h1,
div[data-testid="stSidebar"] .stMarkdown h2,
div[data-testid="stSidebar"] .stMarkdown h3 {
  color: var(--ink) !important;
}
div[data-testid="stSidebar"] [data-testid="stSidebarNav"] a,
div[data-testid="stSidebar"] [data-testid="stSidebarNav"] span {
  color: var(--text) !important;
}
html[data-theme="dark"] div[data-testid="stSidebar"] [data-testid="stSidebarNav"] [aria-current="page"] {
  background: var(--accent-soft) !important;
  border-left: 3px solid var(--accent);
}

[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] p,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] label,
[data-testid="stCaptionContainer"],
label {
  color: var(--text) !important;
}
[data-testid="stMetricLabel"] * { color: var(--muted) !important; }
[data-testid="stMetricValue"] * { color: var(--ink) !important; }

.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
div[data-baseweb="select"] > div,
.stSelectbox div[data-baseweb="select"] span,
.stMultiSelect div[data-baseweb="select"] span {
  color: var(--ink) !important;
  background-color: var(--input-bg) !important;
  border-color: var(--border) !important;
}
[role="option"] {
  color: var(--ink) !important;
  background-color: var(--surface) !important;
}
html[data-theme="dark"] [role="option"]:hover,
html[data-theme="dark"] [aria-selected="true"] {
  background-color: var(--accent-soft) !important;
  color: var(--ink) !important;
}

.stButton > button {
  border-radius: 6px !important;
  font-weight: 600 !important;
  color: var(--ink) !important;
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
  background: var(--accent) !important;
  border-color: var(--accent) !important;
  color: #ffffff !important;
}
.stButton > button[kind="primary"] *,
.stButton > button[data-testid="baseButton-primary"] *,
.stButton > button[data-testid="stBaseButton-primary"] *,
.stButton > button[kind="primary"] p,
.stButton > button[data-testid="stBaseButton-primary"] p {
  color: #ffffff !important;
}
.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover *,
.stButton > button[data-testid="stBaseButton-primary"]:hover * {
  color: #ffffff !important;
}
html[data-theme="dark"] .stButton > button:hover:not([kind="primary"]):not([data-testid="stBaseButton-primary"]) {
  border-color: var(--accent) !important;
  color: var(--accent-2) !important;
}

div[data-testid="stDataFrame"] {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  background: var(--surface) !important;
}
div[data-testid="stDataFrame"] * {
  color: var(--ink) !important;
}
div[data-testid="stAlert"] {
  color: var(--ink) !important;
}
div[data-testid="stExpander"] {
  background: var(--surface) !important;
  border: 1px solid var(--border) !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary span {
  color: var(--ink) !important;
}

hr { border-color: var(--border) !important; }
"""


DARK_FORCE = """
/* Dark mode — hardcoded high contrast (black + orange) */
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stHeader"],
section.main,
.main,
.block-container {
  background-color: #0a0a0a !important;
  color: #f5f5f4 !important;
}

.page-kicker,
.page-sub {
  color: #fb923c !important;
  opacity: 1 !important;
}
div[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
div[data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {
  color: #e7e5e4 !important;
}

/* Sidebar black + readable nav labels */
section[data-testid="stSidebar"],
section[data-testid="stSidebar"] > div,
div[data-testid="stSidebar"],
div[data-testid="stSidebar"] > div,
div[data-testid="stSidebarContent"],
[data-testid="stSidebarUserContent"] {
  background-color: #000000 !important;
  background-image: none !important;
}

section[data-testid="stSidebar"] *,
div[data-testid="stSidebar"] p,
div[data-testid="stSidebar"] span,
div[data-testid="stSidebar"] label,
div[data-testid="stSidebar"] small,
div[data-testid="stSidebar"] li,
div[data-testid="stSidebar"] a,
div[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
div[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] *,
div[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
div[data-testid="stSidebar"] [data-testid="stCaptionContainer"] *,
div[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
div[data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {
  color: #f5f5f4 !important;
}

/* Page / column names in sidebar nav */
[data-testid="stSidebarNav"] a,
[data-testid="stSidebarNav"] span,
[data-testid="stSidebarNav"] p,
[data-testid="stSidebarNavLink"],
[data-testid="stSidebarNavLink"] span,
[data-testid="stSidebarNavLink"] p,
[data-testid="stSidebarNavItems"] * {
  color: #fafaf9 !important;
  opacity: 1 !important;
}
[data-testid="stSidebarNav"] [aria-current="page"],
[data-testid="stSidebarNavLink"][aria-current="page"] {
  background: #431407 !important;
  border-left: 3px solid #ea580c !important;
  color: #fb923c !important;
}
[data-testid="stSidebarNav"] a:hover {
  background: #1c1c1c !important;
  color: #fb923c !important;
}

/* Brand / captions */
div[data-testid="stSidebar"] strong,
div[data-testid="stSidebar"] b {
  color: #fb923c !important;
}
div[data-testid="stSidebar"] code {
  background: #1c1c1c !important;
  color: #fb923c !important;
}

/* Toggle label */
div[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
div[data-testid="stSidebar"] .stToggle label {
  color: #fafaf9 !important;
}

/* Main text */
[data-testid="stMarkdownContainer"],
[data-testid="stMarkdownContainer"] *,
[data-testid="stWidgetLabel"],
[data-testid="stWidgetLabel"] *,
[data-testid="stCaptionContainer"],
[data-testid="stCaptionContainer"] *,
label, .stMarkdown, .stText {
  color: #e7e5e4 !important;
}
.page-title, .section-title, .risk-score, .kv-val,
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {
  color: #fafaf9 !important;
}
.page-kicker, .panel-title {
  color: #fb923c !important;
}
.page-sub, .kv-key, .metric-item .label, .metric-item .hint,
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {
  color: #a8a29e !important;
}

.metric-item, .panel, .risk-line {
  background: #141414 !important;
  border-color: #2a2a2a !important;
  color: #f5f5f4 !important;
}
.metric-item { border-top: 2px solid #ea580c !important; }
.risk-line { border-left: 3px solid #ea580c !important; }
.risk-score { color: #fb923c !important; }

/* Inputs */
.stTextInput input, .stNumberInput input, .stTextArea textarea,
div[data-baseweb="select"] > div,
.stSelectbox div[data-baseweb="select"] span,
.stMultiSelect div[data-baseweb="select"] span {
  background-color: #1c1c1c !important;
  color: #fafaf9 !important;
  border-color: #3f3f46 !important;
}
[role="option"] {
  background-color: #1c1c1c !important;
  color: #fafaf9 !important;
}

/* Buttons */
.stButton > button {
  background: #1c1c1c !important;
  color: #fafaf9 !important;
  border: 1px solid #3f3f46 !important;
}
.stButton > button[kind="primary"],
.stButton > button[data-testid="baseButton-primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
  background: #ea580c !important;
  border-color: #ea580c !important;
  color: #ffffff !important;
}
.stButton > button[kind="primary"] *,
.stButton > button[data-testid="baseButton-primary"] *,
.stButton > button[data-testid="stBaseButton-primary"] * {
  color: #ffffff !important;
}
div[data-testid="stSidebar"] .stButton > button {
  background: #ea580c !important;
  color: #ffffff !important;
  border-color: #c2410c !important;
}

/* Dataframe / column names */
div[data-testid="stDataFrame"],
div[data-testid="stDataFrameResizable"],
div[data-testid="stTable"] {
  background: #141414 !important;
  border: 1px solid #2a2a2a !important;
}
div[data-testid="stDataFrame"] *,
div[data-testid="stDataFrameResizable"] *,
div[data-testid="stTable"] * {
  color: #f5f5f4 !important;
  opacity: 1 !important;
}
div[data-testid="stDataFrame"] th,
div[data-testid="stDataFrame"] [role="columnheader"],
div[data-testid="stDataFrameResizable"] th,
div[data-testid="stDataFrameResizable"] [role="columnheader"],
div[data-testid="stTable"] th,
[data-testid="stDataFrame"] thead *,
[data-testid="stDataFrame"] [class*="header"] {
  color: #fb923c !important;
  background-color: #1c1c1c !important;
  font-weight: 700 !important;
  opacity: 1 !important;
}

div[data-testid="stAlert"] { color: #f5f5f4 !important; }
[data-testid="stExpander"] {
  background: #141414 !important;
  border: 1px solid #2a2a2a !important;
}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary * {
  color: #fafaf9 !important;
}
hr { border-color: #2a2a2a !important; }
.message-box {
  background: #000000 !important;
  border: 1px solid #ea580c !important;
  color: #fafaf9 !important;
}
"""


def _ensure_theme_state() -> str:
    if "ui_theme" not in st.session_state:
        st.session_state["ui_theme"] = "light"
    theme = st.session_state["ui_theme"]
    if theme not in {"light", "dark"}:
        theme = "light"
        st.session_state["ui_theme"] = theme
    return theme


def inject_css(theme: str | None = None) -> None:
    theme = theme or _ensure_theme_state()
    css = APP_CSS if theme != "dark" else APP_CSS + DARK_FORCE
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
    if theme == "dark":
        import streamlit.components.v1 as components

        safe = DARK_FORCE.replace("\\", "\\\\").replace("`", "\\`").replace("</script>", "<\\/script>")
        components.html(
            f"""
            <script>
            (function() {{
              const doc = window.parent.document;
              let el = doc.getElementById('twin-dark-force');
              if (!el) {{
                el = doc.createElement('style');
                el.id = 'twin-dark-force';
                doc.head.appendChild(el);
              }}
              el.textContent = `{safe}`;
              doc.documentElement.setAttribute('data-theme', 'dark');
            }})();
            </script>
            """,
            height=0,
        )
    else:
        import streamlit.components.v1 as components

        components.html(
            """
            <script>
            (function() {
              const doc = window.parent.document;
              if (window.parent.__twinDarkObs) {
                window.parent.__twinDarkObs.disconnect();
                window.parent.__twinDarkObs = null;
              }
              const el = doc.getElementById('twin-dark-force');
              if (el) el.remove();
              doc.documentElement.setAttribute('data-theme', 'light');
            })();
            </script>
            """,
            height=0,
        )


def page_setup(title: str, subtitle: str | None = None, *, kicker: str = "Digital Twin Churn") -> None:
    st.set_page_config(
        page_title=f"{title} · Twin Churn",
        page_icon="▣",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    from interface.auth import require_login, sidebar_workspace_meta

    theme = _ensure_theme_state()
    inject_css(theme)
    require_login()
    with st.sidebar:
        sidebar_workspace_meta()
        dark = st.toggle(
            "Mode sombre",
            value=(theme == "dark"),
            help="Noir + accent orange",
        )
        new_theme = "dark" if dark else "light"
        if new_theme != theme:
            st.session_state["ui_theme"] = new_theme
            st.rerun()

    sub = f'<div class="page-sub">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f"""
<div class="page-header">
  <div class="page-kicker">{html.escape(kicker)}</div>
  <h1 class="page-title">{html.escape(title)}</h1>
  {sub}
</div>
""",
        unsafe_allow_html=True,
    )


def badge_html(band: str) -> str:
    key = {"critique": "critique", "élevé": "eleve", "faible": "faible"}.get(band, "na")
    return f'<span class="badge badge-{key}">{html.escape(band)}</span>'


def kv_html(rows: list[tuple[str, object]]) -> str:
    parts = ['<div class="kv">']
    for key, value in rows:
        if value is None or value == "" or value == []:
            shown = "—"
        elif isinstance(value, float):
            shown = f"{value:.3f}"
        elif isinstance(value, list):
            shown = ", ".join(str(v) for v in value) if value else "—"
        else:
            shown = str(value)
        parts.append(
            "<div class='kv-row'>"
            f"<div class='kv-key'>{html.escape(key)}</div>"
            f"<div class='kv-val'>{html.escape(shown)}</div>"
            "</div>"
        )
    parts.append("</div>")
    return "".join(parts)


def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)

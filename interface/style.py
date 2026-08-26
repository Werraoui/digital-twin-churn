"""Shared Streamlit look & feel."""

from __future__ import annotations

import streamlit as st

APP_CSS = """
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');

:root {
  --ink: #0f1c1a;
  --muted: #5c6f6a;
  --paper: #f3f6f4;
  --card: #ffffff;
  --line: #d5e0db;
  --accent: #0f766e;
  --accent-soft: #ccfbf1;
  --warn: #b45309;
  --danger: #b91c1c;
  --ok: #047857;
}

html, body, [class*="css"] {
  font-family: "DM Sans", sans-serif;
  color: var(--ink);
}

.stApp {
  background:
    radial-gradient(1200px 500px at 10% -10%, #d9f3ec 0%, transparent 55%),
    radial-gradient(900px 400px at 100% 0%, #e8eef5 0%, transparent 50%),
    var(--paper);
}

h1, h2, h3, .brand-title {
  font-family: "Fraunces", Georgia, serif !important;
  letter-spacing: -0.02em;
}

.brand-title {
  font-size: 2.4rem;
  margin-bottom: 0.15rem;
}

.brand-sub {
  color: var(--muted);
  font-size: 1.05rem;
  margin-bottom: 1.5rem;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.85rem;
  margin: 1rem 0 1.5rem;
}

.metric-item {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 1rem 1.1rem;
}

.metric-item .label {
  color: var(--muted);
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.metric-item .value {
  font-family: "Fraunces", Georgia, serif;
  font-size: 1.8rem;
  margin-top: 0.2rem;
}

.badge {
  display: inline-block;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
}

.badge-critique { background: #fee2e2; color: var(--danger); }
.badge-eleve { background: #ffedd5; color: var(--warn); }
.badge-faible { background: #d1fae5; color: var(--ok); }
.badge-na { background: #e5e7eb; color: #4b5563; }

.panel {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1.1rem 1.25rem;
  margin-bottom: 1rem;
}

.message-box {
  white-space: pre-wrap;
  background: #0f1c1a;
  color: #ecfdf5;
  border-radius: 14px;
  padding: 1rem 1.15rem;
  font-size: 0.95rem;
  line-height: 1.5;
}

div[data-testid="stSidebar"] {
  background: #0f1c1a;
}

div[data-testid="stSidebar"] * {
  color: #e7f5f1 !important;
}
"""


def inject_css() -> None:
    st.markdown(f"<style>{APP_CSS}</style>", unsafe_allow_html=True)


def page_setup(title: str, subtitle: str | None = None) -> None:
    st.set_page_config(
        page_title=f"{title} · Twin Churn",
        page_icon="◎",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_css()
    st.markdown(f'<div class="brand-title">{title}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="brand-sub">{subtitle}</div>', unsafe_allow_html=True)


def badge_html(band: str) -> str:
    key = {
        "critique": "critique",
        "élevé": "eleve",
        "faible": "faible",
    }.get(band, "na")
    return f'<span class="badge badge-{key}">{band}</span>'

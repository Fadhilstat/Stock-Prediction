"""Shared visual language for the Ruang Risiko IDX Streamlit pages."""

from __future__ import annotations

from html import escape

import streamlit as st

APP_CSS = """
<style>
:root {
    --rr-ink: #172033;
    --rr-muted: #64748B;
    --rr-border: #E2E8F0;
    --rr-surface: #FFFFFF;
    --rr-soft: #F8FAFC;
    --rr-accent: #1F4E79;
    --rr-risk: #9F3A46;
}

.block-container {
    max-width: 1180px;
    padding-top: 2.15rem;
    padding-bottom: 3.5rem;
}

h1, h2, h3, h4 {
    color: var(--rr-ink);
    letter-spacing: -0.018em;
}

h1 {
    line-height: 1.08;
}

p, li {
    line-height: 1.65;
}

[data-testid="stSidebar"] {
    border-right: 1px solid var(--rr-border);
}

[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
    color: #475569;
}

[data-testid="stMetric"] {
    background: var(--rr-surface);
    border: 1px solid var(--rr-border);
    border-radius: 14px;
    padding: 0.9rem 1rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
}

[data-testid="stMetricLabel"] {
    color: var(--rr-muted);
}

[data-testid="stMetricValue"] {
    color: var(--rr-ink);
    letter-spacing: -0.025em;
}

[data-testid="stTabs"] [data-baseweb="tab-list"] {
    gap: 0.2rem;
    border-bottom: 1px solid var(--rr-border);
}

[data-testid="stTabs"] button {
    border-radius: 8px 8px 0 0;
    padding-left: 0.8rem;
    padding-right: 0.8rem;
}

[data-testid="stDataFrame"] {
    border: 1px solid var(--rr-border);
    border-radius: 12px;
    overflow: hidden;
}

[data-testid="stAlert"] {
    border-radius: 12px;
}

[data-testid="stExpander"] {
    border: 1px solid var(--rr-border);
    border-radius: 12px;
    background: var(--rr-surface);
}

.rr-hero {
    background: var(--rr-surface);
    border: 1px solid var(--rr-border);
    border-radius: 18px;
    padding: 1.45rem 1.55rem 1.35rem 1.55rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.035);
}

.rr-eyebrow {
    color: var(--rr-accent);
    font-size: 0.76rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    margin-bottom: 0.45rem;
}

.rr-hero-title {
    color: var(--rr-ink);
    font-size: clamp(1.85rem, 4vw, 2.55rem);
    font-weight: 720;
    letter-spacing: -0.035em;
    line-height: 1.08;
    margin: 0;
}

.rr-hero-subtitle {
    color: #475569;
    font-size: 1rem;
    line-height: 1.65;
    max-width: 820px;
    margin-top: 0.7rem;
    margin-bottom: 0;
}

.rr-hero-meta {
    color: var(--rr-muted);
    font-size: 0.82rem;
    margin-top: 0.8rem;
}

.rr-note {
    background: var(--rr-soft);
    border: 1px solid var(--rr-border);
    border-radius: 12px;
    padding: 0.9rem 1rem;
    margin: 0.45rem 0 1rem 0;
    color: #334155;
    line-height: 1.6;
}

.rr-kicker {
    color: var(--rr-muted);
    font-size: 0.78rem;
    font-weight: 650;
    letter-spacing: 0.055em;
    text-transform: uppercase;
    margin-bottom: 0.25rem;
}

.rr-state {
    display: inline-block;
    color: var(--rr-accent);
    background: #EEF4FA;
    border: 1px solid #D8E5F1;
    border-radius: 999px;
    font-size: 0.76rem;
    font-weight: 650;
    padding: 0.22rem 0.55rem;
    margin-bottom: 0.55rem;
}

@media (max-width: 768px) {
    .block-container {
        padding-top: 1.15rem;
        padding-left: 1rem;
        padding-right: 1rem;
    }

    .rr-hero {
        border-radius: 14px;
        padding: 1.15rem;
    }

    [data-testid="stMetric"] {
        padding: 0.8rem;
    }

    [data-testid="stTabs"] button {
        padding-left: 0.55rem;
        padding-right: 0.55rem;
        font-size: 0.82rem;
    }
}
</style>
"""


def apply_app_styles() -> None:
    """Apply the shared visual language once per Streamlit page."""

    st.markdown(APP_CSS, unsafe_allow_html=True)


def render_hero(
    title: str,
    subtitle: str,
    *,
    eyebrow: str,
    meta: str | None = None,
) -> None:
    """Render a restrained page header with one clear visual hierarchy."""

    safe_title = escape(title)
    safe_subtitle = escape(subtitle)
    safe_eyebrow = escape(eyebrow)
    meta_html = ""
    if meta:
        meta_html = f'<div class="rr-hero-meta">{escape(meta)}</div>'

    st.markdown(
        (
            '<section class="rr-hero">'
            f'<div class="rr-eyebrow">{safe_eyebrow}</div>'
            f'<h1 class="rr-hero-title">{safe_title}</h1>'
            f'<p class="rr-hero-subtitle">{safe_subtitle}</p>'
            f"{meta_html}"
            "</section>"
        ),
        unsafe_allow_html=True,
    )


def render_state_label(state: str) -> None:
    """Render a compact state label for one analyst role."""

    st.markdown(
        f'<span class="rr-state">{escape(state)}</span>',
        unsafe_allow_html=True,
    )

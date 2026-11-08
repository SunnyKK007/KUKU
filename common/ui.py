"""Shared look and small components for the three web apps."""
from __future__ import annotations

import base64
import html
import os
import pathlib

import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root {
  --ink: #18181B; --ink2: #52525B; --ink3: #71717A; --line: #E4E4E7; --line2: #D4D4D8;
  --bg: #FAFAF9; --card: #FFFFFF; --soft: #F4F4F5; --accent: #27272A;
}
html, body, [class*="css"], .stMarkdown, button, input, textarea, label, select { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: var(--bg); }
.block-container { max-width: 1120px; padding-top: 2.2rem; padding-bottom: 4rem; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stDeployButton"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"], #MainMenu, footer,
[data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] { display: flex !important; visibility: visible !important; }
h1, h2, h3 { letter-spacing: -0.01em; color: var(--ink); }
p, li { color: var(--ink2); line-height: 1.65; }
a { color: var(--ink); text-decoration: underline; text-underline-offset: 3px; text-decoration-color: var(--line2); }
a:hover { text-decoration-color: var(--ink); }

/* hero: the one dark block on the page */
.hero { background: #18181B; border-radius: 18px; padding: 32px 36px; margin-bottom: 24px; display: flex; gap: 22px;
        align-items: flex-start; box-shadow: 0 10px 30px -12px rgba(24,24,27,.35); }
.hero-mark img { box-shadow: 0 0 0 1px #3F3F46; }
.hero-mark { flex: 0 0 auto; padding-top: 4px; }
.hero .eyebrow { font-size: 12px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: #A1A1AA; margin-bottom: 10px; }
.hero h1 { font-size: 34px; font-weight: 700; line-height: 1.15; margin: 0 0 10px 0; color: #FAFAFA; }
.hero p { font-size: 16.5px; color: #D4D4D8; margin: 0; max-width: 700px; }
.brand { display: flex; align-items: center; gap: 12px; margin: 4px 0 6px 0; }
.brand-name { font-size: 17px; font-weight: 700; color: var(--ink); line-height: 1.2; }
.brand-tag { font-size: 12.5px; color: var(--ink3); margin-top: 2px; }

/* section cards */
div[data-testid="stVerticalBlockBorderWrapper"] { background: var(--card); border-color: var(--line) !important; border-radius: 16px !important;
        box-shadow: 0 1px 2px rgba(24,24,27,.03); padding: 8px 12px; }
.step { font-size: 11.5px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--ink3); margin: 2px 0 2px 0; }
.sec-title { font-size: 19px; font-weight: 650; color: var(--ink); margin: 0 0 4px 0; }
.sec-sub { font-size: 14px; color: var(--ink3); margin: 0 0 14px 0; }
.muted { color: var(--ink3); font-size: 13.5px; }
.field-label { font-size: 13.5px; font-weight: 500; color: var(--ink); margin: 14px 0 6px 0; }
.spacer { height: var(--h, 16px); }

/* stat cards */
.stats { display: grid; grid-template-columns: repeat(var(--n, 5), 1fr); gap: 14px; margin: 4px 0 18px 0; }
.stat { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; }
.stat .label { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; color: var(--ink3);
               text-transform: uppercase; letter-spacing: .06em; }
.stat .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
.stat .value { font-size: 30px; font-weight: 700; color: var(--ink); line-height: 1.2; margin-top: 6px; font-variant-numeric: tabular-nums; }
.stat .hint { font-size: 12.5px; color: var(--ink3); margin-top: 2px; }

/* badges and callouts */
.badge { display: inline-block; border-radius: 999px; padding: 3px 11px; font-size: 12px; font-weight: 600; background: var(--bg2); color: var(--c); }
.tag { display: inline-block; border-radius: 6px; padding: 3px 9px; font-size: 12px; font-weight: 500; background: var(--soft); color: var(--ink2); margin-left: 6px; }
.callout { border-left: 3px solid var(--c); background: var(--bg2); border-radius: 8px; padding: 12px 16px; margin: 10px 0 16px 0;
           font-size: 14.5px; color: var(--ink); line-height: 1.55; }
.callout b { color: var(--ink); }

/* buttons */
.stButton > button[kind="primary"] { border-radius: 12px; height: 48px; font-weight: 600; font-size: 15px;
        background: var(--accent); border: 1px solid var(--accent); box-shadow: 0 6px 16px -8px rgba(24,24,27,.5); }
.stButton > button[kind="primary"]:hover { background: #3F3F46; border-color: #3F3F46; }
.stButton > button[kind="primary"] p, .stButton > button[kind="primary"] span, .stButton > button[kind="primary"] div { color: #FFFFFF !important; font-weight: 600; }
.stButton > button[kind="primary"]:disabled { background: #E4E4E7; border-color: #E4E4E7; box-shadow: none; }
.stButton > button[kind="primary"]:disabled p { color: #A1A1AA !important; }
.stDownloadButton > button { border-radius: 10px; height: 44px; font-weight: 500; font-size: 14.5px;
        background: var(--card); border: 1px solid var(--line); color: var(--ink); }
.stDownloadButton > button:hover { border-color: var(--line2); background: var(--soft); color: var(--ink); }
div[data-baseweb="input"], div[data-baseweb="select"] > div, textarea { border-radius: 10px !important; }
label[data-testid="stWidgetLabel"] p { font-size: 13.5px; font-weight: 500; color: var(--ink); }

/* tabs */
button[data-baseweb="tab"] { font-size: 15px; font-weight: 500; padding: 10px 4px; margin-right: 22px; color: var(--ink3); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--ink); font-weight: 600; }
div[data-baseweb="tab-highlight"] { background: var(--ink); height: 2px; }
div[data-baseweb="tab-border"] { background: var(--line); }

/* segmented control */
div[data-testid="stButtonGroup"] { background: var(--soft); border-radius: 12px; padding: 4px; gap: 2px; width: fit-content; max-width: 100%; flex-wrap: wrap; }
div[data-testid="stButtonGroup"] button { border: 0 !important; background: transparent; border-radius: 9px; padding: 7px 16px; font-weight: 500;
        font-size: 14px; color: var(--ink3); }
div[data-testid="stButtonGroup"] button:hover { color: var(--ink); background: rgba(255,255,255,.7); }
div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] { background: var(--card); color: var(--ink);
        font-weight: 600; box-shadow: 0 1px 3px rgba(24,24,27,.12); }

/* expanders */
div[data-testid="stExpander"] { background: var(--card); border: 1px solid var(--line); border-radius: 12px; margin-bottom: 8px; }
div[data-testid="stExpander"]:hover { border-color: var(--line2); }
div[data-testid="stExpander"] details { border: 0; }
div[data-testid="stExpander"] summary p { font-weight: 500; font-size: 14.5px; color: #3F3F46; }

/* option cards (radio shown as large tiles) */
[class*="st-key-cardpick"] div[role="radiogroup"] { display: grid; gap: 14px; width: 100%; grid-auto-rows: 1fr; }
[class*="st-key-cardpick3"] div[role="radiogroup"] { grid-template-columns: repeat(3, 1fr); }
[class*="st-key-cardpick2"] div[role="radiogroup"] { grid-template-columns: repeat(2, 1fr); }
[class*="st-key-cardpick"] label { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 18px 20px;
        min-height: 92px; cursor: pointer; transition: all .15s ease; align-items: flex-start; margin: 0; width: 100%; }
[class*="st-key-cardpick"] label:hover { border-color: var(--line2); background: #FCFCFC; }
[class*="st-key-cardpick"] label:has(input:checked) { border-color: #A1A1AA; background: var(--soft); }
[class*="st-key-cardpick"] label p { font-size: 14.5px; line-height: 1.5; color: var(--ink3); }
[class*="st-key-cardpick"] label p strong { font-size: 16.5px; color: var(--ink); font-weight: 600; }
@media (max-width: 820px) {
  [class*="st-key-cardpick"] div[role="radiogroup"] { grid-template-columns: 1fr !important; }
  .stats { grid-template-columns: repeat(2, 1fr); }
  .hero h1 { font-size: 27px; }
}

/* legend cards */
.sev-legend { background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; margin: 6px 0 4px 0; }
.sev-row { display: flex; gap: 12px; padding: 11px 14px; border-bottom: 1px solid var(--line); }
.sev-row:last-child { border-bottom: 0; }
.sev-bar { flex: 0 0 3px; border-radius: 3px; background: var(--c); }
.sev-name { font-size: 13.5px; font-weight: 600; color: var(--c); line-height: 1.3; }
.sev-desc { font-size: 12.5px; color: var(--ink3); line-height: 1.45; margin-top: 2px; }
.side-title { font-size: 11.5px; font-weight: 600; letter-spacing: .1em; text-transform: uppercase; color: var(--ink3); margin: 6px 0 8px 0; }

/* sidebar */
section[data-testid="stSidebar"] { background: var(--card); border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] h3 { font-size: 18px; font-weight: 650; }
</style>
"""

TONES = {
    "info": ("#52525B", "#F4F4F5"),
    "ok": ("#047857", "#ECFDF5"),
    "warn": ("#B45309", "#FFFBEB"),
    "bad": ("#B91C1C", "#FEF2F2"),
    "neutral": ("#475569", "#F1F5F9"),
}


ASSETS = pathlib.Path(__file__).resolve().parent / "assets"


def logo_path(name: str) -> str:
    return str(ASSETS / f"logo_{name}.png")


def _logo_img(name: str, size: int) -> str:
    data = base64.b64encode((ASSETS / f"logo_{name}.png").read_bytes()).decode()
    return f'<img src="data:image/png;base64,{data}" width="{size}" height="{size}" style="border-radius:{size // 4}px" alt="">'


def brand(name: str, logo: str, tagline: str) -> None:
    """Logo and app name at the top of the sidebar."""
    st.markdown(f'<div class="brand">{_logo_img(logo, 40)}<div><div class="brand-name">{html.escape(name)}</div>'
                f'<div class="brand-tag">{html.escape(tagline)}</div></div></div>', unsafe_allow_html=True)


def apply_theme() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(eyebrow: str, title: str, subtitle: str, logo: str | None = None) -> None:
    mark = f'<div class="hero-mark">{_logo_img(logo, 56)}</div>' if logo else ""
    st.markdown(f'<div class="hero">{mark}<div><div class="eyebrow">{html.escape(eyebrow)}</div>'
                f'<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div></div>', unsafe_allow_html=True)


def section(step: str, title: str, subtitle: str = "") -> None:
    sub = f'<p class="sec-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<div class="step">{html.escape(step)}</div><p class="sec-title">{html.escape(title)}</p>{sub}',
                unsafe_allow_html=True)


def stat_cards(items) -> None:
    """items: list of (label, value, color, hint)."""
    cards = "".join(
        f'<div class="stat" style="--c:{c}"><div class="label"><span class="dot"></span>{html.escape(str(l))}</div>'
        f'<div class="value">{v}</div><div class="hint">{html.escape(str(h))}</div></div>' for l, v, c, h in items)
    st.markdown(f'<div class="stats" style="--n:{len(items)}">{cards}</div>', unsafe_allow_html=True)


def badge(text: str, color: str, bg: str) -> str:
    return f'<span class="badge" style="--c:{color};--bg2:{bg}">{html.escape(text)}</span>'


def callout(text: str, tone: str = "info") -> None:
    c, bg = TONES[tone]
    st.markdown(f'<div class="callout" style="--c:{c};--bg2:{bg}">{text}</div>', unsafe_allow_html=True)


def card_choice(key: str, options: dict, columns: int):
    """Radio rendered as large selectable tiles. options maps value -> markdown label."""
    with st.container(key=f"cardpick{columns}_{key}"):
        return st.radio(key, list(options), format_func=options.get, label_visibility="collapsed")


def spacer(px: int = 16) -> None:
    st.markdown(f'<div class="spacer" style="--h:{px}px"></div>', unsafe_allow_html=True)


MODELS = {
    "gemini": ("Google Gemini", "GEMINI_API_KEY", "https://aistudio.google.com/apikey",
               ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3-flash-preview"]),
    "groq": ("Groq", "GROQ_API_KEY", "https://console.groq.com/keys",
             ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]),
    "anthropic": ("Anthropic Claude", "ANTHROPIC_API_KEY", "https://console.anthropic.com/settings/keys",
                  ["claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-5-5"]),
    "openai": ("OpenAI", "OPENAI_API_KEY", "https://platform.openai.com/api-keys", ["gpt-4o-mini", "gpt-4o"]),
    "openrouter": ("OpenRouter", "OPENROUTER_API_KEY", "https://openrouter.ai/keys",
                   ["meta-llama/llama-3.3-70b-instruct:free", "mistralai/mistral-7b-instruct:free"]),
    "ollama": ("Ollama (runs on your computer)", None, "https://ollama.com", ["llama3.1:8b", "qwen2.5:7b"]),
}


def _saved_key(key_env: str | None) -> str | None:
    """A key already set on this computer (.env) or in Streamlit secrets."""
    if not key_env:
        return None
    if os.environ.get(key_env):
        return os.environ[key_env]
    try:
        v = st.secrets.get(key_env)
        return v if isinstance(v, str) and v else None
    except Exception:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_models(provider: str, key_fingerprint: str, _api_key: str | None) -> list[str]:
    """Live model list, cached for an hour. The key itself is never part of the cache key."""
    from common.llm import list_models
    return list_models(provider, _api_key)


def model_picker(prefix: str, inline: bool = True):
    """Provider and model as two dropdowns side by side, then the API key.
    Returns (spec, api_key, ready). The key stays in this browser session only and is never written anywhere."""
    import hashlib
    c1, c2 = st.columns([1, 1.5]) if inline else (st.container(), st.container())
    with c1:
        prov = st.selectbox("AI provider", list(MODELS), format_func=lambda k: MODELS[k][0], key=f"{prefix}_prov")
    label, key_env, key_url, curated = MODELS[prov]
    key_widget = f"{prefix}_key_{prov}"
    saved = _saved_key(key_env)
    key = st.session_state.get(key_widget) or saved if key_env else None

    models = list(curated)
    if key or not key_env:
        try:
            fetched = _fetch_models(prov, hashlib.sha256((key or "").encode()).hexdigest()[:16], key)
            if fetched:
                models = [m for m in curated if m in fetched] + [m for m in fetched if m not in curated]
        except Exception:
            pass
    with c2:
        chosen = st.selectbox(
            "Model", models, index=0, key=f"{prefix}_m_{prov}_{len(models)}",
            format_func=lambda m: m + ("  (recommended)" if m == curated[0] else ""),
            help="Click to open the list, then scroll or type to find a model. If it runs out of free quota, "
                 "the recommended ones are tried next.")

    ready = True
    if key_env:
        st.text_input(f"{label} API key", type="password", key=key_widget,
                      placeholder="Paste your API key here" if not saved else "Saved on this computer. Paste a different key to replace it.",
                      help="Used only while this page is open. It is never saved.")
        st.markdown(f'<p class="muted">Used only for this session and sent only to {html.escape(label)}. '
                    f'<a href="{key_url}" target="_blank">Get a free key</a></p>', unsafe_allow_html=True)
        key = st.session_state.get(key_widget) or saved
        if not key:
            callout("Paste your API key to run the full check.", "warn")
            ready = False

    backups = [m for m in curated if m != chosen and m in models]
    return f"{prov}:{','.join([chosen] + backups)}", key, ready


def legend(title: str, rows) -> None:
    """A titled card of rows. rows: iterable of (name, color, description)."""
    body = "".join(f'<div class="sev-row" style="--c:{c}"><span class="sev-bar"></span><div>'
                   f'<div class="sev-name">{html.escape(n)}</div><div class="sev-desc">{html.escape(d)}</div></div></div>'
                   for n, c, d in rows)
    st.markdown(f'<div class="side-title">{html.escape(title)}</div><div class="sev-legend">{body}</div>', unsafe_allow_html=True)


def severity_legend(levels) -> None:
    legend("Severity levels", levels)


def side_title(text: str) -> None:
    st.markdown(f'<div class="side-title">{html.escape(text)}</div>', unsafe_allow_html=True)

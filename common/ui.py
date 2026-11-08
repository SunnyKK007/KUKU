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
  --ink: #0F172A; --ink2: #475569; --ink3: #64748B; --line: #E2E8F0; --bg: #F8FAFC; --card: #FFFFFF;
  --accent: #4338CA; --accent-soft: #EEF2FF; --accent-line: #C7D2FE;
}
html, body, [class*="css"], .stMarkdown, button, input, textarea, label, select { font-family: 'Inter', system-ui, sans-serif; }
.stApp { background: var(--bg); }
.block-container { max-width: 1120px; padding-top: 2.2rem; padding-bottom: 4rem; }
header[data-testid="stHeader"] { background: transparent; }
[data-testid="stDeployButton"], [data-testid="stAppDeployButton"], [data-testid="stMainMenu"], #MainMenu, footer, [data-testid="stStatusWidget"] { display: none !important; }
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapsedControl"] { display: flex !important; visibility: visible !important; }
h1, h2, h3 { letter-spacing: -0.01em; color: var(--ink); }
p, li { color: var(--ink2); line-height: 1.65; }
a { color: var(--accent); }

/* hero */
.hero { background: var(--card); border: 1px solid var(--line); border-radius: 16px; padding: 30px 34px; margin-bottom: 22px;
        box-shadow: 0 1px 2px rgba(15,23,42,.04); display: flex; gap: 22px; align-items: flex-start; }
.hero-mark { flex: 0 0 auto; padding-top: 4px; }
.brand { display: flex; align-items: center; gap: 12px; margin: 4px 0 6px 0; }
.brand-name { font-size: 17px; font-weight: 700; color: var(--ink); line-height: 1.2; }
.brand-tag { font-size: 12.5px; color: var(--ink3); margin-top: 2px; }
.hero .eyebrow { font-size: 12px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); margin-bottom: 10px; }
.hero h1 { font-size: 34px; font-weight: 700; line-height: 1.15; margin: 0 0 10px 0; }
.hero p { font-size: 16.5px; color: var(--ink2); margin: 0; max-width: 700px; }

/* section cards */
div[data-testid="stVerticalBlockBorderWrapper"] { background: var(--card); border-color: var(--line) !important; border-radius: 14px !important;
        box-shadow: 0 1px 2px rgba(15,23,42,.04); padding: 6px 10px; }
.step { font-size: 11.5px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--accent); margin: 2px 0 2px 0; }
.sec-title { font-size: 19px; font-weight: 650; color: var(--ink); margin: 0 0 4px 0; }
.sec-sub { font-size: 14px; color: var(--ink3); margin: 0 0 14px 0; }
.muted { color: var(--ink3); font-size: 13.5px; }

/* stat cards */
.stats { display: grid; grid-template-columns: repeat(var(--n, 5), 1fr); gap: 14px; margin: 4px 0 18px 0; }
.stat { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 16px 18px; }
.stat .label { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 600; color: var(--ink3);
               text-transform: uppercase; letter-spacing: .06em; }
.stat .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
.stat .value { font-size: 32px; font-weight: 700; color: var(--ink); line-height: 1.2; margin-top: 6px; font-variant-numeric: tabular-nums; }
.stat .hint { font-size: 12.5px; color: var(--ink3); margin-top: 2px; }

/* badges and callouts */
.badge { display: inline-block; border-radius: 999px; padding: 3px 11px; font-size: 12px; font-weight: 600; background: var(--bg2); color: var(--c); }
.tag { display: inline-block; border-radius: 6px; padding: 3px 9px; font-size: 12px; font-weight: 500; background: #F1F5F9; color: #334155; margin-left: 6px; }
.callout { border-left: 3px solid var(--c); background: var(--bg2); border-radius: 8px; padding: 12px 16px; margin: 10px 0 16px 0;
           font-size: 14.5px; color: var(--ink); line-height: 1.55; }
.callout b { color: var(--ink); }

/* controls */
.stButton > button[kind="primary"], .stDownloadButton > button { border-radius: 10px; height: 46px; font-weight: 600; font-size: 15px; }
.stButton > button[kind="primary"] { background: var(--accent); border: 1px solid var(--accent); }
.stButton > button[kind="primary"]:hover { background: #3730A3; border-color: #3730A3; }
.stButton > button[kind="primary"] p, .stButton > button[kind="primary"] span, .stButton > button[kind="primary"] div { color: #FFFFFF !important; font-weight: 600; }
.stButton > button[kind="primary"]:disabled { background: #CBD5E1; border-color: #CBD5E1; }
.stButton > button[kind="primary"]:disabled p { color: #F8FAFC !important; }
.spacer { height: var(--h, 16px); }
.stDownloadButton > button { background: var(--card); border: 1px solid var(--line); color: var(--ink); }
.stDownloadButton > button:hover { border-color: var(--accent-line); color: var(--accent); }
div[data-baseweb="input"], div[data-baseweb="select"] > div, textarea { border-radius: 10px !important; }
.field-label { font-size: 13.5px; font-weight: 500; color: var(--ink); margin: 14px 0 6px 0; }
label[data-testid="stWidgetLabel"] p { font-size: 13.5px; font-weight: 500; color: var(--ink); }

/* tabs */
button[data-baseweb="tab"] { font-size: 15px; font-weight: 500; padding: 10px 4px; margin-right: 22px; color: var(--ink3); }
button[data-baseweb="tab"][aria-selected="true"] { color: var(--accent); font-weight: 600; }
div[data-baseweb="tab-highlight"] { background: var(--accent); height: 3px; }
div[data-baseweb="tab-border"] { background: var(--line); }

/* segmented control */
div[data-testid="stButtonGroup"] { background: #EEF2F7; border-radius: 12px; padding: 4px; gap: 2px; width: fit-content; max-width: 100%; flex-wrap: wrap; }
div[data-testid="stButtonGroup"] button { border: 0 !important; background: transparent; border-radius: 9px; padding: 7px 16px; font-weight: 500;
        font-size: 14px; color: var(--ink2); }
div[data-testid="stButtonGroup"] button:hover { color: var(--ink); background: rgba(255,255,255,.6); }
div[data-testid="stButtonGroup"] button[data-testid="stBaseButton-segmented_controlActive"] { background: var(--card); color: var(--accent);
        font-weight: 600; box-shadow: 0 1px 3px rgba(15,23,42,.12); }

/* expanders */
div[data-testid="stExpander"] { background: var(--card); border: 1px solid var(--line); border-radius: 12px; margin-bottom: 8px; }
div[data-testid="stExpander"] details { border: 0; }
div[data-testid="stExpander"] summary p { font-weight: 500; font-size: 15px; color: var(--ink); }

/* option cards (radio shown as large tiles) */
[class*="st-key-cardpick"] div[role="radiogroup"] { display: grid; gap: 14px; width: 100%; grid-auto-rows: 1fr; }
[class*="st-key-cardpick3"] div[role="radiogroup"] { grid-template-columns: repeat(3, 1fr); }
[class*="st-key-cardpick2"] div[role="radiogroup"] { grid-template-columns: repeat(2, 1fr); }
[class*="st-key-cardpick"] label { background: var(--card); border: 1.5px solid var(--line); border-radius: 14px; padding: 18px 20px;
        min-height: 92px; cursor: pointer; transition: all .15s ease; align-items: flex-start; margin: 0; width: 100%; }
[class*="st-key-cardpick"] label:hover { border-color: var(--accent-line); background: #FAFAFF; }
[class*="st-key-cardpick"] label:has(input:checked) { border-color: var(--accent); background: var(--accent-soft); box-shadow: 0 0 0 3px rgba(67,56,202,.12); }
[class*="st-key-cardpick"] label p { font-size: 14.5px; line-height: 1.5; color: var(--ink3); }
[class*="st-key-cardpick"] label p strong { font-size: 17px; color: var(--ink); font-weight: 650; }
@media (max-width: 820px) {
  [class*="st-key-cardpick"] div[role="radiogroup"] { grid-template-columns: 1fr !important; }
  .stats { grid-template-columns: repeat(2, 1fr); }
  .hero h1 { font-size: 27px; }
}

/* sidebar */
section[data-testid="stSidebar"] { background: var(--card); border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] h3 { font-size: 18px; font-weight: 650; }
</style>
"""

TONES = {
    "info": ("#1D4ED8", "#EFF6FF"),
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

"""
Web app for the continuity checker.
Run locally:  streamlit run problem3_continuity_checker/app.py
"""
from __future__ import annotations

import csv
import html
import io
import json
import pathlib
import sys
import tempfile
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from common.llm import PROVIDERS  # noqa: E402
from problem3_continuity_checker.check_continuity import run  # noqa: E402

st.set_page_config(page_title="Continuity Checker", page_icon="🎬", layout="wide")

SEV = {
    "high": ("High", "#DC2626", "#FEF2F2", "🔴", "Spoken aloud: heard, subtitled and dubbed"),
    "medium": ("Medium", "#D97706", "#FFFBEB", "🟠", "Reaches video prompts or voice mapping"),
    "low": ("Low", "#2563EB", "#EFF6FF", "🔵", "Worth a look"),
    "info": ("Info", "#6B7280", "#F3F4F6", "⚪", "Format only"),
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, .stText, button, input, textarea { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1180px; }
#MainMenu, footer { visibility: hidden; }
.hero { background: linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 55%, #FDF2F8 100%);
        border: 1px solid #E0E7FF; border-radius: 18px; padding: 28px 32px; margin-bottom: 22px; }
.hero h1 { font-size: 30px; font-weight: 700; color: #1E1B4B; margin: 0 0 6px 0; }
.hero p { font-size: 15.5px; color: #4B5563; margin: 0; max-width: 760px; line-height: 1.55; }
.chips { margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }
.chip { background: #FFFFFF; border: 1px solid #E0E7FF; color: #4338CA; border-radius: 999px;
        padding: 4px 12px; font-size: 12.5px; font-weight: 500; }
.stat-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; margin: 8px 0 18px 0; }
.stat { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 14px; padding: 16px 18px;
        box-shadow: 0 1px 2px rgba(16,24,40,.04); border-top: 4px solid var(--c); }
.stat .label { font-size: 12.5px; color: #6B7280; font-weight: 500; text-transform: uppercase; letter-spacing: .04em; }
.stat .value { font-size: 30px; font-weight: 700; color: #111827; margin-top: 2px; }
.stat .hint { font-size: 12px; color: #9CA3AF; margin-top: 2px; }
.badge { display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 600;
         background: var(--bg); color: var(--c); border: 1px solid var(--c); }
.src { display: inline-block; border-radius: 6px; padding: 2px 8px; font-size: 11.5px; font-weight: 600;
       background: #F3F4F6; color: #374151; margin-left: 6px; }
.detail { color: #374151; font-size: 14.5px; line-height: 1.6; margin: 10px 0; }
.fix { background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; border-radius: 10px;
       padding: 10px 14px; font-size: 14px; margin: 6px 0 12px 0; }
.section-title { font-size: 17px; font-weight: 600; color: #111827; margin: 6px 0 10px 0; }
.muted { color: #6B7280; font-size: 13px; }
.empty { background: #FFFFFF; border: 1px dashed #C7D2FE; border-radius: 14px; padding: 28px; text-align: center; color: #4B5563; }
div[data-testid="stExpander"] { background: #FFFFFF; border-radius: 12px; border: 1px solid #E5E7EB;
        box-shadow: 0 1px 2px rgba(16,24,40,.04); margin-bottom: 10px; }
div[data-testid="stExpander"] summary p { font-weight: 500; font-size: 14.5px; }
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E5E7EB; }
@media (max-width: 800px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### 🎬 Continuity Checker")
    st.markdown('<p class="muted">For script editors working on AI-generated series.</p>', unsafe_allow_html=True)
    st.divider()
    st.markdown("**AI model**")
    options = ["offline"] + [p for p in PROVIDERS if p != "custom"]
    choice = st.selectbox("Provider", options, index=0,
                          help="Offline uses the rule checks only. Pick a provider to add the AI story-level pass.")
    examples = {
        "gemini": ("gemini-3.5-flash", "gemini-3.1-flash-lite"),
        "groq": ("llama-3.3-70b-versatile", "llama-3.1-8b-instant"),
        "anthropic": ("claude-sonnet-5-5", "claude-haiku-5-5"),
        "openai": ("gpt-4o-mini", "gpt-4o"),
        "openrouter": ("meta-llama/llama-3.3-70b-instruct:free", "mistralai/mistral-7b-instruct:free"),
        "ollama": ("llama3.1:8b", "qwen2.5:7b"),
    }
    ex = examples.get(choice)
    model_name = st.text_input(
        "Model id", value="",
        placeholder=f"e.g. {ex[0]}" if ex else "not needed in offline mode",
        disabled=(choice == "offline"),
        help="The exact name of the AI model to use. Leave it blank to use the provider's default model.")
    if ex:
        st.caption(f"Type the model's exact name, for example `{ex[0]}` or `{ex[1]}`. "
                   f"Leave it blank to use the default ({ex[0]}). To try several, separate them with commas: "
                   f"`{ex[0]},{ex[1]}`. The next one is used if one runs out of its free daily limit.")
    else:
        st.caption("Offline uses rules only, so no model is needed. Results come in under a second.")
    spec = choice if choice == "offline" or not model_name else f"{choice}:{model_name.replace(' ', '')}"
    st.divider()
    st.markdown("**Severity guide**")
    for key, (name, color, bg, dot, meaning) in SEV.items():
        st.markdown(f'<span class="badge" style="--c:{color};--bg:{bg}">{name}</span> '
                    f'<span class="muted">{meaning}</span>', unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>Continuity Checker</h1>
  <p>Finds names, titles, speaker labels and props that drift between episodes of an AI-generated series,
     so they are fixed in the script before it becomes video, voice and subtitles.</p>
  <div class="chips">
    <span class="chip">Name spelling</span><span class="chip">Surnames and titles</span>
    <span class="chip">Speaker labels</span><span class="chip">Unnamed characters</span>
    <span class="chip">Props</span><span class="chip">Story continuity (AI)</span>
  </div>
</div>
""", unsafe_allow_html=True)


def load_upload(files) -> pathlib.Path:
    d = pathlib.Path(tempfile.mkdtemp())
    for f in files:
        if f.name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                for n in z.namelist():
                    if n.endswith(".txt") and not n.startswith("__MACOSX"):
                        (d / pathlib.Path(n).name).write_bytes(z.read(n))
        else:
            (d / f.name).write_bytes(f.read())
    return d


with st.container(border=True):
    st.markdown('<div class="section-title">1. Add the episode scripts</div>', unsafe_allow_html=True)
    left, right = st.columns([3, 2], gap="large")
    with left:
        files = st.file_uploader("Upload episode .txt files or one .zip", type=["txt", "zip"],
                                 accept_multiple_files=True)
    with right:
        local = st.text_input("Or a folder path on this computer",
                              placeholder="/path/to/episodes")
        go = st.button("Check continuity", type="primary", use_container_width=True,
                       disabled=not (files or local))
    if go:
        folder = load_upload(files) if files else pathlib.Path(local.strip().strip('"'))
        bar = st.progress(0.0, "Checking the scripts...")
        try:
            st.session_state["c_res"] = run(str(folder), spec,
                                            progress=lambda i, n: bar.progress(i / n, f"AI model pass: episode {i + 1} of {n}"))
        except Exception as e:
            st.error(f"The check could not run: {e}")
        bar.empty()

res = st.session_state.get("c_res")
if not res:
    st.markdown('<div class="empty"><b>No results yet.</b><br>Add the scripts above and click '
                '<b>Check continuity</b>. Files are only used for this session and are not stored.</div>',
                unsafe_allow_html=True)
    st.stop()

counts = res["issue_counts"]
cards = [("Episodes", res["episodes"], "#4F46E5", f"{res['seconds']}s to check")]
cards += [(SEV[k][0], counts[k], SEV[k][1], SEV[k][4]) for k in ("high", "medium", "low", "info")]
st.markdown('<div class="stat-grid">' + "".join(
    f'<div class="stat" style="--c:{c}"><div class="label">{html.escape(l)}</div>'
    f'<div class="value">{v}</div><div class="hint">{html.escape(h)}</div></div>' for l, v, c, h in cards)
    + "</div>", unsafe_allow_html=True)
st.caption(f"Model: {res['model']}" + (f" · {res['model_issues_dropped_unquoted']} AI findings rejected because "
                                        "their quote was not in the script" if res.get("model_issues_dropped_unquoted") else ""))

tab_issues, tab_bible, tab_about = st.tabs(["Issues", "Show bible", "How it works"])

with tab_issues:
    f1, f2, f3 = st.columns([2, 1.2, 2])
    with f1:
        sev = st.multiselect("Severity", list(SEV), default=["high", "medium", "low"],
                             format_func=lambda k: SEV[k][0])
    with f2:
        src = st.selectbox("Found by", ["All", "Rules", "AI model"])
    with f3:
        q = st.text_input("Search", placeholder="name, episode, word...")
    shown = [i for i in res["issues"] if i["severity"] in sev
             and (src == "All" or (src == "Rules") == (i.get("source", "rules") == "rules"))
             and (not q or q.lower() in (i["title"] + " " + i["detail"] + json.dumps(i["evidence"])).lower())]
    st.markdown(f'<p class="muted">Showing {len(shown)} of {len(res["issues"])} issues</p>', unsafe_allow_html=True)

    for i in shown:
        name, color, bg, dot, _ = SEV[i["severity"]]
        by = "AI model" if i.get("source") == "model" else "Rules"
        with st.expander(f"{dot}  {i['title']}"):
            st.markdown(f'<span class="badge" style="--c:{color};--bg:{bg}">{name}</span>'
                        f'<span class="src">{by}</span><span class="src">{html.escape(i["type"])}</span>'
                        f'<span class="src">{i["id"]}</span>', unsafe_allow_html=True)
            if i["detail"]:
                st.markdown(f'<div class="detail">{html.escape(i["detail"])}</div>', unsafe_allow_html=True)
            if i["suggested_fix"]:
                st.markdown(f'<div class="fix"><b>Suggested fix:</b> {html.escape(i["suggested_fix"])}</div>',
                            unsafe_allow_html=True)
            if i["evidence"]:
                st.dataframe([{"Episode": e["episode"], "Line": e["line"] or "", "Text": e["text"]} for e in i["evidence"]],
                             hide_index=True, use_container_width=True)
                if i["evidence_count"] > len(i["evidence"]):
                    st.caption(f"...and {i['evidence_count'] - len(i['evidence'])} more places")
            st.radio("Editor decision", ["Undecided", "Fix", "Intended", "Not an issue"],
                     key=f"d-{i['id']}", horizontal=True)

    decisions = {i["id"]: st.session_state.get(f"d-{i['id']}", "Undecided") for i in res["issues"]}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "severity", "found_by", "title", "suggested_fix", "editor_decision"])
    for i in res["issues"]:
        w.writerow([i["id"], i["severity"], i.get("source", "rules"), i["title"], i["suggested_fix"], decisions[i["id"]]])
    d1, d2 = st.columns(2)
    d1.download_button("Download issues and decisions (CSV)", buf.getvalue(), "continuity_issues.csv",
                       use_container_width=True)
    d2.download_button("Download full results (JSON)",
                       json.dumps({k: v for k, v in res.items() if k != "bible"}, indent=2, ensure_ascii=False),
                       "continuity_results.json", use_container_width=True)

with tab_bible:
    st.markdown('<div class="section-title">Characters</div>', unsafe_allow_html=True)
    st.dataframe([{"Speaker label": c["label"], "Lines": c["lines"],
                   "Episodes": f"{c['first_episode']} to {c['last_episode']}",
                   "Typical delivery": ", ".join(c["typical_delivery"])} for c in res["bible"]["characters"]],
                 hide_index=True, use_container_width=True)
    st.markdown('<div class="section-title">Locations</div>', unsafe_allow_html=True)
    st.dataframe([{"Location": l["heading"], "Episodes": ", ".join(map(str, l["episodes"]))}
                  for l in res["bible"]["locations"]], hide_index=True, use_container_width=True)

with tab_about:
    st.markdown("""
In an AI microdrama pipeline the script feeds everything that follows. A speaker label picks the AI voice, a name
in an action line goes into the video prompt, and a name in dialogue becomes a subtitle and then a dub. A wrong
name in the script spreads into all of them, so this tool checks the script first.

| Check | How |
|---|---|
| Name spelling drift | Fuzzy matching of proper nouns |
| Surname and title drift | Patterns like "Alexander X" and "Duke of X" |
| Speaker label drift and typos | One label inside another, or near-identical labels |
| Unnamed labels | Which name the camera line shows when a generic label speaks |
| Prop name drift | One owner's object called different things |
| Story continuity | An AI model reads episodes in order with a running list of facts |

Rule findings are marked to fix. AI model findings must quote the script, and any whose quote is not found are
rejected automatically; the rest are marked to check, because a model can be wrong.
""")

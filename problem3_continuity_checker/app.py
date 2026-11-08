"""
Web app for the continuity checker.
Run locally:  streamlit run problem3_continuity_checker/app.py
"""
from __future__ import annotations

import csv
import html
import io
import json
import os
import pathlib
import sys
import tempfile
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from common.llm import load_env  # noqa: E402
from problem3_continuity_checker.check_continuity import run  # noqa: E402

DEMO = pathlib.Path(__file__).resolve().parent / "demo_show"
REPO = "https://github.com/SunnyKK007/KUKU"
load_env()

st.set_page_config(page_title="Continuity Checker", layout="wide")

SEV = {
    "high": ("High", "#DC2626", "#FEF2F2", "Spoken aloud: heard, subtitled and dubbed"),
    "medium": ("Medium", "#D97706", "#FFFBEB", "Reaches video prompts or voice mapping"),
    "low": ("Low", "#2563EB", "#EFF6FF", "Worth a look"),
    "info": ("Info", "#6B7280", "#F3F4F6", "Format or notes"),
}
MODELS = {
    "gemini": ("Google Gemini", "GEMINI_API_KEY", "gemini-3.5-flash", "gemini-3.1-flash-lite"),
    "groq": ("Groq", "GROQ_API_KEY", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"),
    "anthropic": ("Anthropic Claude", "ANTHROPIC_API_KEY", "claude-sonnet-5-5", "claude-haiku-5-5"),
    "openai": ("OpenAI", "OPENAI_API_KEY", "gpt-4o-mini", "gpt-4o"),
    "openrouter": ("OpenRouter", "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct:free", "mistralai/mistral-7b-instruct:free"),
    "ollama": ("Ollama (local)", None, "llama3.1:8b", "qwen2.5:7b"),
}

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"], .stMarkdown, button, input, textarea, label { font-family: 'Inter', sans-serif; }
.block-container { padding-top: 1.6rem; padding-bottom: 3rem; max-width: 1100px; }
#MainMenu, footer, [data-testid="stToolbar"] { visibility: hidden; }
.hero { background: linear-gradient(135deg, #EEF2FF 0%, #F5F3FF 60%, #FDF2F8 100%); border: 1px solid #E0E7FF;
        border-radius: 18px; padding: 26px 30px; margin-bottom: 18px; }
.hero h1 { font-size: 30px; font-weight: 700; color: #1E1B4B; margin: 0 0 6px 0; }
.hero p { font-size: 15.5px; color: #4B5563; margin: 0; line-height: 1.55; max-width: 780px; }
.steps { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 18px; }
.stepbox { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 14px; padding: 14px 16px; }
.stepbox .n { display: inline-flex; width: 26px; height: 26px; border-radius: 50%; background: #4F46E5; color: #fff;
              align-items: center; justify-content: center; font-weight: 700; font-size: 13px; margin-right: 8px; }
.stepbox b { color: #111827; font-size: 14.5px; } .stepbox p { color: #6B7280; font-size: 13px; margin: 6px 0 0 34px; }
.card-title { font-size: 17px; font-weight: 600; color: #111827; margin: 0 0 4px 0; }
.card-sub { color: #6B7280; font-size: 13.5px; margin: 0 0 10px 0; }
.stat-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin: 6px 0 14px 0; }
.stat { background: #FFFFFF; border: 1px solid #E5E7EB; border-radius: 14px; padding: 14px 16px; border-top: 4px solid var(--c); }
.stat .label { font-size: 12px; color: #6B7280; font-weight: 600; text-transform: uppercase; letter-spacing: .04em; }
.stat .value { font-size: 28px; font-weight: 700; color: #111827; } .stat .hint { font-size: 12px; color: #9CA3AF; }
.badge { display: inline-block; border-radius: 999px; padding: 2px 10px; font-size: 12px; font-weight: 600;
         background: var(--bg); color: var(--c); border: 1px solid var(--c); }
.tag { display: inline-block; border-radius: 6px; padding: 2px 8px; font-size: 11.5px; font-weight: 600;
       background: #F3F4F6; color: #374151; margin-left: 6px; }
.detail { color: #374151; font-size: 14.5px; line-height: 1.6; margin: 10px 0; }
.fix { background: #ECFDF5; border: 1px solid #A7F3D0; color: #065F46; border-radius: 10px; padding: 10px 14px;
       font-size: 14px; margin: 6px 0 12px 0; }
.muted { color: #6B7280; font-size: 13px; }
.keyok { color: #047857; font-size: 13px; } .keyno { color: #B45309; font-size: 13px; }
div[data-testid="stExpander"] { background: #FFFFFF; border-radius: 12px; border: 1px solid #E5E7EB; margin-bottom: 8px; }
div[data-testid="stExpander"] summary p { font-weight: 500; font-size: 14.5px; }
section[data-testid="stSidebar"] { background: #FFFFFF; border-right: 1px solid #E5E7EB; }
.st-key-src_picker div[role="radiogroup"], .st-key-mode_picker div[role="radiogroup"] {
    display: grid; gap: 14px; width: 100%; grid-auto-rows: 1fr; }
.st-key-src_picker div[role="radiogroup"] { grid-template-columns: repeat(3, 1fr); }
.st-key-mode_picker div[role="radiogroup"] { grid-template-columns: repeat(2, 1fr); }
.st-key-src_picker label, .st-key-mode_picker label {
    background: #FFFFFF; border: 2px solid #E5E7EB; border-radius: 16px; padding: 18px 20px; min-height: 96px;
    cursor: pointer; transition: all .15s ease; align-items: flex-start; margin: 0; width: 100%; }
.st-key-src_picker label:hover, .st-key-mode_picker label:hover { border-color: #A5B4FC; background: #F5F7FF; transform: translateY(-1px); }
.st-key-src_picker label:has(input:checked), .st-key-mode_picker label:has(input:checked) {
    border-color: #4F46E5; background: #EEF2FF; box-shadow: 0 0 0 4px rgba(79,70,229,.14); }
.st-key-src_picker label p, .st-key-mode_picker label p { font-size: 15px; line-height: 1.5; color: #374151; }
.st-key-src_picker label p strong, .st-key-mode_picker label p strong { font-size: 17.5px; color: #111827; }
@media (max-width: 800px) { .st-key-src_picker div[role="radiogroup"], .st-key-mode_picker div[role="radiogroup"] { grid-template-columns: 1fr; } }
@media (max-width: 800px) { .stat-grid { grid-template-columns: repeat(2, 1fr); } .steps { grid-template-columns: 1fr; } }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Continuity Checker")
    st.markdown('<p class="muted">Problem 3 of the Kuku AI Generalist assignment.</p>', unsafe_allow_html=True)
    st.markdown(f"[View the code on GitHub]({REPO})")
    st.divider()
    st.markdown("**What the colours mean**")
    for name, color, bg, meaning in SEV.values():
        st.markdown(f'<span class="badge" style="--c:{color};--bg:{bg}">{name}</span> '
                    f'<span class="muted">{meaning}</span>', unsafe_allow_html=True)
    st.divider()
    st.markdown("**What it checks**")
    st.markdown('<p class="muted">Name spellings, surnames and titles, speaker labels, unnamed characters, '
                'props, and format. The optional AI review also reads the story for things like injuries or '
                'costumes that change between episodes.</p>', unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>Continuity Checker</h1>
  <p>AI-written scripts often change a character's name, title or voice label from one episode to the next.
     This tool finds those slips in the script, before it becomes video, voice and subtitles.</p>
</div>
<div class="steps">
  <div class="stepbox"><span class="n">1</span><b>Choose the scripts</b><p>Try the demo show, upload episodes, or use a folder.</p></div>
  <div class="stepbox"><span class="n">2</span><b>Choose the check</b><p>Quick check with rules, or add an AI review.</p></div>
  <div class="stepbox"><span class="n">3</span><b>Review the issues</b><p>See each slip with its episode and line, and mark what to fix.</p></div>
</div>
""", unsafe_allow_html=True)


def load_upload(files) -> pathlib.Path:
    d = pathlib.Path(tempfile.mkdtemp())
    for f in files:
        if f.name.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(f.getvalue())) as z:
                for n in z.namelist():
                    if n.endswith(".txt") and not n.startswith("__MACOSX"):
                        (d / pathlib.Path(n).name).write_bytes(z.read(n))
        else:
            (d / f.name).write_bytes(f.getvalue())
    return d


with st.container(border=True):
    st.markdown('<p class="card-title">Step 1. Choose the scripts</p>'
                '<p class="card-sub">Each episode is one .txt file in Kuku\'s timestamped screenplay format. '
                'The check compares episodes with each other, so use at least two.</p>', unsafe_allow_html=True)
    SRC_LABELS = {
        "demo": "**Demo show**  \n:gray[4 episodes, ready to run with one click]",
        "upload": "**Upload files**  \n:gray[Your episode .txt files, or one .zip]",
        "folder": "**Use a folder**  \n:gray[Paste the path to a folder of episodes on this computer]",
    }
    with st.container(key="src_picker"):
        source = st.radio("Scripts", list(SRC_LABELS), format_func=SRC_LABELS.get, label_visibility="collapsed")
    folder, files, n_input = None, None, 0
    if source == "demo":
        folder = DEMO
        n_input = len(list(DEMO.glob("*.txt")))
        st.markdown('<p class="muted">A short original show written for this demo, with 8 kinds of continuity '
                    'mistakes planted in it. It works without any other files.</p>', unsafe_allow_html=True)
    elif source == "upload":
        files = st.file_uploader("Episode .txt files, or one .zip of them", type=["txt", "zip"], accept_multiple_files=True)
        if files:
            n_input = sum(1 for f in files if f.name.endswith(".txt")) + sum(1 for f in files if f.name.endswith(".zip"))
    else:
        path = st.text_input("Folder path", placeholder="/Users/you/Downloads/episodes")
        if path:
            p = pathlib.Path(path.strip().strip('"'))
            if p.is_dir():
                folder = p
                n_input = len(list(p.glob("*.txt")))
                st.markdown(f'<p class="keyok">Found {n_input} .txt files in this folder.</p>', unsafe_allow_html=True)
            else:
                st.markdown('<p class="keyno">That folder was not found. Check the path.</p>', unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<p class="card-title">Step 2. Choose the check</p>', unsafe_allow_html=True)
    MODE_LABELS = {
        "quick": "**Quick check**  \n:gray[Rules only. Free, and finishes in under a second]",
        "full": "**Full check**  \n:gray[Rules plus an AI review of the story. Needs an API key and takes a few minutes]",
    }
    with st.container(key="mode_picker"):
        mode = st.radio("Check", list(MODE_LABELS), format_func=MODE_LABELS.get, label_visibility="collapsed")
    spec = "offline"
    if mode == "full":
        c1, c2 = st.columns(2)
        with c1:
            prov = st.selectbox("AI provider", list(MODELS), format_func=lambda k: MODELS[k][0])
        name, key_env, ex1, ex2 = MODELS[prov]
        with c2:
            model_id = st.text_input("Model id (optional)", placeholder=f"e.g. {ex1}",
                                     help="The exact name of the model. Leave blank to use the default.")
        st.markdown(f'<p class="muted">Leave the model id blank to use {ex1}. You can list backups separated by '
                    f'commas, for example <code>{ex1},{ex2}</code>; the next one is used if one runs out of free quota.</p>',
                    unsafe_allow_html=True)
        if key_env and not os.environ.get(key_env):
            st.markdown(f'<p class="keyno">No {key_env} found. Add <code>{key_env}=your_key</code> to the <code>.env</code> '
                        f'file in the code folder, then restart the app. The rules will still run.</p>', unsafe_allow_html=True)
        elif key_env:
            st.markdown(f'<p class="keyok">{key_env} found.</p>', unsafe_allow_html=True)
        spec = prov if not model_id.strip() else f"{prov}:{model_id.replace(' ', '')}"

ready = bool(folder or files)
go = st.button("Run the check", type="primary", use_container_width=True, disabled=not ready)
if not ready:
    st.caption("Choose the scripts in Step 1 to enable the button.")

if go:
    target = load_upload(files) if files else folder
    n_eps = len(list(pathlib.Path(target).glob("*.txt")))
    if n_eps == 0:
        st.error("No .txt episode files were found. Upload Kuku screenplay .txt files or a .zip of them.")
    else:
        bar = st.progress(0.0, "Checking the scripts...")
        try:
            res = run(str(target), spec, progress=lambda i, n: bar.progress(i / n, f"AI review: episode {i + 1} of {n}"))
            res["source_label"] = "Demo show" if target == DEMO else (f"{n_eps} uploaded file(s)" if files else str(target))
            st.session_state["c_res"] = res
        except Exception as e:
            st.error(f"The check could not run: {e}")
        bar.empty()

res = st.session_state.get("c_res")
if not res:
    st.stop()

st.markdown("---")
counts = res["issue_counts"]
total = sum(counts.values())
model_errors = [i for i in res["issues"] if i["type"] == "model error"]
if res["episodes"] < 2:
    st.warning(f"Only {res['episodes']} episode was checked. Continuity problems show up when episodes are compared, "
               "so add at least two episodes for meaningful results.")
if total == 0:
    st.info(f"No continuity problems found in {res['episodes']} episode(s) of {res.get('source_label', 'the scripts')}.")
    st.stop()
st.success(f"Checked {res['episodes']} episodes from {res.get('source_label', 'the scripts')} in {res['seconds']} s "
           f"and found {total} issues to review.")
if model_errors:
    st.warning("The AI review stopped early (" + model_errors[0]["title"].split(": ", 1)[-1] +
               "). The rule results below are complete.")

cards = [("Episodes", res["episodes"], "#4F46E5", res["model"].split(" (")[0])]
cards += [(SEV[k][0], counts[k], SEV[k][1], SEV[k][3]) for k in ("high", "medium", "low", "info")]
st.markdown('<div class="stat-grid">' + "".join(
    f'<div class="stat" style="--c:{c}"><div class="label">{html.escape(str(l))}</div>'
    f'<div class="value">{v}</div><div class="hint">{html.escape(str(h))}</div></div>' for l, v, c, h in cards)
    + "</div>", unsafe_allow_html=True)

tab_issues, tab_bible, tab_about = st.tabs(["Issues", "Show bible", "How it works"])

with tab_issues:
    f1, f2, f3 = st.columns([2, 1.2, 2])
    with f1:
        sev = st.multiselect("Severity", list(SEV), default=["high", "medium", "low"], format_func=lambda k: SEV[k][0])
    with f2:
        src = st.selectbox("Found by", ["All", "Rules", "AI review"])
    with f3:
        q = st.text_input("Search", placeholder="a name, an episode, a word")
    shown = [i for i in res["issues"] if i["severity"] in sev and i["type"] != "model error"
             and (src == "All" or (src == "Rules") == (i.get("source", "rules") == "rules"))
             and (not q or q.lower() in (i["title"] + " " + i["detail"] + json.dumps(i["evidence"])).lower())]
    st.markdown(f'<p class="muted">Showing {len(shown)} of {total} issues. Click an issue to see where it is and mark a decision.</p>',
                unsafe_allow_html=True)
    for i in shown:
        name, color, bg, _ = SEV[i["severity"]]
        by = "AI review" if i.get("source") == "model" else "Rules"
        with st.expander(f"{name}: {i['title']}"):
            st.markdown(f'<span class="badge" style="--c:{color};--bg:{bg}">{name}</span>'
                        f'<span class="tag">{by}</span><span class="tag">{html.escape(i["type"])}</span>'
                        f'<span class="tag">{i["id"]}</span>', unsafe_allow_html=True)
            if i["detail"]:
                st.markdown(f'<div class="detail">{html.escape(i["detail"])}</div>', unsafe_allow_html=True)
            if i["suggested_fix"]:
                st.markdown(f'<div class="fix"><b>Suggested fix:</b> {html.escape(i["suggested_fix"])}</div>',
                            unsafe_allow_html=True)
            if i["evidence"]:
                st.markdown('<p class="muted">Where it appears:</p>', unsafe_allow_html=True)
                st.dataframe([{"Episode": e["episode"], "Line": e["line"] or "", "Text": e["text"]} for e in i["evidence"]],
                             hide_index=True, use_container_width=True)
                if i["evidence_count"] > len(i["evidence"]):
                    st.caption(f"...and {i['evidence_count'] - len(i['evidence'])} more places")
            st.radio("Your decision", ["Undecided", "Fix", "Intended", "Not an issue"], key=f"d-{i['id']}",
                     horizontal=True, help="Fix: a real mistake. Intended: done on purpose. Not an issue: the tool was wrong.")

    decisions = {i["id"]: st.session_state.get(f"d-{i['id']}", "Undecided") for i in res["issues"]}
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "severity", "found_by", "title", "suggested_fix", "your_decision"])
    for i in res["issues"]:
        if i["type"] != "model error":
            w.writerow([i["id"], i["severity"], i.get("source", "rules"), i["title"], i["suggested_fix"], decisions[i["id"]]])
    st.markdown("&nbsp;")
    d1, d2 = st.columns(2)
    d1.download_button("Download issues and decisions (CSV)", buf.getvalue(), "continuity_issues.csv",
                       use_container_width=True)
    d2.download_button("Download full results (JSON)",
                       json.dumps({k: v for k, v in res.items() if k != "bible"}, indent=2, ensure_ascii=False),
                       "continuity_results.json", use_container_width=True)

with tab_bible:
    st.markdown('<p class="muted">Built automatically from the scripts: every speaker and every location.</p>',
                unsafe_allow_html=True)
    st.dataframe([{"Speaker label": c["label"], "Lines": c["lines"],
                   "Episodes": f"{c['first_episode']} to {c['last_episode']}",
                   "Typical delivery": ", ".join(c["typical_delivery"])} for c in res["bible"]["characters"]],
                 hide_index=True, use_container_width=True)
    st.dataframe([{"Location": l["heading"], "Episodes": ", ".join(map(str, l["episodes"]))}
                  for l in res["bible"]["locations"]], hide_index=True, use_container_width=True)

with tab_about:
    st.markdown("""
In an AI microdrama pipeline the script feeds everything that follows. A speaker label picks the AI voice, a name in
an action line goes into the video prompt, and a name in dialogue becomes a subtitle and then a dub. A wrong name in
the script spreads into all of them, so this tool checks the script first.

| Check | How |
|---|---|
| Name spelling | Finds near-identical names, such as Ravenswood and Ravenwood |
| Surnames and titles | Patterns like "Marcus X" and "Duke of X" |
| Speaker labels | The same character under two labels, or a misspelt label |
| Unnamed characters | A generic label, such as HOODED WOMAN, whose camera lines name a known character |
| Props | One object called different things, such as a journal, a diary and a notebook |
| Format | Continuity notes pointing at the wrong episode, inconsistent headers |
| AI review (optional) | A model reads the episodes in order and reports contradictions, quoting the script |

Rule findings are marked to fix. AI findings must quote the script, and any whose quote is not found are rejected;
the rest are marked to check, because a model can be wrong. On Kuku's 50-episode show, the rules found 15 issues in
under a second and caught 44 of 45 deliberately planted mistakes.
""")

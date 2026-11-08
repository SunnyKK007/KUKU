"""
Web app for the promo finder.
Run locally:  streamlit run problem1_promo_finder/app.py
"""
from __future__ import annotations

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

from common import ui  # noqa: E402
from common.llm import load_env  # noqa: E402
from problem1_promo_finder.find_promos import run  # noqa: E402
from problem1_promo_finder.report import review_html, seg_str  # noqa: E402

load_env()
st.set_page_config(page_title="Promo Finder", layout="wide")
ui.apply_theme()

MODELS = {
    "gemini": ("Google Gemini", "GEMINI_API_KEY", "gemini-3.5-flash", "gemini-3.1-flash-lite"),
    "groq": ("Groq", "GROQ_API_KEY", "llama-3.3-70b-versatile", "llama-3.1-8b-instant"),
    "anthropic": ("Anthropic Claude", "ANTHROPIC_API_KEY", "claude-sonnet-5-5", "claude-haiku-5-5"),
    "openai": ("OpenAI", "OPENAI_API_KEY", "gpt-4o-mini", "gpt-4o"),
    "openrouter": ("OpenRouter", "OPENROUTER_API_KEY", "meta-llama/llama-3.3-70b-instruct:free", "mistralai/mistral-7b-instruct:free"),
    "ollama": ("Ollama (local)", None, "llama3.1:8b", "qwen2.5:7b"),
}

with st.sidebar:
    st.markdown("### Promo Finder")
    st.markdown('<p class="muted">Problem 1 of the Kuku AI Generalist assignment.</p>', unsafe_allow_html=True)
    st.markdown("[View the code on GitHub](https://github.com/SunnyKK007/KUKU)")
    st.divider()
    st.markdown("**A good promo**")
    st.markdown('<p class="muted">Runs 20 to 60 seconds, opens on a hook in the first 3 seconds, ends on a cliffhanger, '
                'and makes sense to someone who has never seen the show.</p>', unsafe_allow_html=True)

ui.hero("Promo selection", "Promo Finder",
        "Reads a show's screenplays and returns a ranked shortlist of 20 to 60 second promos, each with exact "
        "timestamps, the hook, the cliffhanger and why it works.")

with st.container(border=True):
    ui.section("Step 1", "Choose the scripts",
               "Each episode is one .txt file in Kuku's timestamped screenplay format.")
    source = ui.card_choice("source", {
        "upload": "**Upload files**  \nYour episode .txt files, or one .zip",
        "folder": "**Use a folder**  \nPaste the path to a folder of episodes on this computer",
    }, 2)
    folder, files = None, None
    if source == "upload":
        files = st.file_uploader("Episode .txt files, or one .zip of them", type=["txt", "zip"], accept_multiple_files=True)
    else:
        path = st.text_input("Folder path", placeholder="/Users/you/Downloads/episodes")
        if path:
            p = pathlib.Path(path.strip().strip('"'))
            if p.is_dir():
                folder = p
                ui.callout(f"Found {len(list(p.glob('*.txt')))} .txt files in this folder.", "ok")
            else:
                ui.callout("That folder was not found. Check the path.", "warn")

ui.spacer(14)
with st.container(border=True):
    ui.section("Step 2", "Choose the check")
    mode = ui.card_choice("mode", {
        "quick": "**Quick check**  \nRules only. Free, about 25 seconds for 50 episodes",
        "full": "**Full check**  \nRules plus an AI model that re-scores the top clips as a first-time viewer. Needs an API key",
    }, 2)
    spec = "offline"
    if mode == "full":
        c1, c2 = st.columns(2)
        with c1:
            prov = st.selectbox("AI provider", list(MODELS), format_func=lambda k: MODELS[k][0])
        name, key_env, ex1, ex2 = MODELS[prov]
        with c2:
            model_id = st.text_input("Model id (optional)", placeholder=f"e.g. {ex1}",
                                     help="The exact name of the model. Leave blank to use the default.")
        if key_env and not os.environ.get(key_env):
            ui.callout(f"No {key_env} found. Add <code>{key_env}=your_key</code> to the <code>.env</code> file in the "
                       "code folder and restart the app.", "warn")
        elif key_env:
            ui.callout(f"{key_env} found.", "ok")
        spec = prov if not model_id.strip() else f"{prov}:{model_id.replace(' ', '')}"
    with st.expander("Options"):
        top = st.slider("Promos to return", 5, 40, 25)
        judge_k = st.slider("Clips the AI re-scores", 0, 80, 40, disabled=(mode == "quick"))

ready = bool(folder or files)
ui.spacer(14)
go = st.button("Find promos", type="primary", use_container_width=True, disabled=not ready)
if not ready:
    st.caption("Choose the scripts in Step 1 to enable the button.")

if go:
    try:
        with st.spinner("Reading the episodes and scoring every possible clip..."):
            if files:
                with tempfile.TemporaryDirectory() as tmp:
                    tmpdir = pathlib.Path(tmp)
                    for f in files:
                        if f.name.endswith(".zip"):
                            with zipfile.ZipFile(io.BytesIO(f.getvalue())) as z:
                                for n in z.namelist():
                                    if n.endswith(".txt") and not n.startswith("__MACOSX"):
                                        (tmpdir / pathlib.Path(n).name).write_bytes(z.read(n))
                        else:
                            (tmpdir / f.name).write_bytes(f.getvalue())
                    st.session_state["res"] = run(str(tmpdir), spec, top, judge_k)
            else:
                st.session_state["res"] = run(str(folder), spec, top, judge_k)
    except Exception as e:
        st.error(f"The run failed: {e}")

res = st.session_state.get("res")
if not res:
    st.stop()

ui.spacer(14)
st.divider()
st.markdown(f'<p class="sec-title">Ranked promos</p><p class="sec-sub">{len(res["promos"])} promos from '
            f'{res["episodes"]} episodes, found in {res["seconds"]} s.</p>', unsafe_allow_html=True)
ui.stat_cards([("Episodes", res["episodes"], "#4338CA", f"{round(res['runtime_minutes'])} minutes read"),
               ("Promos", len(res["promos"]), "#047857", "ranked best first"),
               ("Judged by AI", res["judged"], "#B45309", "top clips re-scored"),
               ("Run time", f"{res['seconds']} s", "#475569", res["model"].split(" (")[0])])

csv_rows = ["rank,score,segments,duration,hook,cliffhanger,why"] + [
    ",".join(json.dumps(str(x)) for x in (p["rank"], p["final_score"], seg_str(p), p["duration"], p["hook"],
                                           p["cliffhanger"], p["why_it_works"])) for p in res["promos"]]
d1, d2, d3 = st.columns(3)
d1.download_button("Download review page (HTML)", review_html(res), "review.html", use_container_width=True)
d2.download_button("Download spreadsheet (CSV)", "\n".join(csv_rows), "promos.csv", use_container_width=True)
d3.download_button("Download everything (JSON)", json.dumps(res, indent=2, ensure_ascii=False), "promos.json",
                   use_container_width=True)
ui.spacer(14)

for p in res["promos"]:
    with st.expander(f"#{p['rank']}   {seg_str(p)}   |   {p['duration']:.0f} s   |   {p['tropes'][0]}"):
        st.markdown(f'<span class="tag" style="margin-left:0">Score {p["final_score"]:.2f}</span>'
                    f'<span class="tag">{html.escape(p["type"])}</span>', unsafe_allow_html=True)
        st.markdown(f"**Hook:** {p['hook']}  \n**Cliffhanger:** {p['cliffhanger']}  \n**Why it works:** {p['why_it_works']}")
        if p["notes"]:
            ui.callout("<b>Watch-outs:</b> " + html.escape("; ".join(p["notes"])), "warn")
        st.code("\n".join(line for s in p["segments"] for line in s["script"]), language=None)
        st.radio("Editor decision", ["Undecided", "Approve", "Reject"], key=f"decision-{p['rank']}", horizontal=True)

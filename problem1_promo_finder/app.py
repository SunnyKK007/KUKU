"""
Web app for the promo finder.
Run locally:  streamlit run problem1_promo_finder/app.py
"""
from __future__ import annotations

import html
import io
import json
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
st.set_page_config(page_title="Promo Finder", page_icon=ui.logo_path("promo"), layout="wide")
ui.apply_theme()

with st.sidebar:
    ui.brand("Promo Finder", "promo", "Problem 1 · Kuku AI Generalist")
    st.markdown("[View the code on GitHub](https://github.com/SunnyKK007/KUKU)")
    st.divider()
    st.markdown("**A good promo**")
    st.markdown('<p class="muted">Runs 20 to 60 seconds, opens on a hook in the first 3 seconds, ends on a cliffhanger, '
                'and makes sense to someone who has never seen the show.</p>', unsafe_allow_html=True)

ui.hero("Promo selection", "Promo Finder",
        "Reads a show's screenplays and returns a ranked shortlist of 20 to 60 second promos, each with exact "
        "timestamps, the hook, the cliffhanger and why it works.", logo="promo")

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
    spec, api_key, key_ok = "offline", None, True
    if mode == "full":
        spec, api_key, key_ok = ui.model_picker("p1")
    with st.expander("Options"):
        top = st.slider("Promos to return", 5, 40, 25)
        judge_k = st.slider("Clips the AI re-scores", 0, 80, 40, disabled=(mode == "quick"))

ready = bool(folder or files) and key_ok
ui.spacer(14)
go = st.button("Find promos", type="primary", use_container_width=True, disabled=not ready)
if not ready:
    missing = ([] if (folder or files) else ["choose the scripts in Step 1"]) + ([] if key_ok else ["add your API key in Step 2"])
    st.caption("To enable the button, " + " and ".join(missing) + ".")

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
                    st.session_state["res"] = run(str(tmpdir), spec, top, judge_k, api_key=api_key)
            else:
                st.session_state["res"] = run(str(folder), spec, top, judge_k, api_key=api_key)
    except Exception as e:
        st.error(f"The run failed: {e}")

res = st.session_state.get("res")
if not res:
    st.stop()

ui.spacer(14)
st.divider()
st.markdown(f'<p class="sec-title">Ranked promos</p><p class="sec-sub">{len(res["promos"])} promos from '
            f'{res["episodes"]} episodes, found in {res["seconds"]} s.</p>', unsafe_allow_html=True)
ui.stat_cards([("Episodes", res["episodes"], "#18181B", f"{round(res['runtime_minutes'])} minutes read"),
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

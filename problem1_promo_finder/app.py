"""
Streamlit app for the promo finder.
Run locally:  streamlit run problem1_promo_finder/app.py
Upload episode .txt files (or a .zip of them), pick a model, get ranked promos.
"""
from __future__ import annotations

import io
import json
import pathlib
import sys
import tempfile
import zipfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from common.llm import PROVIDERS, first_available_spec  # noqa: E402
from problem1_promo_finder.find_promos import run  # noqa: E402
from problem1_promo_finder.report import review_html, seg_str  # noqa: E402

st.set_page_config(page_title="Promo Finder", layout="wide")
st.title("Promo Finder")
st.caption("Reads microdrama screenplays and finds 20-60s promos that open on a hook, "
           "end on a cliffhanger and make sense to a stranger.")

with st.sidebar:
    st.header("Model")
    default = first_available_spec()
    options = ["offline"] + [p for p in PROVIDERS if p != "custom"]
    choice = st.selectbox("Provider", options, index=options.index(default.split(":")[0]) if default.split(":")[0] in options else 0)
    model_name = st.text_input("Model id (blank = provider default)", value=default.split(":", 1)[1] if ":" in default else "")
    spec = choice if choice == "offline" or not model_name else f"{choice}:{model_name}"
    top = st.slider("Promos to return", 5, 40, 25)
    judge_k = st.slider("Clips the model re-scores", 0, 80, 40, disabled=(choice == "offline"))
    st.caption("Offline uses rules only and costs nothing. A model adds a blind 'new viewer' check.")

files = st.file_uploader("Episode screenplays (.txt) or one .zip", type=["txt", "zip"], accept_multiple_files=True)
local = st.text_input("...or, when running locally, a folder path on this machine")

if local and st.button("Find promos in folder", type="primary"):
    with st.spinner("Reading episodes and scoring every possible clip..."):
        try:
            st.session_state["res"] = run(local.strip().strip('"'), spec, top, judge_k)
        except Exception as e:
            st.error(f"Run failed: {e}")

if files and st.button("Find promos", type="primary"):
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = pathlib.Path(tmp)
        for f in files:
            if f.name.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                    for n in z.namelist():
                        if n.endswith(".txt") and not n.startswith("__MACOSX"):
                            (tmpdir / pathlib.Path(n).name).write_bytes(z.read(n))
            else:
                (tmpdir / f.name).write_bytes(f.read())
        with st.spinner("Reading episodes and scoring every possible clip..."):
            try:
                st.session_state["res"] = run(str(tmpdir), spec, top, judge_k)
            except Exception as e:
                st.error(f"Run failed: {e}")

res = st.session_state.get("res")
if res:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Episodes", res["episodes"])
    c2.metric("Runtime read", f"{round(res['runtime_minutes'])} min")
    c3.metric("Clips judged by model", res["judged"])
    c4.metric("Run time", f"{res['seconds']} s")
    st.caption(f"Model: {res['model']}")
    d1, d2, d3 = st.columns(3)
    d1.download_button("Download JSON", json.dumps(res, indent=2, ensure_ascii=False), "promos.json")
    d2.download_button("Download review page (HTML)", review_html(res), "review.html")
    csv_rows = ["rank,score,segments,duration,hook,cliffhanger,why"] + [
        ",".join(json.dumps(str(x)) for x in (p["rank"], p["final_score"], seg_str(p), p["duration"],
                                               p["hook"], p["cliffhanger"], p["why_it_works"]))
        for p in res["promos"]]
    d3.download_button("Download CSV", "\n".join(csv_rows), "promos.csv")
    for p in res["promos"]:
        with st.expander(f"#{p['rank']}  {seg_str(p)}  ·  {p['duration']:.0f}s  ·  {p['tropes'][0]}  ·  score {p['final_score']:.2f}"):
            st.markdown(f"**Hook:** {p['hook']}  \n**Cliffhanger:** {p['cliffhanger']}  \n**Why it works:** {p['why_it_works']}")
            if p["notes"]:
                st.warning("Watch-outs: " + "; ".join(p["notes"]))
            st.code("\n".join(l for s in p["segments"] for l in s["script"]), language=None)
            k = f"decision-{p['rank']}"
            st.radio("Editor decision", ["undecided", "approve", "reject"], key=k, horizontal=True)
elif not files and not local:
    st.info("Upload the episode files to start. Nothing is stored after the session ends.")

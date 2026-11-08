"""
Streamlit app for the continuity checker.
Run locally:  streamlit run problem3_continuity_checker/app.py
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
from problem3_continuity_checker.check_continuity import run  # noqa: E402

st.set_page_config(page_title="Continuity Checker", layout="wide")
st.title("Continuity Checker")
st.caption("Finds names, titles, speaker labels and props that drift between episodes of an AI-generated "
           "series, before the script goes to video, voice and subtitles.")

with st.sidebar:
    st.header("Model")
    default = first_available_spec()
    options = ["offline"] + [p for p in PROVIDERS if p != "custom"]
    choice = st.selectbox("Provider", options, index=options.index(default.split(":")[0]) if default.split(":")[0] in options else 0)
    model_name = st.text_input("Model id (blank = provider default)", value=default.split(":", 1)[1] if ":" in default else "")
    spec = choice if choice == "offline" or not model_name else f"{choice}:{model_name}"
    st.caption("Offline runs the rule checks in under a second. A model adds a slower story-level pass.")

files = st.file_uploader("Episode screenplays (.txt) or one .zip", type=["txt", "zip"], accept_multiple_files=True)
local = st.text_input("...or, when running locally, a folder path on this machine")
if local and st.button("Check folder", type="primary"):
    try:
        st.session_state["c_res"] = run(local.strip().strip('"'), spec)
    except Exception as e:
        st.error(f"Run failed: {e}")

if files and st.button("Check continuity", type="primary"):
    with tempfile.TemporaryDirectory() as tmp:
        d = pathlib.Path(tmp)
        for f in files:
            if f.name.endswith(".zip"):
                with zipfile.ZipFile(io.BytesIO(f.read())) as z:
                    for n in z.namelist():
                        if n.endswith(".txt") and not n.startswith("__MACOSX"):
                            (d / pathlib.Path(n).name).write_bytes(z.read(n))
            else:
                (d / f.name).write_bytes(f.read())
        bar = st.progress(0.0, "Checking...")
        try:
            st.session_state["c_res"] = run(str(d), spec, progress=lambda i, n: bar.progress(i / n, f"Model pass: episode {i + 1}/{n}"))
        except Exception as e:
            st.error(f"Run failed: {e}")
        bar.empty()

res = st.session_state.get("c_res")
if res:
    cols = st.columns(5)
    cols[0].metric("Episodes", res["episodes"])
    for c, s in zip(cols[1:], ["high", "medium", "low", "info"]):
        c.metric(s.capitalize(), res["issue_counts"][s])
    st.caption(f"Model: {res['model']} · {res['seconds']}s · high = spoken aloud, medium = reaches video prompts or voices")
    sev = st.multiselect("Show severities", ["high", "medium", "low", "info"], default=["high", "medium", "low"])
    st.download_button("Download issues (JSON)", json.dumps({k: v for k, v in res.items() if k != "bible"}, indent=2, ensure_ascii=False), "issues.json")
    for i in res["issues"]:
        if i["severity"] not in sev:
            continue
        with st.expander(f"{i['id']} · {i['severity'].upper()} · {i['title']}"):
            st.write(i["detail"])
            st.markdown(f"**Suggested fix:** {i['suggested_fix']}")
            for e in i["evidence"]:
                st.markdown(f"- E{e['episode']} line {e['line']}: `{e['text']}`")
            st.radio("Editor decision", ["undecided", "fix", "intended", "not an issue"], key=f"d-{i['id']}", horizontal=True)
    with st.expander("Show bible (built by code)"):
        st.dataframe(res["bible"]["characters"], use_container_width=True)
        st.dataframe(res["bible"]["locations"], use_container_width=True)
elif not files and not local:
    st.info("Upload the episode files to start. Nothing is stored after the session ends.")

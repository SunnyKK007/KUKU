"""
Nyay Saathi: a legal-information assistant for getting your money back
(security deposit, consumer refund, unpaid salary). Streamlit front end;
all logic lives in engine.py.

Run from the repo root:   streamlit run p2_lawyer/app.py
"""
from __future__ import annotations

import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

try:
    for k, v in dict(st.secrets).items():
        if isinstance(v, str):
            os.environ.setdefault(k, v)
except Exception:
    pass

from common.llm import PROVIDERS, first_available_spec  # noqa: E402
from p2_lawyer import law, voice  # noqa: E402
from p2_lawyer.engine import DISCLAIMER, Session  # noqa: E402

st.set_page_config(page_title="Nyay Saathi: get your money back", page_icon="⚖️", layout="wide")

MODEL_CHOICES = ["auto", "offline", "groq:llama-3.3-70b-versatile", "gemini:gemini-2.5-flash",
                 "openrouter:meta-llama/llama-3.3-70b-instruct:free", "anthropic", "openai:gpt-4o-mini"]


def new_session(model: str):
    spec = first_available_spec() if model == "auto" else model
    st.session_state.session = Session(model=spec)
    st.session_state.messages = []
    st.session_state.practice_msgs = []
    st.session_state.stand = None
    st.session_state.model_choice = model


if "session" not in st.session_state:
    new_session("auto")
S: Session = st.session_state.session

with st.sidebar:
    st.header("Nyay Saathi")
    st.caption("Deposit · Refund · Salary")
    choice = st.selectbox("Model", MODEL_CHOICES, index=MODEL_CHOICES.index(st.session_state.model_choice),
                          help="'offline' needs no key and uses rules only. Others need a key in .env or Streamlit secrets.")
    if choice != st.session_state.model_choice:
        new_session(choice)
        st.rerun()
    st.write(f"In use: `{S.model_label}`")
    keys = [n for n, cfg in PROVIDERS.items() if cfg["key_env"] and os.environ.get(cfg["key_env"])]
    st.caption("Keys found: " + (", ".join(keys) if keys else "none (offline mode)"))
    if S.model_error:
        st.warning(f"Model problem, using rules instead: {S.model_error[:200]}")
    if st.button("New conversation", width="stretch"):
        new_session(st.session_state.model_choice)
        st.rerun()

    st.subheader("Your case file")
    st.markdown(S.case.summary_markdown())
    missing = S.case.missing_slots()
    if S.case.problem_type and missing:
        st.caption("Still to ask: " + ", ".join(m.replace("_", " ") for m in missing))
    if S.case.needs_lawyer():
        st.error("This case needs a real lawyer. Free legal aid: 15100.")

    with st.expander(f"Guardrail log ({len(S.guardrail_log)} blocked)"):
        if not S.guardrail_log:
            st.caption("No unverified law, case, number or link has been blocked yet.")
        for g in S.guardrail_log:
            st.write(f"- **{g['type']}**: `{g['text']}` ({g['reason']})")
    with st.expander("Cost so far"):
        st.json(S.cost_report())

st.title("⚖️ Get your money back")
st.info(f"{DISCLAIMER} I cover three problems only: a deposit your landlord won't return, a refund a company won't "
        f"give, and salary your employer hasn't paid.")

tab_chat, tab_stand, tab_docs, tab_practice, tab_sources = st.tabs(
    ["💬 Chat", "📍 Where I stand", "📝 Draft notice", "🎭 Practise", "📚 Sources"])


def show_reply(msg: dict):
    st.markdown(msg["text"])
    if msg.get("cited"):
        with st.expander("Sources used"):
            st.markdown(msg["sources_md"])


with tab_chat:
    if not st.session_state.messages:
        with st.chat_message("assistant"):
            st.markdown("Tell me what happened, in your own words and language. For example: *\"My landlord in Pune "
                        "is not returning my ₹40,000 deposit\"* or *\"Company ne 2 mahine ki salary nahi di\"*.")
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            if m["role"] == "assistant":
                show_reply(m)
            else:
                st.markdown(m["text"])

    user_text = None
    if hasattr(st, "audio_input"):
        audio = st.audio_input("Or speak (Hindi, English and other Indian languages)")
        if audio is not None and st.session_state.get("last_audio") != audio.name + str(audio.size):
            st.session_state.last_audio = audio.name + str(audio.size)
            if voice.available():
                res = voice.transcribe(audio.getvalue(), filename=audio.name or "voice.wav")
                if res.get("error"):
                    st.warning(res["error"])
                else:
                    user_text = res["text"]
                    st.caption(f"Heard: {user_text}")
            else:
                st.warning("Voice input needs SARVAM_API_KEY (Sarvam AI speech-to-text). Please type for now.")
    typed = st.chat_input("Describe your problem...")
    user_text = typed or user_text
    if user_text:
        st.session_state.messages.append({"role": "user", "text": user_text})
        out = S.reply(user_text)
        st.session_state.messages.append({"role": "assistant", **out})
        st.rerun()

with tab_stand:
    if not S.case.problem_type:
        st.write("Start in the Chat tab first, so I know your problem.")
    else:
        if st.button("Explain where I stand", type="primary"):
            with st.spinner("Putting it together from verified sources..."):
                st.session_state.stand = S.where_i_stand()
        if st.session_state.stand:
            show_reply(st.session_state.stand)

with tab_docs:
    docs = S.documents() if S.case.problem_type else []
    if not docs:
        st.write("Drafts appear here once I know your problem (deposit, refund or salary).")
    else:
        st.warning("These are drafts filled from what you told me. Check every fact and replace every [PLACEHOLDER] "
                   "before sending. Templates are fixed code, not AI-written.")
        for d in docs:
            st.subheader(d["title"])
            st.text_area(d["title"], d["text"], height=420, label_visibility="collapsed", key=d["filename"])
            st.download_button(f"Download {d['filename']}", d["text"].encode("utf-8"), file_name=d["filename"],
                               mime="text/plain", key="dl_" + d["filename"])

with tab_practice:
    if not S.case.problem_type:
        st.write("Practice works once I know your problem.")
    else:
        if st.button("Start practice (I play the other side)"):
            st.session_state.practice_msgs = [{"role": "assistant", **S.start_practice()}]
        for m in st.session_state.practice_msgs:
            with st.chat_message(m["role"]):
                st.markdown(m["text"])
        if S.practice_state and S.practice_state.get("active"):
            with st.form("practice_form", clear_on_submit=True):
                ans = st.text_area("Your reply", height=90)
                if st.form_submit_button("Send") and ans.strip():
                    st.session_state.practice_msgs.append({"role": "user", "text": ans})
                    st.session_state.practice_msgs.append({"role": "assistant", **S.reply(ans)})
                    st.rerun()

with tab_sources:
    st.write("Every legal statement comes from this closed list. Each card was checked against an official source. "
             "If a law, section, court case, helpline or link is not here, the guardrail removes it before you see it.")
    for c in law.load()["cards"]:
        cite = law.short_cite(c["id"])
        st.markdown(f"**{c['title']}** `{c['id']}`" + (f"  \n{cite}" if cite else "")
                    + f"  \n{c['plain']}  \n[{c['source_name']}]({c['source_url']}) · checked {c['verified_on']} · "
                    f"confidence {c['confidence']}" + (f"  \n_Caveat: {c['caveats']}_" if c["caveats"] else ""))

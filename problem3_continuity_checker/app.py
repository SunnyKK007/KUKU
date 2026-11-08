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
import re
import sys
import tempfile
import time
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st  # noqa: E402

from common import ui  # noqa: E402
from common.llm import load_env  # noqa: E402
from problem3_continuity_checker.check_continuity import run  # noqa: E402

DEMO = pathlib.Path(__file__).resolve().parent / "demo_show"
CARD_HINT = {"high": "Spoken aloud", "medium": "Video or voice", "low": "Worth a look", "info": "Format notes"}
REPO = "https://github.com/SunnyKK007/KUKU"
load_env()

st.set_page_config(page_title="Continuity Checker", page_icon=ui.logo_path("continuity"), layout="wide")
ui.apply_theme()

SEV = {
    "high": ("High", "#B91C1C", "#FEF2F2", "Spoken aloud, so viewers hear it and it reaches subtitles and dubs"),
    "medium": ("Medium", "#B45309", "#FFFBEB", "Reaches the video prompt or the choice of AI voice"),
    "low": ("Low", "#0F766E", "#F0FDFA", "Worth a look, but unlikely to reach viewers"),
    "info": ("Info", "#475569", "#F1F5F9", "Formatting and script notes"),
}
with st.sidebar:
    ui.brand("Continuity Checker", "continuity", "Problem 3 · Kuku AI Generalist")
    st.markdown(f"[View the code on GitHub]({REPO})")
    st.divider()
    ui.severity_legend((name, color, meaning) for name, color, bg, meaning in SEV.values())
    st.divider()
    st.markdown('<div class="side-title">What it checks</div>', unsafe_allow_html=True)
    st.markdown('<p class="muted">Name spellings, surnames and titles, speaker labels, unnamed characters, props and '
                'format. The optional AI review also reads the story for things like injuries or costumes that '
                'change between episodes.</p>', unsafe_allow_html=True)

ui.hero("Script quality control", "Continuity Checker",
        "AI-written scripts often change a character's name, title or voice label from one episode to the next. "
        "This tool finds those slips in the script, before it becomes video, voice and subtitles.", logo="continuity")


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


def ai_coverage(res):
    """Per episode: how many AI findings, or why the AI did not review it."""
    if res["model"].startswith("offline") or not res.get("episode_numbers"):
        return None
    nums = res["episode_numbers"]
    found = {n: 0 for n in nums}
    failed = {}
    for i in res["issues"]:
        if i.get("source") != "model":
            continue
        if i["type"] == "model error":
            m = re.match(r"AI model stopped at episode (\d+): (.*)", i["title"])
            if m:
                for n in nums:
                    if n >= int(m.group(1)):
                        failed[n] = m.group(2)
                continue
            m = re.match(r"E(\d+): (.*)", i["title"])
            if m and int(m.group(1)) in found:
                failed[int(m.group(1))] = m.group(2)
        elif i["evidence"] and i["evidence"][0]["episode"] in found:
            found[i["evidence"][0]["episode"]] += 1
    return nums, found, failed


with st.container(border=True):
    ui.section("Step 1", "Choose the scripts",
               "Each episode is one .txt file in Kuku's timestamped screenplay format. The check compares episodes "
               "with each other, so use at least two.")
    source = ui.card_choice("source", {
        "demo": "**Demo show**  \n4 episodes, ready to run with one click",
        "upload": "**Upload files**  \nYour episode .txt files, or one .zip",
        "folder": "**Use a folder**  \nPaste the path to a folder of episodes on this computer",
    }, 3)
    folder, files = None, None
    if source == "demo":
        folder = DEMO
        st.markdown('<p class="muted">A short original show written for this demo, with 8 kinds of continuity '
                    'mistakes planted in it. It works without any other files.</p>', unsafe_allow_html=True)
    elif source == "upload":
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
        "quick": "**Quick check**  \nRules only. Free, and finishes in under a second",
        "full": "**Full check**  \nAn AI model reads the story and reports what it finds. Needs an API key and takes a few minutes",
    }, 2)
    spec, api_key, key_ok = "offline", None, True
    if mode == "full":
        spec, api_key, key_ok = ui.model_picker("p3")

ready = bool(folder or files) and key_ok
ui.spacer(14)
go = st.button("Run the check", type="primary", use_container_width=True, disabled=not ready)
if not ready:
    missing = ([] if (folder or files) else ["choose the scripts in Step 1"]) + ([] if key_ok else ["add your API key in Step 2"])
    st.caption("To enable the button, " + " and ".join(missing) + ".")

if go:
    target = load_upload(files) if files else folder
    n_eps = len(list(pathlib.Path(target).glob("*.txt")))
    if n_eps == 0:
        st.error("No .txt episode files were found. Upload Kuku screenplay .txt files or a .zip of them.")
    else:
        bar = st.progress(0.0, "Checking the scripts...")
        try:
            res = run(str(target), spec, progress=lambda i, n: bar.progress(i / n, f"AI review: episode {i + 1} of {n}"),
                      api_key=api_key)
            res["source_label"] = "the demo show" if target == DEMO else (f"{n_eps} uploaded file(s)" if files else "your folder")
            res["run_id"] = time.time()
            st.session_state["c_res"] = res
        except Exception as e:
            st.error(f"The check could not run: {e}")
        bar.empty()

res = st.session_state.get("c_res")
if not res:
    st.stop()

ui.spacer(14)
st.divider()

ai_ran = not res["model"].startswith("offline")
ai_issues = [i for i in res["issues"] if i.get("source") == "model" and i["type"] != "model error"]
rule_issues = [i for i in res["issues"] if i.get("source", "rules") == "rules"]
rid = res["run_id"]

if res["episodes"] < 2:
    ui.callout(f"Only {res['episodes']} episode was checked. Continuity problems show up when episodes are compared, "
               "so add at least two for meaningful results.", "warn")

view = "rules"
if ai_ran:
    if ai_issues:
        view = "ai"
    else:
        reason = next((i["title"] for i in res["issues"] if i["type"] == "model error"), "it returned no findings")
        ui.callout(f"The AI review did not return any findings ({html.escape(reason.split(': ', 1)[-1])}). "
                   "Showing the rule results instead.", "warn")

head_l, head_r = st.columns([3, 2])
with head_r:
    if ai_ran and ai_issues:
        st.markdown('<p class="muted" style="text-align:right;margin-bottom:4px">Results from</p>', unsafe_allow_html=True)
        picked = st.segmented_control("Results from", ["ai", "rules", "both"], default="ai", key=f"view-{rid}",
                                      format_func={"ai": "AI review", "rules": "Rules", "both": "Both"}.get,
                                      label_visibility="collapsed")
        view = picked or "ai"
scoped = {"ai": ai_issues, "rules": rule_issues, "both": ai_issues + rule_issues}[view]
view_name = {"ai": "AI review", "rules": "Rule checks", "both": "AI review and rule checks"}[view]
with head_l:
    st.markdown(f'<p class="sec-title">{view_name}</p><p class="sec-sub">{len(scoped)} findings in {res["episodes"]} '
                f'episodes of {res.get("source_label", "the scripts")}, checked in {res["seconds"]} s.</p>',
                unsafe_allow_html=True)

counts = {k: sum(1 for i in scoped if i["severity"] == k) for k in SEV}
ui.stat_cards([("Episodes", res["episodes"], "#18181B", res["model"].split(" (")[0])]
              + [(SEV[k][0], counts[k], SEV[k][1], CARD_HINT[k]) for k in SEV])

if view in ("ai", "both"):
    cov = ai_coverage(res)
    if cov:
        nums, found, failed = cov
        rows = []
        for n in nums:
            if n in failed:
                rows.append(f'<span class="tag" style="background:#FFFBEB;color:#B45309" title="{html.escape(failed[n])}">'
                            f'Episode {n}: not reviewed</span>')
            elif found[n]:
                rows.append(f'<span class="tag" style="background:#ECFDF5;color:#047857">Episode {n}: '
                            f'{found[n]} finding{"s" if found[n] != 1 else ""}</span>')
            else:
                rows.append(f'<span class="tag">Episode {n}: nothing found</span>')
        st.markdown('<p class="muted" style="margin-bottom:6px"><b>AI coverage.</b> The AI reads episodes in order and '
                    'flags a slip in the episode where it first contradicts what came before, so its list can differ '
                    'from the rules.</p>' + "".join(rows), unsafe_allow_html=True)
        if failed:
            first = sorted(failed)[0]
            ui.callout(f"The AI did not review {len(failed)} episode(s), starting with episode {first}: "
                       f"{html.escape(failed[first])}.", "warn")
        ui.spacer(14)

tab_issues, tab_bible, tab_about = st.tabs(["Findings", "Show bible", "How it works"])

with tab_issues:
    if not scoped:
        ui.callout("No continuity problems found in this view.", "info")
    else:
        total = len(scoped)
        opts = ["all"] + [k for k in SEV if counts[k]]
        labels = {"all": f"All  {total}", **{k: f"{SEV[k][0]}  {counts[k]}" for k in SEV}}
        f1, f2 = st.columns([3, 2], gap="large")
        with f1:
            pick = st.segmented_control("Severity", opts, default="all", format_func=labels.get,
                                        key=f"sev-{rid}-{view}", label_visibility="collapsed") or "all"
        with f2:
            q = st.text_input("Search", placeholder="Search by name, episode or word", label_visibility="collapsed")
        shown = [i for i in scoped if (pick == "all" or i["severity"] == pick)
                 and (not q or q.lower() in (i["title"] + " " + i["detail"] + json.dumps(i["evidence"])).lower())]
        st.markdown(f'<p class="muted">Showing {len(shown)} of {total}. Click a finding to see where it is and record '
                    'your decision.</p>', unsafe_allow_html=True)
        for i in shown:
            name, color, bg, _ = SEV[i["severity"]]
            by = "AI review" if i.get("source") == "model" else "Rules"
            with st.expander(f"{name}: {i['title']}"):
                st.markdown(f'{ui.badge(name, color, bg)}<span class="tag">{by}</span>'
                            f'<span class="tag">{html.escape(i["type"])}</span><span class="tag">{i["id"]}</span>',
                            unsafe_allow_html=True)
                if i["detail"]:
                    st.markdown(f'<p style="margin:12px 0">{html.escape(i["detail"])}</p>', unsafe_allow_html=True)
                if i["suggested_fix"]:
                    ui.callout(f"<b>Suggested fix:</b> {html.escape(i['suggested_fix'])}", "ok")
                if i["evidence"]:
                    st.markdown('<p class="muted">Where it appears</p>', unsafe_allow_html=True)
                    st.dataframe([{"Episode": e["episode"], "Line": e["line"] or "", "Text": e["text"]} for e in i["evidence"]],
                                 hide_index=True, use_container_width=True)
                    if i["evidence_count"] > len(i["evidence"]):
                        st.caption(f"and {i['evidence_count'] - len(i['evidence'])} more places")
                st.radio("Your decision", ["Undecided", "Fix", "Intended", "Not an issue"], key=f"d-{i['id']}",
                         horizontal=True, help="Fix: a real mistake. Intended: done on purpose. Not an issue: the tool was wrong.")

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(["id", "severity", "found_by", "title", "suggested_fix", "your_decision"])
        for i in scoped:
            w.writerow([i["id"], i["severity"], i.get("source", "rules"), i["title"], i["suggested_fix"],
                        st.session_state.get(f"d-{i['id']}", "Undecided")])
        ui.spacer(14)
        d1, d2 = st.columns(2)
        d1.download_button("Download these findings and decisions (CSV)", buf.getvalue(), "continuity_findings.csv",
                           use_container_width=True)
        d2.download_button("Download everything (JSON)",
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

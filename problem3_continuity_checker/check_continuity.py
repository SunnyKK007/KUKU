"""
Continuity checker for AI microdrama scripts.

  python3 -m problem3_continuity_checker.check_continuity --input "<folder of episode .txt>" --model offline
  python3 -m problem3_continuity_checker.check_continuity --input "<folder>" --model gemini:gemini-2.5-flash

Writes to --out: continuity_report.md, issues.json, issues.csv, show_bible.json
"""
from __future__ import annotations

import argparse
import csv
import json
import pathlib
import time

from common.llm import LLM
from common.screenplay import load_show
from problem3_continuity_checker.bible import build_bible
from problem3_continuity_checker.checks import SEV_ORDER, run_checks
from problem3_continuity_checker.llm_check import run_llm_checks


def run(folder: str, model: str | None = "offline", out: str | None = None, progress=None) -> dict:
    t0 = time.time()
    show = load_show(folder)
    issues = run_checks(show)
    llm = LLM(model)
    facts, dropped = [], 0
    if llm.available:
        extra, facts, dropped = run_llm_checks(llm, show, progress=progress)
        issues.extend(extra)
        issues.sort(key=lambda i: (SEV_ORDER.get(i["severity"], 3), i.get("source") != "rules", -i["evidence_count"]))
        for n, i in enumerate(issues, 1):
            i["id"] = f"C{n:03d}"
    res = {"show_folder": str(folder), "episodes": len(show), "model": llm.label(),
           "seconds": round(time.time() - t0, 1), "issue_counts": {
               s: sum(1 for i in issues if i["severity"] == s) for s in SEV_ORDER},
           "model_issues_dropped_unquoted": dropped, "usage": llm.cost_report(),
           "issues": issues, "story_facts": facts, "bible": build_bible(show)}
    if out:
        write(res, pathlib.Path(out))
    return res


def write(res: dict, out: pathlib.Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "issues.json").write_text(json.dumps({k: v for k, v in res.items() if k != "bible"}, indent=2, ensure_ascii=False))
    (out / "show_bible.json").write_text(json.dumps(res["bible"], indent=2, ensure_ascii=False))
    with open(out / "issues.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "severity", "type", "title", "episodes", "first_evidence", "suggested_fix", "source"])
        for i in res["issues"]:
            eps = sorted({e["episode"] for e in i["evidence"]})
            w.writerow([i["id"], i["severity"], i["type"], i["title"], " ".join(map(str, eps)),
                        i["evidence"][0]["text"] if i["evidence"] else "", i["suggested_fix"], i.get("source", "rules")])
    name = pathlib.Path(res["show_folder"]).name
    md = [f"# Continuity report: {name}", "",
          f"- Episodes checked: {res['episodes']}. Model: {res['model']}. Time: {res['seconds']}s",
          "- Issues by severity: " + ", ".join(f"{k} {v}" for k, v in res["issue_counts"].items()),
          "", "Severity guide: **high** is spoken aloud (heard, subtitled, dubbed); **medium** reaches "
          "video prompts or voice mapping; **low** is worth a look; **info** is format only.", "",
          "| ID | Severity | Type | Issue |", "|---|---|---|---|"]
    for i in res["issues"]:
        md.append(f"| {i['id']} | {i['severity']} | {i['type']} | {i['title'].replace('|', '/')} |")
    md += ["", "## Details", ""]
    for i in res["issues"]:
        md += [f"### {i['id']} · {i['title']}", "", f"{i['detail']}", "",
               f"**Suggested fix:** {i['suggested_fix']}", "", "Evidence:" if i["evidence"] else ""]
        for e in i["evidence"]:
            md.append(f"- E{e['episode']} line {e['line']}: {e['text']}")
        if i["evidence_count"] > len(i["evidence"]):
            md.append(f"- ...and {i['evidence_count'] - len(i['evidence'])} more")
        md.append("")
    b = res["bible"]
    md += ["## Show bible (built by code)", "", "| Speaker label | Lines | Episodes | Typical delivery |", "|---|---|---|---|"]
    for c in b["characters"][:25]:
        md.append(f"| {c['label']} | {c['lines']} | {c['first_episode']}-{c['last_episode']} | {', '.join(c['typical_delivery'])} |")
    (out / "continuity_report.md").write_text("\n".join(md), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", default="outputs/problem3")
    a = ap.parse_args()
    res = run(a.input, a.model, a.out)
    print(f"{res['episodes']} episodes, model={res['model']}, {res['seconds']}s, issues: {res['issue_counts']}")
    for i in res["issues"][:12]:
        print(f"  {i['id']} [{i['severity']}] {i['title'][:110]}")
    print(f"Report: {a.out}/continuity_report.md")


if __name__ == "__main__":
    main()

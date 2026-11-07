"""
Run every persona in test_cases.json through the engine and write the raw,
unedited transcripts plus automatic checks.

    python3 -m p2_lawyer.run_tests --model offline
    python3 -m p2_lawyer.run_tests --model groq:llama-3.3-70b-versatile --out outputs/p2_groq

Outputs: <out>/<case_id>.md, <out>/summary.json, <out>/guardrail_tests.json
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import logging
import pathlib
import re
import time

from common.llm import PRICE_PER_M, ROOT

from . import test_model_stub, test_validator
from .engine import DISCLAIMER, Session
from .validator import validate

HERE = pathlib.Path(__file__).resolve().parent
TODAY = dt.date(2026, 11, 8)   # pinned so re-runs give the same transcripts


def run_case(case: dict, model: str) -> tuple[str, dict]:
    s = Session(model=model, today=TODAY)
    exp = case["expect"]
    s.reply(case["opening"])
    answered = {}
    for _ in range(14):
        c = s.case
        ps = c.pending_slot
        if ps is None or c.status in ("ready", "out_of_scope"):
            break
        if ps == "__type__" and "__type__" not in case["answers"]:
            break
        answered[ps] = answered.get(ps, 0) + 1
        if answered[ps] > 2:   # the engine keeps asking the same thing: stop, this is a failure to record
            break
        s.reply(case["answers"].get(ps, "skip"))
    for msg in case.get("followups", []):
        s.reply(msg)

    stand = docs_out = None
    if s.case.problem_type and s.case.status != "out_of_scope":
        stand = s.where_i_stand()
        docs_out = s.documents_reply()
        if case.get("practice_reply"):
            s.reply("practise")
            s.reply(case["practice_reply"])
            s.reply("stop")
    sources = s.sources_reply()
    docs = s.documents()

    # ---------------------------------------------------------- checks
    c = s.case
    assistant_texts = [m["text"] for m in s.transcript if m["role"] == "assistant"] + [d["text"] for d in docs]
    leaked = [v for t in assistant_texts for v in validate(t).violations]
    codes = {e["code"] for e in c.escalations}
    checks = {}
    checks["problem_type"] = c.problem_type == exp.get("problem_type")
    checks["escalation"] = (c.needs_lawyer() == exp.get("escalate", False)
                            and set(exp.get("escalation_codes", [])) <= codes)
    checks["no_unverified_citations_shown"] = not leaked
    checks["notice_generated"] = bool(docs) == exp.get("notice", False)
    if "missing_proof" in exp:
        checks["missing_proof_list"] = bool(c.missing_proof()) == exp["missing_proof"]
    if "language" in exp:
        checks["language"] = c.language == exp["language"]
    if "amount" in exp:
        checks["amount_extracted"] = c.facts.get("amount") == exp["amount"]
    if "proof_strength" in exp:
        checks["proof_strength"] = c.proof_strength() == exp["proof_strength"]
    if exp.get("caselaw_refusal"):
        checks["caselaw_refused"] = any(m.get("kind") == "refusal" for m in s.transcript if m["role"] == "assistant")
    if exp.get("cards_include"):
        stand_cited = stand["cited"] if stand else []
        checks["right_law_cards"] = set(exp["cards_include"]) <= set(stand_cited)
    if c.needs_lawyer():
        checks["legal_aid_offered"] = any("15100" in t for t in assistant_texts)

    # ---------------------------------------------------------- transcript
    md = [f"# {case['id']}", "", f"**Persona:** {case['persona']}", "",
          f"**Model:** {s.model_label}  |  **Run date (pinned):** {TODAY}  |  Raw output, not edited.", "",
          f"> {DISCLAIMER}", "", "## Conversation", ""]
    for m in s.transcript:
        who = "User" if m["role"] == "user" else f"Assistant ({m.get('kind', '')})"
        md.append(f"**{who}:**\n\n{m['text']}\n")
    md += ["## Case file (as built)", "", "```json", json.dumps(c.to_dict(), ensure_ascii=False, indent=2, default=str),
           "```", "", "## Documents generated", ""]
    for d in docs:
        md += [f"### {d['title']} (`{d['filename']}`)", "", "```", d["text"], "```", ""]
    if not docs:
        md.append("_None (out of scope or problem not identified)._\n")
    md += ["## Sources used in 'Where I stand'", "", stand["sources_md"] if stand else "_n/a_", "",
           "## Guardrail log (citations blocked before reaching the user)", ""]
    md += [f"- {g['type']}: `{g['text']}` ({g['reason']})" for g in s.guardrail_log] or ["- none"]
    md += ["", "## Automatic checks", ""]
    md += [f"- {'PASS' if v else 'FAIL'}: {k}" for k, v in checks.items()]
    if exp.get("note"):
        md += ["", f"Note: {exp['note']}"]
    if s.model_error:
        md += ["", f"Model error during run: `{s.model_error}`"]
    result = {"id": case["id"], "pass": all(checks.values()), "checks": checks,
              "detected": {"problem_type": c.problem_type, "language": c.language,
                           "amount": c.facts.get("amount"), "escalations": sorted(codes),
                           "proof_strength": c.proof_strength(), "missing_proof": [m[0] for m in c.missing_proof()]},
              "turns": sum(1 for m in s.transcript if m["role"] == "user"),
              "guardrail_blocked": len(s.guardrail_log), "cost": s.cost_report()}
    return "\n".join(md) + "\n", result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="offline")
    ap.add_argument("--out", default=str(ROOT / "outputs" / "p2"))
    ap.add_argument("--only", default=None, help="run one case id")
    args = ap.parse_args()
    logging.basicConfig(level=logging.ERROR)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cases = json.loads((HERE / "test_cases.json").read_text(encoding="utf-8"))["cases"]
    if args.only:
        cases = [c for c in cases if c["id"] == args.only]
    results = []
    t0 = time.time()
    for case in cases:
        md, res = run_case(case, args.model)
        (out / f"{case['id']}.md").write_text(md, encoding="utf-8")
        results.append(res)
        print(f"{'PASS' if res['pass'] else 'FAIL'}  {case['id']}  "
              + " ".join(f"{k}={'ok' if v else 'X'}" for k, v in res["checks"].items()))

    g = test_validator.run(verbose=False)
    (out / "guardrail_tests.json").write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    ms = test_model_stub.run(verbose=False)
    (out / "model_stub_test.json").write_text(json.dumps(ms, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

    n = len(results)
    est_p = sum(r["cost"]["estimated_if_model_mode"]["prompt_tokens"] for r in results) / max(n, 1)
    est_c = sum(r["cost"]["estimated_if_model_mode"]["completion_tokens"] for r in results) / max(n, 1)
    per_1000 = {m: round(1000 * (est_p / 1e6 * p[0] + est_c / 1e6 * p[1]), 2) for m, p in PRICE_PER_M.items()}
    summary = {
        "model": results[0]["cost"]["model"] if results else args.model,
        "run_date_pinned": str(TODAY),
        "seconds": round(time.time() - t0, 1),
        "cases_passed": sum(r["pass"] for r in results), "cases_total": n,
        "checks_passed": sum(sum(r["checks"].values()) for r in results),
        "checks_total": sum(len(r["checks"]) for r in results),
        "guardrail_unit_tests": f"{g['passed']}/{g['total']}",
        "model_mode_stub_safety_checks": f"{ms['passed']}/{ms['total']}",
        "estimated_tokens_per_conversation_if_model_mode": {"prompt": round(est_p), "completion": round(est_c)},
        "estimated_usd_per_1000_conversations_at_paid_rates": per_1000,
        "cases": results,
    }
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"\n{summary['cases_passed']}/{n} cases fully passed; {summary['checks_passed']}/{summary['checks_total']} "
          f"checks; guardrail unit tests {summary['guardrail_unit_tests']}; "
          f"model-mode stub safety checks {summary['model_mode_stub_safety_checks']}")
    print(f"Est. tokens/conversation in model mode: {summary['estimated_tokens_per_conversation_if_model_mode']}; "
          f"USD per 1,000 conversations: {per_1000}")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()

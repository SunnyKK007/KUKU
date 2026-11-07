"""
Quality check for a promo run.

1. Hard checks on every promo (code): 20-60s total, segments inside the
   episode, no cut in the middle of a spoken line, something happens in the
   first 3 seconds.
2. Recall against reference moments: how many must-catch moments appear in
   the top 10 / top 25.

Usage: python3 -m p1_promos.evaluate --run outputs/p1/promos.json --input "<folder>"
"""
from __future__ import annotations

import argparse
import json
import pathlib

from common.screenplay import load_show

HERE = pathlib.Path(__file__).parent


def hard_checks(res: dict, show) -> list[dict]:
    eps = {e.number: e for e in show}
    rows = []
    for p in res["promos"]:
        problems = []
        if not 20 <= p["duration"] <= 60.5:
            problems.append(f"length {p['duration']}s")
        for s in p["segments"]:
            ep = eps[s["episode"]]
            if s["start"] < 0 or s["end"] > ep.duration + 0.05:
                problems.append("segment outside episode")
            for b in ep.dialogue:
                if b.start + 0.05 < s["start"] < b.end - 0.05 or b.start + 0.05 < s["end"] < b.end - 0.05:
                    problems.append(f"cuts mid-line at E{s['episode']} {b.as_text()[:40]}")
        first = p["segments"][0]
        early = [b for b in eps[first["episode"]].window(first["start"], first["start"] + 3)
                 if b.kind != "camera"]
        if not early:
            problems.append("only camera directions in first 3s")
        rows.append({"rank": p["rank"], "ok": not problems, "problems": problems})
    return rows


def recall(res: dict, gold: list[dict], k: int) -> tuple[int, list[str]]:
    caught, missed = 0, []
    for g in gold:
        hit = any(s["episode"] == g["episode"] and s["start"] - 0.5 <= g["t"] <= s["end"] + 0.5
                  for p in res["promos"][:k] for s in p["segments"])
        caught += hit
        if not hit:
            missed.append(g["id"])
    return caught, missed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="outputs/p1/promos.json")
    ap.add_argument("--input", required=True)
    ap.add_argument("--gold", default=str(HERE / "gold_moments.json"))
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    res = json.loads(pathlib.Path(a.run).read_text())
    show = load_show(a.input)
    gold = json.loads(pathlib.Path(a.gold).read_text())["moments"]
    checks = hard_checks(res, show)
    lines = [f"# Evaluation of {a.run}", "", f"Model: {res['model']}", ""]
    ok = sum(c["ok"] for c in checks)
    lines.append(f"Hard checks passed: {ok}/{len(checks)} promos")
    for c in checks:
        if not c["ok"]:
            lines.append(f"- #{c['rank']}: {'; '.join(c['problems'])}")
    for k in (10, 25):
        c, missed = recall(res, gold, k)
        lines.append(f"Reference moments caught in top {k}: {c}/{len(gold)}. Missed: {', '.join(missed) or 'none'}")
    eps_picked = {s["episode"] for p in res["promos"] for s in p["segments"]}
    ep_hits = [g["id"] for g in gold if g["episode"] in eps_picked]
    lines.append(f"Reference episodes that have a promo in the top {len(res['promos'])}: {len(ep_hits)}/{len(gold)}")
    alt_hits = 0
    for g in gold:
        spans = [(s["episode"], s["start"], s["end"]) for p in res["promos"] for s in p["segments"]]
        for p in res["promos"]:
            for alt in p.get("alternates", []):
                for seg in alt["segments"]:
                    e, rng = seg.split(" ", 1)
                    a0, a1 = rng.split("-")
                    to = lambda x: int(x.split(":")[0]) * 60 + float(x.split(":")[1])
                    spans.append((int(e[1:]), to(a0), to(a1)))
        alt_hits += any(e == g["episode"] and s0 - 0.5 <= g["t"] <= s1 + 0.5 for e, s0, s1 in spans)
    lines.append(f"Reference moments caught when the editor also sees each pick's alternates: {alt_hits}/{len(gold)}")
    text = "\n".join(lines)
    print(text)
    if a.out:
        pathlib.Path(a.out).write_text(text + "\n")


if __name__ == "__main__":
    main()

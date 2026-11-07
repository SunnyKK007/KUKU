"""
Promo finder: reads a folder of timestamped microdrama screenplays and returns
ranked 20-60s promos, each with segments, hook, cliffhanger and a reason.

Pipeline
  1. parse      (code)   screenplay -> timestamped beats
  2. generate   (code)   every clip between clean cut points, 20-60s, never mid-line
  3. score      (rules)  hook (first 3s), cliffhanger (last 4s), standalone, intensity
  4. shortlist  (code)   best non-overlapping clips per episode + stitched cold-opens
  5. judge      (model)  optional blind re-score of the shortlist; swappable model
  6. rank       (code)   final score + diversity + funnel position
  7. report     (code)   JSON, CSV, Markdown and an HTML review page for the editor

Usage
  python3 -m p1_promos.find_promos --input "<folder of .txt>" --model offline
  python3 -m p1_promos.find_promos --input "<folder>" --model groq:llama-3.3-70b-versatile
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import time

from common.llm import LLM
from common.screenplay import Episode, fmt, load_show
from p1_promos import signals as S
from p1_promos.judge import judge
from p1_promos.report import write_reports

MIN_LEN, MAX_LEN = 20.0, 60.0
SWEET_LO, SWEET_HI = 28.0, 50.0


# ----------------------------------------------------------------- cut points
def cut_points(ep: Episode) -> tuple[list[float], list[float]]:
    """Starts: shot changes. Ends: shot ends or episode end. Never inside a spoken line."""
    lines = ep.dialogue

    def inside_line(t: float) -> bool:
        return any(b.start + 0.05 < t < b.end - 0.05 for b in lines)

    cams = [b for b in ep.beats if b.kind == "camera"]
    starts = sorted({round(b.start, 2) for b in cams} | {0.0})
    ends = sorted({round(b.end, 2) for b in cams} | {round(ep.duration, 2)})
    return [t for t in starts if not inside_line(t)], [t for t in ends if not inside_line(t)]


def make_segment(ep: Episode, start: float, end: float) -> dict:
    beats = ep.window(start, end)
    return {"episode": ep.number, "start": round(start, 2), "end": round(end, 2),
            "start_tc": fmt(start), "end_tc": fmt(end),
            "script": [b.as_text() for b in beats]}


# ------------------------------------------------------------------- scoring
def score_clip(ep: Episode, start: float, end: float, known: set[str]) -> dict:
    beats = ep.window(start, end)
    dur = end - start
    h_raw, h_beat = S.hook_score(beats, start)
    c_raw, c_beat = S.cliff_score(beats, end, ep.duration)
    alone, notes = S.standalone_score(beats, known)
    body = S.body_intensity(beats, dur)
    hook, cliff, inten = S.squash(h_raw, 4.0), S.squash(c_raw, 4.0), S.squash(body, 6.0)
    fit = 1.0 if SWEET_LO <= dur <= SWEET_HI else 0.92
    total = (0.35 * hook + 0.30 * cliff + 0.20 * alone + 0.15 * inten) * fit
    return {"hook_rule": hook, "cliff_rule": cliff, "standalone_rule": round(alone, 2),
            "intensity_rule": inten, "rule_score": round(total, 3),
            "hook_beat": h_beat.as_text() if h_beat else "",
            "cliff_beat": c_beat.as_text() if c_beat else "",
            "notes": notes, "tropes": S.tropes(beats)}


def overlap(a: tuple[float, float], b: tuple[float, float]) -> float:
    inter = max(0.0, min(a[1], b[1]) - max(a[0], b[0]))
    return inter / min(a[1] - a[0], b[1] - b[0])


def best_clips(ep: Episode, known: set[str], keep: int = 3) -> list[dict]:
    starts, ends = cut_points(ep)
    cands = []
    for s in starts:
        for e in ends:
            if MIN_LEN <= e - s <= MAX_LEN:
                cands.append((s, e, score_clip(ep, s, e, known)))
    cands.sort(key=lambda x: -x[2]["rule_score"])
    chosen: list[tuple[float, float, dict]] = []
    for s, e, sc in cands:                       # non-max suppression
        if all(overlap((s, e), (cs, ce)) < 0.3 for cs, ce, _ in chosen):
            chosen.append((s, e, sc))
        if len(chosen) >= keep:
            break
    out = []
    for s, e, sc in chosen:
        out.append({"type": "continuous", "segments": [make_segment(ep, s, e)],
                    "duration": round(e - s, 2), "entry_episode": ep.number, **sc})
    return out


def stitched_cold_open(ep: Episode, base: dict, known: set[str]) -> dict | None:
    """Cold-open promo: flash the episode's most violent/shocking 3-8s moment first,
    then play a continuous build that ends on a cliffhanger. Common ReelShort pattern."""
    starts, ends = cut_points(ep)
    seg = base["segments"][0]
    best = None
    for s in starts:
        for e in ends:
            if 3.0 <= e - s <= 8.0 and not (seg["start"] <= s < seg["end"]):
                beats = ep.window(s, e)
                inten = sum(S.beat_intensity(b) for b in beats) / (e - s)
                if best is None or inten > best[2]:
                    best = (s, e, inten)
    if not best:
        return None
    fs, fe, _ = best
    total = (fe - fs) + (seg["end"] - seg["start"])
    if total > MAX_LEN:                     # trim the build from the front, at a valid start
        need = total - MAX_LEN
        later = [t for t in starts if t >= seg["start"] + need and seg["end"] - t >= 15]
        if not later:
            return None
        new_start = later[0]
    else:
        new_start = seg["start"]
    flash = make_segment(ep, fs, fe)
    build = make_segment(ep, new_start, seg["end"])
    h_raw, h_beat = S.hook_score(ep.window(fs, fe), fs)
    beats = ep.window(new_start, seg["end"])
    alone, notes = S.standalone_score(beats, known)
    hook = S.squash(h_raw, 4.0)
    cliff = base["cliff_rule"]
    inten = S.squash(S.body_intensity(ep.window(fs, fe) + beats, total), 6.0)
    rule = (0.35 * hook + 0.30 * cliff + 0.20 * (alone - 0.8) + 0.15 * inten)  # stitching risk
    return {"type": "stitched cold open", "segments": [flash, build],
            "duration": round((fe - fs) + (seg["end"] - new_start), 2), "entry_episode": ep.number,
            "hook_rule": hook, "cliff_rule": cliff, "standalone_rule": round(alone - 0.8, 2),
            "intensity_rule": inten, "rule_score": round(rule, 3),
            "hook_beat": h_beat.as_text() if h_beat else "", "cliff_beat": base["cliff_beat"],
            "notes": notes + ["stitched: the flash moment comes from later in the scene, so an "
                              "editor should check continuity of costume and position"],
            "tropes": base["tropes"]}


# -------------------------------------------------------------- final ranking
def _short(text: str, n: int = 110) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n].rsplit(" ", 1)[0] + "..."


def _first_line_within(seg: dict, secs: float) -> str:
    """First spoken line starting within `secs` of the segment start, from its script."""
    for line in seg["script"]:
        m = re.match(r"\[(\d+):(\d+\.\d+)\] (.+?): (.*)$", line)
        if not m:
            continue
        t = int(m.group(1)) * 60 + float(m.group(2))
        who = m.group(3)
        if t > seg["start"] + secs:
            break
        if who.split(" (")[0] not in ("CAMERA", "ACTION", "SFX") and t >= seg["start"] - 0.3:
            return f'{who.split(" (")[0].title()}: "{m.group(4)}"'
    return ""


def describe(p: dict) -> dict:
    """Offline (rules-only) hook / cliffhanger / reason text, from the anchor beats."""
    def clean(t: str) -> str:
        return t.split("] ", 1)[-1]
    hook = _short(clean(p["hook_beat"])) or "no strong beat in first 3s"
    line = _first_line_within(p["segments"][0], 3.0)
    if line and line.split(": ", 1)[-1].strip('"') not in hook:
        hook = f"{hook} | {_short(line, 80)}"
    cliff = _short(clean(p["cliff_beat"]), 140)
    bits = []
    if p["hook_rule"] >= 6: bits.append("opens on a hard shock")
    elif p["hook_rule"] >= 4: bits.append("opens on conflict")
    if p.get("ends_episode"): bits.append("cuts on the writers' own episode cliffhanger")
    elif p["cliff_rule"] >= 5: bits.append("cuts on an unresolved beat")
    if p["standalone_rule"] >= 8: bits.append("stakes are clear without backstory")
    why = f"{p['tropes'][0].capitalize()} promo that " + ", ".join(bits or ["has steady tension"]) + "."
    return {"hook": hook, "cliffhanger": cliff, "why_it_works": why}


def rank(promos: list[dict], top: int) -> list[dict]:
    n_eps = max(p["entry_episode"] for p in promos)
    for p in promos:
        # earlier entry episode = shorter path from ad to the free first episodes
        funnel = 1.0 - 0.06 * (p["entry_episode"] - 1) / max(n_eps - 1, 1)
        j = p.get("judge") or {}
        if j and all(isinstance(j.get(k), int) for k in ("hook_score", "cliff_score", "standalone_score")):
            model = 0.35 * j["hook_score"] + 0.30 * j["cliff_score"] + 0.35 * j["standalone_score"]
            p["final_score"] = round((0.5 * p["rule_score"] + 0.5 * model) * funnel, 3)
        else:
            p["final_score"] = round(p["rule_score"] * funnel, 3)
        p["funnel_factor"] = round(funnel, 3)
    promos.sort(key=lambda p: -p["final_score"])
    # A slate of ads should cover the whole show: one promo per episode, at most
    # three per 5-episode stretch, and no trope more than a third of the slate.
    ranked, alternates, per_block, trope_count = [], [], {}, {}
    used_eps = set()
    for p in promos:
        ep, block, trope = p["entry_episode"], (p["entry_episode"] - 1) // 5, p["tropes"][0]
        if ep in used_eps or per_block.get(block, 0) >= 3 or trope_count.get(trope, 0) >= max(3, top // 3):
            alternates.append(p)
            continue
        used_eps.add(ep)
        per_block[block] = per_block.get(block, 0) + 1
        trope_count[trope] = trope_count.get(trope, 0) + 1
        p["rank"] = len(ranked) + 1
        ranked.append(p)
        if len(ranked) >= top:
            break
    # Short shows: if the slate rules leave empty slots, fill them with the best
    # remaining clips, still skipping near-duplicates of a pick already made.
    for p in sorted(alternates, key=lambda x: -x["final_score"]):
        if len(ranked) >= top:
            break
        span = (p["segments"][-1]["start"], p["segments"][-1]["end"])
        if any(r["entry_episode"] == p["entry_episode"] and
               overlap(span, (r["segments"][-1]["start"], r["segments"][-1]["end"])) > 0.3 for r in ranked):
            continue
        p["rank"] = len(ranked) + 1
        p["notes"] = p["notes"] + ["added to fill the slate: same episode as another pick"]
        ranked.append(p)
    alternates = [a for a in alternates if "rank" not in a]
    for p in ranked:
        p["alternates"] = [
            {"segments": [f"E{s['episode']} {s['start_tc']}-{s['end_tc']}" for s in a["segments"]],
             "type": a["type"], "final_score": a["final_score"]}
            for a in alternates if a["entry_episode"] == p["entry_episode"]][:2]
    return ranked


def run(folder: str, model: str = "offline", top: int = 25, judge_k: int = 40,
        out: str | None = None) -> dict:
    t0 = time.time()
    show = load_show(folder)
    known = {b.speaker.upper() for e in show for b in e.dialogue}
    llm = LLM(model)
    promos = []
    for ep in show:
        clips = best_clips(ep, known)
        for c in clips:
            seg = c["segments"][0]
            c["ends_episode"] = abs(seg["end"] - ep.duration) <= 1.5
        promos.extend(clips)
        if clips:
            st = stitched_cold_open(ep, clips[0], known)
            if st:
                st["ends_episode"] = clips[0]["ends_episode"]
                promos.append(st)
    # shortlist for the (optional) model judge
    promos.sort(key=lambda p: -p["rule_score"])
    judged = 0
    approx_tokens = 0
    for p in promos[:judge_k]:
        approx_tokens += sum(len(l) for s in p["segments"] for l in s["script"]) // 4 + 450
        if llm.available:
            p["judge"] = judge(llm, p)
            judged += 1
    ranked = rank(promos, top)
    for p in ranked:
        d = describe(p)
        j = p.get("judge") or {}
        p["hook"] = j.get("hook") or d["hook"]
        p["cliffhanger"] = j.get("cliffhanger") or d["cliffhanger"]
        p["why_it_works"] = j.get("why_it_works") or d["why_it_works"]
        p["text_source"] = "model" if j.get("hook") else "rules"
    result = {
        "show_folder": str(folder), "episodes": len(show),
        "runtime_minutes": round(sum(e.duration for e in show) / 60, 1),
        "model": llm.label(), "candidates_kept": len(promos), "judged": judged,
        "approx_tokens_if_judged": approx_tokens + judge_k * 120,
        "usage": llm.cost_report(), "seconds": round(time.time() - t0, 1),
        "parse_warnings": {e.number: e.warnings for e in show if e.warnings},
        "promos": ranked,
    }
    if out:
        write_reports(result, pathlib.Path(out))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--input", required=True, help="folder of episode .txt screenplays")
    ap.add_argument("--model", default=None, help="provider:model, or 'offline' (default: first key in .env)")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--judge-k", type=int, default=40, help="how many shortlisted clips the model re-scores")
    ap.add_argument("--out", default="outputs/p1")
    a = ap.parse_args()
    res = run(a.input, a.model, a.top, a.judge_k, a.out)
    print(f"{res['episodes']} episodes, {res['candidates_kept']} shortlisted, model={res['model']}, "
          f"{res['seconds']}s. Top 5:")
    for p in res["promos"][:5]:
        segs = " + ".join(f"E{s['episode']} {s['start_tc']}-{s['end_tc']}" for s in p["segments"])
        print(f"  #{p['rank']} [{p['final_score']:.2f}] {segs} ({p['duration']:.0f}s) {p['tropes'][0]}")
    print(f"Reports written to {a.out}/")


if __name__ == "__main__":
    main()

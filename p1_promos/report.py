"""Writes promos.json, promos.csv, promos.md and review.html (editor approve/reject page)."""
from __future__ import annotations

import csv
import html
import json
import pathlib


def seg_str(p: dict) -> str:
    return " + ".join(f"E{s['episode']} {s['start_tc']}-{s['end_tc']}" for s in p["segments"])


def write_reports(res: dict, out: pathlib.Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    (out / "promos.json").write_text(json.dumps(res, indent=2, ensure_ascii=False))

    with open(out / "promos.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["rank", "final_score", "type", "segments", "duration_s", "hook", "cliffhanger",
                    "why_it_works", "hook_rule", "cliff_rule", "standalone_rule", "tropes", "text_source"])
        for p in res["promos"]:
            w.writerow([p["rank"], p["final_score"], p["type"], seg_str(p), p["duration"], p["hook"],
                        p["cliffhanger"], p["why_it_works"], p["hook_rule"], p["cliff_rule"],
                        p["standalone_rule"], "; ".join(p["tropes"]), p["text_source"]])

    md = [f"# Promo picks: {pathlib.Path(res['show_folder']).name}", "",
          f"- Episodes read: {res['episodes']} ({res['runtime_minutes']} min of runtime)",
          f"- Model: {res['model']}. Clips judged by model: {res['judged']}",
          f"- Shortlisted candidates: {res['candidates_kept']}. Run time: {res['seconds']}s",
          "", "## Ranking", "",
          "| # | Score | Segments | Length | Type | Trope |", "|---|---|---|---|---|---|"]
    for p in res["promos"]:
        md.append(f"| {p['rank']} | {p['final_score']:.2f} | {seg_str(p)} | {p['duration']:.0f}s | "
                  f"{p['type']} | {p['tropes'][0]} |")
    md += ["", "## Details", ""]
    for p in res["promos"]:
        md += [f"### #{p['rank']}  {seg_str(p)}  ({p['duration']:.0f}s)", "",
               f"- **Hook:** {p['hook']}", f"- **Cliffhanger:** {p['cliffhanger']}",
               f"- **Why it works:** {p['why_it_works']}",
               f"- **Scores:** hook {p['hook_rule']}, cliffhanger {p['cliff_rule']}, standalone "
               f"{p['standalone_rule']}, intensity {p['intensity_rule']} (rules)"
               + (f"; model hook {p['judge'].get('hook_score')}, cliff {p['judge'].get('cliff_score')}, "
                  f"standalone {p['judge'].get('standalone_score')}" if p.get("judge") and "error" not in p["judge"] else ""),
               f"- **Watch-outs:** {'; '.join(p['notes']) or 'none found by rules'}"
               + (f"; model: {p['judge'].get('risk')}" if p.get("judge") and p['judge'].get('risk') else ""),
               "", "<details><summary>Script of the clip</summary>", "", "```"]
        for i, s in enumerate(p["segments"], 1):
            if len(p["segments"]) > 1:
                md.append(f"--- segment {i}: E{s['episode']} {s['start_tc']}-{s['end_tc']} ---")
            md += s["script"]
        md += ["```", "", "</details>", ""]
    (out / "promos.md").write_text("\n".join(md), encoding="utf-8")
    (out / "review.html").write_text(review_html(res), encoding="utf-8")


def review_html(res: dict) -> str:
    cards = []
    for p in res["promos"]:
        script = "\n".join(
            ([f"--- segment {i}: E{s['episode']} {s['start_tc']}-{s['end_tc']} ---"] if len(p["segments"]) > 1 else [])
            + s["script"] for i, s in enumerate(p["segments"], 1)) if False else "\n".join(
            "\n".join(([f"--- segment {i}: E{s['episode']} {s['start_tc']}-{s['end_tc']} ---"]
                       if len(p["segments"]) > 1 else []) + s["script"]) for i, s in enumerate(p["segments"], 1))
        e = html.escape
        cards.append(f"""
<article class="card" data-rank="{p['rank']}">
  <header><span class="rank">#{p['rank']}</span><span class="segs">{e(seg_str(p))}</span>
  <span class="pill">{p['duration']:.0f}s</span><span class="pill">{e(p['type'])}</span>
  <span class="pill">{e(p['tropes'][0])}</span><span class="score">{p['final_score']:.2f}</span></header>
  <dl><dt>Hook</dt><dd>{e(p['hook'])}</dd><dt>Cliffhanger</dt><dd>{e(p['cliffhanger'])}</dd>
  <dt>Why</dt><dd>{e(p['why_it_works'])}</dd><dt>Watch-outs</dt><dd>{e('; '.join(p['notes']) or 'none')}</dd></dl>
  <details><summary>Script</summary><pre>{e(script)}</pre></details>
  <div class="actions"><button data-v="approve">Approve</button><button data-v="reject">Reject</button>
  <input placeholder="Note for the tool (why?)"></div>
</article>""")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Promo Review</title>
<style>
:root{{--bg:#f7f6f2;--card:#fff;--ink:#1d1d1b;--muted:#6b6a65;--line:#e4e2db;--ok:#1f7a4d;--no:#b3261e;--acc:#3b4cca}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151514;--card:#1f1f1d;--ink:#ecebe6;--muted:#a3a29b;--line:#33332f;--ok:#5cc28f;--no:#ff8a80;--acc:#9aa5ff}}}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif}}
main{{max-width:900px;margin:0 auto;padding:24px 16px}} h1{{font-size:22px;margin:0 0 4px}}
.meta{{color:var(--muted);margin-bottom:16px}} .card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0}}
.card header{{display:flex;flex-wrap:wrap;gap:8px;align-items:center}} .rank{{font-weight:700;font-size:18px}}
.segs{{font-family:ui-monospace,monospace}} .pill{{border:1px solid var(--line);border-radius:99px;padding:0 8px;font-size:12px;color:var(--muted)}}
.score{{margin-left:auto;font-weight:600;color:var(--acc)}} dl{{display:grid;grid-template-columns:110px 1fr;gap:4px 10px;margin:10px 0}}
dt{{color:var(--muted)}} dd{{margin:0}} pre{{white-space:pre-wrap;font-size:12px;background:var(--bg);padding:10px;border-radius:6px;max-height:320px;overflow:auto}}
.actions{{display:flex;gap:8px;flex-wrap:wrap}} button{{border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:6px;padding:4px 12px;cursor:pointer}}
input{{flex:1;min-width:180px;border:1px solid var(--line);background:var(--card);color:var(--ink);border-radius:6px;padding:4px 8px}}
.card.approve{{border-color:var(--ok);box-shadow:inset 4px 0 var(--ok)}} .card.reject{{border-color:var(--no);box-shadow:inset 4px 0 var(--no);opacity:.7}}
.bar{{position:sticky;top:0;background:var(--bg);padding:8px 0;display:flex;gap:10px;align-items:center;z-index:2}}
@media (max-width:560px){{dl{{grid-template-columns:1fr}}}}
</style></head><body><main>
<h1>Promo review</h1>
<div class="meta">{html.escape(pathlib.Path(res['show_folder']).name)} · {res['episodes']} episodes · model: {html.escape(res['model'])}</div>
<div class="bar"><span id="tally">0 approved · 0 rejected</span><button id="export">Export decisions (JSON)</button></div>
{''.join(cards)}
</main><script>
const KEY='promo-review-'+location.pathname; let st={{}};
try{{st=JSON.parse(localStorage.getItem(KEY)||'{{}}')}}catch(e){{}}
function save(){{try{{localStorage.setItem(KEY,JSON.stringify(st))}}catch(e){{}};tally()}}
function tally(){{const v=Object.values(st);document.getElementById('tally').textContent=
 v.filter(x=>x.v==='approve').length+' approved · '+v.filter(x=>x.v==='reject').length+' rejected'}}
document.querySelectorAll('.card').forEach(c=>{{const r=c.dataset.rank, inp=c.querySelector('input');
 if(st[r]){{c.classList.add(st[r].v||'');inp.value=st[r].note||''}}
 c.querySelectorAll('button').forEach(b=>b.onclick=()=>{{c.classList.remove('approve','reject');c.classList.add(b.dataset.v);
  st[r]={{...(st[r]||{{}}),v:b.dataset.v}};save()}});
 inp.oninput=()=>{{st[r]={{...(st[r]||{{}}),note:inp.value}};save()}}}});
document.getElementById('export').onclick=()=>{{const a=document.createElement('a');
 a.href=URL.createObjectURL(new Blob([JSON.stringify(st,null,2)],{{type:'application/json'}}));
 a.download='promo_decisions.json';a.click()}};tally();
</script></body></html>"""

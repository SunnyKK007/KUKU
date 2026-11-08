"""
Model judge: re-scores the rule-based shortlist.

The judge sees ONLY the clip's script lines, never the show summary. That
simulates the real audience, a stranger scrolling TikTok, so "makes sense on
its own" is tested directly instead of assumed.
"""
from __future__ import annotations

from common.llm import LLM

SYSTEM = """You are a senior promo editor for vertical microdrama apps like ReelShort and DramaBox.
You judge candidate promo clips (20-60s) for TikTok/Reels/Shorts. You only see the clip's
timestamped script, exactly what a new viewer would see and hear. You know nothing else
about the show.

Score strictly, 1-10:
- hook_score: does something in the FIRST 3 SECONDS stop a scrolling thumb (slap, reveal,
  shocking line, danger)? A calm establishing shot or small talk scores low.
- cliff_score: does it END on an unresolved moment that makes the viewer need the next
  episode? Ending on resolution, a hug or a calm beat scores low.
- standalone_score: can a stranger tell who wants what and what is at stake from this clip
  alone? Unexplained names and references to earlier events score low.

Reply with JSON only:
{"viewer_understands": "one sentence: what a stranger thinks is happening",
 "hook": "what happens in the first 3 seconds, quoted or described, max 15 words",
 "hook_score": int,
 "cliffhanger": "the unresolved final moment, max 15 words",
 "cliff_score": int,
 "standalone_score": int,
 "why_it_works": "one line for a marketing lead",
 "risk": "biggest weakness of this clip, or 'none'"}"""


def clip_script(segments: list[dict]) -> str:
    parts = []
    for i, seg in enumerate(segments, 1):
        if len(segments) > 1:
            parts.append(f"--- SEGMENT {i} (cut) ---")
        parts.extend(seg["script"])
    return "\n".join(parts)


def judge(llm: LLM, promo: dict) -> dict | None:
    if not llm.available:
        return None
    user = ("Candidate promo, " + f"{promo['duration']:.0f} seconds"
            + (", stitched from several cuts" if len(promo["segments"]) > 1 else "") + ":\n\n"
            + clip_script(promo["segments"]))
    try:
        out = llm.json(SYSTEM, user, max_tokens=500)
    except Exception as e:
        return {"error": str(e)[:200]}
    for k in ("hook_score", "cliff_score", "standalone_score"):
        try:
            out[k] = max(1, min(10, int(out.get(k, 0))))
        except (TypeError, ValueError):
            out[k] = None
    return out

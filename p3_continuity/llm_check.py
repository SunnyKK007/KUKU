"""
Optional model pass: reads episodes in order with a rolling list of story facts
and reports contradictions the rules cannot see (a dead character speaking, an
injury that vanishes, the same person under two descriptions).

Guardrail: every model issue must quote the episode text. If the quote is not
found in that episode, the issue is dropped as a possible hallucination.
"""
from __future__ import annotations

import difflib
import re

from common.llm import LLM
from common.screenplay import Episode

SYSTEM = """You are the continuity supervisor for an AI-generated vertical drama series.
You get the story facts established so far and the next episode's script.
Find CONTRADICTIONS between the new episode and the facts: a character's name, surname,
title, relationship, appearance, injury or status changing; a place or object renamed;
the same person given two different descriptions or labels; timeline errors.
Do not report style issues, plot holes you merely suspect, or anything you cannot quote.

Reply with JSON only:
{"issues": [{"type": "name|title|relationship|appearance|injury|status|object|label|timeline",
             "severity": "high|medium|low",
             "title": "short description",
             "earlier_fact": "the established fact it contradicts",
             "quote": "exact words copied from THIS episode's script",
             "suggested_fix": "one line"}],
 "new_facts": ["short durable facts this episode establishes, max 8"]}"""


def compact(ep: Episode, limit: int = 9000) -> str:
    lines = [f"EPISODE {ep.number}. Logline: {ep.logline}"]
    for b in ep.beats:
        if b.kind == "dialogue":
            lines.append(f"{b.speaker}: {b.text}")
        elif b.kind == "action":
            lines.append(f"(action) {b.text}")
        elif b.kind == "camera" and re.search(r"\b[A-Z][a-z]{3,}\b", b.text):
            lines.append(f"(shot) {b.text}")
    text = "\n".join(lines)
    return text[:limit]


def quote_found(quote: str, ep: Episode) -> bool:
    if not quote or len(quote) < 4:
        return False
    hay = " ".join([ep.logline] + [b.text for b in ep.beats] + [b.speaker for b in ep.dialogue]).lower()
    q = quote.lower().strip(' "\'')
    if q in hay:
        return True
    m = difflib.SequenceMatcher(None, hay, q).find_longest_match(0, len(hay), 0, len(q))
    return m.size >= 0.8 * len(q)


def run_llm_checks(llm: LLM, show: list[Episode], max_facts: int = 80, progress=None) -> tuple[list[dict], list[str], int]:
    facts: list[str] = []
    issues: list[dict] = []
    dropped = 0
    for i, ep in enumerate(show):
        if progress:
            progress(i, len(show))
        user = ("FACTS SO FAR:\n" + ("\n".join(f"- {f}" for f in facts[-max_facts:]) or "- none yet")
                + "\n\nNEXT EPISODE SCRIPT:\n" + compact(ep))
        try:
            out = llm.json(SYSTEM, user, max_tokens=1200)
        except Exception as e:
            issues.append({"type": "model error", "severity": "info", "title": f"E{ep.number}: {str(e)[:120]}",
                           "detail": "", "evidence": [], "evidence_count": 0, "suggested_fix": "", "source": "model"})
            continue
        for it in out.get("issues", []) or []:
            if not quote_found(it.get("quote", ""), ep):
                dropped += 1
                continue
            issues.append({"type": f"model: {it.get('type', 'other')}",
                           "severity": it.get("severity", "low") if it.get("severity") in ("high", "medium", "low") else "low",
                           "title": f"E{ep.number}: {it.get('title', '')}",
                           "detail": f"Earlier: {it.get('earlier_fact', '')}",
                           "evidence": [{"episode": ep.number, "line": 0, "file": ep.path.name, "text": it.get("quote", "")[:160]}],
                           "evidence_count": 1, "suggested_fix": it.get("suggested_fix", ""), "source": "model"})
        facts.extend(f"E{ep.number}: {f}" for f in (out.get("new_facts") or [])[:8])
    return issues, facts, dropped

"""Loads the closed set of verified law cards. The model never adds to this set."""
from __future__ import annotations

import json
import pathlib
from functools import lru_cache

CARDS_PATH = pathlib.Path(__file__).resolve().parent / "law_cards.json"


@lru_cache(maxsize=1)
def load() -> dict:
    data = json.loads(CARDS_PATH.read_text(encoding="utf-8"))
    data["by_id"] = {c["id"]: c for c in data["cards"]}
    return data


def card(card_id: str) -> dict:
    return load()["by_id"][card_id]


def cards_for(problem_type: str) -> list[dict]:
    """Cards selected by rule for a problem type (plus the always-on legal-aid cards)."""
    return [c for c in load()["cards"]
            if problem_type in c["applies_to"] or "all" in c["applies_to"]]


def short_cite(card_id: str) -> str:
    """Human citation string for a card, e.g. 'Section 69 of the Consumer Protection Act, 2019'."""
    c = card(card_id)
    parts = []
    for ci in c["cites"]:
        inst = ci["instrument"]
        word = "Rule" if "Rules" in inst else "Section"
        parts.append(f"{word} {ci['section']} of the {inst}" if ci["section"] else f"the {inst}")
    return "; ".join(parts)


def sources_markdown(card_ids) -> str:
    """'Sources used' block with official links for every card cited."""
    lines = []
    seen = set()
    for cid in card_ids:
        if cid in seen or cid not in load()["by_id"]:
            continue
        seen.add(cid)
        c = card(cid)
        cite = short_cite(cid)
        cite = f" ({cite})" if cite else ""
        lines.append(f"- **{c['title']}**{cite}. Source: [{c['source_name']}]({c['source_url']}), "
                     f"checked {c['verified_on']}, confidence: {c['confidence']}.")
    return "\n".join(lines) if lines else "- (no legal sources used in this reply)"

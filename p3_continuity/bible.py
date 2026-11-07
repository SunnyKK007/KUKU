"""Builds a show bible from the scripts with code: who speaks, where scenes happen, which names exist."""
from __future__ import annotations

import re
from collections import Counter, defaultdict

from common.screenplay import Episode
from p3_continuity.checks import proper_names


def build_bible(show: list[Episode]) -> dict:
    chars = defaultdict(lambda: {"lines": 0, "episodes": set(), "cues": Counter()})
    for ep in show:
        for b in ep.dialogue:
            c = chars[b.speaker]
            c["lines"] += 1
            c["episodes"].add(ep.number)
            for cue in re.split(r",\s*", b.cue):
                if cue:
                    c["cues"][cue.strip().lower()] += 1
    characters = [{"label": k, "lines": v["lines"], "first_episode": min(v["episodes"]),
                   "last_episode": max(v["episodes"]), "episodes": len(v["episodes"]),
                   "typical_delivery": [c for c, _ in v["cues"].most_common(4)]}
                  for k, v in sorted(chars.items(), key=lambda x: -x[1]["lines"])]
    places = defaultdict(set)
    for ep in show:
        for s in ep.scenes:
            loc = re.sub(r"\s*[–-]\s*(DAY|NIGHT|DUSK|DAWN|CONTINUOUS|MORNING|EVENING|LATER|SAME)\b.*$", "",
                         s.heading, flags=re.I).strip()
            places[loc].add(ep.number)
    names, _ = proper_names(show)
    return {
        "episodes": len(show),
        "characters": characters,
        "locations": [{"heading": k, "episodes": sorted(v)} for k, v in sorted(places.items(), key=lambda x: min(x[1]))],
        "proper_names": [{"name": n, "count": len(v), "episodes": sorted({e.number for e, *_ in v})}
                         for n, v in sorted(names.items(), key=lambda x: -len(x[1])) if len(v) >= 2],
    }

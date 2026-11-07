"""
Rule-based continuity checks for AI-generated microdrama scripts.

Why these checks: in an AI pipeline the script feeds everything downstream.
A speaker label picks the AI voice, a name in an action line goes into the
video prompt, a name in dialogue becomes a subtitle and a dub. One misspelt
name can mean a re-render, a wrong voice, or a viewer comment saying
"wasn't he called something else last episode?"

Every issue carries evidence: episode, source line number and the quoted text.
"""
from __future__ import annotations

import difflib
import re
from collections import Counter, defaultdict

from common.screenplay import Episode

TITLE_WORDS = {"LADY", "LORD", "THE", "SIR", "DUKE", "DUCHESS", "DOWAGER", "MR", "MRS", "MISS", "MASTER",
               "MISTRESS", "COUNT", "COUNTESS", "EARL", "BARON", "PRINCE", "PRINCESS", "KING", "QUEEN"}
DESCRIPTOR_WORDS = {"MAN", "WOMAN", "STRANGER", "NOBLEMAN", "NOBLEWOMAN", "MATRIARCH", "GROOM", "BRIDE",
                    "GUARD", "MAID", "THUG", "OFFICIAL", "PRIEST", "SOLDIER", "GIRL", "BOY", "OLD", "YOUNG",
                    "BLOND", "BLONDE", "BEARDED", "MYSTERIOUS", "FORMER", "ELDER", "HOODED", "MASKED", "VOICE"}
OBJECT_GROUPS = {
    "book": r"book|ledger|journal|diary|grimoire|herbarium|notebook|tome|almanac|manuscript|compendium",
    "jewellery": r"ring|necklace|pendant|locket|brooch|bracelet|earrings|tiara",
    "home": r"cottage|cabin|house|manor|estate|home|hut",
}
POSSESSORS = r"(?:her|his|their)\s+(?:late\s+)?(?:beloved\s+)?(mother|father|husband|wife|family|grandmother|son)'s"

SEV_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


def issue(kind, severity, title, detail, evidence, fix):
    return {"type": kind, "severity": severity, "title": title, "detail": detail,
            "evidence": evidence[:12], "evidence_count": len(evidence), "suggested_fix": fix}


def _ev(ep: Episode, line: int, text: str) -> dict:
    return {"episode": ep.number, "line": line, "file": ep.path.name, "text": text[:160]}


def _texts(show: list[Episode]):
    """Yield (episode, line, kind, text) for every piece of prose in the show."""
    for ep in show:
        yield ep, 2, "logline", ep.logline
        yield ep, 3, "notes", ep.continuity
        for b in ep.beats:
            yield ep, b.line + 2, b.kind, b.text


def proper_names(show: list[Episode]) -> tuple[dict[str, list], set[str]]:
    lower_words = set()
    occ = defaultdict(list)
    for ep, line, kind, text in _texts(show):
        lower_words.update(re.findall(r"\b[a-z][a-z]+\b", text))
        for m in re.finditer(r"\b([A-Z][a-z]{3,})(?:'s)?\b", text):
            occ[m.group(1)].append((ep, line, kind, text))
    names = {n: v for n, v in occ.items() if n.lower() not in lower_words}
    speakers = {w for ep in show for b in ep.dialogue for w in re.findall(r"[A-Z]+", b.speaker)}
    return names, speakers


def name_drift(show: list[Episode]) -> list[dict]:
    names, speakers = proper_names(show)
    keys = sorted(names)
    parent = {k: k for k in keys}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if a[0] != b[0] or abs(len(a) - len(b)) > 3:
                continue
            if a + "s" == b or b + "s" == a or a + "es" == b or b + "es" == a:
                continue
            ratio = difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()
            prefix = len(__import__("os").path.commonprefix([a.lower(), b.lower()]))
            if a.upper() in speakers and b.upper() in speakers:
                continue
            if ratio >= 0.8 or (prefix >= 4 and ratio >= 0.6 and min(len(a), len(b)) >= 6):
                parent[find(a)] = find(b)
    groups = defaultdict(list)
    for k in keys:
        groups[find(k)].append(k)
    out = []
    for members in groups.values():
        if len(members) < 2:
            continue
        counts = {m: len(names[m]) for m in members}
        canon = max(counts, key=counts.get)
        evidence = []
        in_dialogue = False
        for m in sorted(members, key=lambda m: -counts[m]):
            if m == canon:
                continue
            for ep, line, kind, text in names[m]:
                evidence.append(_ev(ep, line, f"[{kind}] {text}"))
                in_dialogue |= kind == "dialogue"
        eps = sorted({e["episode"] for e in evidence})
        out.append(issue(
            "name spelling drift", "high" if in_dialogue else "medium",
            f"One name, {len(members)} spellings: " + ", ".join(f"{m} ({counts[m]})" for m in
                                                                sorted(members, key=lambda m: -counts[m])),
            f"Most common spelling is '{canon}'. Variants appear in episodes {eps}. "
            + ("Some are spoken aloud, so they will be heard, subtitled and dubbed."
               if in_dialogue else "They sit in action/camera text, so they flow into video prompts."),
            evidence,
            f"Pick one spelling (likely '{canon}') and add it to the show bible; replace the variants."))
    return out


def surname_and_title_drift(show: list[Episode]) -> list[dict]:
    proper, _ = proper_names(show)
    first_names = {b.speaker.split()[-1].title() for ep in show for b in ep.dialogue
                   if len(b.speaker.split()) <= 2}
    surname = defaultdict(lambda: defaultdict(list))
    titles = defaultdict(lambda: defaultdict(list))
    for ep, line, kind, text in _texts(show):
        for m in re.finditer(r"\b([A-Z][a-z]+) ([A-Z][a-z]{3,})\b", text):
            if m.group(1) in first_names and m.group(2) in proper and m.group(2) not in first_names:
                surname[m.group(1)][m.group(2)].append((ep, line, kind, text))
        for m in re.finditer(r"\b(Duke|Duchess|Earl|Countess|Count|Baron|Baroness|House|Lord|Lady) of ([A-Z][a-z]+)", text):
            titles[m.group(1)][m.group(2)].append((ep, line, kind, text))
    out = []
    for first, sur in surname.items():
        if len(sur) > 1:
            ev = [_ev(ep, line, f"[{kind}] {t}") for s in sur for ep, line, kind, t in sur[s]]
            spoken = any(k == "dialogue" for s in sur for _, _, k, _ in sur[s])
            out.append(issue("surname drift", "high" if spoken else "medium",
                             f"{first} has {len(sur)} surnames: " + ", ".join(f"{s} ({len(v)})" for s, v in
                                                                             sorted(sur.items(), key=lambda x: -len(x[1]))),
                             "A main character's family name changes between episodes.", ev,
                             f"Fix {first}'s surname in the show bible and correct every episode."))
    for title, places in titles.items():
        if len(places) > 1:
            ev = [_ev(ep, line, f"[{kind}] {t}") for p in places for ep, line, kind, t in places[p]]
            spoken = any(k == "dialogue" for p in places for _, _, k, _ in places[p])
            out.append(issue("title drift", "high" if spoken else "medium",
                             f"'{title} of ...' names {len(places)} places: " + ", ".join(
                                 f"{p} ({len(v)})" for p, v in sorted(places.items(), key=lambda x: -len(x[1]))),
                             "Check whether these are meant to be the same title.", ev,
                             "If it is one title, keep one spelling everywhere."))
    return out


def label_drift(show: list[Episode]) -> list[dict]:
    labels = defaultdict(list)
    for ep in show:
        for b in ep.dialogue:
            labels[b.speaker].append((ep, b))
    core = defaultdict(set)
    for lab in labels:
        words = [w for w in lab.split() if w not in TITLE_WORDS]
        if words and not set(words) & DESCRIPTOR_WORDS:
            core[" ".join(words)].add(lab)
    out = []
    for name, labs in core.items():
        sets = [set(l.split()) for l in labs]
        nested = any(a < b for a in sets for b in sets)
        if len(labs) > 1 and nested:
            ev = []
            for lab in sorted(labs, key=lambda l: len(labels[l])):
                eps = sorted({ep.number for ep, _ in labels[lab]})
                ep0, b0 = labels[lab][0]
                ev.append(_ev(ep0, b0.line, f"label '{lab}' used {len(labels[lab])} times in episodes {eps}"))
            out.append(issue("speaker label drift", "medium",
                             f"Character '{name.title()}' is labelled {len(labs)} ways: " + ", ".join(
                                 f"{l} ({len(labels[l])})" for l in sorted(labs, key=lambda l: -len(labels[l]))),
                             "In an AI pipeline the speaker label usually maps to a voice. Two labels can "
                             "mean two different voices for one character.", ev,
                             f"Use one label for {name.title()} in every episode, or map both labels to one voice ID."))
    return out


def label_typos(show: list[Episode]) -> list[dict]:
    """'ROBRET' next to 'ROBERT': a typo in a label silently creates a new voice."""
    labels = defaultdict(list)
    for ep in show:
        for b in ep.dialogue:
            labels[b.speaker].append((ep, b))
    keys = sorted(labels, key=lambda k: -len(labels[k]))
    out = []
    for i, rare in enumerate(keys):
        for common in keys[:i]:
            diff = set(rare.split()) ^ set(common.split())
            if len(labels[rare]) * 3 > len(labels[common]) or (diff and diff <= TITLE_WORDS):
                continue
            if difflib.SequenceMatcher(None, rare, common).ratio() >= 0.85:
                ev = [_ev(ep, b.line, f"label '{rare}': {b.text[:80]}") for ep, b in labels[rare]]
                out.append(issue("speaker label typo", "medium",
                                 f"Label '{rare}' ({len(labels[rare])} lines) looks like a typo of '{common}' ({len(labels[common])})",
                                 "A misspelt label is treated as a new character and may get a new AI voice.", ev,
                                 f"Rename to '{common}'."))
                break
    return out


def descriptor_labels(show: list[Episode]) -> list[dict]:
    known = {w.title() for ep in show for b in ep.dialogue for w in b.speaker.split()
             if w not in TITLE_WORDS and w not in DESCRIPTOR_WORDS and len(w) > 3}
    out = []
    labels = defaultdict(list)
    for ep in show:
        for b in ep.dialogue:
            words = set(b.speaker.split())
            if words & DESCRIPTOR_WORDS and not any(w.title() in known for w in words - DESCRIPTOR_WORDS - TITLE_WORDS):
                labels[b.speaker].append((ep, b))
    base = Counter()
    total_lines = 0
    for ep in show:
        for b in ep.dialogue:
            total_lines += 1
            for n in set(_shot_names(ep, b, known)):
                base[n] += 1
    for lab, uses in labels.items():
        votes = Counter()
        ev = []
        for ep, b in uses:
            for n in set(_shot_names(ep, b, known)):
                votes[n] += 1
                if len(ev) < 6:
                    shot = _covering_shot(ep, b)
                    ev.append(_ev(ep, shot.line + 2, f"[camera] {shot.text}  ->  line by {lab}: \"{b.text[:60]}\""))
        lift = {n: (c / len(uses)) / (base[n] / total_lines) for n, c in votes.items() if base[n]}
        votes = Counter({n: c for n, c in votes.items() if lift.get(n, 0) >= 2.0})
        eps = sorted({ep.number for ep, _ in uses})
        if votes:
            top, n = votes.most_common(1)[0]
            share = n / len(uses)
            if n >= 3 and share >= 0.4:
                out.append(issue("unnamed label for a named character", "medium",
                                 f"'{lab}' ({len(uses)} lines, episodes {eps[0]}-{eps[-1]}) is probably {top}",
                                 f"The shot on screen when this label speaks names '{top}' in {n} of {len(uses)} lines "
                                 f"({lift[top]:.1f}x more often than for other speakers). "
                                 "A generic label for a named character breaks voice and face consistency.",
                                 ev, f"Relabel '{lab}' as {top.upper()} once the audience knows the name."))
                continue
        if len(eps) >= 3:
            out.append(issue("unnamed recurring character", "low",
                             f"'{lab}' speaks in {len(eps)} episodes without a name",
                             "A recurring character with only a description is hard to keep consistent.",
                             [_ev(uses[0][0], uses[0][1].line, f"first use: {uses[0][1].text[:80]}")],
                             "Give the character a name in the show bible."))
    return out


def _covering_shot(ep: Episode, b):
    shots = [x for x in ep.beats if x.kind == "camera" and x.start <= b.start + 0.3 and x.end >= b.start]
    return shots[-1] if shots else b


def _shot_names(ep: Episode, b, known: set[str]) -> list[str]:
    shot = _covering_shot(ep, b)
    if shot is b:
        return []
    return [n for n in re.findall(r"\b([A-Z][a-z]{3,})\b", shot.text) if n in known]


def prop_drift(show: list[Episode]) -> list[dict]:
    found = defaultdict(lambda: defaultdict(list))
    for ep, line, kind, text in _texts(show):
        for m in re.finditer(POSSESSORS + r"\s+((?:[a-z-]+\s+){0,3}?)(" + "|".join(OBJECT_GROUPS.values()) + r")\b", text, re.I):
            owner, noun = m.group(1).lower(), m.group(3).lower()
            group = next(g for g, p in OBJECT_GROUPS.items() if re.fullmatch(p, noun))
            found[(owner, group)][noun].append((ep, line, kind, text))
    out = []
    for (owner, group), nouns in found.items():
        if len(nouns) >= 3 or (len(nouns) == 2 and min(len(v) for v in nouns.values()) >= 2):
            ev = [_ev(ep, line, f"[{kind}] {t}") for n in nouns for ep, line, kind, t in nouns[n][:3]]
            out.append(issue("prop name drift", "low",
                             f"The {owner}'s {group} is called {len(nouns)} things: " + ", ".join(
                                 f"{n} ({len(v)})" for n, v in sorted(nouns.items(), key=lambda x: -len(x[1]))),
                             "If these are one object, the video model may draw a different prop each time.",
                             ev, "Confirm whether this is one object; if so, name it once in the show bible."))
    return out


def format_lint(show: list[Episode]) -> list[dict]:
    out = []
    for i, ep in enumerate(show):
        m = re.search(r"(?:picks? up|picking up|continu\w*|follow\w*)\s+(?:immediately\s+|directly\s+)?"
                      r"(?:on\s+)?(?:from|after)\s+(?:[^.;]{0,80}?\bin\s+)?episode\s+(\d+)", ep.continuity, re.I)
        if m and int(m.group(1)) != ep.number - 1 and i > 0:
            out.append(issue("continuity note mismatch", "medium",
                             f"Episode {ep.number} says it picks up from Episode {m.group(1)}",
                             "The continuity note points to the wrong previous episode.",
                             [_ev(ep, 3, ep.continuity)], f"Should probably reference Episode {ep.number - 1}."))
        raw = ep.path.read_text(encoding="utf-8")
        if re.search(r"^SCENE HEADING:", raw, re.M):
            out.append(issue("format drift", "info", f"Episode {ep.number} uses upper-case scene headers",
                             "Other episodes use 'Scene heading:'. Strict parsers downstream may skip these scenes.",
                             [_ev(ep, 8, "SCENE HEADING: ...")], "Normalise the header format at export."))
        for b in ep.beats:
            if b.end < b.start:
                out.append(issue("timing error", "medium", f"E{ep.number} block ends before it starts", "",
                                 [_ev(ep, b.line, b.as_text())], "Fix the timestamp."))
    return out


ALL_CHECKS = [name_drift, surname_and_title_drift, label_drift, label_typos, descriptor_labels, prop_drift, format_lint]


def run_checks(show: list[Episode]) -> list[dict]:
    issues = []
    for chk in ALL_CHECKS:
        issues.extend(chk(show))
    issues.sort(key=lambda i: (SEV_ORDER[i["severity"]], -i["evidence_count"]))
    for n, i in enumerate(issues, 1):
        i["id"] = f"C{n:03d}"
        i["source"] = "rules"
    return issues

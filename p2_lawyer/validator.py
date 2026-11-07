"""
Citation guardrail. Every outgoing message (from templates OR from a model)
passes through `validate()` before the user sees it.

It finds anything that looks like a legal authority and checks it against the
closed set in law_cards.json:
  - statutes / rules by name (known ones pass, unknown ones are removed)
  - "Section / Sec. / S. / u/s / Rule / Article / धारा N" (must belong to a known
    instrument AND to a section number that a card lists)
  - IPC / CrPC / Evidence Act (removed and flagged as out of date)
  - case law: "X v. Y", "vs", AIR / SCC citations, "the Supreme Court held ..."
  - helpline numbers and government web links (must be on the verified list)
  - [[CARD-ID]] tokens the model uses to cite cards (unknown ids are removed)

Anything not allowed is replaced with a visible marker and logged. This is
code, not a model, so it behaves the same every time and can be unit-tested.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from . import law

log = logging.getLogger("p2_lawyer.guardrail")

YEAR = r"(?:18|19|20)\d{2}"
SECTION_NUM = r"\d+[A-Z]?(?:\s*\(\s*[0-9a-zA-Z]{1,4}\s*\))*"
SECTION_RE = re.compile(
    r"(?<![\w])(?P<kw>[Ss]ections?|[Ss]ecs?\.?|[Ss]\.|u/s\.?|U/S\.?|[Rr]ules?|[Aa]rticles?|[Aa]rt\.|धारा|[Dd]hara|कलम|ধারা|பிரிவு|કલમ|సెక్షన్|ಸೆಕ್ಷನ್|വകുപ്പ്)"
    rf"\s*(?P<nums>{SECTION_NUM}(?:\s*(?:,|and|&|or|to|/)\s*{SECTION_NUM})*)")
GENERIC_INSTR_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z.'&-]*(?:\s+(?:[A-Z(][A-Za-z.'&()-]*|of|on|and|for|the|to|in)){0,8}"
    r"\s+(?:Act|Code|Rules|Sanhita|Adhiniyam|Regulations?|Ordinance))\s*,?\s*(?P<year>" + YEAR + r")\b")
GENERIC_INSTR_NOYEAR_RE = re.compile(
    r"\b(?P<name>(?:[A-Z][A-Za-z.'&-]*\s+){1,6}(?:Act|Sanhita|Adhiniyam|Ordinance))\b(?!\s*,?\s*" + YEAR + ")")
GENERIC_INSTR_HI_RE = re.compile(
    r"(?P<name>(?:[\u0900-\u097F]+\s+){1,5}(?:अधिनियम|संहिता))(?:\s*,?\s*(?P<year>" + YEAR + r"))?")
CRIMINAL_OLD_RE = re.compile(
    r"\b(?:भारतीय दंड संहिता|IPC|I\.\s?P\.\s?C\.?|Indian Penal Code(?:,?\s*1860)?|CrPC|Cr\.\s?P\.\s?C\.?|"
    r"Code of Criminal Procedure(?:,?\s*1973)?|Indian Evidence Act(?:,?\s*1872)?)")
CASE_PATTERNS = [
    re.compile(r"\b[A-Z][\w.&']*(?:\s+(?:[A-Z][\w.&']*|of|and|&)){0,6}\s+(?:v\.|vs\.?|Vs\.?|versus)\s+"
               r"[A-Z][\w.&']*(?:\s+(?:[A-Z][\w.&']*|of|and|&))*"),
    re.compile(r"\bAIR\s+" + YEAR + r"(?:\s+[A-Z][A-Za-z]{1,10})?(?:\s+\d+)?"),
    re.compile(r"\(\s*" + YEAR + r"\s*\)\s*\d+\s*(?:SCC|SCR|SCALE|Comp\s?LJ|CPJ|CPR)\s*\d+"),
    re.compile(r"\b" + YEAR + r"\s+(?:SCC|SCR|SCALE|CPJ)\s+(?:OnLine\s+)?[A-Za-z]*\s*\d+"),
    re.compile(r"\b(?:SCC|SCR)\s+OnLine\s+\w+\s+\d+"),
    re.compile(r"(?i)\b(?:in the (?:landmark |famous |well-known )?case of|it was held in|"
               r"landmark (?:judgment|judgement|ruling)|as held by the (?:hon'?ble )?(?:supreme|high) court|"
               r"the (?:hon'?ble )?(?:supreme court|high court|ncdrc|national commission)\s+(?:has\s+)?"
               r"(?:held|ruled|observed|decided)|\b(?:supreme|high) court (?:has |had )?(?:held|ruled|observed|decided))[^.\n]*"),
]
PHONE_RE = re.compile(
    r"(?i)(?:\bhelpline|toll[- ]?free|\bcall\b|\bdial\b|whats\s?app|\bsms\b|\bphone\b|\bmobile\b|contact number|"
    r"हेल्पलाइन|नंबर)[^\d\n]{0,25}?(?P<num>\+?\d[\d -]{1,14}\d)")
URL_RE = re.compile(
    r"(?<![@\w.])(?P<url>(?:https?://)?(?:www\.)?(?P<domain>(?:[a-z0-9-]+\.)+(?:gov\.in|nic\.in))(?:/[^\s)\]>\"']*)?"
    r"|https?://(?P<domain2>(?:[a-z0-9-]+\.)+[a-z]{2,})(?:/[^\s)\]>\"']*)?)", re.I)
CARD_TOKEN_RE = re.compile(r"\[\[\s*([A-Za-z0-9-]+)\s*\]\]")

MARKERS = {
    "unverified_statute": "[law name removed: not in my verified sources]",
    "unverified_section": "[section removed: not in my verified sources]",
    "section_without_act": "[section removed: unclear which law]",
    "outdated_criminal_code": "[IPC/CrPC reference removed: replaced by BNS/BNSS from 1 July 2024]",
    "case_law": "[case reference removed: I do not cite court cases]",
    "unverified_phone": "[number removed: not a verified helpline]",
    "unverified_link": "[link removed: not a verified source]",
    "unknown_card": "",
}


@dataclass
class ValidationResult:
    text: str
    violations: list = field(default_factory=list)
    cited: list = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("’", "'")).strip().lower().rstrip(",")


def _norm_sec(s: str) -> str:
    return re.sub(r"\s+", "", s)


def _registry():
    data = law.load()
    alias_to_canon = {}
    for canon, aliases in data["instruments"].items():
        for a in [canon] + aliases:
            alias_to_canon[_norm(a)] = canon
        # bare name without the year, e.g. "Code on Wages"
        bare = re.sub(r",?\s*" + YEAR + r"$", "", canon)
        alias_to_canon.setdefault(_norm(bare), canon)
    allowed_secs: dict[str, set] = {}
    sec_to_cards: dict[tuple, list] = {}
    inst_to_cards: dict[str, list] = {}
    for c in data["cards"]:
        for ci in c["cites"]:
            inst, sec = ci["instrument"], ci["section"]
            allowed_secs.setdefault(inst, set())
            if sec:
                allowed_secs[inst].add(_norm_sec(sec))
                sec_to_cards.setdefault((inst, _norm_sec(sec)), []).append(c["id"])
            else:
                inst_to_cards.setdefault(inst, []).append(c["id"])
    return data, alias_to_canon, allowed_secs, sec_to_cards, inst_to_cards


def _section_allowed(inst: str, sec: str, allowed: dict) -> bool:
    for a in allowed.get(inst, ()):  # exact, a sub-part of an allowed one, or the parent of one
        if sec == a or sec.startswith(a + "(") or a.startswith(sec + "("):
            return True
    return False


def _cards_for_section(inst, sec, sec_to_cards):
    out = []
    for (i, s), ids in sec_to_cards.items():
        if i == inst and (sec == s or sec.startswith(s + "(") or s.startswith(sec + "(")):
            out += ids
    return out


def validate(text: str, extra_cited=()) -> ValidationResult:
    data, alias_to_canon, allowed_secs, sec_to_cards, inst_to_cards = _registry()
    spans = []      # (start, end, kind, matched_text, reason)
    cited: list[str] = []
    instr_mentions = []  # (start, end, canonical or None)

    # 1. known instruments (longest aliases first so the full name wins)
    taken = [False] * len(text)
    for alias in sorted(alias_to_canon, key=len, reverse=True):
        pat = re.compile(r"(?<![\w])" + r"\s+".join(re.escape(w) for w in alias.split()) + r"(?![\w])"
                         + (r"(?!\s*,?\s*" + YEAR + ")" if not re.search(YEAR + r"$", alias) else ""), re.I)
        for m in pat.finditer(text):
            if any(taken[m.start():m.end()]):
                continue
            for i in range(m.start(), m.end()):
                taken[i] = True
            canon = alias_to_canon[alias]
            instr_mentions.append((m.start(), m.end(), canon))
            cited += inst_to_cards.get(canon, [])

    # 2. out-of-date criminal codes
    for m in CRIMINAL_OLD_RE.finditer(text):
        if not any(taken[m.start():m.end()]):
            spans.append((m.start(), m.end(), "outdated_criminal_code", m.group(0),
                          "IPC/CrPC/Evidence Act were replaced from 1 July 2024"))
            instr_mentions.append((m.start(), m.end(), None))
            for i in range(m.start(), m.end()):
                taken[i] = True

    # 3. unknown instruments (with or without a year)
    for rx in (GENERIC_INSTR_RE, GENERIC_INSTR_NOYEAR_RE, GENERIC_INSTR_HI_RE):
        for m in rx.finditer(text):
            s, e = m.start("name"), m.end()
            name = m.group("name")
            # trim leading words like "The", "Under", "Per" so we keep the actual name
            lead = re.match(r"(?:(?:The|the|Under|under|Per|As|In|Of|By|And|See)\s+)+", name)
            if lead:
                s += lead.end()
            if any(taken[s:e]) or e - s < 6:
                continue
            spans.append((s, e, "unverified_statute", text[s:e], "law not in verified card set"))
            instr_mentions.append((s, e, None))
            for i in range(s, e):
                taken[i] = True

    instr_mentions.sort()

    # 4. sections / rules / articles
    for m in SECTION_RE.finditer(text):
        if any(taken[m.start():m.end()]):
            continue
        nums = [_norm_sec(n) for n in re.findall(SECTION_NUM, m.group("nums"))]
        kw = m.group("kw").lower()
        # which instrument is this attached to? first: one starting right after ("of the X")
        inst = None
        after = [im for im in instr_mentions if 0 <= im[0] - m.end() <= 14]
        if after:
            inst = after[0][2] or "UNKNOWN"
        else:
            # same sentence, nearest instrument before or after
            sent_start = max(text.rfind(".", 0, m.start()) + 1, text.rfind("\n", 0, m.start()) + 1,
                             text.rfind("।", 0, m.start()) + 1)
            nxt = [p for p in (text.find(".", m.end()), text.find("\n", m.end()), text.find("।", m.end())) if p != -1]
            sent_end = min(nxt) if nxt else len(text)
            near = [im for im in instr_mentions if sent_start <= im[0] < sent_end]
            if near:
                near.sort(key=lambda im: abs(im[0] - m.start()))
                inst = near[0][2] or "UNKNOWN"
        if kw.startswith("art"):
            reason, kind = "Articles (e.g. of the Constitution) are not in the verified set", "unverified_section"
        elif inst is None:
            reason, kind = "section cited without saying which law", "section_without_act"
        elif inst == "UNKNOWN":
            reason, kind = "section of a law that is not verified", "unverified_section"
        else:
            bad = [n for n in nums if not _section_allowed(inst, n, allowed_secs)]
            if not bad:
                for n in nums:
                    cited += _cards_for_section(inst, n, sec_to_cards)
                continue
            reason, kind = f"{', '.join(bad)} of {inst} is not on a verified card", "unverified_section"
        spans.append((m.start(), m.end(), kind, m.group(0), reason))
        for i in range(m.start(), m.end()):
            taken[i] = True

    # 5. case law
    for rx in CASE_PATTERNS:
        for m in rx.finditer(text):
            if any(taken[m.start():m.end()]):
                continue
            spans.append((m.start(), m.end(), "case_law", m.group(0), "case law is never cited"))
            for i in range(m.start(), m.end()):
                taken[i] = True

    # 6. helpline numbers
    allowed_nums = set(data["allowed_phone_numbers"])
    for m in PHONE_RE.finditer(text):
        raw = m.group("num")
        gap = text[m.start():m.start("num")].lower()
        tail = text[m.end("num"):m.end("num") + 2]
        if (re.search(r"rs\.?|₹|inr|rupee|call upon", gap) or re.match(r"[,.]\d|/-", tail)
                or re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", raw.strip())):
            continue   # money amounts ("call upon you to pay Rs 1,80,000") are not phone numbers
        digits = re.sub(r"\D", "", raw)
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) < 3 or digits in allowed_nums or any(taken[m.start("num"):m.end("num")]):
            continue
        spans.append((m.start("num"), m.end("num"), "unverified_phone", raw, "phone number not on verified list"))
        for i in range(m.start("num"), m.end("num")):
            taken[i] = True

    # 7. links
    allowed_domains = set(data["allowed_domains"])
    for m in URL_RE.finditer(text):
        dom = (m.group("domain") or m.group("domain2") or "").lower()
        dom = dom[4:] if dom.startswith("www.") else dom
        ok = any(dom == d or dom.endswith("." + d) for d in allowed_domains)
        if ok or any(taken[m.start():m.end()]):
            continue
        spans.append((m.start(), m.end(), "unverified_link", m.group("url"), "link not on verified list"))
        for i in range(m.start(), m.end()):
            taken[i] = True

    # 8. [[CARD-ID]] tokens from the model
    for m in CARD_TOKEN_RE.finditer(text):
        cid = m.group(1).upper()
        if cid in data["by_id"]:
            cited.append(cid)
        else:
            spans.append((m.start(), m.end(), "unknown_card", m.group(0), "model cited a card id that does not exist"))

    # build cleaned text
    spans.sort()
    out, pos, violations = [], 0, []
    for s, e, kind, matched, reason in spans:
        if s < pos:
            continue
        out.append(text[pos:s])
        out.append(MARKERS[kind])
        pos = e
        violations.append({"type": kind, "text": matched, "reason": reason})
        log.warning("guardrail blocked %s: %r (%s)", kind, matched, reason)
    out.append(text[pos:])
    clean = "".join(out)
    # valid card tokens become short visible refs
    clean = CARD_TOKEN_RE.sub(lambda m: f"[{m.group(1).upper()}]" if m.group(1).upper() in data["by_id"] else "", clean)
    seen, ordered = set(), []
    for cid in list(extra_cited) + cited:
        if cid not in seen and cid in data["by_id"]:
            seen.add(cid)
            ordered.append(cid)
    return ValidationResult(text=clean, violations=violations, cited=ordered)

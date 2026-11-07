"""
The conversation engine. Plain Python, no Streamlit, so the app and the tests
share exactly the same logic.

    from p2_lawyer.engine import Session
    s = Session(model="offline")          # or "groq", "gemini:gemini-2.5-flash", ...
    out = s.reply("My landlord in Pune won't return my 50,000 deposit")
    print(out["text"])

What is code (always, in both modes): escalation rules, the law cards and
which ones apply, the citation validator, document templates, the slot list.
What the model does (model mode only): read messy text into the slots, ask the
next question in the user's language, rephrase "where you stand", play the
other side in practice. Every model output passes the validator.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re

from common.llm import LLM

from . import advice, documents, law, practice
from .casefile import CaseFile
from .escalation import BLOCKING, HINDI_PREFIX, LEGAL_AID_LINE, check_case, check_text
from .intake import (LANG_NAMES, MONTHS_COUNT_RE, PROOF_ITEMS, SKIP_RE, SLOTS, WORDNUM, classify, clean_answer,
                     detect_language, extract_amounts, extract_dates, extract_location, extract_party,
                     extract_proof, parse_choice, question)
from .validator import validate

log = logging.getLogger("p2_lawyer.engine")

DISCLAIMER = ("Legal information, not legal advice. I can be wrong. For court cases or anything serious, "
              "speak to a lawyer. Free legal aid: 15100.")

TEXT = {
    "clarify": {
        "en": "I can help with three money problems: (1) a security deposit your landlord won't return, (2) a refund "
              "a company or seller hasn't given, (3) salary or dues your employer hasn't paid. Which one is yours? "
              "Reply 1, 2 or 3, or tell me a little more.",
        "hinglish": "Main teen tarah ki paise wali problems mein madad kar sakta hoon: (1) makaan malik security deposit "
                    "wapas nahi kar raha, (2) company/seller refund nahi de raha, (3) employer salary nahi de raha. "
                    "Aapki problem kaunsi hai? 1, 2 ya 3 likhiye, ya thoda aur bataiye.",
        "hi": "मैं तीन तरह की पैसों वाली समस्याओं में मदद कर सकता हूँ: (1) मकान मालिक सिक्योरिटी डिपॉजिट वापस नहीं कर रहा, "
              "(2) कंपनी या विक्रेता रिफंड नहीं दे रहा, (3) मालिक तनख्वाह नहीं दे रहा। आपकी समस्या कौन-सी है? "
              "1, 2 या 3 लिखिए, या थोड़ा और बताइए।",
    },
    "ack": {
        "en": "Understood: this is about {what}. I'll ask a few short questions, one at a time, to build your case file. "
              "Type 'skip' for anything you don't know.",
        "hinglish": "Samajh gaya: yeh {what} ka maamla hai. Aapki case file banane ke liye main ek-ek karke kuch chhote "
                    "sawaal poochhunga. Jo nahi pata, uske liye 'skip' likhiye.",
        "hi": "समझ गया: यह {what} का मामला है। आपकी केस फ़ाइल बनाने के लिए मैं एक-एक करके कुछ छोटे सवाल पूछूँगा। "
              "जो पता न हो, उसके लिए 'skip' लिखिए।",
    },
    "what": {
        "en": {"deposit": "a security deposit not returned", "refund": "a refund not given",
               "salary": "unpaid salary/dues"},
        "hinglish": {"deposit": "security deposit wapas na milne", "refund": "refund na milne",
                     "salary": "salary na milne"},
        "hi": {"deposit": "सिक्योरिटी डिपॉजिट वापस न मिलने", "refund": "रिफंड न मिलने", "salary": "तनख्वाह न मिलने"},
    },
    "ready": {
        "en": "Thanks. Your case file is ready (see the panel). Next you can ask: **'Where do I stand?'**, "
              "**'Draft notice'**, or **'Practise'** to rehearse with the other side.",
        "hinglish": "Shukriya. Aapki case file taiyaar hai. Ab aap likh sakte hain: **'Where do I stand?'**, "
                    "**'Draft notice'**, ya **'Practise'** (doosri party se baat ki practice).",
        "hi": "धन्यवाद। आपकी केस फ़ाइल तैयार है। अब आप लिख सकते हैं: **'Where do I stand?'** (मेरी स्थिति), "
              "**'Draft notice'** (नोटिस), या **'Practise'** (दूसरी पार्टी से बात की प्रैक्टिस)।",
    },
    "out_of_scope": {
        "en": "I'm sorry, this is outside what I can safely help with. I only cover deposits, refunds and unpaid salary.",
        "hinglish": "Maaf kijiye, yeh mere daayre se bahar hai. Main sirf deposit, refund aur salary ke maamle dekhta hoon.",
        "hi": "माफ़ कीजिए, यह मेरे दायरे से बाहर है। मैं सिर्फ़ डिपॉजिट, रिफंड और तनख्वाह के मामले देखता हूँ।",
    },
    "caselaw": {
        "en": "I don't give court cases or judgments. AI tools often invent case names and citations that look real, and "
              "quoting a fake case in a notice or complaint can seriously hurt you. What I can show you is the law "
              "itself from official sources (see 'Sources'). If you need case law for a filing, a lawyer or free legal "
              "aid (helpline 15100) can find real, current judgments for you.",
        "hinglish": "Main court cases ya judgments nahi deta. AI aksar nakli case names bana deta hai jo asli lagte hain, "
                    "aur notice mein nakli case likhna aapko nuksaan pahuncha sakta hai. Main sirf official source se "
                    "kanoon dikhata hoon ('Sources' dekhiye). Case law chahiye to vakeel ya free legal aid (helpline 15100) "
                    "se poochhiye.",
        "hi": "मैं अदालत के फ़ैसले या केस नहीं बताता। AI अक्सर नकली केस के नाम गढ़ देता है जो असली लगते हैं, और नोटिस में "
              "नकली केस लिखना आपको नुकसान पहुँचा सकता है। मैं सिर्फ़ आधिकारिक स्रोतों से क़ानून दिखाता हूँ ('Sources' देखिए)। "
              "केस लॉ चाहिए तो वकील या मुफ़्त कानूनी सहायता (हेल्पलाइन 15100) से पूछिए।",
    },
    "offline_lang": "(Without an AI model I can only reply in English, Hindi or Hinglish. I detected {lang}. "
                    "With a model key set, I reply in {lang}.)",
    "practice_intro": "**Practice mode.** I'll play {persona}. Reply as you would in real life; I'll coach you after "
                      "each reply. Type 'stop' to end.",
}

CASELAW_RE = re.compile(r"(?i)case ?laws?|judge?ments?|precedents?|(?:supreme|high) court (?:cases?|rulings?|decisions?|orders?)|"
                        r"past cases|court cases|similar cases|citations?|faisl[ae]|nazir|नज़ीर|फ़ैसले|फैसले|केस लॉ")
STAND_RE = re.compile(r"(?i)where (?:do )?i stand|my options|what are my options|what (?:can|should) i do( now)?\??$|"
                      r"my rights|meri sthiti|kya kar sakt[ae]|ab kya kar(?:u|oon|na)|मेरी स्थिति|मेरे विकल्प|क्या कर सकत")
NOTICE_RE = re.compile(r"(?i)\b(?:draft|write|make|prepare|create|generate|give me|bana(?:o|do|iye|ke)?|likh(?:o|do|iye)?)\b"
                       r".{0,25}\b(?:notice|letter|complaint)\b|^\s*(?:draft\s+)?(?:legal\s+)?notice\s*\??\s*$|नोटिस\s*(?:बना|लिख|तैयार)")
PRACTICE_RE = re.compile(r"(?i)\b(?:practi[cs]e|role ?play|rehears\w*|mock)\b|abhyas|अभ्यास|प्रैक्टिस")
SOURCES_RE = re.compile(r"(?i)^\s*(?:show\s+)?(?:the\s+)?(?:sources?|links?)\s*\??\s*$|स्रोत")
STOP_RE = re.compile(r"(?i)^\s*(?:stop|exit|quit|end|done|band karo|bas|बस|बंद)\b")

MODEL_SYSTEM = """You are Nyay Saathi, a legal-information assistant for ordinary people in India.
You ONLY handle three problems: deposit (security deposit not returned by a landlord), refund (a consumer refund not given by a company/seller), salary (unpaid salary or dues from an employer).

Hard rules:
1. Reply in the user's language and script: Devanagari Hindi if they write Devanagari, Roman Hinglish if they write Hinglish, Tamil if Tamil, and so on. Keep act names and section numbers in English exactly as written in the cards.
2. You may state law ONLY using the LAW CARDS provided. Cite a card by writing its id in double brackets, e.g. [[CPA-LIMITATION]]. Never write any section number, act name, rule, court case, judgment, helpline number or website that is not in the cards. Never cite case law. If asked for case law, say you don't provide it.
3. Ask exactly ONE follow-up question, for the most important item in missing_slots. Be short and kind. No legal jargon.
4. Never promise an outcome. Say clearly when you are not sure. Do not give advice on criminal, family or property matters.
5. escalation_flags are decided by code; if any are present, acknowledge them briefly in the user's language.
6. Extract facts only from what the user actually said. Never invent names, amounts or dates. Use null when unknown.

Return ONLY a JSON object:
{"problem_type": "deposit|refund|salary|unclear|out_of_scope",
 "language": "en|hi|hinglish|ta|te|kn|ml|bn|mr|gu|pa|other",
 "facts": {"amount": int|null, "monthly_rent": int|null, "monthly_salary": int|null, "unpaid_months": int|null,
           "other_party": str|null, "city": str|null, "state": str|null,
           "start_date": "YYYY-MM-DD or text"|null, "end_date": "YYYY-MM-DD or text"|null,
           "what_happened": str|null, "their_reason": str|null, "promise": str|null, "your_name": str|null},
 "proof": {"<proof_key>": true|false|null},
 "asked_slot": "<slot name you are asking about>"|null,
 "reply": "<your message to the user>"}"""

REPHRASE_SYSTEM = """Rewrite the given legal-information text for an ordinary person in {lang}.
Rules: keep the markdown headings and numbered steps; keep every [[CARD-ID]] token exactly; keep all amounts, dates,
names, act names and section numbers exactly as written (do not translate act names); do NOT add any law, section,
case, number or website that is not already in the text; short sentences, plain words.
Return ONLY JSON: {{"text": "<rewritten text>"}}"""

PRACTICE_SYSTEM = """You are role-playing {persona} in a dispute in India so the user can practise. Stay in character:
realistic, a bit evasive, never abusive, never threatening. Use the user's language ({lang}).
Base your objection on this typical line: "{seed}". Do NOT cite any law, section, case or number.
Facts of the case: {facts}
Return ONLY JSON: {{"in_character": "<what {persona} says next, 1-3 sentences>"}}"""


def make_llm(model: str | None):
    try:
        llm = LLM(model or "offline")
        return llm, None
    except Exception as e:  # missing key, unknown provider
        return LLM("offline"), f"{type(e).__name__}: {e}"


def _est_tokens(s: str) -> int:
    indic = sum(1 for ch in s if 0x0900 <= ord(ch) <= 0x0DFF)
    return int((len(s) - indic) / 4 + indic / 2) + 1


class Session:
    def __init__(self, model: str | None = "offline", today: dt.date | None = None):
        self.llm, self.model_error = make_llm(model)
        self.case = CaseFile(today=today or dt.date.today())
        self.transcript: list[dict] = []
        self.guardrail_log: list[dict] = []
        self.practice_state: dict | None = None
        self.shadow = {"model_calls": 0, "prompt_tokens": 0, "completion_tokens": 0}

    # --------------------------------------------------------------- helpers
    @property
    def model_label(self) -> str:
        return self.llm.label()

    @property
    def lang(self) -> str:
        return self.case.language if self.case.language in ("en", "hi", "hinglish") else "en"

    def t(self, key: str, **kw) -> str:
        return TEXT[key][self.lang].format(**kw)

    def _out(self, text: str, kind: str = "chat", cited=(), escalations=()) -> dict:
        res = validate(text, extra_cited=cited)
        for v in res.violations:
            entry = {"turn": len(self.transcript), "kind": kind, **v}
            self.guardrail_log.append(entry)
        self.transcript.append({"role": "assistant", "kind": kind, "text": res.text})
        return {"text": res.text, "kind": kind, "cited": res.cited, "sources_md": law.sources_markdown(res.cited),
                "violations": res.violations, "escalations": list(escalations)}

    def _shadow_cost(self, prompt: str, completion_tokens: int = 250):
        """Estimate what model mode would spend for this step (used for cost reports in offline runs)."""
        self.shadow["model_calls"] += 1
        self.shadow["prompt_tokens"] += _est_tokens(prompt)
        self.shadow["completion_tokens"] += completion_tokens

    # ------------------------------------------------------------ main entry
    def reply(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            return self._out(self.t("clarify"))
        self.transcript.append({"role": "user", "text": text})
        c = self.case
        if not c.story:
            c.story = text
        lang = detect_language(text)
        # sticky: short answers ("Sharma ji, Sector 62", "20000") must not flip the reply language
        if lang != "en" or len(self.transcript) == 1 or len(text.split()) >= 8:
            c.language = lang

        if self.practice_state and self.practice_state.get("active"):
            if STOP_RE.search(text):
                self.practice_state["active"] = False
                return self._out("Practice ended. Well done for rehearsing. You can ask 'Where do I stand?' or "
                                 "'Draft notice' any time.", kind="practice")
            return self._practice_turn(text)

        short = len(text.split()) <= 12
        if CASELAW_RE.search(text):
            esc = c.add_escalations(check_text(text))
            msg = self.t("caselaw")
            if c.problem_type and c.pending_slot:
                msg += "\n\n" + question(c.problem_type, c.pending_slot, self.lang)
            return self._out(msg, kind="refusal", cited=["NALSA-15100"], escalations=esc)
        if c.problem_type and short:
            if SOURCES_RE.search(text):
                return self.sources_reply(log_user=False)
            if PRACTICE_RE.search(text):
                return self.start_practice(log_user=False)
            if NOTICE_RE.search(text):
                return self.documents_reply(log_user=False)
            if STAND_RE.search(text):
                return self.where_i_stand(log_user=False)

        new_esc = c.add_escalations(check_text(text))
        newly_typed = False
        if c.problem_type is None:
            ptype = parse_choice(text) if c.pending_slot == "__type__" else None
            ptype = ptype or classify(text)[0]
            if ptype:
                c.problem_type, c.pending_slot, newly_typed = ptype, None, True

        payload = self._model_payload(text)
        self._shadow_cost(MODEL_SYSTEM + payload)
        if self.llm.available and c.status != "out_of_scope":
            try:
                return self._model_turn(text, payload, new_esc, newly_typed)
            except Exception as e:  # network, quota, bad JSON: fall back to rules for this turn
                self.model_error = f"{type(e).__name__}: {e}"
                log.warning("model turn failed, using rules: %s", self.model_error)
        return self._offline_turn(text, new_esc, newly_typed)

    # ---------------------------------------------------------- offline turn
    def _escalation_block(self, esc: list[dict]) -> str:
        if not esc:
            return ""
        lines = []
        if self.lang == "hi":
            lines += [HINDI_PREFIX[e["code"]] for e in esc if e["code"] in HINDI_PREFIX]
        lines += [f"**Important:** {e['message']}" for e in esc]
        if any(e["level"] in ("urgent", "refer") for e in esc):
            lines.append(LEGAL_AID_LINE)
        return "\n\n".join(lines)

    def _offline_turn(self, text: str, new_esc: list[dict], newly_typed: bool) -> dict:
        c = self.case
        parts = []
        esc_block = self._escalation_block(new_esc)
        cited = ["NALSA-15100"] if esc_block else []
        if any(e["code"] == "danger" for e in new_esc):
            cited.insert(0, "EMERGENCY-112")
        if c.language not in ("en", "hi", "hinglish"):
            parts.append(TEXT["offline_lang"].format(lang=LANG_NAMES.get(c.language, c.language)))

        if c.problem_type is None:
            blocking = [e for e in c.escalations if e["code"] in BLOCKING]
            if blocking:
                c.status = "out_of_scope"
                parts += [self.t("out_of_scope"), esc_block or self._escalation_block(blocking)]
                return self._out("\n\n".join(p for p in parts if p), kind="referral",
                                 cited=["LEGAL-AID", "NALSA-15100"], escalations=new_esc)
            if esc_block:
                parts.append(esc_block)
            c.pending_slot = "__type__"
            parts.append(self.t("clarify"))
            return self._out("\n\n".join(parts), kind="clarify", cited=cited, escalations=new_esc)

        if c.pending_slot and c.pending_slot != "__type__" and not newly_typed:
            self._fill_slot(c.pending_slot, text)
        self._extract_all(text)
        new_esc += c.add_escalations(check_case(c))
        esc_block = self._escalation_block(new_esc)
        if esc_block:
            cited.append("NALSA-15100")
            parts.append(esc_block)
        if newly_typed:
            parts.append(self.t("ack", what=TEXT["what"][self.lang][c.problem_type]))

        missing = c.missing_slots()
        if missing:
            c.pending_slot = missing[0]
            parts.append(question(c.problem_type, missing[0], self.lang))
            kind = "question"
        else:
            c.pending_slot = None
            c.status = "ready"
            parts.append(c.summary_markdown())
            parts.append(self.t("ready"))
            kind = "ready"
        return self._out("\n\n".join(parts), kind=kind, cited=cited, escalations=new_esc)

    def _fill_slot(self, slot: str, text: str):
        c, f = self.case, self.case.facts
        if slot not in c.asked:
            c.asked.append(slot)
        if SKIP_RE.match(text):
            c.skipped.append(slot)
            if slot == "amount" and f.get("amount") in (None, "") and f.get("amount_paid"):
                f["amount"] = f["amount_paid"]      # best available figure
            return
        if slot in ("amount", "monthly_rent", "monthly_salary"):
            amts = extract_amounts(text, force=True)
            if amts:
                if slot == "amount" and len(amts) > 1:
                    owed = [a for a in amts if re.search(r"not returned|pending|baaki|baki|due|unpaid|owe|withheld|back\b|remaining|"
                                                         r"kept|rakh|wapas nahi|बाकी|नहीं", a["ctx"])]
                    f["amount"] = (owed[-1] if owed else amts[0])["value"]
                else:
                    f[slot] = amts[0]["value"]
            else:
                c.skipped.append(slot)
                f[slot + "_note"] = clean_answer(text, 120)
                if slot == "amount" and f.get("amount") in (None, "") and f.get("amount_paid"):
                    f["amount"] = f["amount_paid"]
            self._months(text)
        elif slot in ("end_date", "start_date"):
            ds = extract_dates(text, c.today)
            if re.search(r"(?i)still (?:working|employed|there)|abhi bhi|अभी भी", text) and slot == "end_date":
                f[slot] = {"text": "still employed", "iso": None}
            elif ds:
                f[slot] = {"text": ds[0]["text"], "iso": ds[0]["iso"]}
            else:
                f[slot] = {"text": clean_answer(text, 80), "iso": None}
        elif slot == "location":
            f["location"] = extract_location(text) or {"city": clean_answer(text, 60), "state": None}
        elif slot == "other_party":
            party = extract_party(text)
            if not party:
                party = re.sub(r"(?i)^(?:his|her|their|the)?\s*(?:name is|landlord is|landlord'?s name is|company is|"
                               r"employer is|it'?s|it is|naam|unka naam|company ka naam)\s*", "", text).strip(" .")
                party = re.sub(r"(?i)\s+(?:hai|he|h)\.?$", "", party)
            f["other_party"] = clean_answer(party, 80)
        elif slot == "proof":
            c.proof.update(extract_proof(c.problem_type, text, answering=True))
        elif slot == "your_name":
            name = re.sub(r"(?i)^(?:my name is|i am|i'm|name:|mera naam)\s*", "", text).strip(" .")
            name = re.sub(r"(?i)\s+(?:hai|he)\.?$", "", name)
            f["your_name"] = clean_answer(name, 60)
        else:
            f[slot] = clean_answer(text)

    def _months(self, text: str):
        m = MONTHS_COUNT_RE.search(text)
        if m and self.case.problem_type == "salary" and not self.case.facts.get("unpaid_months"):
            n = m.group(1).lower()
            self.case.facts["unpaid_months"] = int(n) if n.isdigit() else WORDNUM.get(n)

    def _extract_all(self, text: str):
        """Opportunistic extraction from any message. Never overwrites a fact already set."""
        c, f = self.case, self.case.facts
        p = c.problem_type
        low = text.lower()
        cats = {
            "monthly_rent": r"rent|kiraya|kiraye|किराया|किराए",
            "monthly_salary": r"monthly|per month|a month|/month|\bpm\b|ctc|in-hand|har mahine|हर महीने|महीने के",
            "amount": r"deposit|unpaid|not paid|pending|due|owe|baaki|baki|withheld|kept|not returned|refund|total|"
                      r"paid|बाकी|नहीं दी|नहीं मिली|जमा|डिपॉजिट|wapas",
        }
        amts = extract_amounts(text)
        # "deposit was 2,50,000 and he is returning only 1,00,000" -> amount at stake is the difference
        if p == "deposit" and len(amts) >= 2 and f.get("amount") in (None, ""):
            pos2 = low.find(amts[1]["raw"].lower())
            if re.search(r"(?:return(?:ing|ed)?|gave back|giving back|refund(?:ed|ing)?|paid back|wapas (?:kiya|diya|de raha))"
                         r"\s+(?:me\s+)?only|only\s+(?:return|gave|refund)|sirf", low[max(0, pos2 - 40):pos2]) \
                    and amts[0]["value"] > amts[1]["value"]:
                f["amount"] = amts[0]["value"] - amts[1]["value"]
                f["amount_note"] = f"deposit {amts[0]['raw']}, returned {amts[1]['raw']}"
        for a in amts:
            pos = low.find(a["raw"].lower())
            best, best_d = None, 999
            for cat, pat in cats.items():
                if cat == "monthly_rent" and p != "deposit" or cat == "monthly_salary" and p != "salary":
                    continue
                for m in re.finditer(pat, low):
                    d = (pos - m.end()) if m.end() <= pos else (m.start() - pos - len(a["raw"])) * 1.5
                    if 0 <= d < best_d and d <= 40:
                        best, best_d = cat, d
            slot = best or "amount"
            # Refunds: "I paid 12,000" is what was paid, not necessarily what is owed
            # (a gym that ran 4 of 12 months owes less). Keep it apart so the bot asks.
            before = low[max(0, pos - 45):pos]
            if (p == "refund" and slot == "amount" and re.search(r"\bpaid\b|payment|bought|purchased|cost", before)
                    and not re.search(r"refund|due|owe|back|remaining|pending|wapas|baaki|baki", before)):
                f.setdefault("amount_paid", a["value"])
                continue
            if f.get(slot) in (None, ""):
                f[slot] = a["value"]
        dates = extract_dates(text, c.today)
        if dates:
            known = {d["text"] for d in f.get("dates_mentioned", [])}
            f.setdefault("dates_mentioned", [])
            for d in dates:
                if d["text"] not in known:
                    f["dates_mentioned"].append({"text": d["text"], "iso": d["iso"]})
                ctx = low[max(0, d["pos"] - 50):d["pos"] + len(d["text"]) + 40]
                if p in ("deposit", "salary") and not f.get("end_date") and re.search(
                        r"vacat|moved out|left|shift|khaali|khali|chhod|last working|last day|resign|relieved|"
                        r"quit|छोड़|खाली", ctx):
                    f["end_date"] = {"text": d["text"], "iso": d["iso"]}
                sent_start = max(low.rfind(ch, 0, d["pos"]) for ch in ".!?\n।") + 1
                before = low[sent_start:d["pos"]]
                buy = list(re.finditer(r"order|paid|bought|booked|purchase|kharid|placed|joined|subscribed|ऑर्डर|खरीद",
                                       before))
                if p == "refund" and not f.get("start_date") and buy and not re.search(
                        r"return|pick ?up|picked|cancel|refund|deliver|shut|closed", before):
                    f["start_date"] = {"text": d["text"], "iso": d["iso"]}
        if not f.get("location"):
            loc = extract_location(text)
            if loc:
                f["location"] = loc
        if not f.get("other_party"):
            party = extract_party(text)
            if party:
                f["other_party"] = party
        if p:
            for k, v in extract_proof(p, text).items():
                if c.proof.get(k) is not True:
                    c.proof[k] = v
        if not f.get("their_reason"):
            q = (re.search(r"[\"“]([^\"”]{4,120})[\"”]", text)
                 or re.search(r"(?:^|[\s(])['‘]([^'’]{4,120})['’](?=[\s.,!?)]|$)", text))
            r2 = None
            for sent in re.split(r"[.!?।\n]", text):
                if re.search(r"(?i)deposit|keep|kept|keeping|deduct|cut|withh|rakh", sent):
                    r2 = re.search(r"(?i)(?:for|citing|because of|due to|in the name of|ke naam par|ke liye)\s+"
                                   r"((?:\w+\s){0,3}(?:charges?|cleaning|painting|damages?|repairs?|notice period|"
                                   r"maintenance))", sent)
                    if r2:
                        break
            if q and p in ("deposit", "salary"):
                f["their_reason"] = q.group(1).strip()
            elif r2 and p == "deposit":
                f["their_reason"] = r2.group(1).strip()
        if p == "refund" and not f.get("what_happened"):
            m = re.search(r"(?i)[^.!?\n]*\b(?:returned|return|not delivered|never (?:arrived|delivered|came)|cancel+ed|"
                          r"defective|damaged|wrong item|not working|service not|didn'?t get|did not get|"
                          r"shut down|closed down|refus\w+ to refund|"
                          r"refund nahi|wapas kiya)\b[^.!?\n]*", text)
            if m:
                f["what_happened"] = clean_answer(m.group(0), 200)
        if p == "salary":
            if re.search(r"(?i)\bresign", text) and "resigned" not in str(f.get("what_happened", "")):
                f.setdefault("what_happened", "resigned")
            self._months(text)

    # ------------------------------------------------------------- model turn
    def _model_payload(self, text: str) -> str:
        c = self.case
        types = [c.problem_type] if c.problem_type else ["deposit", "refund", "salary"]
        cards = [{"id": cd["id"], "title": cd["title"], "plain": cd["plain"], "cite": law.short_cite(cd["id"]),
                  "caveats": cd["caveats"]}
                 for cd in law.load()["cards"] if any(t in cd["applies_to"] for t in types + ["all"])]
        proof_keys = {k: lbl for t in types for k, (lbl, _) in PROOF_ITEMS[t].items()}
        payload = {
            "case_file": c.to_dict(),
            "missing_slots": c.missing_slots() if c.problem_type else ["problem_type"],
            "slot_order": SLOTS.get(c.problem_type, []),
            "proof_keys": proof_keys,
            "escalation_flags": [{"code": e["code"], "message": e["message"]} for e in c.escalations],
            "law_cards": cards,
            "recent_conversation": self.transcript[-8:],
            "latest_user_message": text,
        }
        return json.dumps(payload, ensure_ascii=False, default=str)

    def _model_turn(self, text: str, payload: str, new_esc: list[dict], newly_typed: bool) -> dict:
        c, f = self.case, self.case.facts
        # deterministic extraction first, so the model sees it and rules stay in charge
        if c.problem_type and c.pending_slot and c.pending_slot != "__type__" and not newly_typed:
            self._fill_slot(c.pending_slot, text)
        if c.problem_type:
            self._extract_all(text)
            payload = self._model_payload(text)
        data = self.llm.json(MODEL_SYSTEM, payload, max_tokens=900)
        pt = data.get("problem_type")
        if c.problem_type is None and pt in ("deposit", "refund", "salary"):
            c.problem_type, newly_typed = pt, True
        if data.get("language") and data["language"] != "other":
            c.language = data["language"]
        mf = data.get("facts") or {}
        for k in ("amount", "monthly_rent", "monthly_salary", "unpaid_months"):
            v = mf.get(k)
            if f.get(k) in (None, "") and v not in (None, ""):
                try:
                    f[k] = int(float(str(v).replace(",", "")))
                except ValueError:
                    pass
        for k in ("other_party", "what_happened", "their_reason", "promise", "your_name"):
            if not f.get(k) and mf.get(k):
                f[k] = clean_answer(str(mf[k]), 240)
        for k in ("start_date", "end_date"):
            if not f.get(k) and mf.get(k):
                v = str(mf[k])
                iso = v if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else None
                f[k] = {"text": v, "iso": iso}
        if not f.get("location") and (mf.get("city") or mf.get("state")):
            f["location"] = {"city": mf.get("city"), "state": mf.get("state")}
        if c.problem_type:
            keys = PROOF_ITEMS[c.problem_type]
            mp = {k: v for k, v in (data.get("proof") or {}).items() if k in keys and isinstance(v, bool)}
            if mp:
                for k, v in mp.items():
                    if c.proof.get(k) is not True:
                        c.proof[k] = v
                if c.pending_slot == "proof" and "proof" not in c.asked:
                    c.asked.append("proof")
        new_esc += c.add_escalations(check_case(c))
        if pt == "out_of_scope" and c.problem_type is None:
            c.status = "out_of_scope"
        asked = data.get("asked_slot")
        c.pending_slot = asked if asked in SLOTS.get(c.problem_type, []) else (c.missing_slots() or [None])[0]
        if c.problem_type and not c.missing_slots():
            c.status = "ready"
        reply = str(data.get("reply") or "").strip() or (question(c.problem_type, c.pending_slot, self.lang)
                                                         if c.problem_type and c.pending_slot else self.t("clarify"))
        esc_block = self._escalation_block(new_esc)
        msg = (esc_block + "\n\n" + reply) if esc_block else reply
        if c.status == "ready" and c.problem_type:
            msg += "\n\n" + c.summary_markdown()
        cited = ["NALSA-15100"] if esc_block else []
        return self._out(msg, kind="model", cited=cited, escalations=new_esc)

    # ----------------------------------------------------------- where I stand
    def where_i_stand(self, log_user: bool = True) -> dict:
        if log_user:
            self.transcript.append({"role": "user", "text": "[Where do I stand?]"})
        c = self.case
        if c.status == "out_of_scope":
            return self._out(self.t("out_of_scope") + "\n\n" + LEGAL_AID_LINE, kind="stand",
                             cited=["LEGAL-AID", "NALSA-15100"])
        base, ids = advice.where_you_stand(c)
        text = base
        prompt = REPHRASE_SYSTEM.format(lang=LANG_NAMES.get(c.language, "English")) + base
        self._shadow_cost(prompt, completion_tokens=_est_tokens(base) + 100)
        if self.llm.available and c.problem_type:
            try:
                data = self.llm.json(REPHRASE_SYSTEM.format(lang=LANG_NAMES.get(c.language, "English")), base,
                                     max_tokens=2500)
                cand = str(data.get("text") or "")
                kept = sum(1 for cid in ids if f"[[{cid}]]" in cand)
                had = sum(1 for cid in ids if f"[[{cid}]]" in base)
                if cand and kept >= max(1, had // 2):
                    text = cand
            except Exception as e:
                self.model_error = f"{type(e).__name__}: {e}"
        return self._out(text, kind="stand")

    # --------------------------------------------------------------- documents
    def documents(self) -> list[dict]:
        out = []
        for d in documents.build_documents(self.case):
            res = validate(d["text"])
            for v in res.violations:
                self.guardrail_log.append({"turn": len(self.transcript), "kind": "document", **v})
            out.append({**d, "text": res.text, "cited": res.cited, "violations": res.violations})
        return out

    def documents_reply(self, log_user: bool = True) -> dict:
        if log_user:
            self.transcript.append({"role": "user", "text": "[Draft notice]"})
        docs = self.documents()
        if not docs:
            return self._out("I can only draft documents for deposit, refund or salary cases. "
                             + LEGAL_AID_LINE, kind="documents", cited=["NALSA-15100"])
        body = "\n\n".join(f"#### {d['title']}\n```\n{d['text']}\n```" for d in docs)
        body += ("\n\nHow to send: print and sign, send by Speed Post or Registered Post with acknowledgement, keep the "
                 "receipt and a copy, and also email/WhatsApp a scanned copy. A lawyer can review it first; free legal "
                 "aid: 15100.")
        cited = [cid for d in docs for cid in d["cited"]] + documents.DOC_CARDS.get(self.case.problem_type, [])
        return self._out(body, kind="documents", cited=cited)

    # ---------------------------------------------------------------- practice
    def start_practice(self, log_user: bool = True) -> dict:
        if log_user:
            self.transcript.append({"role": "user", "text": "[Practise]"})
        c = self.case
        if not c.problem_type or c.status == "out_of_scope":
            return self._out("Practice works once I know your problem (deposit, refund or salary).", kind="practice")
        self.practice_state = {"active": True, "i": 0}
        persona = practice.PERSONA[c.problem_type]
        line = self._in_character(0)
        return self._out(TEXT["practice_intro"].format(persona=persona) + f"\n\n**{persona.capitalize()}:** {line}",
                         kind="practice")

    def _in_character(self, i: int) -> str:
        c = self.case
        seed = practice.opening(c, i)
        persona = practice.PERSONA[c.problem_type]
        prompt = PRACTICE_SYSTEM.format(persona=persona, lang=LANG_NAMES.get(c.language, "English"), seed=seed,
                                        facts=json.dumps(c.to_dict()["facts"], ensure_ascii=False, default=str))
        self._shadow_cost(prompt + json.dumps(self.transcript[-4:], ensure_ascii=False), completion_tokens=80)
        if self.llm.available:
            try:
                msgs = [{"role": "system", "content": prompt}] + [
                    {"role": "user" if m["role"] == "user" else "assistant", "content": m["text"]}
                    for m in self.transcript[-4:]]
                raw = self.llm.chat(msgs, json_mode=True, max_tokens=300)
                from common.llm import parse_json
                line = str(parse_json(raw).get("in_character") or "").strip()
                if line:
                    return line
            except Exception as e:
                self.model_error = f"{type(e).__name__}: {e}"
        return seed

    def _practice_turn(self, text: str) -> dict:
        c, st = self.case, self.practice_state
        fb = practice.feedback(c, st["i"], text)
        st["i"] += 1
        persona = practice.PERSONA[c.problem_type]
        if st["i"] >= len(practice.OBJECTIONS[c.problem_type]):
            st["active"] = False
            return self._out(fb + "\n\nThat's all four common objections. Practice ended. You did well to rehearse.",
                             kind="practice")
        return self._out(fb + f"\n\n**{persona.capitalize()}:** {self._in_character(st['i'])}", kind="practice")

    # ----------------------------------------------------------------- sources
    def sources_reply(self, log_user: bool = True) -> dict:
        if log_user:
            self.transcript.append({"role": "user", "text": "[Sources]"})
        ids = advice.select_cards(self.case) if self.case.problem_type else ["LEGAL-AID", "NALSA-15100"]
        return self._out("These are the only legal sources I use. Each was checked against an official source:\n\n"
                         + law.sources_markdown(ids), kind="sources", cited=ids)

    def cost_report(self) -> dict:
        return {"model": self.model_label, "actual": self.llm.cost_report(),
                "estimated_if_model_mode": dict(self.shadow), "model_error": self.model_error}

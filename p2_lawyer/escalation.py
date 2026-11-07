"""
Escalation rules. These are code, not model judgement: they run on every user
message and on the case file, in both offline and model mode, and the model
cannot switch them off.

level "urgent"  -> safety first (112), then a lawyer / legal aid
level "refer"   -> tell the person clearly they need a real lawyer or legal aid
level "caution" -> keep helping, but flag the risk
"""
from __future__ import annotations

import datetime as dt
import re

LARGE_AMOUNT = 500_000
DISTRICT_LIMIT = 5_000_000

RULES = [
    ("danger", "urgent", r"threat|dhamk|dhamaki|beat me|hit me|\bhit\b|assault|attack|violen|\bkill|maar(?:ne|unga|dunga|a)|"
                         r"goond|goon|abus(?:e|ed|ing) me|slap|unsafe|scared for my|धमकी|मारने|मारा|हिंसा|गुंडे"),
    ("criminal", "refer", r"\bpolice\b|\bfir\b|f\.i\.r|arrest|cheating case|fraud case|criminal|\b420\b|cyber ?crime|"
                          r"\bjail\b|पुलिस|एफआईआर|गिरफ्तार"),
    ("family", "refer", r"divorce|talaq|talak|custody|alimony|dowry|dahej|domestic violence|\b498a?\b|"
                        r"separation from my|my (?:husband|wife|in-laws) (?:won'?t|will not|is not|isn'?t|refus)|"
                        r"तलाक|दहेज|घरेलू हिंसा|ससुराल"),
    ("property", "refer", r"property dispute|land dispute|zameen|zamin|title deed|ancestral|inheritance|wasiyat|vasiyat|"
                          r"partition of|encroach|builder|possession of (?:my|the) flat|\brera\b|जमीन|ज़मीन|वसीयत|पुश्तैनी"),
    ("court_running", "refer", r"summons?|court date|next hearing|hearing (?:is|on)|sued me|filed (?:a )?(?:case|suit|complaint)"
                               r" against me|case against me|(?:received|got) (?:a )?legal notice|legal notice from|"
                               r"lawyer'?s notice|court notice|eviction (?:suit|case|petition)|मुकदमा|समन|मुझ पर केस"),
    ("eviction", "refer", r"evict|locked me out|lock(?:ed)? (?:the )?(?:flat|room|house)|threw (?:out )?my (?:things|stuff)|"
                          r"thrown out|ghar se nikal|nikaal diya|lock laga|बेदखल|घर से निकाल|ताला लगा"),
    ("minor", "refer", r"\bi(?:'m| am)\s*(?:only\s*)?(?:1[0-7]|[5-9])\s*(?:years?|yrs?)?\s*(?:old)?\b|\bminor\b|under 18|"
                       r"\bclass (?:[6-9]|1[0-2])(?:th)?\b|school student|meri umar (?:1[0-7]|[5-9])|नाबालिग"),
    ("other_area", "refer", r"cheque bounce|cheque bounced|accident|insurance claim|loan app|recovery agent|"
                            r"medical negligence|income tax|immigration|"
                            r"chit fund|ponzi|चेक बाउंस|बीमा|लोन"),
]
COMPILED = [(code, level, re.compile(p, re.I)) for code, level, p in RULES]

MESSAGES = {
    "danger": "Your safety comes first. If you are in danger now, call 112. Threats or violence are a criminal matter: "
              "please contact the police and a lawyer. I can still help you with the money part, but I cannot advise on the threat itself.",
    "criminal": "This involves police or criminal law, which I do not handle. Please speak to a lawyer. Free legal aid is available (see below).",
    "family": "Family matters like divorce, dowry or custody are outside what I can help with. Please speak to a lawyer or your District Legal Services Authority.",
    "property": "Property, land or builder disputes are outside what I can help with. Please speak to a lawyer.",
    "court_running": "A case, court notice or hearing is already running. Deadlines in court can be strict. Please see a lawyer now, "
                     "and do not ignore any notice or date.",
    "eviction": "Being locked out or evicted is a serious tenancy matter that I do not handle. Please speak to a lawyer or legal aid quickly.",
    "minor": "If you are under 18, please involve a parent or guardian. You are entitled to free legal services as a child.",
    "other_area": "This sounds like a different area of law (outside deposits, refunds and salary). I do not want to guess, so please speak to a lawyer.",
    "large_amount": "The amount is large (above Rs 5 lakh). For this much money a real lawyer is worth it, at least to review the notice before you send it.",
    "above_district_limit": "The amount is above Rs 50 lakh, so a consumer case would not go to the District Commission. Please see a lawyer.",
    "time_limit_near": "You may be close to the time limit for filing. Act quickly and consider seeing a lawyer this week.",
    "time_limit_passed": "The usual time limit may have passed. A late case is possible only with a good reason for the delay. Please see a lawyer before doing anything else.",
}
HINDI_PREFIX = {
    "danger": "आपकी सुरक्षा सबसे पहले। अगर अभी खतरा है तो 112 पर कॉल करें।",
    "family": "तलाक, दहेज या बच्चों की कस्टडी जैसे पारिवारिक मामले मेरे दायरे से बाहर हैं। कृपया वकील या जिला विधिक सेवा प्राधिकरण से मिलें।",
    "court_running": "कोर्ट का मामला या नोटिस पहले से चल रहा है। कृपया तुरंत वकील से मिलें।",
}
LEGAL_AID_LINE = ("Free legal aid: call NALSA's toll-free helpline 15100, or visit your District Legal Services Authority. "
                  "Women, children, SC/ST members, persons with disability, industrial workmen and people below the "
                  "state's income limit are among those entitled to a free lawyer.")
BLOCKING = {"family", "property", "other_area", "criminal"}


def check_text(text: str) -> list[dict]:
    hits = []
    for code, level, rx in COMPILED:
        m = rx.search(text)
        if m:
            if code == "danger" and m.group(0).lower() == "hit" and not re.search(r"hit (?:me|him|her|us)", text, re.I):
                continue
            hits.append({"code": code, "level": level, "trigger": m.group(0), "message": MESSAGES[code]})
    return hits


def check_case(case) -> list[dict]:
    """Rules on the structured case file: amount and time limits."""
    hits = []
    amt = case.facts.get("amount")
    if isinstance(amt, (int, float)):
        if case.problem_type == "refund" and amt > DISTRICT_LIMIT:
            hits.append({"code": "above_district_limit", "level": "refer", "trigger": f"Rs {amt:,}",
                         "message": MESSAGES["above_district_limit"]})
        elif amt > LARGE_AMOUNT:
            hits.append({"code": "large_amount", "level": "refer", "trigger": f"Rs {amt:,}",
                         "message": MESSAGES["large_amount"]})
    limit_days = {"refund": 730, "salary": 1095}.get(case.problem_type)
    key = "start_date" if case.problem_type == "refund" else "end_date"
    iso = (case.facts.get(key) or {}).get("iso") if isinstance(case.facts.get(key), dict) else None
    if limit_days and iso:
        try:
            age = (case.today - dt.date.fromisoformat(iso)).days
        except ValueError:
            age = None
        if age is not None and age > limit_days:
            hits.append({"code": "time_limit_passed", "level": "refer", "trigger": f"{age} days ago",
                         "message": MESSAGES["time_limit_passed"]})
        elif age is not None and age > limit_days - 120:
            hits.append({"code": "time_limit_near", "level": "caution", "trigger": f"{age} days ago",
                         "message": MESSAGES["time_limit_near"]})
    return hits

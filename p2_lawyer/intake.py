"""
Rule-based intake: classify the problem, detect the language, pull out facts
(amounts, dates, places, proof) and pick the next question to ask.

This is what runs with no model. In model mode the model does extraction, but
the slot list and proof checklist below are still the schema it must fill.
"""
from __future__ import annotations

import datetime as dt
import re

PROBLEM_TYPES = ("deposit", "refund", "salary")

HINGLISH_MARKERS = {
    "hai", "hain", "nahi", "nahin", "mera", "meri", "mere", "mujhe", "kya", "kar", "raha", "rahi", "rahe",
    "wapas", "vapas", "paise", "paisa", "bhai", "tha", "thi", "diya", "diye", "mila", "mili", "abhi", "kaise",
    "kyun", "kyon", "aur", "bhi", "ko", "se", "ne", "ki", "ka", "ke", "hoga", "kuch", "koi", "kab", "mahine",
    "saal", "hum", "humne", "maine", "unhone", "bol", "bola", "boli", "de", "dena", "lena", "chahiye", "ji",
}
SCRIPTS = {
    "hi": (0x0900, 0x097F), "bn": (0x0980, 0x09FF), "pa": (0x0A00, 0x0A7F), "gu": (0x0A80, 0x0AFF),
    "ta": (0x0B80, 0x0BFF), "te": (0x0C00, 0x0C7F), "kn": (0x0C80, 0x0CFF), "ml": (0x0D00, 0x0D7F),
}
LANG_NAMES = {"en": "English", "hi": "Hindi", "hinglish": "Hinglish", "bn": "Bengali", "pa": "Punjabi",
              "gu": "Gujarati", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam"}


def detect_language(text: str) -> str:
    letters = [ch for ch in text if ch.isalpha()]
    if not letters:
        return "en"
    for code, (lo, hi) in SCRIPTS.items():
        n = sum(1 for ch in letters if lo <= ord(ch) <= hi)
        if n / len(letters) > 0.3:
            return code
    words = re.findall(r"[a-z]+", text.lower())
    hits = sum(1 for w in words if w in HINGLISH_MARKERS)
    return "hinglish" if hits >= 2 and hits / max(len(words), 1) >= 0.12 else "en"


KEYWORDS = {
    "deposit": [r"security deposit", r"\bdeposit\b", r"landlord", r"land lord", r"house ?owner", r"flat owner",
                r"\bowner\b", r"\brent(?:ed|al)?\b", r"tenant", r"\bpg\b", r"paying guest", r"kiray[ae]", r"kiraye",
                r"makaa?n ?malik", r"\bjama\b", r"\bjamaa\b", r"advance wapas", r"vacat", r"moved out", r"shifted out",
                r"मकान मालिक", r"किराय", r"किराए", r"जमा", r"डिपॉजिट", r"सिक्योरिटी", r"एडवांस"],
    "refund": [r"refund", r"\border(?:ed)?\b", r"deliver", r"\breturn(?:ed)?\b", r"cancel", r"e-?commerce",
               r"online (?:shopping|order|purchase)", r"\bseller\b", r"customer care", r"\bproduct\b", r"\bapp\b",
               r"booking", r"flight", r"airline", r"membership", r"\bgym\b", r"subscription", r"\bcourse\b",
               r"warranty", r"defective", r"replacement", r"paise wapas nahi", r"रिफंड", r"ऑर्डर", r"सामान",
               r"वापसी", r"डिलीवरी", r"flipkart", r"amazon", r"myntra", r"meesho", r"ajio", r"swiggy", r"zomato"],
    "salary": [r"salary", r"salaries", r"\bwages?\b", r"\bpay ?slip", r"payslip", r"employer", r"\bhr\b",
               r"resign", r"full and final", r"\bf ?& ?f\b", r"\bfnf\b", r"notice period", r"relieving",
               r"tankh?wa+h?", r"tankhah", r"\bvetan\b", r"\bpagar\b", r"salary nahi", r"my company", r"old company",
               r"former company", r"office", r"job", r"naukri", r"तनख्वाह", r"तनख़्वाह", r"वेतन", r"सैलरी",
               r"मज़दूरी", r"मजदूरी", r"नौकरी", r"कंपनी", r"मालिक ने पैसे"],
}
WEIGHTS = {r"security deposit": 3, r"landlord": 3, r"refund": 3, r"salary": 3, r"tankh?wa+h?": 3,
           r"मकान मालिक": 3, r"तनख्वाह": 3, r"वेतन": 3, r"रिफंड": 3, r"\bwages?\b": 3, r"resign": 2,
           r"सैलरी": 3, r"डिपॉजिट": 3, r"\bdeposit\b": 2}


def classify(text: str) -> tuple[str | None, dict]:
    t = text.lower()
    scores = {}
    for ptype, pats in KEYWORDS.items():
        scores[ptype] = sum(WEIGHTS.get(p, 1) for p in pats if re.search(p, t))
    if scores["deposit"] >= 3 and scores["refund"] and re.search(r"deposit|landlord|kiray|मकान", t):
        scores["deposit"] += 2
    best = max(scores, key=scores.get)
    ranked = sorted(scores.values(), reverse=True)
    if ranked[0] == 0 or ranked[0] == ranked[1]:
        return None, scores
    return best, scores


def parse_choice(text: str) -> str | None:
    t = text.strip().lower()
    m = re.fullmatch(r"\(?([123])\)?\.?", t)
    if m:
        return PROBLEM_TYPES[int(m.group(1)) - 1]
    return None


AMOUNT_RE = re.compile(
    r"(?P<cur>₹|rs\.?|inr|rupees?|रु\.?)?\s*(?P<num>\d{1,3}(?:,\d{2,3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*"
    r"(?P<mult>k\b|thousand|hazaa?r|हज़ार|हजार|lakhs?|lacs?|लाख|crores?|cr\b|करोड़)?\s*(?P<cur2>rupees?|rs\b|/-|रुपये|रुपए|रुपया)?",
    re.I)
MULT = {"k": 1e3, "thousand": 1e3, "hazar": 1e3, "hazaar": 1e3, "हज़ार": 1e3, "हजार": 1e3,
        "lakh": 1e5, "lakhs": 1e5, "lac": 1e5, "lacs": 1e5, "लाख": 1e5, "crore": 1e7, "crores": 1e7, "cr": 1e7,
        "करोड़": 1e7}


MONEY_WORDS = (r"deposit|salary|salaries|refund|rent\b|kiraya|kiraye|paise|paisa|rupay|rupaye|rupees|amount|baaki|baki|"
               r"\bdue\b|\bowe|\bpaid\b|\bpay\b|wages|tankh|जमा|तनख्वाह|रुपये|वेतन|किराया|डिपॉजिट|सैलरी")


def extract_amounts(text: str, force: bool = False) -> list[dict]:
    """Return [{'value': int, 'raw': str, 'ctx': str}] for money amounts in text."""
    out = []
    for m in AMOUNT_RE.finditer(text):
        num = m.group("num")
        mult = (m.group("mult") or "").lower()
        has_cur = bool(m.group("cur") or m.group("cur2"))
        before, after = text[max(0, m.start("num") - 1):m.start("num")], text[m.end("num"):m.end("num") + 1]
        if before in "/-." and before or after in ("/", "-") and after and not mult:
            continue
        value = float(num.replace(",", "")) * MULT.get(mult, 1)
        plain_year = re.fullmatch(r"(19|20)\d{2}", num) and not has_cur and not mult
        if plain_year:
            continue
        near = text[max(0, m.start() - 25):m.end() + 25].lower()
        money_word = re.search(MONEY_WORDS, near) and value >= 500 and not re.search(r"\d\s*(?:years?|yrs|saal|months?|days?)\b", text[m.start("num"):m.end() + 8].lower())
        if not (has_cur or mult or "," in num or (force and value >= 100) or money_word):
            continue
        ident = re.search(r"(?:order|ticket|\bid|\bno\.?|number|#|pnr|flat|room|house|sector|pin|phone|mobile|"
                          r"utr|awb|tracking|account)\s*[:#-]?\s*$", text[max(0, m.start("num") - 14):m.start("num")].lower())
        if ident or (len(num.replace(",", "")) >= 8 and not has_cur):
            continue
        if value < 50:
            continue
        s = max(0, m.start() - 45)
        out.append({"value": int(round(value)), "raw": m.group(0).strip(), "ctx": text[s:m.end() + 30].lower()})
    return out


MONTHS_COUNT_RE = re.compile(r"(\d+|one|two|three|four|five|six|ek|do|teen|char|paanch|दो|तीन|चार|पांच)\s*"
                             r"(?:months?|mahine|mahina|महीने|महीना)", re.I)
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "ek": 1, "do": 2, "teen": 3,
           "char": 4, "paanch": 5, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5}

MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct",
                                           "nov", "dec"])}
HI_MONTHS = {"जनवरी": 1, "फरवरी": 2, "फ़रवरी": 2, "मार्च": 3, "अप्रैल": 4, "मई": 5, "जून": 6, "जुलाई": 7,
             "अगस्त": 8, "सितंबर": 9, "सितम्बर": 9, "अक्टूबर": 10, "नवंबर": 11, "नवम्बर": 11, "दिसंबर": 12,
             "दिसम्बर": 12}
MON = r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
HIMON = "(?:" + "|".join(HI_MONTHS) + ")"
DATE_PATTERNS = [
    ("dmy_num", re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})\b")),
    ("ymd", re.compile(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b")),
    ("d_mon_y", re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + MON + r")\b,?\s*(\d{4})?", re.I)),
    ("mon_d_y", re.compile(r"\b(" + MON + r")\s+(\d{1,2})(?:st|nd|rd|th)?\b,?\s*(\d{4})?", re.I)),
    ("mon_y", re.compile(r"\b(" + MON + r")\s*,?\s*(\d{4})\b", re.I)),
    ("hi_d_mon_y", re.compile(r"(\d{1,2})\s*(" + HIMON + r")\s*,?\s*(\d{4})?")),
    ("hi_mon_y", re.compile(r"(" + HIMON + r")\s*,?\s*(\d{4})")),
    ("relative", re.compile(r"\b(?:last|pichhle|pichle|past)\s+(?:month|week|year|mahine|saal)\b|"
                            r"\b\d+\s*(?:days?|weeks?|months?|years?|din|hafte|mahine|saal)\s*(?:ago|back|pehle|se|before)\b|"
                            r"\byesterday\b|\btoday\b|\bkal\b|पिछले\s+(?:\d+\s*)?\S+|\d+\s*(?:दिन|महीने|साल)\s*(?:पहले|से)", re.I)),
]


def _mk(y, m, d):
    try:
        y = int(y)
        y = y + 2000 if y < 100 else y
        return dt.date(y, int(m), int(d)).isoformat()
    except (ValueError, TypeError):
        return None


def extract_dates(text: str, today: dt.date | None = None) -> list[dict]:
    today = today or dt.date.today()
    out, used = [], []
    for kind, rx in DATE_PATTERNS:
        for m in rx.finditer(text):
            if any(s <= m.start() < e for s, e in used):
                continue
            iso = None
            g = m.groups()
            if kind == "dmy_num":
                iso = _mk(g[2], g[1], g[0])
            elif kind == "ymd":
                iso = _mk(g[0], g[1], g[2])
            elif kind == "d_mon_y":
                iso = _mk(g[2] or today.year, MONTHS[g[1][:3].lower()], g[0])
            elif kind == "mon_d_y":
                iso = _mk(g[2] or today.year, MONTHS[g[0][:3].lower()], g[1])
            elif kind == "mon_y":
                iso = _mk(g[1], MONTHS[g[0][:3].lower()], 1)
            elif kind == "hi_d_mon_y":
                iso = _mk(g[2] or today.year, HI_MONTHS[g[1]], g[0])
            elif kind == "hi_mon_y":
                iso = _mk(g[1], HI_MONTHS[g[0]], 1)
            elif kind == "relative":
                iso = _relative(m.group(0).lower(), today)
            used.append((m.start(), m.end()))
            out.append({"text": m.group(0).strip(), "iso": iso, "pos": m.start()})
    out.sort(key=lambda d: d["pos"])
    return out


def _relative(s: str, today: dt.date) -> str | None:
    m = re.search(r"(\d+)\s*(day|din|दिन|week|hafte|month|mahine|महीने|year|saal|साल)", s)
    if m:
        n, unit = int(m.group(1)), m.group(2)
        days = {"day": 1, "din": 1, "दिन": 1, "week": 7, "hafte": 7, "month": 30, "mahine": 30, "महीने": 30,
                "year": 365, "saal": 365, "साल": 365}[unit]
        return (today - dt.timedelta(days=n * days)).isoformat()
    if "yesterday" in s or s == "kal":
        return (today - dt.timedelta(days=1)).isoformat()
    if "last month" in s or "pichle mahine" in s or "pichhle mahine" in s:
        return (today - dt.timedelta(days=30)).isoformat()
    return None


STATES = ["Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
          "Himachal Pradesh", "Jharkhand", "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
          "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana",
          "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir", "Ladakh",
          "Chandigarh", "Puducherry"]
CITIES = {"bengaluru": "Karnataka", "bangalore": "Karnataka", "mysuru": "Karnataka", "mumbai": "Maharashtra",
          "pune": "Maharashtra", "nagpur": "Maharashtra", "thane": "Maharashtra", "nashik": "Maharashtra",
          "delhi": "Delhi", "new delhi": "Delhi", "noida": "Uttar Pradesh", "greater noida": "Uttar Pradesh",
          "ghaziabad": "Uttar Pradesh", "lucknow": "Uttar Pradesh", "kanpur": "Uttar Pradesh",
          "varanasi": "Uttar Pradesh", "prayagraj": "Uttar Pradesh", "gurugram": "Haryana", "gurgaon": "Haryana",
          "faridabad": "Haryana", "chennai": "Tamil Nadu", "coimbatore": "Tamil Nadu", "madurai": "Tamil Nadu",
          "hyderabad": "Telangana", "secunderabad": "Telangana", "visakhapatnam": "Andhra Pradesh",
          "vijayawada": "Andhra Pradesh", "guntur": "Andhra Pradesh", "kolkata": "West Bengal",
          "ahmedabad": "Gujarat", "surat": "Gujarat", "vadodara": "Gujarat", "jaipur": "Rajasthan",
          "jodhpur": "Rajasthan", "indore": "Madhya Pradesh", "bhopal": "Madhya Pradesh", "patna": "Bihar",
          "guwahati": "Assam", "dispur": "Assam", "kochi": "Kerala", "thiruvananthapuram": "Kerala",
          "chandigarh": "Chandigarh", "bhubaneswar": "Odisha", "ranchi": "Jharkhand", "dehradun": "Uttarakhand",
          "मुंबई": "Maharashtra", "दिल्ली": "Delhi", "जयपुर": "Rajasthan", "लखनऊ": "Uttar Pradesh",
          "पटना": "Bihar", "बेंगलुरु": "Karnataka", "पुणे": "Maharashtra", "नोएडा": "Uttar Pradesh",
          "इंदौर": "Madhya Pradesh", "भोपाल": "Madhya Pradesh", "कानपुर": "Uttar Pradesh"}
MTA_STATES = {"Andhra Pradesh", "Tamil Nadu", "Uttar Pradesh", "Assam"}


def extract_location(text: str) -> dict | None:
    t = text.lower()
    for city in sorted(CITIES, key=len, reverse=True):
        if re.search(r"(?<![\w])" + re.escape(city) + r"(?![\w])", t):
            return {"city": city.title() if city.isascii() else city, "state": CITIES[city]}
    for st in STATES:
        if re.search(r"\b" + re.escape(st.lower()) + r"\b", t):
            return {"city": None, "state": st}
    return None


PROOF_ITEMS = {
    "deposit": {
        "rent_agreement": ("Rent agreement", [r"agreement", r"lease", r"एग्रीमेंट", r"अनुबंध", r"करारनामा"]),
        "deposit_paid_proof": ("Proof you paid the deposit (bank transfer, UPI, cheque or receipt)",
                               [r"receipt", r"bank transfer", r"\bupi\b", r"g ?pay", r"google pay", r"phone ?pe",
                                r"paytm", r"\bneft\b", r"\bimps\b", r"bank statement", r"cheque", r"रसीद",
                                r"transfer", r"online payment", r"bank se"]),
        "handover_proof": ("Photos/video or a handover note from move-out day",
                           [r"photo", r"video", r"handover", r"hand over", r"keys", r"inspection", r"फोटो", r"वीडियो"]),
        "written_demand": ("Messages or emails where you asked for the deposit",
                           [r"whats ?app", r"\bchats?\b", r"messages?", r"e-?mails?", r"\bmail\b", r"\bsms\b",
                            r"चैट", r"मैसेज", r"text(?:ed)?"]),
    },
    "refund": {
        "order_proof": ("Order confirmation or invoice", [r"invoice", r"order (?:id|number|no|confirmation|details)",
                                                         r"\bbill\b", r"booking (?:id|confirmation)", r"\bpnr\b",
                                                         r"receipt", r"इनवॉइस", r"बिल"]),
        "payment_proof": ("Proof of payment (bank/card statement, UPI reference)",
                          [r"\bupi\b", r"card statement", r"bank statement", r"debited", r"transaction id",
                           r"credit card", r"debit card", r"payment (?:proof|screenshot|receipt)", r"\butr\b",
                           r"statement", r"पेमेंट"]),
        "return_proof": ("Proof of return / cancellation (pickup receipt, tracking, cancellation email)",
                         [r"pick ?up", r"picked up", r"courier", r"tracking", r"\bawb\b", r"return (?:receipt|id)",
                          r"cancellation (?:email|mail|message|confirmation)", r"cancelled"]),
        "complaint_trail": ("Your complaints to the company (ticket numbers, chats, emails)",
                            [r"ticket", r"complaint (?:number|no|id|e-?mails?)", r"complain(?:ed|ts)", r"\bchats?\b",
                             r"e-?mailed (?:them|support|customer care)", r"wrote to", r"customer care", r"screenshots?",
                             r"grievance", r"whats ?app"]),
    },
    "salary": {
        "appointment_letter": ("Offer / appointment letter or employment contract",
                               [r"offer letter", r"appointment letter", r"joining letter", r"contract", r"agreement",
                                r"ऑफर लेटर", r"नियुक्ति"]),
        "salary_slips": ("Salary slips", [r"salary slips?", r"pay ?slips?", r"सैलरी स्लिप", r"वेतन पर्ची"]),
        "bank_statements": ("Bank statements showing past salary credits",
                            [r"bank statements?", r"\bstatements?\b", r"credited", r"passbook", r"पासबुक", r"बैंक"]),
        "work_proof": ("Proof you worked the unpaid period (attendance, work emails, timesheets)",
                       [r"attendance", r"time ?sheets?", r"work e-?mails?", r"office e-?mails?", r"\bid card\b",
                        r"हाजिरी", r"रजिस्टर"]),
        "exit_proof": ("Resignation email / acceptance / relieving letter",
                       [r"resignation", r"relieving", r"acceptance", r"experience letter", r"exit e-?mail",
                        r"इस्तीफ"]),
        "hr_messages": ("Messages or emails from HR/employer about the dues",
                        [r"whats ?app", r"\bchats?\b", r"e-?mails? from (?:hr|manager|boss)", r"hr (?:said|replied|told)",
                         r"messages?", r"मैसेज"]),
    },
}
NEG_BEFORE = re.compile(r"(?:\bno\b|\bnot\b|don'?t have|do not have|never|without|\bno\s+\w+\s+or\b|lost|"
                        r"\bna\b|bina|बिना|नहीं|koi bhi nahi)\s*(?:\w+\s+){0,3}$", re.I)
NEG_AFTER = re.compile(r"^\s*(?:\w+\s+){0,2}(?:nahi|nahin|नहीं|nai)\b", re.I)
NONE_RE = re.compile(r"(?i)\b(?:nothing|none|no proof|no documents?|nothing in writing|kuch nahi|kuch bhi nahi|"
                     r"koi proof nahi|koi saboot nahi|no paperwork|all cash|only cash)\b|कुछ नहीं|कोई सबूत नहीं")
ALL_RE = re.compile(r"(?i)\b(?:all of (?:them|these|the above)|everything|sab hai|sab kuch hai|all four|all three)\b|सब है")


def extract_proof(ptype: str, text: str, answering: bool = False) -> dict:
    """Map proof items to True/False. Items not mentioned are False only when answering the proof question."""
    items = PROOF_ITEMS.get(ptype, {})
    found = {}
    t = text.lower()
    for key, (_, pats) in items.items():
        for p in pats:
            m = re.search(p, t)
            if not m:
                continue
            neg = NEG_BEFORE.search(t[max(0, m.start() - 30):m.start()]) or NEG_AFTER.search(t[m.end():m.end() + 25])
            found[key] = not bool(neg)
            break
    if answering:
        if ALL_RE.search(t) and not NONE_RE.search(t):
            return {k: True for k in items}
        for k in items:
            found.setdefault(k, False)
    elif NONE_RE.search(t):
        for k in items:
            found.setdefault(k, False)
    return found


SKIP_RE = re.compile(r"(?i)^\s*(?:skip|pass|don'?t know|dont know|do not know|not sure|no idea|pata nahi|"
                     r"maloom nahi|nahi pata|पता नहीं|मालूम नहीं|na|n/a|-)\s*[.!]?\s*$")

SLOTS = {
    "deposit": ["amount", "monthly_rent", "other_party", "location", "end_date", "their_reason", "proof", "your_name"],
    "refund": ["other_party", "amount", "start_date", "what_happened", "promise", "location", "proof", "your_name"],
    "salary": ["other_party", "amount", "monthly_salary", "end_date", "their_reason", "location", "proof", "your_name"],
}
SLOT_LABELS = {
    "amount": "Amount at stake", "monthly_rent": "Monthly rent", "monthly_salary": "Monthly salary",
    "other_party": "Other side", "location": "Place", "end_date": "Date you left / moved out",
    "start_date": "Order / payment date", "their_reason": "Their reason", "what_happened": "What went wrong",
    "promise": "What they promised", "proof": "Proof", "your_name": "Your name",
}

QUESTIONS = {
    "en": {
        "deposit": {
            "amount": "How much security deposit did you pay, and how much of it has not been returned?",
            "monthly_rent": "What was the monthly rent?",
            "other_party": "What is the landlord's full name? (Add their address too if you have it.)",
            "location": "Which city and state is the house in?",
            "end_date": "When did you vacate and hand over the keys? A date is best.",
            "their_reason": "Has the landlord given any reason for keeping the money? What exactly did they say?",
            "proof": "Which of these do you have? (a) rent agreement, (b) proof you paid the deposit (bank transfer, UPI, cheque or receipt), (c) photos/video from move-out day, (d) messages or emails where you asked for the deposit.",
            "your_name": "Last one: your full name for the draft notice? (Type 'skip' to leave a blank.)",
        },
        "refund": {
            "other_party": "Which company, app or seller is this with?",
            "amount": "How much did you pay, and how much refund is due?",
            "start_date": "When did you order or pay? A date is best.",
            "what_happened": "What went wrong: not delivered, returned, cancelled, defective, or a service not given?",
            "promise": "Did they promise a refund? When, and do you have a ticket or complaint number?",
            "location": "Which city and state do you live in? (You can file a consumer complaint where you live.)",
            "proof": "Which of these do you have? (a) order confirmation or invoice, (b) proof of payment, (c) proof of return or cancellation, (d) your complaints to the company (tickets, chats, emails).",
            "your_name": "Last one: your full name for the draft notice? (Type 'skip' to leave a blank.)",
        },
        "salary": {
            "other_party": "What is the name of your employer (company or person)?",
            "amount": "How much salary is unpaid in total, and for which months?",
            "monthly_salary": "What was your monthly salary?",
            "end_date": "Are you still working there? If you left, what was your last working day?",
            "their_reason": "What has the employer or HR said about why it is not paid?",
            "location": "Which city and state is (or was) your workplace in?",
            "proof": "Which of these do you have? (a) offer/appointment letter, (b) salary slips, (c) bank statements showing earlier salary, (d) proof you worked the unpaid period (attendance, work emails), (e) resignation/relieving email or letter, (f) messages from HR about the dues.",
            "your_name": "Last one: your full name for the draft notice? (Type 'skip' to leave a blank.)",
        },
    },
    "hinglish": {
        "deposit": {
            "amount": "Aapne kitna security deposit diya tha, aur usme se kitna wapas nahi mila?",
            "monthly_rent": "Mahine ka kiraya kitna tha?",
            "other_party": "Makaan malik ka poora naam kya hai? (Address ho to woh bhi likhiye.)",
            "location": "Ghar kis sheher aur state mein hai?",
            "end_date": "Aapne flat kab khaali kiya aur chaabi kab di? Date ho to best hai.",
            "their_reason": "Makaan malik ne paise rakhne ki koi wajah batayi? Unhone exactly kya kaha?",
            "proof": "Inme se aapke paas kya hai? (a) rent agreement, (b) deposit dene ka proof (bank transfer, UPI, cheque ya receipt), (c) flat chhodte waqt ki photo/video, (d) WhatsApp/email jisme aapne deposit maanga.",
            "your_name": "Aakhri sawaal: notice ke liye aapka poora naam? ('skip' likh sakte hain.)",
        },
        "refund": {
            "other_party": "Yeh kis company, app ya seller ke saath hai?",
            "amount": "Aapne kitna pay kiya tha, aur kitna refund baaki hai?",
            "start_date": "Order ya payment kab kiya tha? Date ho to best hai.",
            "what_happened": "Kya hua tha: delivery nahi hui, return kiya, cancel kiya, kharab nikla, ya service nahi mili?",
            "promise": "Kya unhone refund ka promise kiya? Kab, aur koi ticket ya complaint number hai?",
            "location": "Aap kis sheher aur state mein rehte hain? (Complaint aap apne sheher mein kar sakte hain.)",
            "proof": "Inme se aapke paas kya hai? (a) order confirmation ya invoice, (b) payment ka proof, (c) return/cancel ka proof, (d) company ko ki gayi complaints (ticket, chat, email).",
            "your_name": "Aakhri sawaal: notice ke liye aapka poora naam? ('skip' likh sakte hain.)",
        },
        "salary": {
            "other_party": "Aapke employer (company ya malik) ka naam kya hai?",
            "amount": "Kul kitni salary baaki hai, aur kin mahino ki?",
            "monthly_salary": "Aapki monthly salary kitni thi?",
            "end_date": "Kya aap abhi bhi wahan kaam karte hain? Agar chhod diya, to last working day kab tha?",
            "their_reason": "Employer ya HR ne salary na dene ki kya wajah batayi?",
            "location": "Aapka office kis sheher aur state mein hai (ya tha)?",
            "proof": "Inme se aapke paas kya hai? (a) offer/appointment letter, (b) salary slips, (c) purani salary wale bank statements, (d) kaam karne ka proof (attendance, work emails), (e) resignation/relieving email ya letter, (f) HR ke messages.",
            "your_name": "Aakhri sawaal: notice ke liye aapka poora naam? ('skip' likh sakte hain.)",
        },
    },
    "hi": {
        "deposit": {
            "amount": "आपने कितना सिक्योरिटी डिपॉजिट दिया था, और उसमें से कितना वापस नहीं मिला?",
            "monthly_rent": "महीने का किराया कितना था?",
            "other_party": "मकान मालिक का पूरा नाम क्या है? (पता हो तो वह भी लिखिए।)",
            "location": "घर किस शहर और राज्य में है?",
            "end_date": "आपने घर कब खाली किया और चाबी कब दी? तारीख हो तो सबसे अच्छा।",
            "their_reason": "मकान मालिक ने पैसे रखने की कोई वजह बताई? उन्होंने ठीक-ठीक क्या कहा?",
            "proof": "इनमें से आपके पास क्या है? (a) रेंट एग्रीमेंट, (b) डिपॉजिट देने का सबूत (बैंक ट्रांसफर, UPI, चेक या रसीद), (c) घर छोड़ते समय की फोटो/वीडियो, (d) मैसेज या ईमेल जिनमें आपने डिपॉजिट माँगा।",
            "your_name": "आखिरी सवाल: नोटिस के लिए आपका पूरा नाम? ('skip' लिख सकते हैं।)",
        },
        "refund": {
            "other_party": "यह किस कंपनी, ऐप या विक्रेता के साथ है?",
            "amount": "आपने कितना भुगतान किया, और कितना रिफंड बाकी है?",
            "start_date": "ऑर्डर या भुगतान कब किया था? तारीख हो तो सबसे अच्छा।",
            "what_happened": "क्या गड़बड़ हुई: डिलीवरी नहीं हुई, सामान लौटाया, कैंसल किया, खराब निकला, या सेवा नहीं मिली?",
            "promise": "क्या उन्होंने रिफंड का वादा किया? कब, और क्या कोई टिकट या शिकायत नंबर है?",
            "location": "आप किस शहर और राज्य में रहते हैं? (शिकायत आप अपने शहर में कर सकते हैं।)",
            "proof": "इनमें से आपके पास क्या है? (a) ऑर्डर कन्फर्मेशन या इनवॉइस, (b) भुगतान का सबूत, (c) सामान लौटाने/कैंसल करने का सबूत, (d) कंपनी से की गई शिकायतें (टिकट, चैट, ईमेल)।",
            "your_name": "आखिरी सवाल: नोटिस के लिए आपका पूरा नाम? ('skip' लिख सकते हैं।)",
        },
        "salary": {
            "other_party": "आपके नियोक्ता (कंपनी या मालिक) का नाम क्या है?",
            "amount": "कुल कितनी तनख्वाह बाकी है, और किन महीनों की?",
            "monthly_salary": "आपकी महीने की तनख्वाह कितनी थी?",
            "end_date": "क्या आप अभी भी वहाँ काम करते हैं? अगर छोड़ दिया, तो आखिरी कार्य-दिवस कब था?",
            "their_reason": "मालिक या HR ने तनख्वाह न देने की क्या वजह बताई?",
            "location": "आपका काम का स्थान किस शहर और राज्य में है (या था)?",
            "proof": "इनमें से आपके पास क्या है? (a) ऑफर/नियुक्ति पत्र, (b) सैलरी स्लिप, (c) पुरानी तनख्वाह वाले बैंक स्टेटमेंट, (d) काम करने का सबूत (हाजिरी, ईमेल), (e) इस्तीफा/रिलीविंग पत्र, (f) HR के मैसेज।",
            "your_name": "आखिरी सवाल: नोटिस के लिए आपका पूरा नाम? ('skip' लिख सकते हैं।)",
        },
    },
}


def question(ptype: str, slot: str, lang: str) -> str:
    table = QUESTIONS.get(lang) or QUESTIONS["en"]
    return table[ptype][slot]


BRANDS = ["flipkart", "amazon", "myntra", "meesho", "ajio", "nykaa", "swiggy", "zomato", "makemytrip", "indigo",
          "air india", "spicejet", "ola", "uber", "paytm", "bigbasket", "blinkit", "zepto", "tata cliq", "croma",
          "reliance digital", "urban company", "cult.fit", "byju's"]
PARTY_RE = re.compile(r"\b(?:Mr\.?|Mrs\.?|Ms\.?|Shri|Smt\.?|Sri)\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2}")
COMPANY_RE = re.compile(r"\b([A-Z][\w&.]*(?:\s+[A-Z][\w&.]*){0,3}\s+(?:Pvt\.?\s*Ltd\.?|Private Limited|Ltd\.?|"
                        r"Limited|LLP|Technologies|Solutions|Services|Infotech|Systems|Enterprises|Traders|Logistics|Gym|Fitness|"
                        r"Academy|Institute|Classes|Hospital|Clinic|Travels|Airlines|Motors|Mart|Stores?|Hotel|Resorts?|"
                        r"Builders|Electronics|Furniture))")


CAMEL_RE = re.compile(r"\b([A-Z][a-z]+[A-Z][a-z]\w*)\b")
NOT_PARTIES = {"WhatsApp", "PhonePe", "GooglePay", "YouTube", "LinkedIn", "PayTm", "iPhone", "MacBook", "PlayStation"}


def extract_party(text: str) -> str | None:
    m = PARTY_RE.search(text) or COMPANY_RE.search(text)
    if m:
        return m.group(0).strip()
    for cm in CAMEL_RE.finditer(text):
        if cm.group(1) not in NOT_PARTIES:
            return cm.group(1)
    t = text.lower()
    for b in BRANDS:
        if re.search(r"\b" + re.escape(b) + r"\b", t):
            return b.title()
    return None


def clean_answer(text: str, limit: int = 240) -> str:
    t = re.sub(r"\s+", " ", text).strip()
    return t if len(t) <= limit else t[:limit].rsplit(" ", 1)[0] + "..."

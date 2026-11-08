"""
"Where you stand": assembled by rules from the case file and the law cards.
No model is needed. In model mode the model may only rephrase/translate this
text (and must keep the [[CARD]] references); it cannot add law.
"""
from __future__ import annotations

from . import law
from .escalation import LEGAL_AID_LINE

CARD_SETS = {
    "deposit": ["TENANCY-STATE", "CONTRACT-BREACH", "MTA", "LEGAL-AID", "NALSA-15100"],
    "refund": ["CPA-CONSUMER", "CPA-DEFICIENCY", "ECOM-GRIEVANCE", "NCH", "CPA-RELIEF", "CPA-WHERE-FILE",
               "CPA-JURISDICTION", "CPA-FEE", "CPA-LIMITATION", "EJAGRITI", "LEGAL-AID", "NALSA-15100"],
    "salary": ["COW-IN-FORCE", "COW-TIMELINE", "COW-CLAIM", "CONTRACT-BREACH", "LEGAL-AID", "NALSA-15100"],
}


def select_cards(case) -> list[str]:
    """Which cards apply. Rules, not model."""
    ids = list(CARD_SETS.get(case.problem_type, ["LEGAL-AID", "NALSA-15100"]))
    if case.problem_type == "refund":
        online = any(w in (case.story + " " + str(case.facts.get("other_party", "")) + " " +
                           str(case.facts.get("what_happened", ""))).lower()
                     for w in ("online", "app", "website", "order", "deliver", "flipkart", "amazon", "kart", "myntra"))
        if not online:
            ids.remove("ECOM-GRIEVANCE")
    if any(e["code"] in ("danger",) for e in case.escalations):
        ids.insert(0, "EMERGENCY-112")
    if any(e["code"] in ("criminal",) for e in case.escalations):
        ids.append("BNS")
    return ids


def _cite(cid: str) -> str:
    return f"[[{cid}]]"


def where_you_stand(case) -> tuple[str, list[str]]:
    ids = select_cards(case)
    p = case.problem_type
    out = []
    if not p:
        out.append("I could not yet tell which of my three areas this is (deposit, refund or salary). "
                   "Please tell me a little more, or speak to free legal aid.")
        out.append("\n" + LEGAL_AID_LINE + " " + _cite("NALSA-15100"))
        return "\n".join(out), ["LEGAL-AID", "NALSA-15100"]

    if case.language in ("hi", "hinglish"):
        out.append("_(नीचे की जानकारी अभी अंग्रेज़ी में है: बिना AI मॉडल के मैं क़ानूनी बातें सिर्फ़ जाँचे हुए अंग्रेज़ी पाठ में देता हूँ। "
                   "मॉडल चालू होने पर यह आपकी भाषा में आएगी। मदद के लिए 15100 पर कॉल करें।)_"
                   if case.language == "hi" else
                   "_(Neeche ki jaankari abhi English mein hai: bina AI model ke main kanooni baatein sirf checked English "
                   "text mein deta hoon. Model on hone par yeh Hinglish mein aayegi. Madad ke liye 15100 par call karein.)_")
    amt = case.fmt("amount")
    party = case.fmt("other_party") if case.facts.get("other_party") else \
        {"deposit": "the landlord", "refund": "the seller", "salary": "Your employer"}[p]
    one_line = {
        "deposit": f"You paid a security deposit and {party} has not returned {amt}.",
        "refund": f"You paid {party} and a refund of {amt} has not reached you.",
        "salary": f"{party} has not paid you {amt} in salary/dues.",
    }[p]
    out.append("### Your case in one line\n" + one_line.replace("not given", "(not given yet)"))

    if case.escalations:
        out.append("### Please read first")
        for e in case.escalations:
            out.append(f"- {e['message']}")
        out.append(f"- {LEGAL_AID_LINE} {_cite('NALSA-15100')}")

    out.append("### What the law says (only verified sources)")
    for cid in ids:
        if cid in ("NALSA-15100", "EMERGENCY-112"):
            continue
        if cid == "MTA" and not case.in_mta_state():
            continue
        c = law.card(cid)
        cite = law.short_cite(cid)
        out.append(f"- **{c['title']}.** {c['plain']}" + (f" ({cite})" if cite else "") + f" {_cite(cid)}")
    if p == "deposit":
        state = (case.facts.get("location") or {}).get("state") if isinstance(case.facts.get("location"), dict) else None
        if case.in_mta_state():
            out.append(f"- You said the house is in **{state}**. The Centre reported {state} revised its tenancy law on the "
                       f"lines of the Model Tenancy Act. Your state's own Act may set up a Rent Authority and limits on "
                       f"deposits, but I do not hold its exact text. Check it or ask legal aid. {_cite('MTA')}")
            rent = case.facts.get("monthly_rent")
            dep = case.facts.get("amount")
            if isinstance(rent, int) and isinstance(dep, int) and rent > 0:
                out.append(f"- For reference, the model law caps a home deposit at two months' rent (Rs {2 * rent:,} for you). "
                           f"Whether your state copied this cap, and whether it applies to your tenancy's start date, needs checking. {_cite('MTA')}")
        elif state:
            out.append(f"- You said the house is in **{state}**. I have no verified record that {state} adopted the Model "
                       f"Tenancy Act, so I treat this as a normal agreement dispute: the deposit is owed back under your "
                       f"agreement unless there is a valid deduction. {_cite('TENANCY-STATE')}")

    out.append(f"### How strong is your proof: **{case.proof_strength()}**")
    have = case.have_proof()
    if have:
        out.append("You have: " + "; ".join(have) + ".")
    missing = case.missing_proof()
    if missing:
        out.append("Missing or not confirmed, and how to fix it:")
        for _, lbl, tip in missing:
            out.append(f"- **{lbl}.** {tip}")
    else:
        out.append("You have all the key documents I look for. Keep copies in two places.")

    out.append("### Your options, step by step")
    out += OPTIONS[p](case)

    out.append("### Time limits")
    if p == "refund":
        out.append(f"- File a consumer complaint within 2 years of the problem. {_cite('CPA-LIMITATION')}")
        out.append(f"- If you bought online: the platform's grievance officer must reply within 48 hours and resolve within one month. {_cite('ECOM-GRIEVANCE')}"
                   if "ECOM-GRIEVANCE" in ids else "- Give the seller a clear written deadline (for example 15 days).")
    elif p == "salary":
        out.append(f"- Wage claims to the authority: within 3 years from when the claim arose. {_cite('COW-CLAIM')}")
        out.append(f"- The employer should have paid by the 7th of the next month, or within 2 working days after you left. {_cite('COW-TIMELINE')}")
    else:
        out.append("- I do not have a verified time limit for deposit recovery cases in my sources. Do not wait: "
                   "send the notice now and ask legal aid or a lawyer about the time limit for a civil case.")

    out.append("### What I am not sure about")
    out += UNSURE[p](case)
    out.append("- I only know what you told me. I have not seen your documents.")
    out.append("- This is legal information, not legal advice. For a decision about going to court, speak to a lawyer. "
               f"{LEGAL_AID_LINE} {_cite('NALSA-15100')}")
    return "\n".join(out), ids


def _deposit_options(case):
    return [
        "1. **Ask in writing (today).** Send a short WhatsApp/email: the amount, the date you vacated, and a date to pay by. "
        "Ask for an itemised bill for any deduction (for example 'painting') and which clause of the agreement allows it.",
        "2. **Send a legal notice (draft ready in 'Draft notice').** Give 15 days. Send by Speed Post or Registered Post with "
        "acknowledgement, keep the receipt, and also send it by email/WhatsApp. You can send it yourself or through a lawyer.",
        "3. **Talk / settle.** Many landlords pay after a formal notice. If they offer part, decide whether a quick "
        "settlement is worth more to you than the full amount later. Get any settlement in writing.",
        ("4. **Rent Authority / Rent Court (your state's tenancy Act).** Your state revised its tenancy law on Model Tenancy "
         "Act lines, so there may be a Rent Authority for disputes. Ask the District Collector's office or legal aid which "
         "office handles it. [[MTA]]") if case.in_mta_state() else
        ("4. **Civil recovery.** If they still do not pay, the next step is a money recovery case in the civil court for "
         "breach of the agreement. A lawyer (or free legal aid) should handle this step. [[CONTRACT-BREACH]]"),
        "5. **Free help any time:** NALSA legal aid helpline 15100. [[NALSA-15100]]",
    ]


def _refund_options(case):
    online = "ECOM-GRIEVANCE" in select_cards(case)
    steps = []
    if online:
        steps.append("1. **Complain to the grievance officer.** Find the 'Grievance Officer' contact on the app/website "
                     "(it must be displayed). Write: order details, amount, what happened, and the refund you want. "
                     "They must acknowledge within 48 hours and resolve within one month. [[ECOM-GRIEVANCE]]")
    else:
        steps.append("1. **Complain in writing to the seller/company.** Email or letter: details, amount, the refund you "
                     "want, and a date. Keep proof that you sent it.")
    steps += [
        "2. **National Consumer Helpline.** Call 1915 (8 AM to 8 PM) or WhatsApp 8800001915, or file on "
        "consumerhelpline.gov.in. It is free and tries to settle with the company first. [[NCH]]",
        "3. **Legal notice (draft ready in 'Draft notice').** Give 15 days. Mention that you will go to the Consumer "
        "Commission if not paid.",
        "4. **Consumer Commission.** File online on e-Jagriti (e-jagriti.gov.in) at the District Commission where you live. "
        "No fee if you paid up to Rs 5 lakh. The Commission can order refund with interest and compensation. "
        "[[EJAGRITI]] [[CPA-WHERE-FILE]] [[CPA-FEE]] [[CPA-RELIEF]]",
        "5. **Also:** if you paid by card or UPI, you can ask your bank whether they can raise a dispute on the "
        "transaction. (I have no verified rule on this; it depends on your bank.)",
    ]
    return steps


def _salary_options(case):
    return [
        "1. **Ask in writing.** Email HR and your manager: months unpaid, amount, your last working day, and a date to pay "
        "by. Ask for a written breakdown of your full-and-final settlement.",
        "2. **Legal notice / demand letter (draft ready in 'Draft notice').** Give 15 days and point out the time limits "
        "for paying wages. [[COW-TIMELINE]]",
        "3. **Wage claim with the government authority.** Go to your district's Labour Department office and ask for the "
        "authority that hears wage claims. You, your union, or the Inspector-cum-Facilitator can file. It can order up "
        "to ten times the claim as compensation. [[COW-CLAIM]]",
        "4. **Civil route via a lawyer** for large amounts, bonuses, or if the employer raises counter-claims (notice "
        "period, damages). [[CONTRACT-BREACH]]",
        "5. **Free help any time:** NALSA legal aid helpline 15100; industrial workmen are among those entitled to a free "
        "lawyer. [[LEGAL-AID]] [[NALSA-15100]]",
    ]


OPTIONS = {"deposit": _deposit_options, "refund": _refund_options, "salary": _salary_options}

UNSURE = {
    "deposit": lambda c: [
        "- Your state's exact tenancy law and any time limit: I do not hold state Acts.",
        "- Whether a deduction (painting, cleaning, damage, notice period) is valid depends on your agreement's wording.",
    ],
    "refund": lambda c: [
        "- Whether the seller's own policy (for example 'no refund on opened items') was shown to you before you paid.",
        "- How much interest or compensation a Commission would award: nobody can promise this.",
    ],
    "salary": lambda c: [
        "- Which wage authority handles your district: it depends on your state's notification under the Code.",
        "- If the salary fell due before 21 Nov 2025, whether the old Payment of Wages Act route applies. [[COW-IN-FORCE]]",
        "- Deductions for notice period or company property depend on your appointment letter.",
    ],
}

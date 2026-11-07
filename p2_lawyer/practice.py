"""
Practice mode: the assistant plays the other side so the person can rehearse.
Offline: a scripted set of the objections people actually hear, with a coach
note scored by simple rules. Model mode: the model plays a persona, but the
coach tips and legal points still come from here and pass the validator.
"""
from __future__ import annotations

import re

PERSONA = {"deposit": "the landlord", "refund": "the company's customer support agent", "salary": "the HR manager"}

OBJECTIONS = {
    "deposit": [
        ("The flat needs fresh painting and deep cleaning. I'm keeping {amount} for that. That's standard.",
         "Ask for an itemised bill with receipts, and which clause of the agreement allows this deduction. Ask them to "
         "separate real damage from ordinary use. Offer to pay only proven, reasonable costs if the agreement allows it."),
        ("You didn't give me proper notice before leaving, so the deposit is gone.",
         "Check the notice clause in your agreement. If you gave notice, quote the date and the message. If you did not, "
         "ask them to show what the agreement says about short notice; it rarely means losing the whole deposit, but "
         "the wording decides."),
        ("I'll return it when the new tenant pays me. Wait a few weeks.",
         "Your agreement is with them, not with the next tenant. Ask politely for a fixed date in writing, and say you "
         "will send a formal notice if it is not paid by then."),
        ("There was damage to the geyser and furniture. You have no proof it was like that before.",
         "Ask for photos and repair bills. Share your move-out photos or the handover message. Offer a joint inspection "
         "record if it is still possible."),
    ],
    "refund": [
        ("Your refund has been processed from our side. It takes 7 to 10 working days to reflect.",
         "Ask for the refund reference number (UTR/ARN) and the exact date it was processed. Write it down. If it does "
         "not arrive, your bank can trace it with that number."),
        ("The seller rejected your return because the product was used or damaged.",
         "Ask for the rejection reason and photos in writing. Share your pickup proof and any unboxing photos. Ask for "
         "the grievance officer's contact; online platforms must show it."),
        ("Our policy only allows store credit or a voucher, not a cash refund.",
         "Ask where this policy was shown before you paid. If you were promised a refund, quote that message. Say you "
         "will escalate to the National Consumer Helpline (1915) and then the Consumer Commission."),
        ("Your ticket has been escalated to the concerned team. Please wait.",
         "Ask for the ticket number, the name of the team, and a date. Note that an online platform's grievance officer "
         "must resolve complaints within one month."),
    ],
    "salary": [
        ("Full and final settlement takes 45 to 90 days as per company policy.",
         "Point out that the Code on Wages, 2019 sets a time limit for paying wages after you leave (two working days). "
         "Ask for at least the salary part now and a written timeline for anything else."),
        ("You didn't serve your full notice period, so we are adjusting your salary.",
         "Ask for the written calculation and the clause in your appointment letter. If the deduction is bigger than "
         "the clause allows, say so in writing. If they claim large damages, talk to a lawyer."),
        ("The company is facing cash problems. Please wait a few months, everyone is in the same boat.",
         "Be sympathetic but firm: ask for a written commitment with dates and amounts, and a part-payment now. Keep "
         "everything in email."),
        ("You haven't returned the laptop and access card, so we can't process anything.",
         "Return company property against a written acknowledgement (email or signed note). Then ask again for payment "
         "with a date."),
    ],
}

CHECKS = [
    ("amount", r"(?:₹|rs\.?|rupees?|\d{1,3}(?:,\d{2,3})+|\d{4,}|lakh|हज़ार|हजार|रुपये)", "State the exact amount you are owed."),
    ("deadline", r"(?:\bby\b|within|\bdays?\b|deadline|date|tak\b|तक|दिन)", "Give a clear deadline (for example 'within 15 days')."),
    ("proof", r"(?:agreement|receipt|screenshot|photo|bill|invoice|email|letter|slip|statement|message|proof|record|"
              r"saboot|सबूत|रसीद)", "Point to your proof (agreement, receipt, messages)."),
    ("next_step", r"(?:notice|complain|complaint|helpline|1915|commission|labour|authority|lawyer|legal|court|"
                  r"शिकायत|नोटिस)", "Say calmly what you will do next if they don't pay (notice, helpline, Commission/authority)."),
    ("in_writing", r"(?:in writing|written|email|mail|likh|लिख)", "Ask for their answer in writing."),
]


def coach(answer: str) -> tuple[int, list[str], list[str]]:
    t = answer.lower()
    good, tips = [], []
    for key, pat, tip in CHECKS:
        if re.search(pat, t):
            good.append(key)
        else:
            tips.append(tip)
    if re.search(r"(?:idiot|stupid|cheat(?:er)?|chor|fraud|bloody|i will kill|dekh lunga)", t):
        tips.insert(0, "Avoid insults or threats. Stay calm and factual; it protects you if this goes to a Commission or court.")
    return len(good), good, tips


def opening(case, i: int = 0) -> str:
    p = case.problem_type
    amt = case.fmt("amount") if case.facts.get("amount") else "some of it"
    line, _ = OBJECTIONS[p][i % len(OBJECTIONS[p])]
    return line.format(amount=amt)


def feedback(case, i: int, answer: str) -> str:
    p = case.problem_type
    score, good, tips = coach(answer)
    _, model_answer = OBJECTIONS[p][i % len(OBJECTIONS[p])]
    parts = [f"**Coach:** your reply covered {score}/5 key points"
             + (f" ({', '.join(good)})" if good else "") + "."]
    if tips:
        parts.append("To make it stronger: " + " ".join(tips[:3]))
    parts.append(f"**A good answer here:** {model_answer}")
    return "\n\n".join(parts)

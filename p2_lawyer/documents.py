"""
Fill-in templates for the documents a person needs. Templates are code, not
model output, so the legal wording never drifts. Missing facts stay as
[PLACEHOLDERS] the user must fill in; we never invent them.
"""
from __future__ import annotations

DRAFT_BANNER = ("DRAFT. Check every fact before sending. This is a template filled from what you told me, "
                "not advice from a lawyer. Replace every [PLACEHOLDER].")


def _v(case, slot, placeholder):
    v = case.facts.get(slot)
    if v in (None, "", {}):
        return f"[{placeholder}]"
    if slot in ("amount", "amount_paid", "monthly_rent", "monthly_salary") and isinstance(v, (int, float)):
        return f"Rs {int(v):,}/-"
    if isinstance(v, dict) and "text" in v:
        return v["text"]
    if isinstance(v, dict) and "state" in v:
        return ", ".join(x for x in (v.get("city"), v.get("state")) if x)
    return str(v)


def _header(case, to_label):
    today = case.today.strftime("%d %B %Y")
    name = _v(case, "your_name", "YOUR FULL NAME")
    return [
        f"Date: {today}",
        "",
        "From:",
        f"{name}",
        "[YOUR ADDRESS]",
        "[YOUR PHONE / EMAIL]",
        "",
        "To:",
        f"{_v(case, 'other_party', to_label)}",
        f"[{to_label} ADDRESS]",
        "",
        "Sent by: Speed Post / Registered Post A.D. and email/WhatsApp",
        "",
    ]


def _proof_lines(case):
    have = case.have_proof()
    if not have:
        return ["I will produce documents and messages in support of the above when required."]
    return ["Copies of the following are with me and will be produced when required: " + "; ".join(have) + "."]


def deposit_notice(case) -> str:
    amt = _v(case, "amount", "DEPOSIT AMOUNT")
    lines = _header(case, "LANDLORD NAME")
    lines += [
        "Subject: Legal notice for refund of security deposit",
        "",
        "Sir/Madam,",
        "",
        f"1. I was your tenant at [PROPERTY ADDRESS], {_v(case, 'location', 'CITY, STATE')}, under a rent agreement dated "
        f"[AGREEMENT DATE], at a monthly rent of {_v(case, 'monthly_rent', 'MONTHLY RENT')}.",
        f"2. At the start of the tenancy I paid you a refundable security deposit of {amt}.",
        f"3. I vacated the premises and handed over vacant possession and the keys on {_v(case, 'end_date', 'DATE OF VACATING')}. "
        "All rent and utility dues up to that date were cleared.",
        f"4. Despite my requests, you have not returned the deposit of {amt}. "
        + (f"The reason you gave was: \"{case.facts['their_reason']}\". " if case.facts.get("their_reason") else "")
        + "No itemised bill or proof of any damage beyond normal use has been given to me, and no clause of our "
          "agreement allows you to keep the deposit for this.",
        "5. Keeping my deposit without a valid reason is a breach of our agreement, and you are liable to compensate "
        "me for the loss caused by the breach under Section 73 of the Indian Contract Act, 1872.",
        "",
        f"I therefore call upon you to pay me {amt} within 15 (fifteen) days of receiving this notice, by bank transfer "
        "to [YOUR BANK ACCOUNT / UPI ID]. If any deduction is claimed, send an itemised bill with proof within the same period.",
        "",
        "If you fail to do so, I will take appropriate legal action to recover the amount with interest and costs, "
        "entirely at your risk as to costs and consequences.",
        "",
        *_proof_lines(case),
        "",
        "Yours faithfully,",
        f"{_v(case, 'your_name', 'YOUR FULL NAME')}",
        "(Signature)",
    ]
    return "\n".join(lines)


def _paid(case) -> str:
    """What the user paid. Differs from the refund due when only part is owed."""
    return _v(case, "amount_paid", "") if case.facts.get("amount_paid") else _v(case, "amount", "AMOUNT PAID")


def refund_notice(case) -> str:
    amt = _v(case, "amount", "AMOUNT PAID / REFUND DUE")
    lines = _header(case, "COMPANY / SELLER NAME (and its Grievance Officer)")
    lines += [
        "Subject: Legal notice for refund under the Consumer Protection Act, 2019",
        "",
        "Sir/Madam,",
        "",
        f"1. On {_v(case, 'start_date', 'DATE OF ORDER / PAYMENT')} I paid {_paid(case)} to you for [PRODUCT / SERVICE], "
        "order/booking number [ORDER NUMBER].",
        f"2. What went wrong: {_v(case, 'what_happened', 'WHAT HAPPENED: not delivered / returned / cancelled / defective')}.",
        f"3. The refund was not paid. {('Your promise/response: ' + case.facts['promise'] + '.') if case.facts.get('promise') else ''} "
        "My complaints to your customer care have not resolved this.",
        "4. I bought this for my own use and am a consumer under Section 2(7) of the Consumer Protection Act, 2019. "
        "Failing to refund the amount due is a deficiency in service under Section 2(11) of the Consumer Protection Act, 2019.",
        "5. Your grievance officer was required to acknowledge my complaint within 48 hours and resolve it within one month "
        "under Rule 4(5) of the Consumer Protection (E-Commerce) Rules, 2020. [Delete this point if you did not buy online.]",
        "",
        f"I call upon you to refund {amt} within 15 (fifteen) days of receiving this notice to my original payment method "
        "or to [YOUR BANK ACCOUNT / UPI ID].",
        "",
        "If you fail to do so, I will file a complaint before the District Consumer Disputes Redressal Commission seeking "
        "refund with interest, compensation and costs (Section 39(1) of the Consumer Protection Act, 2019).",
        "",
        *_proof_lines(case),
        "",
        "Yours faithfully,",
        f"{_v(case, 'your_name', 'YOUR FULL NAME')}",
        "(Signature)",
    ]
    return "\n".join(lines)


def salary_notice(case) -> str:
    amt = _v(case, "amount", "TOTAL UNPAID AMOUNT")
    still = _v(case, "end_date", "") == "still employed"
    lines = _header(case, "EMPLOYER / COMPANY NAME (through its HR head / Director)")
    lines += [
        "Subject: Legal notice for payment of unpaid wages and dues",
        "",
        "Sir/Madam,",
        "",
        f"1. I {'am' if still else 'was'} employed with you as [DESIGNATION] from [JOINING DATE] at a monthly salary of "
        f"{_v(case, 'monthly_salary', 'MONTHLY SALARY')}, at {_v(case, 'location', 'WORKPLACE CITY, STATE')}.",
        "2. I am still working with you." if still else
        f"2. My last working day was {_v(case, 'end_date', 'LAST WORKING DAY')}.",
        f"3. You have not paid my wages amounting to {amt} for [MONTHS UNPAID]. "
        + (f"Your stated reason: \"{case.facts['their_reason']}\". " if case.facts.get("their_reason") else ""),
        "4. Under Section 17 of the Code on Wages, 2019, monthly wages must be paid before the seventh day of the next "
        "month, and on resignation or removal the wages due must be paid within two working days.",
        "",
        (f"I call upon you to pay {amt}, along with my salary slips, " if still else
         f"I call upon you to pay {amt}, along with my salary slips and a written full-and-final settlement statement, ")
        +
        "within 15 (fifteen) days of receiving this notice, to [YOUR BANK ACCOUNT].",
        "",
        "If you fail to do so, I will file a claim before the authority under Section 45 of the Code on Wages, 2019, "
        "which may also order compensation, and take any other legal action available to me, at your risk as to costs.",
        "",
        *_proof_lines(case),
        "",
        "Yours faithfully,",
        f"{_v(case, 'your_name', 'YOUR FULL NAME')}",
        "(Signature)",
    ]
    return "\n".join(lines)


def consumer_complaint_draft(case) -> str:
    amt_v = case.facts.get("amount")
    fee = ("Nil (amount up to Rs 5 lakh)" if isinstance(amt_v, int) and amt_v <= 500_000
           else "[CHECK FEE TABLE: Rs 200 above Rs 5 lakh up to Rs 10 lakh]")
    forum = ("District Consumer Disputes Redressal Commission" if not isinstance(amt_v, int) or amt_v <= 5_000_000
             else "[STATE COMMISSION: amount above Rs 50 lakh, see a lawyer]")
    return "\n".join([
        "DRAFT CONSUMER COMPLAINT SUMMARY (to fill into e-Jagriti, e-jagriti.gov.in)",
        "",
        f"Before: {forum}, {_v(case, 'location', 'YOUR DISTRICT')}",
        f"Complainant: {_v(case, 'your_name', 'YOUR FULL NAME')}, [ADDRESS]",
        f"Opposite party: {_v(case, 'other_party', 'COMPANY / SELLER NAME')}, [REGISTERED ADDRESS from website/invoice]",
        f"Value of goods/service paid: {_paid(case)}   Fee: {fee}",
        "",
        "Facts (short, in date order):",
        f"- {_v(case, 'start_date', 'DATE')}: paid {_paid(case)} for [PRODUCT/SERVICE], order [NUMBER].",
        f"- What went wrong: {_v(case, 'what_happened', 'DESCRIBE')}.",
        f"- Refund promise / response: {_v(case, 'promise', 'DESCRIBE, with ticket numbers')}.",
        "- [DATE]: legal notice sent; no refund within 15 days.",
        "",
        "Deficiency in service / unfair trade practice: refund not paid despite requests (Section 2(11) and, if a false "
        "promise was made, Section 2(47) of the Consumer Protection Act, 2019).",
        "",
        "Reliefs sought (Section 39(1) of the Consumer Protection Act, 2019):",
        f"(a) refund of {_v(case, 'amount', 'AMOUNT')} with interest; (b) compensation of Rs [AMOUNT] for harassment and "
        "loss; (c) litigation costs of Rs [AMOUNT].",
        "",
        "Jurisdiction: I reside / work within this District (Section 34(2) of the Consumer Protection Act, 2019). "
        "Filed within 2 years of the cause of action (Section 69 of the Consumer Protection Act, 2019).",
        "",
        "Documents to upload: order/invoice, payment proof, return/cancellation proof, complaint trail, legal notice and "
        "postal receipt, ID proof.",
    ])


def wage_claim_draft(case) -> str:
    return "\n".join([
        "DRAFT WAGE CLAIM SUMMARY (for the authority under Section 45 of the Code on Wages, 2019)",
        "",
        "To: The Authority under the Code on Wages, 2019, [DISTRICT] (ask your district Labour Department office)",
        f"Applicant: {_v(case, 'your_name', 'YOUR FULL NAME')}, [ADDRESS, PHONE]",
        f"Employer: {_v(case, 'other_party', 'EMPLOYER NAME')}, [ESTABLISHMENT ADDRESS], {_v(case, 'location', 'CITY, STATE')}",
        f"Monthly wages: {_v(case, 'monthly_salary', 'MONTHLY SALARY')}   Last working day: {_v(case, 'end_date', 'DATE')}",
        f"Amount claimed: {_v(case, 'amount', 'TOTAL')} for [MONTHS]",
        "",
        "Grounds: wages not paid within the time limits in Section 17 of the Code on Wages, 2019, despite written "
        "requests and a legal notice dated [DATE].",
        "Relief: payment of the claim, and compensation as the authority thinks fit.",
        "Filed within 3 years of the claim arising.",
        "",
        "Attach: appointment letter, salary slips, bank statements, attendance/work proof, resignation/relieving emails, "
        "HR messages, legal notice and postal receipt.",
    ])


def build_documents(case) -> list[dict]:
    """Return [{'title', 'filename', 'text'}]. Empty if the case is out of scope."""
    if case.problem_type is None or case.status == "out_of_scope":
        return []
    p = case.problem_type
    docs = []
    notice = {"deposit": deposit_notice, "refund": refund_notice, "salary": salary_notice}[p](case)
    docs.append({"title": "Legal notice", "filename": f"legal_notice_{p}.txt", "text": DRAFT_BANNER + "\n\n" + notice})
    if p == "refund":
        docs.append({"title": "Consumer complaint summary (for e-Jagriti)", "filename": "consumer_complaint_draft.txt",
                     "text": DRAFT_BANNER + "\n\n" + consumer_complaint_draft(case)})
    if p == "salary":
        docs.append({"title": "Wage claim summary", "filename": "wage_claim_draft.txt",
                     "text": DRAFT_BANNER + "\n\n" + wage_claim_draft(case)})
    return docs


DOC_CARDS = {"deposit": ["CONTRACT-BREACH"],
             "refund": ["CPA-CONSUMER", "CPA-DEFICIENCY", "ECOM-GRIEVANCE", "CPA-RELIEF", "CPA-WHERE-FILE",
                        "CPA-LIMITATION", "CPA-FEE", "EJAGRITI"],
             "salary": ["COW-TIMELINE", "COW-CLAIM"]}

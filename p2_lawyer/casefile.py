"""The structured case file that builds up during the conversation."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

from .intake import PROOF_ITEMS, SLOT_LABELS, SLOTS, MTA_STATES

PROOF_TIPS = {
    "rent_agreement": "No agreement? Old rent receipts, bank transfers of monthly rent, or messages with the landlord about rent also show there was a tenancy.",
    "deposit_paid_proof": "Ask your bank for a statement showing the transfer. If you paid cash, look for any message where the landlord mentions the deposit amount, or a witness who was present.",
    "handover_proof": "If you have no move-out photos, a message sent on the day you returned the keys helps. Ask anyone who was there to confirm the flat's condition.",
    "written_demand": "Send a short WhatsApp/email today asking for the deposit by a date. This creates a written record and their reply is evidence.",
    "order_proof": "Download the invoice or order details page from the app/website now, before the account changes.",
    "payment_proof": "Download your bank/card statement for that month or a UPI transaction screenshot with the reference number.",
    "return_proof": "Screenshot the return/cancellation status and pickup details in the app. Courier tracking IDs help.",
    "complaint_trail": "Raise a written complaint (email or in-app) and note the ticket number. Screenshot every chat.",
    "appointment_letter": "Look in your email for the offer letter. If there is none, past salary credits and work emails still show employment.",
    "salary_slips": "Ask HR in writing for your salary slips. Download them from the payroll portal if you still have access.",
    "bank_statements": "Download bank statements showing earlier salary credits from this employer.",
    "work_proof": "Forward key work emails to your personal email only if your contract allows it; otherwise note dates, attendance and who you worked with.",
    "exit_proof": "Save your resignation email and any reply accepting it. If you have no relieving letter, ask for it in writing.",
    "hr_messages": "Email HR asking for your dues with a breakdown and a date. Their reply (or silence) is useful.",
}


@dataclass
class CaseFile:
    problem_type: str | None = None
    language: str = "en"
    facts: dict = field(default_factory=dict)
    proof: dict = field(default_factory=dict)
    pending_slot: str | None = None
    asked: list = field(default_factory=list)
    skipped: list = field(default_factory=list)
    escalations: list = field(default_factory=list)
    story: str = ""
    today: dt.date = field(default_factory=dt.date.today)
    status: str = "intake"

    def slots(self) -> list[str]:
        return SLOTS.get(self.problem_type, [])

    def is_filled(self, slot: str) -> bool:
        if slot == "proof":
            return "proof" in self.asked
        return slot in self.facts and self.facts[slot] not in (None, "", {})

    def missing_slots(self) -> list[str]:
        return [s for s in self.slots() if not self.is_filled(s) and s not in self.skipped]

    def intake_done(self) -> bool:
        return bool(self.problem_type) and not self.missing_slots()

    def still_employed(self) -> bool:
        v = self.facts.get("end_date")
        return isinstance(v, dict) and v.get("text") == "still employed"

    def proof_items(self) -> dict:
        items = dict(PROOF_ITEMS.get(self.problem_type, {}))
        if self.problem_type == "salary" and self.still_employed():
            items.pop("exit_proof", None)
        return items

    def have_proof(self) -> list[str]:
        return [lbl for k, (lbl, _) in self.proof_items().items() if self.proof.get(k) is True]

    def missing_proof(self) -> list[tuple[str, str, str]]:
        """(key, label, tip) for each proof item not confirmed."""
        return [(k, lbl, PROOF_TIPS.get(k, "")) for k, (lbl, _) in self.proof_items().items()
                if self.proof.get(k) is not True]

    def proof_strength(self) -> str:
        items = self.proof_items()
        if not items:
            return "unknown"
        have = sum(1 for k in items if self.proof.get(k) is True)
        ratio = have / len(items)
        return "strong" if ratio >= 0.75 else "medium" if ratio >= 0.4 else "weak"

    def add_escalations(self, hits: list[dict]) -> list[dict]:
        new = []
        have = {e["code"] for e in self.escalations}
        for h in hits:
            if h["code"] not in have:
                self.escalations.append(h)
                have.add(h["code"])
                new.append(h)
        return new

    def needs_lawyer(self) -> bool:
        return any(e["level"] in ("urgent", "refer") for e in self.escalations)

    def in_mta_state(self) -> bool:
        loc = self.facts.get("location") or {}
        return isinstance(loc, dict) and loc.get("state") in MTA_STATES

    def fmt(self, slot: str) -> str:
        v = self.facts.get(slot)
        if v in (None, "", {}):
            return "not given"
        if slot in ("amount", "monthly_rent", "monthly_salary") and isinstance(v, (int, float)):
            return f"Rs {int(v):,}"
        if isinstance(v, dict) and "text" in v:
            return v["text"] + (f" ({v['iso']})" if v.get("iso") and v["iso"] != v["text"] else "")
        if isinstance(v, dict) and "state" in v:
            return ", ".join(x for x in (v.get("city"), v.get("state")) if x)
        return str(v)

    def summary_markdown(self) -> str:
        if not self.problem_type:
            return "_Problem type not identified yet._"
        names = {"deposit": "Security deposit not returned", "refund": "Consumer refund not given",
                 "salary": "Unpaid salary / dues"}
        lines = [f"**Problem:** {names[self.problem_type]}"]
        for s in self.slots():
            if s == "proof":
                continue
            lines.append(f"- **{SLOT_LABELS[s]}:** {self.fmt(s)}")
        if self.facts.get("unpaid_months"):
            lines.append(f"- **Unpaid months:** {self.facts['unpaid_months']}")
        if self.facts.get("dates_mentioned"):
            lines.append("- **Dates mentioned:** " + "; ".join(d["text"] for d in self.facts["dates_mentioned"][:6]))
        lines.append("")
        lines.append(f"**Proof** (strength: {self.proof_strength() if 'proof' in self.asked or self.proof else 'not checked yet'})")
        for k, (lbl, _) in self.proof_items().items():
            v = self.proof.get(k)
            mark = "have" if v is True else "missing" if v is False else "not asked yet"
            lines.append(f"- [{'x' if v is True else ' '}] {lbl} ({mark})")
        if self.escalations:
            lines.append("")
            lines.append("**Flags:** " + "; ".join(f"{e['code']} ({e['level']})" for e in self.escalations))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {"problem_type": self.problem_type, "language": self.language, "facts": self.facts,
                "proof": self.proof, "missing_slots": self.missing_slots(), "escalations": self.escalations,
                "status": self.status}

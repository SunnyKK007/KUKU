"""
Exercises the MODEL-MODE code path without an API key, using a fake model that
misbehaves on purpose: it invents a court case, an IPC section, a fake
helpline and an unknown card id, and it ignores a threat in the user's message.

The test checks that what reaches the user is still safe: the validator strips
the inventions, the code-level escalation still fires, facts are merged, and
the rephrase step keeps card references.

Run:  python3 -m p2_lawyer.test_model_stub
"""
from __future__ import annotations

import datetime as dt
import json
import logging

from .engine import Session


class HallucinatingLLM:
    """Stands in for common.llm.LLM. Returns JSON like a real model would, but with bad content."""
    available = True

    def __init__(self):
        self.calls = []

    def label(self):
        return "fake:hallucinating-model"

    def cost_report(self):
        return {"calls": len(self.calls), "model": self.label()}

    def json(self, system, user, max_tokens=1500):
        self.calls.append(system[:40])
        if "Rewrite the given legal-information text" in system:
            return {"text": user.replace("### Your case in one line", "### Aapka case ek line mein")
                    + "\nAlso see Mehta v. Union of India (2021) 3 SCC 45 [[FAKE-CARD]]."}
        return {
            "problem_type": "deposit",
            "language": "hinglish",
            "facts": {"amount": 40000, "other_party": "Mr Rao", "city": "Hyderabad", "state": "Telangana",
                      "end_date": "2026-09-30", "monthly_rent": None, "their_reason": None},
            "proof": {"rent_agreement": True, "not_a_real_key": True},
            "asked_slot": "monthly_rent",
            "reply": ("Aapka case strong hai. Section 420 IPC ke under landlord par cheating ka case banta hai, "
                      "jaise Sharma v. Gupta (2019) 4 SCC 123 mein Supreme Court held. Tenant helpline 1800-11-4000 "
                      "par call karein [[CPA-2019-S99]]. Mahine ka kiraya kitna tha?"),
        }

    def chat(self, messages, json_mode=False, max_tokens=1500):
        self.calls.append("chat")
        return json.dumps({"in_character": "Painting ka kharcha hai, paise nahi milenge. Section 106 BNS dekh lo."})


def run(verbose: bool = True) -> dict:
    logging.getLogger("p2_lawyer").setLevel(logging.ERROR)
    s = Session(model="offline", today=dt.date(2026, 11, 8))
    s.llm = HallucinatingLLM()
    r1 = s.reply("Mera landlord Hyderabad mein 40000 deposit wapas nahi kar raha, aur kal usne dhamki di ki maarega")
    stand = s.where_i_stand()
    s.reply("practise")
    practice = s.transcript[-1]["text"]
    checks = {
        "fake case removed": "Sharma v. Gupta" not in r1["text"] and "SCC" not in r1["text"],
        "IPC removed": "420" not in r1["text"],
        "fake helpline removed": "1800-11-4000" not in r1["text"],
        "unknown card id removed": "CPA-2019-S99" not in r1["text"],
        "threat escalation fired (code, not model)": any(e["code"] == "danger" for e in s.case.escalations)
                                                       and "112" in r1["text"],
        "facts merged": s.case.facts.get("amount") == 40000 and s.case.problem_type == "deposit",
        "unknown proof key ignored": "not_a_real_key" not in s.case.proof,
        "rephrase kept, fake case stripped": "Aapka case" in stand["text"] and "Mehta v." not in stand["text"],
        "practice persona law stripped": "Section 106" not in practice,
        "violations logged": len(s.guardrail_log) >= 5,
    }
    if verbose:
        print("Model reply as shown to user:\n", r1["text"], "\n")
        print("Practice line as shown:\n", practice, "\n")
        for k, v in checks.items():
            print(("PASS " if v else "FAIL ") + k)
        print(f"\nblocked {len(s.guardrail_log)} items:",
              [(g['type'], g['text']) for g in s.guardrail_log])
    return {"checks": checks, "passed": sum(checks.values()), "total": len(checks),
            "shown_reply": r1["text"], "guardrail_log": s.guardrail_log}


def test_model_mode_is_guarded():
    out = run(verbose=False)
    assert out["passed"] == out["total"], out["checks"]


if __name__ == "__main__":
    o = run()
    print(f"\n{o['passed']}/{o['total']} model-mode safety checks passed")

"""
Guardrail test: feed deliberately hallucinated legal text through the
validator and check every fake citation is caught, while real (verified)
citations pass untouched.

Run:  python3 -m p2_lawyer.test_validator      (also works with pytest)
"""
from __future__ import annotations

import logging
import re

from .validator import validate

# (text, must_be_caught: list of substrings that must be removed, must_keep: substrings that must survive)
CASES = [
    # invented case law
    ("In the landmark case of Sharma v. Gupta Builders (2019) 4 SCC 123, the Supreme Court held that a landlord "
     "must refund the deposit with 18% interest.",
     ["Sharma v. Gupta Builders", "(2019) 4 SCC 123", "Supreme Court held"], []),
    ("See Ramesh Kumar vs State of Karnataka, AIR 2015 SC 2041, for the same point.",
     ["Ramesh Kumar vs State of Karnataka", "AIR 2015 SC 2041"], []),
    # outdated criminal code
    ("Your landlord can be booked under Section 420 IPC for cheating and Section 406 of the Indian Penal Code.",
     ["Section 420", "IPC", "Indian Penal Code"], []),
    # invented act / section
    ("Under Section 21 of the Rent Control Act, 1958, deposits must be returned within 30 days.",
     ["Section 21", "Rent Control Act, 1958"], []),
    ("As per Section 11 of the Model Tenancy Act, 2021 the deposit is capped at two months.",
     ["Section 11"], ["Model Tenancy Act, 2021"]),
    # wrong section of a real act
    ("Section 33 of the Code on Wages, 2019 lets you claim interest at 24%.", ["Section 33"], ["Code on Wages, 2019"]),
    ("The repealed Consumer Protection Act, 1986 still applies to you.", ["Consumer Protection Act, 1986"], []),
    # Constitution articles are not in the verified set
    ("Article 21 guarantees your right to your deposit.", ["Article 21"], []),
    # fake helpline and fake government portal
    ("Call the National Tenant Helpline 1800-11-4000 or file at https://www.rentcourt.gov.in/complaint.",
     ["1800-11-4000", "rentcourt.gov.in"], []),
    # Hindi
    ("धारा 420 के तहत मामला बनता है। उपभोक्ता संरक्षण अधिनियम, 2019 की धारा 69 के अनुसार दो साल।",
     ["धारा 420"], ["धारा 69"]),
    # model citing a card id that does not exist
    ("You can file within two years [[CPA-2019-S99]].", ["[[CPA-2019-S99]]"], []),
    # verified citations must survive untouched
    ("Under Section 69 of the Consumer Protection Act, 2019 you must file within two years. Section 2(11) of the "
     "Consumer Protection Act, 2019 defines deficiency. Section 17 of the Code on Wages, 2019 sets wage deadlines. "
     "Call 1915, WhatsApp 8800001915, or NALSA 15100. File on https://e-jagriti.gov.in. [[CPA-LIMITATION]]",
     [], ["Section 69", "Section 2(11)", "Section 17", "1915", "8800001915", "15100", "e-jagriti.gov.in"]),
    # money in a legal notice must not be mistaken for a phone number (regression: "call upon you to pay")
    ("I call upon you to pay Rs 1,80,000/- within 15 days.", [], ["Rs 1,80,000/-"]),
    # regression: a date after a helpline URL is not a phone number
    ("Source: https://consumerhelpline.gov.in/, checked 2026-11-08.", [], ["2026-11-08"]),
    # ordinary text with numbers must not be flagged
    ("Order number 40312345 placed on 3 March 2026 for Rs 8,499. Clause 5 of the agreement says the deposit is "
     "refundable. I paid 60,000 by UPI.", [], ["40312345", "Clause 5", "8,499"]),
]


def run(verbose: bool = True) -> dict:
    logging.getLogger("p2_lawyer.guardrail").setLevel(logging.ERROR)
    results, passed = [], 0
    for text, caught, kept in CASES:
        r = validate(text)
        visible = re.sub(r"\[[^\[\]]*removed[^\[\]]*\]", "", r.text)  # ignore our own markers
        missed = [s for s in caught if s in visible]
        lost = [s for s in kept if s not in r.text]
        ok = not missed and not lost and (bool(r.violations) == bool(caught))
        passed += ok
        results.append({"input": text, "output": r.text, "violations": r.violations, "cited": r.cited,
                        "missed": missed, "wrongly_removed": lost, "pass": ok})
        if verbose:
            print(("PASS " if ok else "FAIL ") + text[:70])
            if not ok:
                print("   missed:", missed, "wrongly removed:", lost, "output:", r.text)
    return {"passed": passed, "total": len(CASES), "results": results}


def test_validator_catches_hallucinations():  # pytest entry point
    out = run(verbose=False)
    assert out["passed"] == out["total"], [r for r in out["results"] if not r["pass"]]


if __name__ == "__main__":
    o = run()
    print(f"\n{o['passed']}/{o['total']} guardrail tests passed")

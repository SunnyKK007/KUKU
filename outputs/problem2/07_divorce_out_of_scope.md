# 07_divorce_out_of_scope

**Persona:** Anita, 35. Wants a divorce; husband took jewellery and money.

**Model:** offline (rules only)  |  **Run date (pinned):** 2026-11-08  |  Raw output, not edited.

> Legal information, not legal advice. I can be wrong. For court cases or anything serious, speak to a lawyer. Free legal aid: 15100.

## Conversation

**User:**

I want to divorce my husband. He took my jewellery and ₹2 lakh from my account. What should I do?

**Assistant (referral):**

I'm sorry, this is outside what I can safely help with. I only cover deposits, refunds and unpaid salary.

**Important:** Family matters like divorce, dowry or custody are outside what I can help with. Please speak to a lawyer or your District Legal Services Authority.

Free legal aid: call NALSA's toll-free helpline 15100, or visit your District Legal Services Authority. Women, children, SC/ST members, persons with disability, industrial workmen and people below the state's income limit are among those entitled to a free lawyer.

**User:**

[Sources]

**Assistant (sources):**

These are the only legal sources I use. Each was checked against an official source:

- **You may be entitled to a free lawyer** (Section 12 of the Legal Services Authorities Act, 1987). Source: [NALSA: Legal Services Authorities Act, 1987 (official PDF)](https://cdnbbsr.s3waas.gov.in/s32e45f93088c7db59767efef516b306aa/uploads/2025/04/202504081796627129.pdf), checked 2026-11-08, confidence: high.
- **Free legal aid helpline: 15100**. Source: [nalsa.gov.in](https://nalsa.gov.in/), checked 2026-11-08, confidence: high.

## Case file (as built)

```json
{
  "problem_type": null,
  "language": "en",
  "facts": {},
  "proof": {},
  "missing_slots": [],
  "escalations": [
    {
      "code": "family",
      "level": "refer",
      "trigger": "divorce",
      "message": "Family matters like divorce, dowry or custody are outside what I can help with. Please speak to a lawyer or your District Legal Services Authority."
    }
  ],
  "status": "out_of_scope"
}
```

## Documents generated

_None (out of scope or problem not identified)._

## Sources used in 'Where I stand'

_n/a_

## Guardrail log (citations blocked before reaching the user)

- none

## Automatic checks

- PASS: problem_type
- PASS: escalation
- PASS: no_unverified_citations_shown
- PASS: notice_generated
- PASS: legal_aid_offered

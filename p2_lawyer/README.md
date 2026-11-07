# Problem 2: Nyay Saathi (get your money back)

An AI legal-information assistant for three everyday money problems in India:
a security deposit the landlord won't return, a consumer refund that never came,
and unpaid salary. It builds a case file from a messy story, explains where the
person stands using only verified law, drafts the notice, and lets them practise
against the other side. Anything outside scope is sent to a lawyer or free legal aid.

All commands run from the **repo root** (`kuku-solutions/`), so `common/` imports work.

## 1. Run with no key (offline, rules only, free)

```bash
python3 -m p2_lawyer.run_tests --model offline   # 15 personas -> outputs/p2/*.md + summary.json
python3 -m p2_lawyer.test_validator              # guardrail test: fake laws, cases, helplines
python3 -m p2_lawyer.test_model_stub             # model-mode code path with a deliberately lying fake model
streamlit run p2_lawyer/app.py                   # the chat app
```

## 2. Run with a model (better language handling)

Copy `.env.example` to `.env` at the repo root and fill one free key, e.g. `GROQ_API_KEY=...`
or `GEMINI_API_KEY=...`. Then:

```bash
python3 -m p2_lawyer.run_tests --model groq:llama-3.3-70b-versatile --out outputs/p2_groq
python3 -m p2_lawyer.run_tests --model gemini:gemini-2.5-flash --out outputs/p2_gemini
streamlit run p2_lawyer/app.py        # pick the model in the sidebar
```

Swapping the model is one string (`common/llm.py`). Any OpenAI-compatible endpoint works via
`custom:<model>` with `LLM_BASE_URL` and `LLM_API_KEY`. Responses are cached in `.llm_cache/`,
so re-runs are free and repeatable. If the model fails mid-conversation, that turn falls back to rules.

Optional voice: set `SARVAM_API_KEY` (Sarvam AI speech-to-text, model `saaras:v4`, auto language
detection). Without it the app shows a message and you type instead.

## 3. Deploy on Streamlit Community Cloud (free)

1. Push the repo to GitHub (the `.gitignore` already excludes `.env`).
2. On share.streamlit.io: **New app** -> pick the repo -> main file path `p2_lawyer/app.py`.
   Streamlit installs `p2_lawyer/requirements.txt` (it looks next to the entry point first).
3. **Advanced settings -> Secrets**: add e.g. `GROQ_API_KEY = "..."` (and `SARVAM_API_KEY` for voice).
   The app copies secrets into environment variables. With no secrets it runs offline.

## Files

| File | What it is |
|---|---|
| `law_cards.json` | The only law the assistant may state: 21 cards, each checked against an official source, with link and date |
| `validator.py` | Guardrail run on every outgoing message: removes unverified acts/sections, case law, IPC/CrPC, unknown helplines and links |
| `escalation.py` | Code rules for "see a real lawyer": threats, police, family, property, court case running, minors, large amounts, time limits |
| `intake.py` | Classifier (English, Hindi, Hinglish keywords), language detection, amount/date/place/proof extraction, questions in 3 languages |
| `engine.py` | The conversation engine shared by app and tests; offline and model mode |
| `advice.py` | "Where you stand", assembled by rules from the case file and cards |
| `documents.py` | Fixed templates: legal notice (3 types), consumer complaint summary, wage claim summary |
| `practice.py` | Role-play objections with a coach |
| `voice.py` | Sarvam speech-to-text (optional) |
| `app.py` | Streamlit UI |
| `test_cases.json`, `run_tests.py` | 15 personas and the runner with automatic checks |

Legal information, not legal advice. Free legal aid in India: NALSA helpline 15100.

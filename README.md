# Kuku AI Generalist assignment

Kuku makes AI-generated microdramas, short vertical series with 1 to 2 minute episodes. Its take-home assignment offers three problems and asks for one submission. I submitted Problem 3, a continuity checker, and built the other two on the same code:

| Problem | Folder | What it does |
|---|---|---|
| 1. Find the promos | `problem1_promo_finder/` | Reads timestamped screenplays and returns ranked 20-60 second promos with segments, hook, cliffhanger and a reason |
| 2. AI lawyer | `problem2_ai_lawyer/` | Helps a person in India recover a deposit, refund or unpaid salary, and cannot cite law that isn't on a verified list |
| 3. Continuity checker | `problem3_continuity_checker/` | Finds names, titles, voice labels and props that drift between episodes of an AI-generated series |

Kuku's input pack (the brief and 50 episode scripts of one show) is confidential, so it is not in this repo. Neither are the outputs for Problems 1 and 3, which quote the scripts.

## Contents
1. [Setup](#setup)
2. [Running the tools](#running-the-tools)
3. [Shared code](#shared-code)
4. [Problem 1: promo finder](#problem-1-promo-finder)
5. [Problem 2: AI lawyer](#problem-2-ai-lawyer-nyay-saathi)
6. [Problem 3: continuity checker](#problem-3-continuity-checker)
7. [Limits](#limits)
8. [Troubleshooting](#troubleshooting)

## Setup
You need Python 3.11 or newer. Google Chrome is only used to rebuild the PDFs.

```bash
cd ~/Downloads/KUKU/2_Code
pip install -r requirements.txt
```

Run every command from `2_Code/`. Each tool works with no API key, in an offline mode that uses rules only, costs nothing and gives the same answer every time. Adding a key lets a model handle what rules can't: language, story understanding, and judging a clip as a stranger would.

To add a key, create a file named `.env` in `2_Code/` (Finder hides it; press Cmd+Shift+. to see it) with one line:

```
GEMINI_API_KEY=your_key_here
```

`GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `OPENROUTER_API_KEY` work the same way. For any other OpenAI-compatible endpoint, set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`. `SARVAM_API_KEY` turns on voice input in Problem 2. Free keys are available from Groq (console.groq.com) and Gemini (aistudio.google.com). Check a key with `python3 check_key.py`.

The model is chosen with one flag:

```bash
--model groq:llama-3.3-70b-versatile
--model gemini:gemini-3.5-flash
--model "gemini:gemini-3.5-flash,gemini-3.1-flash-lite"   # moves to the next model when one runs out of daily quota
--model anthropic:claude-sonnet-5-5
--model ollama:llama3.1:8b
--model custom:<model-name>      # any OpenAI-compatible endpoint: set LLM_BASE_URL and LLM_API_KEY in .env
```

Without the flag, a tool uses the first key it finds in `.env`, or offline mode if there is none.

## Running the tools
Problem 1, about 25 seconds for 50 episodes:

```bash
python3 -m problem1_promo_finder.find_promos --input "../1_Assignment/episodes" --model offline --out outputs/problem1_check
python3 -m problem1_promo_finder.evaluate --run outputs/problem1_check/promos.json --input "../1_Assignment/episodes"
```

Then open `outputs/problem1_check/review.html` in a browser.

Problem 2 (details in `problem2_ai_lawyer/README.md`):

```bash
python3 -m problem2_ai_lawyer.run_tests --model offline
python3 -m problem2_ai_lawyer.test_validator
python3 -m problem2_ai_lawyer.test_model_stub
streamlit run problem2_ai_lawyer/app.py
```

Problem 3, under a second for the rules:

```bash
python3 -m problem3_continuity_checker.check_continuity --input "../1_Assignment/episodes" --model offline --out outputs/problem3_check
python3 -m problem3_continuity_checker.inject_test --input "../1_Assignment/episodes" --trials 10 --seed-base 7000
```

Then open `outputs/problem3_check/continuity_report.md`.

The web apps:

```bash
streamlit run problem1_promo_finder/app.py
streamlit run problem3_continuity_checker/app.py
streamlit run problem2_ai_lawyer/app.py
```

The Problem 1 and 3 apps take uploaded `.txt` files or a `.zip`, or, when running locally, a folder path.

To run on a new show, point `--input` at any folder of episode `.txt` files in the same format:

```bash
python3 -m problem1_promo_finder.find_promos --input "/path/to/new show" --model offline --out outputs/new_p1
python3 -m problem3_continuity_checker.check_continuity --input "/path/to/new show" --model offline --out outputs/new_p3
```

I tested this on a 10-episode subset and in a clean copy of the project, and the results matched the saved runs exactly.

## Shared code
`common/screenplay.py` parses the screenplays. Each episode file has a header, then scenes with start and end times, and each scene holds camera, action, sound and dialogue blocks with their own timestamps. Dialogue also carries a speaker and a delivery cue such as "Cold, Commanding". The parser turns a file into a list of timed beats and copes with two quirks in the pack: episode 6 uses upper-case scene headers while the other 49 use mixed case, and some speakers carry `(O.S.)` or `(Off-screen)` tags.

`common/llm.py` is the one model adapter every tool uses. Every provider it supports speaks the OpenAI chat format, so changing models is one flag. It caches responses, so a rerun is free and repeatable. It retries when a free tier rate-limits it, and switches to the next model in the list when one runs out of daily quota. It also tolerates JSON wrapped in code fences, and counts tokens so each run can report its cost.

The design is the same in all three tools. Code parses, counts, matches and validates, because that is free, instant and repeatable. The model is used only for judgment, which costs money, can be wrong and can be rate-limited. A person makes the final call. So every tool works fully without a model.

Each tool's folder holds a main script (`find_promos.py`, `run_tests.py`, `check_continuity.py`), the rules, the model step and a Streamlit `app.py`. Raw outputs go to `outputs/`, and files named `manual_audit.md` hold my review of those outputs, kept apart so the raw files stay unedited.

## Problem 1: promo finder
Kuku's editors watch every episode to choose promo moments. A promo is a 20 to 60 second clip for Instagram, TikTok or YouTube that opens on a hook in the first 3 seconds, ends on a cliffhanger, and makes sense to someone who has never seen the show. The brief asks for the best promos across the 50 episodes, with episode and timestamps for every segment, the hook, the cliffhanger and one line on why it works, then a ranking and a note on where the tool picks badly.

| Step | Done by | What happens |
|---|---|---|
| Parse | Code | Screenplay becomes timed beats |
| Generate | Code | Lists every clip of 20 to 60 seconds that starts on a shot change and never cuts a spoken line in half, about 50,000 for this show |
| Score | Rules | The hook is the strongest beat in the first 3 seconds. The cliffhanger is an unresolved last 4 seconds, with a bonus for the writers' own episode ending and a penalty for calm endings. Clear relationships help standalone clarity; references to earlier events and crowded scenes hurt it |
| Shortlist | Code | Keeps the best non-overlapping clips per episode, plus stitched cold opens that flash the episode's most shocking 3 to 8 seconds before a build to a cliffhanger, a common pattern in apps like ReelShort |
| Judge | Model, optional | Re-scores the top 40 clips seeing only the clip, which tests "makes sense on its own" directly |
| Rank | Code | Final score, a small bonus for early episodes, then at most one promo per episode, three per five-episode stretch, and no trope over a third of the slate. Second-best clips are kept as alternates |
| Review | Human | `review.html` and the Streamlit app show each pick with its script for an editor to approve or reject |

The full run produced 25 promos across 25 episodes, 10 of them stitched cold opens, covering all 7 story tropes. Every one is 20 to 60 seconds, stays inside its episode, cuts no spoken line and has a sound or action beat in the first 3 seconds, and all 676 script lines quoted in them match the episode files at their timestamps. For recall I wrote 16 must-catch moments from the episode loglines before tuning (`gold_moments.json`). Nine appear in the top 25, and 10 when the editor also sees the alternates. The top 10 catches only 4, because the slate rules spread picks across the show. My audit of the top 12 rated 3 strong, 6 good, 1 mixed, 1 weak and 1 duplicate of another pick. Reading the first version's results exposed bugs: a hand-in-hand walk into sunlight counted as a cliffhanger, and "strikes flint over kindling" counted as violence. That version is kept in `outputs/problem1_first_version/`.

The picks I would post first:
1. E13, 00:45.80 to 01:20.50. Her husband screams at her to stop as she crawls barehanded into thorns to save him.
2. E12, 00:20.80 to 01:09.50. It ends on a villain's whispered ultimatum that her husband will hang. The tool ranked it only #12.
3. E32, 01:59.50 to 02:34.38. A red-hot iron stops millimetres from her eye.
4. E3 cold open, 01:24.00 to 01:28.10 then 00:25.80 to 01:06.00. A mystery man drops a guard, then the bride is dragged from the altar.
5. E11, 00:58.00 to 01:39.20. She begs officers not to destroy her late mother's medicines during a raid.

It misses quiet lines that devastate only in context, such as a calm line at the altar that reveals the betrayal. It can pick the same moment twice, since episodes replay the previous cliffhanger (E31 and E32 both end on the hot iron). It scores shots from their written descriptions and can't see the generated video, and a cold open can spoil the ending by showing a rescue first. The word lists suit revenge romance, so a comedy or thriller would need new lists or the model judge. The model judge has not been run yet.

| Mode | Cost per show | At 250 shows a month |
|---|---|---|
| Rules only | $0, about 25 seconds | $0 |
| Llama 3.3 70B, paid | about $0.04 | about $10 |
| Frontier model at $3 and $15 per million tokens | about $0.27 | about $70 |

## Problem 2: AI lawyer (Nyay Saathi)
Most people in India never get legal help for everyday money problems, because a lawyer costs more than the amount at stake. The brief asks for a conversational AI, by text or voice and in the person's language, that helps them act, is honest about what it doesn't know, says when someone needs a lawyer, and doesn't invent laws or cases.

It covers three problems in depth: a security deposit, a consumer refund and unpaid salary. Divorce, police matters, property and running court cases go to a lawyer or to free legal aid (NALSA helpline 15100).

| Step | Done by | What happens |
|---|---|---|
| Intake | Rules, plus model if available | Classifies the problem from English, Hindi and Hinglish words, extracts amounts, dates, place and proof, and asks for missing facts one at a time |
| Escalation | Code only | Runs on every message, looking for threats (it shows 112), police, family matters, a running court case, minors, large amounts, and time limits close or passed. A model can't switch it off |
| Where I stand | Rules, plus model to rephrase | Built from a closed set of 21 verified law cards: proof strength, options step by step, time limits, and what it isn't sure about |
| Documents | Templates | A legal notice per problem type, and a consumer complaint summary for e-Jagriti or a wage claim summary. Missing facts stay as `[PLACEHOLDER]`; nothing here is written by AI |
| Practise | Script, plus model if available | Plays the landlord, support agent or HR with the four objections people really hear, and coaches each reply |
| Guardrail | Code only | Checks every outgoing message |

The model never writes law. Each card has a plain summary, the exact section, an official source link and the date it was checked, and the model sees only the relevant cards and must cite them as `[[CARD-ID]]`. A validator scans every message, from a template or a model, and removes any act, section, rule or article not on a card, case names and citations, outdated IPC and CrPC references (replaced by the BNS in 2024), helpline numbers and links not on the verified list, and unknown card ids. Every removal is logged and shown, and requests for case law are refused with a reason.

The card sources are official: the Consumer Protection Act 2019 gazette, PIB releases, India Code, NALSA and consumerhelpline.gov.in. A few items are marked medium confidence, such as the Model Tenancy Act two-month deposit cap, which I confirmed only from an index of the official PDF. Anything I couldn't verify has no card: the civil time limit to sue for a deposit, state rent Acts, legal-aid income limits, and any case law.

I wrote 15 test personas (`test_cases.json`), including Hinglish, Hindi and Tamil messages, a case-law request, a divorce question, a threatened tenant, a large salary claim, no proof at all, a vague one-liner, a Model Tenancy Act state and a running court case. Each produces an unedited transcript in `outputs/problem2/`.

| Check | Result |
|---|---|
| Conversation cases passing every check | 14 of 15 |
| Individual checks passing | 106 of 108 |
| Hallucination samples caught (fake sections, cases, IPC, helplines) | 15 of 15, with real citations kept |
| Fake model that invents law, safety checks | 10 of 10 |

The tests caught bugs that I fixed. The validator read "pay Rs 1,80,000" as a phone number and cut it from the notice. A short answer flipped a Hinglish chat back to English, and a cancellation date was used as the order date. For a gym refund, the notice demanded the ₹12,000 paid instead of the ₹8,000 owed.

Offline mode can't read Tamil script; it says so and offers a menu. Offline answers for "where I stand" and the notices come out in English even when the questions were in Hindi or Hinglish. The validator checks citations, not plain-language claims, so "he can be charged with cheating" with no section number gets through. Model mode has not been run with a real model.

In model mode a conversation uses about 12,900 input and 2,600 output tokens, measured from the prompts the engine builds. That is about $3.50 per 1,000 conversations on gpt-4o-mini, $9.60 on Llama 3.3 70B and $10.30 on Gemini 2.5 Flash. Offline mode and the notice templates cost nothing. The app has a microphone input that transcribes Indian languages through Sarvam AI when `SARVAM_API_KEY` is set; without it, the app says so and you type instead.

## Problem 3: continuity checker
Problem 3 asks you to find a real problem in making or promoting AI microdramas, show it is real, and build the smallest thing that helps.

I found mine while reading the 50 episodes, because I kept losing track of names. The hero's surname changes three times: Ashwin (E39), Ashburn (E42 to 43) and Ashburton (E45 to 46), all spoken aloud. His estate and duchy appear under at least 9 spellings, sometimes two in one episode. A villain speaks 53 lines across ten episodes as "BLOND NOBLEMAN" while the camera directions call him Rupert, the lead is labelled "JULIANA" 352 times and "LADY JULIANA" 110 times, and a typo of a character's name reaches spoken dialogue. Viewers notice this kind of thing: public app reviews complain about wrong character names, faces and pronunciation that shift between scenes, and misspelt subtitles.

The problem belongs to the script editor between AI script generation and video generation. In an AI pipeline the script feeds everything after it. A speaker label can pick the voice, a name in an action line goes into the video prompt, and a name in dialogue becomes a subtitle and then a dub in every language. An error is cheapest to fix in the script, before any of that happens.

| Check | Done by | Example finding |
|---|---|---|
| Name spelling drift | Code, fuzzy matching of proper nouns | 8 spellings of the estate |
| Surname and title drift | Code | Duke of Ashburn vs Duke of Ashburton |
| Speaker label drift and typos | Code | JULIANA vs LADY JULIANA |
| Unnamed labels | Code: which name the camera line shows when a generic label speaks, compared with how often that name appears overall | BLOND NOBLEMAN is probably Rupert |
| Prop name drift | Code | Her mother's book is called a ledger, a herbarium, a journal and a grimoire |
| Format lint | Code | A continuity note pointing at the wrong episode, or episode 6's header style |
| Story-level contradictions | Model | Bandages vanish from her injured hands (E22-24); her wound moves from torso to shoulder (E25) |

Each issue has a severity (high means it is spoken aloud; medium means it reaches video prompts or voice mapping), evidence with the episode, line number and quoted text, and a suggested fix. The model must quote the episode for every issue, and an issue whose quote isn't in the script is dropped as a possible hallucination. The tool also builds a show bible listing every speaker, their line count and episode range, and every location. Outputs are `continuity_report.md`, `issues.json`, `issues.csv`, `show_bible.json`, the error-injection results and my audit.

On the real scripts the rules flag 15 issues in under a second. Checked by hand, 13 are clearly real, 1 is real but grouped oddly, and 1 needs a human call: a shortened name in E22 that may be a deliberate alias while she is disguised. Every evidence line points at the quoted text in the script. To measure recall, I planted errors at random in copies of the scripts (name typos in dialogue, misspelt labels, labels that gain a title, a wrong episode in a continuity note) and counted how many the tool caught:

| Run | Planted | Caught |
|---|---|---|
| First version | 23 | 17 (74%) |
| After fixing two causes, same seeds | 23 | 23 |
| Held-out run, 10 new trials | 45 | 44 (98%), no false alarms |

I ran the model pass on all 50 episodes with free Gemini 3 Flash models, switching models as each one's daily quota of about 20 requests ran out (`outputs/problem3_with_model/`). It dropped 14 findings whose quotes weren't in the script and kept 58, with one episode timing out. About half are real and are things the rules can't see, such as vanishing bandages, a wound that moves, chains and prison clothes that change, and "Aristocratic Woman" in E7 being Clarissa. The rest come from invented earlier facts or normal changes, such as a new gown on a new day, so model findings reach the editor as "check" rather than "fix".

The rules can't tell that two different descriptions are one person, so they miss that ALEXANDER'S MOTHER and DOWAGER DUCHESS are the same, that LADY IN GOLD GOWN is Clarissa, and that NOBLEWOMAN is Catherine. The planted errors are error types I chose, so 98% is an upper bound. The tool can't judge intent either: a deliberate alias looks like an error, so a person decides.

| Mode | Per show (50 episodes) | At 250 shows a month |
|---|---|---|
| Rules only | $0, under 1 second | $0 |
| Model pass, Llama 3.3 70B list price | about $0.10 (measured: about 153k input and 12k output tokens) | about $25 |
| Model pass, frontier model at $3/$15 per million | about $0.64 | about $160 |

## Limits
- Only Problem 3's model pass has run with a real model. The other model paths were tested against a fake local server and, for Problem 2, a fake model that tries to invent law, so they work mechanically but their quality is unmeasured.
- I chose the 16 Problem 1 reference moments from the episode loglines with AI help. A real editor's picks would be a better yardstick.
- The `manual_audit.md` verdicts were made with AI help and are my judgment calls.
- Problem 2 gives legal information, not legal advice. The law cards were checked against official sources in November 2026, but law changes, and a few items are marked medium confidence.
- Model costs are measured token counts multiplied by public list prices, not real bills.

## Troubleshooting
| Problem | Fix |
|---|---|
| `ModuleNotFoundError: common` | Run commands from `2_Code/`, using `python3 -m ...` as shown. |
| `GROQ_API_KEY is not set` | Add the key to `.env`, or add `--model offline`. |
| Model run hits a rate limit | The adapter retries and, with a model list, moves to the next model. Cached answers are reused on a rerun. |
| Model output is not valid JSON | The parser handles code fences and extra text. If it still fails, the tool skips that clip or episode and keeps going. |
| PDF rebuild fails | It needs Google Chrome at `/Applications/Google Chrome.app`. Edit the path in `docs/build_pdfs.py` if yours differs. |
| A PDF is over two pages | Shorten the Markdown; the brief's limit is two pages. The builder prints the page count. |
| Streamlit says port in use | Add `--server.port 8510` to the command. |
| Different results on a new show | Expected. The word lists are tuned for revenge romance. Check `outputs/.../evaluation.md` and the manual audit. |

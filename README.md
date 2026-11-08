# Kuku AI Generalist Assignment: three working solutions

This folder is a complete attempt at Kuku's "AI Generalist" take-home assignment. Kuku makes AI-generated
microdramas (short vertical series with 1 to 2 minute episodes). The brief offers three problems and asks for
**one** submission. I built all three so you can choose, and they share one engine.

**Contents**
1. [The assignment in one minute](#1-the-assignment-in-one-minute)
2. [What is in this folder](#2-what-is-in-this-folder)
3. [Setup and how to run everything](#3-setup-and-how-to-run-everything)
4. [Shared building blocks](#4-shared-building-blocks)
5. [Problem 1: Promo finder](#5-problem-1-promo-finder)
6. [Problem 2: AI lawyer (Nyay Saathi)](#6-problem-2-ai-lawyer-nyay-saathi)
7. [Problem 3: Continuity checker](#7-problem-3-continuity-checker)
8. [What gets submitted](#8-what-gets-submitted)
9. [What you have to do now](#9-what-you-have-to-do-now)
10. [Honest limits of this work](#10-honest-limits-of-this-work)
11. [Troubleshooting](#11-troubleshooting)

---

## 1. The assignment in one minute

Source: `../4_Kuku_input_pack/Assignment_brief.pdf`.

- **Pick one problem**, spend about 2 to 3 hours, submit within 48 hours.
- **Make assumptions instead of asking.** Write them down.
- **Use any AI tool, and say which ones**, plus one place they got it wrong.
- **Free tiers only.** A paid API earns no extra credit.
- **Build something you can run again.** If shortlisted, you will run it on a **new input** in the interview. Kuku may
  plug in stronger models, so the model must be easy to swap.
- **Submit:** a solution doc (PDF, at most 2 pages), a prototype link, a folder of unedited raw outputs, and
  optionally a video of up to 3 minutes.
- **They score:** problem choice and framing, approach and scale (what is AI, what is code, where a human stays in the
  loop, cost at volume), quality checking with honest failures, the prototype, and short clear communication.
- **Honesty beats polish.** "A simple, honest submission that works and is clear about its limits will beat a
  polished one that overpromises."

The three problems:

| # | Problem | Input |
|---|---|---|
| 1 | Find the promos: read a microdrama screenplay and pick 20 to 60 second promo clips that open on a hook and end on a cliffhanger | The 50-episode input pack |
| 2 | Build an AI lawyer an ordinary person in India can talk to | None, you write test cases |
| 3 | Find your own problem in making or promoting AI microdramas and build the smallest thing that helps | Optional |

---

## 2. What is in this folder

```
KUKU/
├── 1_SUBMIT_THESE_FILES/      WHAT YOU UPLOAD: Project_Documentation + Output_Documentation (Problem 3)
├── 3_CODE/                    everything built, this folder (this README lives here)
└── 4_Kuku_input_pack/         Kuku's brief and the 50 episodes. CONFIDENTIAL, never upload
    ├── Assignment_brief.pdf
    └── episodes/
```

Inside `3_CODE/` (the python folders keep their names because the code imports them):

```
3_CODE/
├── README.md                  this file
├── check_key.py               tests your API key
├── make_submission.sh         rebuilds the PDFs and refills 1_SUBMIT_THESE_FILES
├── requirements.txt, .gitignore
├── .env                       YOUR API KEY GOES HERE
├── common/                    shared code
│   ├── screenplay.py          parses the timestamped screenplays
│   └── llm.py                 one swappable model adapter
├── p1_promos/                 PROBLEM 1 code: promo finder
├── p2_lawyer/                 PROBLEM 2 code: AI lawyer (has its own README)
├── p3_continuity/             PROBLEM 3 code: continuity checker
├── docs/                      solution docs (.md and .pdf) and video scripts
└── outputs/                   raw outputs from real runs
    ├── p1/, p1_baseline/      Problem 1 run, plus the first version
    ├── p2/                    15 test conversations and results
    └── p3/                    Problem 3 results and tests
```

Inside each problem folder:
- **p1_promos:** `find_promos.py` (run this), `signals.py` (the rules), `judge.py` (model step), `report.py`, `evaluate.py`, `app.py`.
- **p2_lawyer:** `engine.py` (conversation), `law_cards.json` and `validator.py` (verified law and the guardrail), `run_tests.py`, `app.py`.
- **p3_continuity:** `check_continuity.py` (run this), `checks.py` (the rules), `llm_check.py` (model step), `inject_test.py`, `app.py`.

Files named `manual_audit.md` are reviews of the raw outputs. They are kept separate from the raw output on purpose,
so the raw files stay unedited.

---

## 3. Setup and how to run everything

**Requirements:** Python 3.11 or newer. Google Chrome is only needed to rebuild the PDFs.

```bash
cd ~/Downloads/KUKU/3_CODE
pip install -r requirements.txt
```

All commands below run from `3_CODE/`. No key is needed to start.

### Two modes

| Mode | How | Cost | What you get |
|---|---|---|---|
| **Offline** | `--model offline` | Free, no internet | Rules only. Fast and repeatable. All saved results come from this mode. |
| **Model** | Add a free key to `.env`, drop `--model offline` | Free on free tiers | A model adds judgment the rules cannot, such as language, story understanding and a blind "new viewer" check. |

To use a model, create a file named `.env` in `3_CODE/` (it is hidden in Finder; press Cmd+Shift+. to see it) containing one line:

```
GEMINI_API_KEY=your_key_here
```

Use `GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` or `OPENROUTER_API_KEY` for those providers. For any other OpenAI-compatible endpoint, set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`. Optional: `SARVAM_API_KEY` enables voice input in Problem 2.

Free keys: Groq at console.groq.com, or Gemini at aistudio.google.com. Then change the model with one flag:

```bash
--model groq:llama-3.3-70b-versatile
--model gemini:gemini-2.5-flash
--model anthropic:claude-sonnet-5-5
--model ollama:llama3.1:8b
--model custom:<model-name>      # any OpenAI-compatible endpoint: set LLM_BASE_URL and LLM_API_KEY in .env
```

With no `--model` flag, a tool uses the first key it finds in `.env`, and falls back to offline if there is none.

### Run Problem 1

```bash
python3 -m p1_promos.find_promos --input "../4_Kuku_input_pack/episodes" --model offline --out outputs/p1_check
python3 -m p1_promos.evaluate --run outputs/p1_check/promos.json --input "../4_Kuku_input_pack/episodes"
```

Takes about 25 seconds. Then open `outputs/p1_check/review.html` in a browser.

### Run Problem 2

```bash
python3 -m p2_lawyer.run_tests --model offline
python3 -m p2_lawyer.test_validator
python3 -m p2_lawyer.test_model_stub
streamlit run p2_lawyer/app.py
```

More detail is in `p2_lawyer/README.md`.

### Run Problem 3

```bash
python3 -m p3_continuity.check_continuity --input "../4_Kuku_input_pack/episodes" --model offline --out outputs/p3_check
python3 -m p3_continuity.inject_test --input "../4_Kuku_input_pack/episodes" --trials 10 --seed-base 7000
```

Takes under a second for the first command. Open `outputs/p3_check/continuity_report.md`.

### Run the apps

```bash
streamlit run p1_promos/app.py
streamlit run p3_continuity/app.py
streamlit run p2_lawyer/app.py
```

The Problem 1 and 3 apps take uploaded `.txt` files or a `.zip`. When running locally you can instead paste the folder
path into the path box.

### Run on a new show (what the interview will do)

Point `--input` at any folder of episode `.txt` files in the same format:

```bash
python3 -m p1_promos.find_promos --input "/path/to/new show" --model offline --out outputs/new_p1
python3 -m p3_continuity.check_continuity --input "/path/to/new show" --model offline --out outputs/new_p3
```

I tested this on a 10-episode subset, and in a clean copy of the project: the results matched the saved ones exactly.

---

## 4. Shared building blocks

### The screenplay parser: `common/screenplay.py`

Each episode file has a loglines header, then scenes. Every scene has a start and end time, and holds blocks for
**camera**, **action**, **sound effects** and **dialogue**, each with its own timestamps. A line of dialogue also has a
speaker and a delivery cue such as "Cold, Commanding".

The parser turns each file into a list of timed beats. It copes with the quirks in this pack:
- Episode 6 uses upper-case scene headers (`SCENE HEADING:`) while the other 49 use mixed case.
- Some speakers carry `(O.S.)` or `(Off-screen)` tags.

This step is pure code, so it is free, instant and testable.

### The model adapter: `common/llm.py`

One adapter for every tool. Every provider here speaks the OpenAI chat format, so swapping a model is one flag.
It also gives you:
- A **response cache**, so reruns are free and give the same answer.
- **Retry with backoff** when a free tier rate-limits you.
- **Tolerant JSON parsing**, so a model that wraps its answer in code fences still works.
- **Token counting**, so every run can report its cost.
- An **offline** setting, where tools skip the model entirely.

### The design idea behind all three

> Code does what code can do: parse, count, match and validate. The model only does judgment. A human approves.

Rules are free, instant and give the same answer every time. A model adds taste and understanding, but costs money,
can be wrong and can be rate-limited. Every tool therefore works fully without a model, and a person makes the final
call.

---

## 5. Problem 1: Promo finder

### What it is trying to solve

An editor watches every episode by hand to choose promo moments, and Kuku releases new shows every week. A promo is a
20 to 60 second clip posted on Instagram, TikTok or YouTube to pull in new viewers. A good one:
1. opens on a **hook** in the first 3 seconds, such as a slap, a reveal or a shocking line,
2. ends on a **cliffhanger**, an unresolved moment that makes you need the next episode,
3. **makes sense on its own** to someone who has never seen the show.

The task: find the best promos across all 50 episodes, with the episode and start and end timestamps of every segment,
the hook, the cliffhanger and one line on why it works. Then rank them, and say where the tool picks badly.

### How it works

| Step | Done by | What happens |
|---|---|---|
| 1. Parse | Code | Screenplay becomes timed beats. |
| 2. Generate | Code | Lists every clip of 20 to 60 seconds that **starts on a shot change** and **never cuts a spoken line in half**. About 50,000 clips for this show. |
| 3. Score | Rules | **Hook:** the strongest beat in the first 3 seconds (violence, danger, a shocking line, intense delivery). **Cliffhanger:** an unresolved last 4 seconds, with a bonus for the writers' own episode ending and a penalty for calm endings like a hug. **Standalone:** clear relationships help, while references to earlier events and crowded scenes hurt. |
| 4. Shortlist | Code | Keeps the best non-overlapping clips per episode. Also builds **stitched cold opens**: it flashes the episode's most shocking 3 to 8 seconds first, then plays a continuous build to a cliffhanger. This is a common pattern in apps like ReelShort. |
| 5. Judge | Model, optional | A model re-scores the top 40 clips while seeing **only the clip**, like a stranger scrolling. That tests "makes sense on its own" directly. |
| 6. Rank | Code | Final score, a small bonus for early episodes, then slate rules: at most one promo per episode, at most three per five-episode stretch, no story trope more than a third of the slate. The second-best clips are kept as "alternates". |
| 7. Review | Human | `review.html` and the Streamlit app show each pick with its script. The editor approves or rejects and exports the decisions. |

### What it produces (`outputs/p1/`)

| File | What it is |
|---|---|
| `promos.json` | Everything, one record per promo |
| `promos.csv` | Spreadsheet view |
| `promos.md` | Readable report with each clip's script |
| `review.html` | One-file review page with Approve and Reject buttons, usable offline |
| `evaluation.md` | Automatic quality results |
| `manual_audit.md` | My review of the top 12, as a human editor would |

### Results from the full run

- 25 promos across 25 episodes, 10 of them stitched cold opens, covering all 7 story tropes.
- **Hard checks:** all 25 are 20 to 60 seconds, stay inside their episode, cut no spoken line, and have a sound or action beat
  in the first 3 seconds.
- **Quote check:** all 676 script lines quoted in the promos match the episode files at their timestamps.
- **Recall:** I wrote 16 "must-catch" moments from the episode loglines before tuning (`gold_moments.json`). 9 of 16 appear in
  the top 25, and 10 of 16 when the editor also sees each pick's alternates. The top 10 catches only 4, because the slate
  rules deliberately spread picks across the show.
- **Manual audit of the top 12:** 4 strong, 6 good, 1 mixed, 1 weak.
- **Bugs found by reading the results, then fixed:** a hand-in-hand walk into sunlight counted as a cliffhanger, and
  "strikes flint over kindling" counted as violence. The first version is kept in `outputs/p1_baseline/`.

### My top picks to post first

1. **E13, 00:45.80 to 01:20.50.** Her husband screams at her to stop as she crawls barehanded into thorns to save him.
2. **E12, 00:20.80 to 01:09.50.** Ends on a villain's whispered ultimatum that her husband will hang. The tool ranked it only #12.
3. **E32, 01:59.50 to 02:34.38.** A red-hot iron stops millimetres from her eye.
4. **E3 cold open, 01:24.00 to 01:28.10 then 00:25.80 to 01:06.00.** A mystery man drops a guard, then the bride is dragged from the altar.
5. **E11, 00:58.00 to 01:39.20.** She begs officers not to destroy her late mother's medicines during a raid.

### Where it picks badly (also in the doc)

- It misses quiet but devastating lines, such as a calm line at the altar that reveals the betrayal, because they contain no shock words.
- It picks the same moment twice, because episodes replay the previous cliffhanger. E31 and E32 both end on the hot iron.
- It scores a shot from its written description and cannot see the generated video.
- A cold open can spoil the ending, for example by flashing a rescue before the cliffhanger.
- The word lists are tuned for revenge romance. A comedy or thriller needs new lists, or the model judge.
- The model judge is **built but untested**, because no key was available.

### Cost and scale

| Mode | Cost per show | At 250 shows a month |
|---|---|---|
| Rules only | $0, about 25 seconds | $0 |
| Llama 3.3 70B, paid | about $0.04 | about $10 |
| Frontier model at $3 and $15 per million tokens | about $0.27 | about $70 |

---

## 6. Problem 2: AI lawyer (Nyay Saathi)

### What it is trying to solve

Most people in India never get legal help for everyday problems: a deposit the landlord won't return, a refund that
never came, salary that stopped. A lawyer costs more than the money at stake and the process is intimidating. The brief
asks for a conversational AI, by text or voice and in the person's language, that helps them act. It must be honest about
what it doesn't know, say when someone needs a real lawyer, and avoid inventing laws, sections and cases.

### Scope: depth over breadth

It covers exactly three problems: a **security deposit**, a **consumer refund**, and **unpaid salary**. Divorce, police
matters, property and running court cases are routed to a lawyer or to free legal aid (NALSA helpline 15100).

### How it works

| Step | Done by | What happens |
|---|---|---|
| Intake | Rules, plus model if available | Classifies the problem from English, Hindi and Hinglish words. Extracts amounts, dates, place and proof, and asks the missing facts one at a time. |
| Escalation | Code only | Runs on every message: threats (shows 112), police, family matters, a court case already running, minors, large amounts, time limits close or passed. A model cannot switch this off. |
| Where I stand | Rules, plus model to rephrase | Built from a closed set of 21 verified law cards. Covers proof strength, options step by step, time limits and "what I am not sure about". |
| Documents | Templates | A legal notice for each problem type, a consumer complaint summary for e-Jagriti, or a wage claim summary. Missing facts stay as `[PLACEHOLDER]`. Never AI-written. |
| Practise | Script, plus model if available | Plays the landlord, support agent or HR, using the four objections people really hear, and coaches each reply. |
| Guardrail | Code only | Checks every outgoing message. |

### How it avoids inventing law (the main idea)

1. **Law is data, not generation.** Each of the 21 cards has a plain summary, the exact section, an official source link and
   the date it was checked. If I could not verify something, it is not a card.
2. **The model may only cite cards.** It sees the relevant cards and must cite them as `[[CARD-ID]]`.
3. **A validator scans every message**, from templates or a model. It removes any act, section, rule or article that is
   not on a card, plus case names and citations, outdated IPC and CrPC references (replaced by the BNS in 2024),
   helpline numbers and links not on the verified list, and unknown card ids. Every removal is logged and shown.
4. **It refuses to give case law**, and explains why.

Sources behind the cards are official: the Consumer Protection Act 2019 gazette, PIB releases, India Code, NALSA and
consumerhelpline.gov.in. A few items are marked "medium" confidence in the cards, such as the Model Tenancy Act two-month
deposit cap, which was confirmed only from an index of the official PDF. Things I could not verify were left out
instead of guessed: the civil time limit to sue for a deposit, state rent Acts, legal-aid income limits and any case law.

### Test results (`outputs/p2/`)

I wrote 15 test personas (`test_cases.json`). They include Hinglish, Hindi and Tamil messages, someone asking for case
law, a divorce question, a threatened tenant, a large salary claim, no proof at all, a one-line vague message, a Model
Tenancy Act state and a running court case. Each one produces an unedited transcript.

| Check | Result |
|---|---|
| Conversation cases passing every check | **14 of 15** |
| Individual checks passing | **106 of 108** |
| Hallucination samples caught (fake sections, cases, IPC, helplines) | **15 of 15**, with real citations kept |
| Fake model that invents law, safety checks | **10 of 10** |

**Bugs the tests caught, which I fixed:** the validator read "pay Rs 1,80,000" as a phone number and cut it from the notice;
a short answer flipped a Hinglish chat back to English; a cancellation date was used as the order date; and for a gym
refund the notice demanded the ₹12,000 paid instead of the ₹8,000 actually owed.

### Where it fails (also in the doc)

- **Tamil script without a model:** not understood. It says so and offers a menu.
- **Offline replies come out in English** for "where I stand" and notices, even when its questions are in Hindi or Hinglish.
- **The validator checks citations, not claims.** A plain-words claim like "he can be charged with cheating" with no section
  number is not caught.
- **Model mode is untested with a real model.**

### Cost

About 12,700 input and 2,600 output tokens per conversation in model mode, from the prompts the engine really builds.
That is about $3.40 per 1,000 conversations on gpt-4o-mini, $9.50 on Llama 3.3 70B and $10.20 on Gemini 2.5 Flash.
Offline mode costs nothing, and notices cost nothing because they are templates.

### Voice

The app has a microphone input. With a `SARVAM_API_KEY` it transcribes Indian languages through Sarvam AI. Without a key it
shows a clear message and you can type instead.

---

## 7. Problem 3: Continuity checker

### What it is trying to solve

Problem 3 asks you to find your own real problem in making or promoting AI microdramas, show that it is real, and build the
smallest thing that helps.

**The problem I found, in Kuku's own scripts.** While reading the 50 episodes I kept losing track of names, so I counted:
- The hero's surname changes three times: **Ashwin** (E39), **Ashburn** (E42 to 43), **Ashburton** (E45 to 46), all spoken aloud.
- His estate and duchy appear under **at least 9 spellings**, sometimes two in one episode.
- A villain speaks 53 lines as "BLOND NOBLEMAN" for ten episodes, while the shots on screen call him Rupert.
- The lead is labelled "JULIANA" 352 times and "LADY JULIANA" 110 times.
- A typo of a character's name reaches spoken dialogue.

Real viewers notice such things. In public app reviews people complain about "wrong character names", faces and
pronunciation that shift between scenes, and misspellings in subtitles.

**Who has it:** the script editor between AI script generation and video generation. One person, one step, one output.

**Why it matters more than Problems 1 and 2:** in an AI pipeline the script feeds everything after it. A speaker label can pick
the voice, a name in an action line goes into the video prompt, and a name in dialogue becomes a subtitle and then a dub in
every language. One error in the text multiplies into re-renders and wrong voices. Fixing it in the script is the cheapest
point in the pipeline.

### How it works

| Check | Done by | Example finding |
|---|---|---|
| Name spelling drift | Code, fuzzy matching of proper nouns | 8 spellings of the estate |
| Surname and title drift | Code | Duke of Ashburn vs Duke of Ashburton |
| Speaker label drift and typos | Code | JULIANA vs LADY JULIANA |
| Unnamed labels | Code: which name the camera line shows when a generic label speaks, compared with how often that name appears overall | BLOND NOBLEMAN is probably Rupert |
| Prop name drift | Code | Her mother's book is called a ledger, a herbarium, a journal and a grimoire |
| Format lint | Code | A continuity note pointing at the wrong episode, or episode 6's header style |
| Story-level contradictions | Model, optional | One person under two descriptions, an injury that disappears |

Every issue has a **severity**: high means the error is spoken aloud, medium means it reaches video prompts or voice
mapping. It also has **evidence** (episode, line number and quoted text) and a **suggested fix**. If the optional model
pass cannot quote the episode for an issue, that issue is dropped as a possible hallucination. The tool also builds a
**show bible**: every speaker, line count, episode range and every location.

### What it produces (`outputs/p3/`)

| File | What it is |
|---|---|
| `continuity_report.md` | Readable report with all issues and evidence |
| `issues.json`, `issues.csv` | Same data for tools and spreadsheets |
| `show_bible.json` | Characters and locations |
| `injection_test_*.md` | Error-injection test results |
| `manual_audit.md` | My check of every flag, plus errors the rules miss |

### Results

- **15 issues on the real pack in under a second.** Checked by hand, 13 are clearly real, 1 is real but grouped oddly and 1
  needs a human call (a shortened name in E22, which may be a deliberate alias while she is disguised).
- **Line numbers:** every evidence line points at the quoted text in the script.
- **Error-injection test.** I planted known errors at random in copies of the scripts (name typos in dialogue, misspelt
  labels, labels that gain a title, a wrong episode in a continuity note) and measured how many the tool caught.

| Run | Planted | Caught |
|---|---|---|
| First version | 23 | 17 (74%) |
| After fixing two causes, same seeds | 23 | 23 |
| **Held-out run, 10 new trials** | **45** | **44 (98%), zero false alarms** |

### Where it fails (also in the doc)

- It cannot tell that **two different descriptions are one person**. It misses ALEXANDER'S MOTHER and DOWAGER DUCHESS, LADY IN
  GOLD GOWN as Clarissa, and NOBLEWOMAN as Catherine. That needs the model pass.
- The model pass is **built but untested with a real model**.
- The planted errors are my own error types, so 98% is an upper bound on real-world recall.
- It cannot judge intent. A deliberate alias looks like an error, so a person decides.

### Cost

| Mode | Per show (50 episodes) | At 250 shows a month |
|---|---|---|
| Rules only | $0, under 1 second | $0 |
| Model pass, Llama 3.3 70B | about $0.12 | about $30 |
| Model pass, frontier model | about $0.92 | about $230 |

---

## 8. What gets submitted

Problem 3 is submitted, because the brief asks for one problem. Its doc says Problems 1 and 2 were also built.
`make_submission.sh` fills `../1_SUBMIT_THESE_FILES/` with `Project_Documentation/` (the Problem 3 PDF),
`Output_Documentation/` (its raw-output zip) and `Other_problems_NOT_uploaded/` (Problems 1 and 2).

---

## 9. What you have to do now

Work through this in order. Items 1 to 4 are required for any submission.

1. **Read everything you will submit.** The interview asks why you made each decision. Run the tools, open the outputs, and
   open `outputs/p1/manual_audit.md` or `outputs/p3/manual_audit.md`. Disagree where you see it differently, and change the
   doc to say what *you* think.
2. **Get a free model key and run once in model mode.** Every saved number is from offline mode. A model run lets you report
   the model judge honestly. Get a free key from Groq or Gemini, then:
   ```bash
   # put GEMINI_API_KEY=your_key in 3_CODE/.env, then:
   python3 check_key.py
   python3 -m p3_continuity.check_continuity --input "../4_Kuku_input_pack/episodes" --out outputs/p3_model
   python3 -m p1_promos.find_promos --input "../4_Kuku_input_pack/episodes" --out outputs/p1_model
   python3 -m p2_lawyer.run_tests --model groq:llama-3.3-70b-versatile --out outputs/p2_groq
   ```
   Check the new results and update the numbers in the doc if they change. If a model run fails or looks bad, say so in
   the doc. Honest failures help you.
3. **Fill the placeholders in the doc you submit** (`docs/p1_solution.md`, `p2_solution.md` or `p3_solution.md`):
   your name, roll number, branch, prototype link, video link, and the section **"AI tools used and one place they got it wrong"**.
   Each already has real examples from this build. Put them in your own words. Then rebuild the PDF and confirm it is still two pages:
   ```bash
   python3 docs/build_pdfs.py
   ```
4. **Make the links work without leaking Kuku's content.** The brief says the pack is confidential but every link must open for anyone.
   - **Prototype:** a **public** GitHub repo with code only. Before you push, move `outputs/p1` and `outputs/p3` out of the repo,
     because they quote the scripts. Do not add the episode files.
   - **Optionally** deploy an app on Streamlit Community Cloud. Reviewers upload the episodes themselves.
   - **Raw outputs:** a Google Drive folder set to "anyone with the link can view", holding the matching `outputs/` folder.
   - **Problem 2** has no Kuku material, so all of it can be public.
   - Free tiers such as Gemini's may use inputs for training. Groq or an endpoint Kuku provides avoids that.
5. **Record the video** (3 minutes at most, in your own voice). Use `docs/p1_video_script.md`, `p2_video_script.md` or
   `p3_video_script.md` as your outline. Show the tool running, then the output, then the honest failures.
6. **Fill in the form** with your name, roll number, branch, the problem you chose, and the links.
7. **Prepare for the interview.** They will run your tool on a new show, so practice that command. They may plug in a
   stronger model, so know how to change `--model`. Be ready to explain what is code and what is AI, where a human stays in the
   loop, and each failure listed above.

The same steps, with exact commands, are in `../1_SUBMIT_THESE_FILES/SUBMIT_NOW.md`.

---

## 10. Honest limits of this work

- **No real model was used.** This Mac had no API key. All results are from rules-only mode. The model paths were tested only
  against a fake local server and, for Problem 2, a fake model that tries to invent law. They are written and plumbing-tested but unproven
  with a real model.
- **The Problem 1 reference moments are mine.** The 16 must-catch moments were chosen by an AI from the episode loglines, then
  located in the scripts. A real editor's picks would be a better yardstick.
- **The audits are written by an AI.** `manual_audit.md` files hold my verdicts. Please re-check them.
- **Problem 2 is legal information, not legal advice.** The law cards were verified from official sources in November 2026, but
  law changes, and a few items are marked medium confidence. Do not present it as a lawyer.
- **The error-injection test uses my own error types**, so real recall is probably lower.
- **Time and cost figures for model mode are estimates** from measured token counts and public list prices, not real bills.

---

## 11. Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: common` | Run commands from `3_CODE/`, using `python3 -m ...` as shown. |
| `GROQ_API_KEY is not set` | Add the key to `.env`, or add `--model offline`. |
| Model run hits a rate limit | The adapter retries with backoff. Free tiers are slow. Cached answers are reused on a rerun. |
| Model output is not valid JSON | The parser handles code fences and extra text. If it still fails, the tool skips that clip or episode and keeps going. |
| PDF rebuild fails | It needs Google Chrome at `/Applications/Google Chrome.app`. Edit the path in `docs/build_pdfs.py` if yours differs. |
| A PDF is over two pages | Shorten the Markdown, because the brief limit is two pages. The builder prints the page count. |
| Streamlit says port in use | Add `--server.port 8510` to the command. |
| Different results on my new show | Expected. The word lists are tuned for revenge romance. Check `outputs/.../evaluation.md` and the manual audit. |

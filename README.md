# AI tools for microdrama production

Three working prototypes for AI microdrama production. Microdramas are short vertical series with 1 to 2 minute episodes, and a studio such as Kuku can release hundreds of shows a month. Each tool here takes one slow, manual step in that process and turns it into something a person can review in minutes.

| | Problem | Tool | What it does |
|---|---|---|---|
| Submitted | 3. Find your own problem | `problem3_continuity_checker/` | Catches names, titles, voice labels and props that drift between episodes of an AI-generated script, before the script goes to video, voice and subtitles |
| Also built | 1. Find the promos | `problem1_promo_finder/` | Reads a show's screenplays and returns a ranked slate of 20 to 60 second promos, each with exact timestamps, the hook, the cliffhanger and why it works |
| Also built | 2. AI lawyer | `problem2_ai_lawyer/` | A chat assistant that helps people in India recover a deposit, a refund or unpaid salary, and is built so it cannot cite a law that has not been verified |

## Highlights

- The continuity checker finds 15 issues across 50 episodes in under a second, including the hero's surname changing three times and his estate spelled at least nine ways. On 10 fresh rounds of planted errors it caught 44 of 45, with no false alarms.
- An AI model pass reads the series in order and catches story-level slips that rules cannot, such as bandages vanishing from an injured character's hands between episodes. Every model finding must quote the script, and 14 findings that could not were rejected automatically.
- The promo finder scores every possible clip in a 50-episode show (about 50,000 of them) in about 25 seconds and never cuts a line of dialogue in half. All 676 script lines it quotes were checked against the source files.
- The AI lawyer works in English, Hindi and Hinglish, drafts real legal notices from templates, and passes 15 of 15 tests designed to make it invent laws, cases or helpline numbers.
- Every tool runs with no API key at zero cost, and any AI model can be plugged in with one setting, including a model Kuku provides.
- Results are reproducible: rerunning on a clean copy of the repo gives identical output.

## Contents
1. [Quick start](#quick-start)
2. [Choosing an AI model](#choosing-an-ai-model)
3. [How the tools are designed](#how-the-tools-are-designed)
4. [Problem 3: continuity checker](#problem-3-continuity-checker)
5. [Problem 1: promo finder](#problem-1-promo-finder)
6. [Problem 2: AI lawyer](#problem-2-ai-lawyer)
7. [Repository layout](#repository-layout)
8. [Known limitations](#known-limitations)
9. [Troubleshooting](#troubleshooting)

## Quick start

Requirements: Python 3.11 or newer.

```bash
git clone https://github.com/SunnyKK007/KUKU.git
cd KUKU
pip install -r requirements.txt
```

The tools read Kuku's timestamped screenplay format: one `.txt` file per episode. Kuku's input pack is confidential and is not included here; point `--input` at your own copy.

Run the continuity checker:

```bash
python3 -m problem3_continuity_checker.check_continuity --input "/path/to/episodes" --model offline --out outputs/problem3
python3 -m problem3_continuity_checker.inject_test --input "/path/to/episodes" --trials 10 --seed-base 7000
```

Run the promo finder:

```bash
python3 -m problem1_promo_finder.find_promos --input "/path/to/episodes" --model offline --out outputs/problem1
python3 -m problem1_promo_finder.evaluate --run outputs/problem1/promos.json --input "/path/to/episodes"
```

Run the AI lawyer's test suite and chat app:

```bash
python3 -m problem2_ai_lawyer.run_tests --model offline
python3 -m problem2_ai_lawyer.test_validator
python3 -m problem2_ai_lawyer.test_model_stub
streamlit run problem2_ai_lawyer/app.py
```

The quickest way to try the continuity checker is its web app, which includes a short original demo show with planted mistakes, so it works without any other files. Each tool has a web app:

```bash
streamlit run problem3_continuity_checker/app.py
streamlit run problem1_promo_finder/app.py
```

The continuity and promo apps accept uploaded `.txt` files or a `.zip`, and when running locally they also accept a folder path. Running any tool on a new show is the same command with a different `--input` folder.

## Choosing an AI model

Every tool works in offline mode, which uses rules only, costs nothing and gives the same answer every time. Adding a model gives each tool judgment that rules cannot provide: understanding a story, judging a clip as a first-time viewer would, or answering in the user's own language.

In the web apps, choose Full check, pick a provider and a model from the list, and paste your API key into the key box on the page. The key is used only for that browser session and is never saved. For the command line, or to avoid pasting it each time, create a file named `.env` in the repo folder with one key (`.env` is listed in `.gitignore`, so it is never uploaded):

```
GEMINI_API_KEY=your_key_here
```

`GROQ_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY` and `OPENROUTER_API_KEY` work the same way. For any other OpenAI-compatible endpoint, set `LLM_BASE_URL`, `LLM_API_KEY` and `LLM_MODEL`. `SARVAM_API_KEY` adds voice input in Indian languages to the AI lawyer. Free keys are available from Gemini (aistudio.google.com) and Groq (console.groq.com). Check a key with:

```bash
python3 check_key.py
```

Then pick a model with one flag:

```bash
--model gemini:gemini-3.5-flash
--model "gemini:gemini-3.5-flash,gemini-3.1-flash-lite"   # uses the next model when one runs out of daily quota
--model groq:llama-3.3-70b-versatile
--model anthropic:claude-sonnet-5-5
--model ollama:llama3.1:8b
--model custom:<model-name>      # any OpenAI-compatible endpoint: set LLM_BASE_URL and LLM_API_KEY in .env
```

Without the flag, a tool uses the first key it finds in `.env`, or offline mode if there is none.

## How the tools are designed

All three tools follow the same principle: code does everything that can be checked mechanically, the AI model does only what needs judgment, and a person makes the final call.

Code parses, counts, matches and validates, because that is free, instant, repeatable and easy to test. A model adds understanding but costs money, can be wrong and can be rate-limited, so its output is always checked by code before anyone sees it. In the continuity checker, a model finding is discarded if its quote is not in the script. In the AI lawyer, the model is never allowed to write law at all. Each tool ends at a review screen where a person approves, rejects or edits the result.

Two shared modules sit underneath all three tools.

`common/screenplay.py` reads Kuku's screenplay format. Each episode has scenes with start and end times, and each scene holds camera, action, sound and dialogue blocks with their own timestamps. Dialogue also carries a speaker and a delivery cue such as "Cold, Commanding". The parser turns every file into a list of timed beats and handles real-world format variation, such as one episode using upper-case scene headers and speakers tagged as off-screen.

`common/llm.py` is the single connection to AI models. Every supported provider speaks the OpenAI chat format, so changing models is one setting. It caches every response so reruns are free and identical, retries when a service is busy, moves to the next model in a list when one runs out of daily quota, limits each request to 60 seconds so a stuck call never hangs a run, reads JSON even when a model wraps it in extra text, and counts tokens so every run can report its cost.

## Problem 3: continuity checker

### The problem

In an AI microdrama pipeline, the script feeds everything that follows. A speaker label selects the AI voice, a name in an action line goes into the video prompt, and a name in dialogue becomes a subtitle and then a dub in every language. A wrong name in the script therefore spreads into the video, the voice and every translation. Fixing it in the text takes seconds; fixing it after rendering can mean re-generating scenes.

Kuku's own 50-episode input pack shows how common this is. The hero's surname appears as Ashwin, Ashburn and Ashburton in different episodes, all spoken aloud. His estate is spelled at least nine ways, sometimes two ways in one episode. A villain speaks 53 lines over 10 episodes under a generic label while the camera directions use his name, and the lead character is labelled two different ways across 462 lines. Viewers notice: public reviews of microdrama apps complain about wrong character names, faces and pronunciation that shift between scenes, and misspelt subtitles.

The tool is built for the script editor who sits between AI script generation and video generation. It produces one output: a continuity report for a batch of episodes before they are rendered.

### How it works

| Check | Method | Example finding |
|---|---|---|
| Name spelling drift | Fuzzy matching of proper nouns, ignoring ordinary words that also appear in lower case | 8 spellings of the estate in one cluster |
| Surname and title drift | Patterns such as "Alexander X" and "Duke of X" | Duke of Ashburn vs Duke of Ashburton |
| Speaker label drift and typos | One label contained in another, or near-identical labels | JULIANA vs LADY JULIANA |
| Unnamed labels | Which name the camera line shows when a generic label speaks, compared with how often that name appears overall | BLOND NOBLEMAN: camera lines name Rupert in 32 of his 53 lines |
| Prop name drift | One owner's object described with different nouns | Her mother's book is a ledger, herbarium, journal and grimoire |
| Format checks | Continuity notes pointing at the wrong episode, inconsistent headers | One episode uses a different header format |
| Story-level contradictions | AI model reads episodes in order with a running list of established facts | Bandages vanish from her injured hands; a wound moves from torso to shoulder |

Each issue has a severity (high when the error is spoken aloud, medium when it reaches video prompts or voice mapping), the episode, line number and quoted evidence, and a suggested fix. The tool also builds a show bible from the scripts: every speaker with their line count, episode range and typical delivery, and every location. Results come as a readable report, CSV and JSON, and the web app lets an editor mark each issue as fix, intended or not an issue.

### Results on the 50-episode pack

| Measure | Result |
|---|---|
| Issues found by the rules | 15, in under a second |
| Issues confirmed real on manual review | 13 clearly real, 1 real but grouped with another, 1 for a human to decide |
| Planted-error test, held-out (10 new trials) | 44 of 45 caught, 0 false alarms |
| Planted-error test, first version | 17 of 23 caught, which led to two fixes |
| AI model pass | 58 findings kept for review; 14 rejected automatically because their quote was not in the script |

The planted-error test copies the scripts, inserts realistic mistakes at random (misspelt names in dialogue, misspelt speaker labels, labels that gain a title, continuity notes pointing to the wrong episode) and measures how many the tool catches. Running it on seeds the tool was never tuned on keeps the score honest.

The model pass found a different class of error from the rules: physical continuity such as injuries, bandages, chains and costumes, a character described as someone's mother when he is a cousin, and an unnamed "Aristocratic Woman" who is actually a named character. Because model findings vary in accuracy, they reach the editor marked "check", while rule findings are marked "fix".

### Cost at scale

| Mode | Per show (50 episodes) | At 250 shows a month |
|---|---|---|
| Rules only | $0, under 1 second | $0 |
| With model, Llama 3.3 70B list price | about $0.10 (measured about 153k input and 12k output tokens) | about $25 |
| With model, frontier model at $3/$15 per million tokens | about $0.64 | about $160 |

In production the rules would run automatically on every batch of scripts before video generation, with high-severity issues holding the render until an editor signs off. The model pass can run on flagged episodes or once per story arc. Useful measures once a team uses it: errors caught before rendering per 100 episodes, the share of flags editors accept, re-renders avoided, and review minutes per episode.

## Problem 1: promo finder

### The problem

Promos are 20 to 60 second clips posted on Instagram, TikTok and YouTube to bring in new viewers. A good one opens on a hook in the first 3 seconds, ends on a cliffhanger, and makes sense to someone who has never seen the show. Today an editor watches every episode to find them. This tool reads the screenplays instead and hands the editor a ranked shortlist with exact timestamps.

### How it works

| Step | Method | What happens |
|---|---|---|
| Parse | Code | Each episode becomes timed beats with speaker and delivery cue |
| Generate | Code | Every clip of 20 to 60 seconds that starts on a shot change and never cuts a spoken line, about 50,000 for one show |
| Score | Rules | Hook strength in the first 3 seconds, an unresolved ending in the last 4 seconds (with a bonus for the writers' own episode cliffhanger), and standalone clarity |
| Shortlist | Code | The best non-overlapping clips per episode, plus "cold open" promos that flash the most shocking 3 to 8 seconds first, a format used widely by apps such as ReelShort |
| Judge | AI model, optional | Re-scores the top 40 clips seeing only the clip, exactly as a stranger scrolling past would |
| Rank | Code | Final score with slate rules that spread picks across the show and across story types, keeping second choices as alternates |
| Review | Person | A one-file review page and a web app where an editor approves or rejects each pick and exports the decisions |

### Results on the 50-episode pack

| Measure | Result |
|---|---|
| Promos returned | 25, covering 25 episodes and all 7 story types, in about 25 seconds |
| Cold-open promos | 10 of the 25 |
| Timing checks | 25 of 25 are 20 to 60 seconds, stay inside their episode, cut no dialogue, and open with sound or action |
| Quote accuracy | 676 of 676 quoted script lines match the source at their timestamps |
| Must-catch moments, written before tuning | 12 of 16 episodes covered; 9 of 16 exact moments in the slate, 10 with alternates |

Top picks include a wife crawling barehanded into thorns as her husband screams for her to stop, a villain's whispered ultimatum that the husband will hang, and a red-hot iron stopping millimetres from the heroine's eye.

| Mode | Cost per show | At 250 shows a month |
|---|---|---|
| Rules only | $0, about 25 seconds | $0 |
| With model, Llama 3.3 70B | about $0.04 | about $10 |
| With model, frontier model | about $0.27 | about $70 |

## Problem 2: AI lawyer

### The problem

Most people in India never get legal help for everyday money disputes, because a lawyer costs more than the amount at stake. Nyay Saathi focuses on three common cases in depth: a security deposit the landlord keeps, a refund a company never pays, and unpaid salary. It turns a messy story into a case file, explains the person's options in plain language, drafts the legal notice, and lets them practise against the other side. Serious matters such as divorce, police cases, property or a court case already running are sent to a lawyer or to free legal aid (NALSA helpline 15100).

### How it works

| Step | Method | What happens |
|---|---|---|
| Intake | Rules, plus model when available | Understands English, Hindi and Hinglish, extracts amounts, dates, place and proof, and asks for missing facts one at a time |
| Escalation | Code only | Checks every message for threats (and shows the 112 emergency number), police matters, family matters, minors, large amounts and approaching deadlines; a model cannot override it |
| Where you stand | Rules, plus model to rephrase | Built only from 21 verified law cards: proof strength, step-by-step options and time limits |
| Documents | Templates | A legal notice for each case type, plus a consumer complaint summary for e-Jagriti or a wage claim summary |
| Practise | Script, plus model when available | Plays the landlord, company or employer using the objections people really hear, and coaches each reply |
| Guardrail | Code only | Checks every outgoing message before the user sees it |

The central design choice is that the model never writes law. Each law card holds a plain-language summary, the exact section, a link to the official source (the Gazette of India, India Code, PIB, NALSA or the National Consumer Helpline) and the date it was checked. The model sees only the relevant cards and must cite them by ID. A validator then scans every message and removes any act or section not on a card, any case citation, any outdated IPC or CrPC reference (replaced by the Bharatiya Nyaya Sanhita in 2024), and any helpline number or website not on the verified list. Every removal is logged and shown in the app.

### Results

| Test | Result |
|---|---|
| 15 test conversations, including Hindi, Hinglish, a case-law request, a threatened tenant and a running court case | 14 pass every check |
| Individual checks across all conversations | 106 of 108 |
| Attempts to slip in invented sections, cases, IPC references and helplines | 15 of 15 caught, with real citations kept |
| A deliberately misbehaving fake model that invents law | 10 of 10 safety checks pass |

The test runs also caught and led to fixes for real issues, including a notice that would have demanded the full amount a gym member paid instead of the smaller amount actually owed.

In model mode a conversation uses about 12,900 input and 2,600 output tokens, or roughly $3.50 to $10.30 per 1,000 conversations depending on the model. Offline mode and all document templates cost nothing.

## Repository layout

```
common/
  screenplay.py            reads Kuku's timestamped screenplay format
  llm.py                   one connection to any AI model
problem3_continuity_checker/
  check_continuity.py      main tool
  demo_show/               a 4-episode original demo show with planted mistakes
  checks.py                the rule checks
  llm_check.py             the AI model pass
  bible.py                 builds the show bible
  inject_test.py           planted-error test
  app.py                   web app
problem1_promo_finder/
  find_promos.py           main tool
  signals.py               hook, cliffhanger and clarity scoring
  judge.py                 the AI model judge
  report.py                JSON, CSV, Markdown and review page
  evaluate.py              quality checks
  app.py                   web app
problem2_ai_lawyer/
  engine.py                conversation engine
  law_cards.json           21 verified law cards
  validator.py             the citation guardrail
  intake.py, escalation.py, advice.py, documents.py, practice.py, casefile.py, voice.py
  run_tests.py, test_validator.py, test_model_stub.py, test_cases.json
  app.py                   web app
outputs/problem2/          full transcripts of all 15 test conversations
check_key.py               checks an API key
```

Outputs for Problems 1 and 3 quote Kuku's confidential scripts, so they are shared separately rather than in this repository.

## Known limitations

- The continuity checker's rules match spellings and patterns, so two completely different descriptions of the same character are left to the AI model pass, and a deliberate alias is flagged for a person to decide.
- About half of the model pass's findings are real, which is why they are marked "check" rather than "fix".
- The promo finder scores shots from their written descriptions and cannot see the generated video, and its word lists are tuned for revenge romance, the most common microdrama genre.
- The promo finder's model judge and the AI lawyer's model mode have been tested end to end with a simulated model but not yet scored with a live one.
- The AI lawyer gives legal information, not legal advice. Its law cards were checked against official sources in November 2026.

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: common` | Run commands from the repo folder using `python3 -m ...` as shown. |
| A key is reported missing | Add it to `.env`, or run with `--model offline`. |
| A model hits its rate limit | The tool retries, and with a list of models it moves to the next one. Cached answers are reused on a rerun. |
| A model returns malformed JSON | The parser handles extra text and code fences; if a reply still fails, that item is skipped and the run continues. |
| Streamlit says the port is in use | Add `--server.port 8510` to the command. |

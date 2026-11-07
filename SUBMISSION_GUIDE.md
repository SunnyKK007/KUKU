# How to submit (read this first)

Kuku reviews **one problem per person**. All three are built so you can choose, but submit one.

## Which one to submit

| Problem | Strength | Risk |
|---|---|---|
| **3. Continuity checker** (recommended) | You found a real problem in Kuku's own scripts and proved it with counts. It hits their AI pipeline directly and has the strongest quality evidence: 44 of 45 planted errors caught on held-out trials, and 13 of 15 flags real on the actual pack. | The brief asks you to argue it matters more than Problems 1 and 2. The doc does this, but be ready to defend it in the interview. |
| **1. Promo finder** | It is the problem Kuku wrote the input pack for, and it runs on a new show in one command. | The most common choice. Recall is modest (9 of 16 reference moments in the top 25), and the doc says so honestly. |
| **2. AI lawyer** | A full working app with a hard block on invented law. | It has no Kuku context, so it shows less fit for the job. |

## Before you submit (all problems)

1. **Read every file you submit.** The interview will ask why each decision was made. Rewrite the doc in your own words where it does not sound like you.
2. **Fill the placeholders.** Your name, roll number, branch, links, and "AI tools used and one place they got it wrong" in `docs/pX_solution.md`. Then rebuild the PDF:
   ```bash
   python3 docs/build_pdfs.py
   ```
3. **Get a free model key and rerun once** (Groq or Gemini). Every number in the docs is from rules-only mode. A model run lets you report the model judge honestly. If the numbers change, update the doc.
   ```bash
   cp .env.example .env   # paste the key, then:
   python3 -m p1_promos.find_promos --input "../I Married a Broken Soldier. He was a Duke" --out outputs/p1_model
   python3 -m p3_continuity.check_continuity --input "../I Married a Broken Soldier. He was a Duke" --out outputs/p3_model
   ```
4. **Check the links open for anyone.** The brief requires this.

## Links, and the confidentiality rule

The brief says not to publish or share the input pack, but every link must open for anyone. Do both like this:
- **Prototype:** a **public** GitHub repo with code only. The scripts are not in it. Before pushing, move `outputs/p1` and `outputs/p3` out of the repo, because they quote the scripts. Optionally deploy the app on Streamlit Community Cloud. Reviewers upload the episodes themselves.
- **Raw outputs:** a Google Drive folder set to "anyone with the link can view", holding the matching `outputs/` folder. This shares Kuku's material only with Kuku's reviewers, which is the intended use.
- **Problem 2** contains no Kuku material, so everything for it can be public.

## The form

| Field | What to put |
|---|---|
| Solution doc | `docs/p1_solution.pdf`, `p2_solution.pdf` or `p3_solution.pdf` (2 pages each) |
| Prototype link | GitHub repo, or the Streamlit app URL |
| Raw outputs | Drive folder link with `outputs/p1` (plus `p1_baseline`), `outputs/p2` or `outputs/p3` |
| Video | Record using `docs/pX_video_script.md`. 3 minutes maximum, in your own voice. Loom or unlisted YouTube. |

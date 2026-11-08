"""
Error-injection test: how many planted continuity errors does the checker catch?

We copy the scripts to a temp folder, plant known errors of five kinds at random
places (seeded, so results are reproducible), run the checker, and count which
planted errors appear in the report. New issues that were not planted and not in
the clean run are counted as noise.

  python3 -m problem3_continuity_checker.inject_test --input "<folder>" --trials 5
"""
from __future__ import annotations

import argparse
import json
import pathlib
import random
import re
import shutil
import tempfile
from collections import Counter

from common.screenplay import load_show
from problem3_continuity_checker.checks import proper_names, run_checks


def typo(word: str, rng: random.Random) -> str:
    i = rng.randrange(1, len(word) - 2)
    w = word[:i] + word[i + 1] + word[i] + word[i + 2:]
    return w if w != word else word[:-1] + ("e" if word[-1] != "e" else "a")


def plant(folder: pathlib.Path, rng: random.Random) -> list[dict]:
    show = load_show(folder)
    names, speakers = proper_names(show)
    frequent = [n for n, v in names.items() if len(v) >= 10 and n.upper() in speakers]
    files = sorted(folder.glob("*.txt"))
    planted = []

    def edit(path, old, new, count=1):
        t = path.read_text(encoding="utf-8")
        if old not in t:
            return False
        path.write_text(t.replace(old, new, count), encoding="utf-8")
        return True

    for name in rng.sample(frequent, 2):
        for _ in range(20):
            f = rng.choice(files)
            lines = f.read_text(encoding="utf-8").splitlines()
            idx = [i for i, l in enumerate(lines) if l.startswith('"') and re.search(rf"\b{name}\b", l)]
            if idx:
                i = rng.choice(idx)
                bad = typo(name, rng)
                lines[i] = re.sub(rf"\b{name}\b", bad, lines[i], count=1)
                f.write_text("\n".join(lines), encoding="utf-8")
                planted.append({"kind": "name typo in dialogue", "token": bad, "file": f.name})
                break
    labels = Counter(b.speaker for e in show for b in e.dialogue)
    lab = rng.choice([l for l, c in labels.items() if c >= 40 and len(l) >= 6])
    bad_lab = typo(lab, rng)
    for _ in range(20):
        f = rng.choice(files)
        if edit(f, f"**{lab} (", f"**{bad_lab} ("):
            planted.append({"kind": "speaker label typo", "token": bad_lab, "file": f.name})
            break
    single = [l for l, c in labels.items() if c >= 40 and not l.startswith(("LADY", "LORD")) and len(l.split()) == 1]
    lab2 = rng.choice(single)
    new_lab = rng.choice(["LORD", "LADY", "SIR"]) + " " + lab2
    for _ in range(20):
        f = rng.choice(files)
        if edit(f, f"**{lab2} (", f"**{new_lab} (", count=3):
            planted.append({"kind": "label gains a title", "token": new_lab, "file": f.name})
            break
    for _ in range(40):
        f = rng.choice(files)
        t = f.read_text(encoding="utf-8")
        m = re.search(r"(from [^.\n]{0,80}?Episode )(\d+)", t)
        if m and "CONTINUITY" in t[:t.find(m.group(0))][-400:]:
            wrong = str(int(m.group(2)) + rng.choice([3, 5, 7]))
            f.write_text(t.replace(m.group(0), m.group(1) + wrong, 1), encoding="utf-8")
            planted.append({"kind": "wrong episode in continuity note", "token": f"from Episode {wrong}", "file": f.name,
                            "episode_ref": wrong})
            break
    return planted


def caught(p: dict, issues: list[dict]) -> bool:
    for i in issues:
        blob = i["title"] + " " + json.dumps(i["evidence"])
        if p["kind"] == "wrong episode in continuity note":
            if i["type"] == "continuity note mismatch" and f"Episode {p['episode_ref']}" in i["title"]:
                return True
        elif p["token"] in blob:
            return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--trials", type=int, default=5)
    ap.add_argument("--seed-base", type=int, default=1000, help="change for a held-out run")
    ap.add_argument("--out", default="outputs/problem3/injection_test.md")
    a = ap.parse_args()
    norm = lambda t: re.sub(r"\d+", "#", t)
    clean = {norm(i["title"]) for i in run_checks(load_show(a.input))}
    by_kind, noise_total, rows = Counter(), 0, []
    hits = Counter()
    noise_titles: list[str] = []
    for t in range(a.trials):
        rng = random.Random(a.seed_base + t)
        with tempfile.TemporaryDirectory() as tmp:
            dst = pathlib.Path(tmp)
            for f in pathlib.Path(a.input).glob("*.txt"):
                shutil.copy(f, dst / f.name)
            planted = plant(dst, rng)
            issues = run_checks(load_show(dst))
            for p in planted:
                ok = caught(p, issues)
                by_kind[p["kind"]] += 1
                hits[p["kind"]] += ok
                rows.append(f"| {t + 1} | {p['kind']} | `{p['token']}` | {p['file'][:24]} | {'caught' if ok else 'MISSED'} |")
            tokens = [p["token"] for p in planted]
            noise = [i for i in issues if norm(i["title"]) not in clean and not any(tok in i["title"] + json.dumps(i["evidence"]) for tok in tokens)
                     and i["type"] != "continuity note mismatch"]
            noise_total += len(noise)
            noise_titles.extend(f"trial {t + 1}: {i['title'][:120]}" for i in noise)
    total, got = sum(by_kind.values()), sum(hits.values())
    lines = ["# Error-injection test", "", f"Trials: {a.trials} (seeds from {a.seed_base}). Planted errors: {total}. Caught: {got} ({got / total:.0%}).",
             f"New unrelated issues raised across all trials (noise): {noise_total}", "",
             "| Kind | Planted | Caught |", "|---|---|---|"]
    lines += [f"| {k} | {by_kind[k]} | {hits[k]} |" for k in by_kind]
    lines += ["", "Noise issues:"] + [f"- {n}" for n in noise_titles] + ["", "| Trial | Kind | Planted token | File | Result |", "|---|---|---|---|---|"] + rows
    text = "\n".join(lines)
    print(text)
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(text + "\n")


if __name__ == "__main__":
    main()

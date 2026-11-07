"""
Rule-based signals for promo scoring. Pure code: cheap, explainable, and the
same on every run. The model judge (judge.py) only re-scores a shortlist.

Lexicons are tuned for the revenge / romance / betrayal genre that dominates
microdrama. A comedy or thriller would need its own word lists (see doc).
"""
from __future__ import annotations

import re

from common.screenplay import Beat

# --- what makes a scrolling viewer stop (hook) ------------------------------
HOOK_WORDS = {
    # physical shock, weight 3
    3.0: r"slap|strikes?|struck|punch|explo|blast|ablaze|inferno|flames?|blood|bleed|dagger|blade|sword|"
         r"pistol|gun|riding crop|whip|lash|chain|shackle|red-hot|iron rod|branding|noose|gallows|"
         r"strangl|chok|stab|smash|shatter|hurls?|throws?|slams?|seiz|drags?|kicks?|burns?|fire\b|"
         r"poison|arsenic|corpse|dead body|collapses?|faints?",
    # dramatic reveal / romance beat, weight 2
    2.0: r"kneel|drops? to one knee|propos|kiss|bursts? (in|through|open)|storms? (in|into)|"
         r"reveal|unmask|tears? (off|open)|rips?|crown|signet|ring\b|veil|altar|tiara|regalia|"
         r"gasps?|screams?|shrieks?|sob|tears stream|weep|trembl|mud\b|on her knees|on his knees",
}
INTENSE_CUES = (r"scream|shout|furious|rage|enraged|venom|cruel|threat|mock|sneer|vicious|shock|"
                r"horrif|desperate|menac|contempt|triumph|sadistic|spite|scorn|taunt|savage|"
                r"livid|seething|icy|cold|condemn|accus|commanding|defiant|fierce|hysteric|"
                r"broken|devastat|anguish|pleading|begging|smug|disdain|malicious|vindictive")
SHOCK_LINE = (r"\b(never|dead|die|kill|hang|hanged|witch|marry|married|wife|husband|betray|liar|thief|"
              r"murder|poison|disown|nothing|beg|kneel|mine|traitor|whore|bastard|worthless|"
              r"filth|beggar|execute|burn|arrest|guards|take her|take him|get out|how dare|"
              r"not anymore|you will|you are no|i am the|i will destroy|on your knees|"
              r"rightful|heir|lawful|duke|duchess|pregnant|inheritance|disinherit)\b")
# cosy-scene words that make fire/strike words false alarms ("strikes flint over kindling")
COSY = r"flint|kindling|hearth|fireplace|candle|lantern|stove|cooking|kettle"

# --- what leaves the viewer needing more (cliffhanger) -----------------------
CLIFF_WORDS = (r"cut(s|ting)? (abruptly )?to black|abrupt|cliffhanger|freez|frozen|realiz|horror|"
               r"terrified|terror|shock|gasps?|stunned|eyes widen|wide eyes|wide-eyed|jaw drops|"
               r"smirk|venomous|triumphant|bursts? (in|open|through)|silhouett|footsteps|appears|"
               r"emerges?|door (creaks|swings|bursts)|someone|unknown|reveal|explod|seiz|drags?|"
               r"looms?|raises? (the|his|her) (blade|sword|hand|iron|crop)|lunges?|grabs?|"
               r"falls? silent|trap|doom|sentence")
RESOLVED_WORDS = (r"embrace|smiles? warmly|warm smile|peaceful|peace\b|relief|relieved|laughs? softly|"
                  r"tender(ly)? kiss|falls asleep|sleeps|content(ed)?\b|settles|hand[- ]in[- ]hand|"
                  r"walk(s|ing)? (away|off|out)( \w+)? together|together into|sunlight|warmth|warm\b|cozy|"
                  r"gentle|soft smile|calm|fad(es|ing) out|music swells? (warmly|softly)|safe\b|comfort")

# --- what a new viewer can follow without backstory (standalone) -------------
ARCHETYPES = (r"\b(wife|husband|sister|mother|father|bride|groom|wedding|duke|duchess|son|daughter|"
              r"family|fianc[eé]e?|stepmother|heir|maid|lord|lady|king|queen|witch|soldier)\b")
NEEDS_CONTEXT = (r"\b(remember|again|last night|yesterday|earlier|as i said|as i told|like before|"
                 r"that day|after what|the other|you promised|we agreed|back then)\b")

TROPES = {
    "betrayal / jilted": r"altar|jilt|abandon|betray|fianc|wedding|sister|disown|cast aside",
    "revenge / power reveal": r"duke|duchess|regalia|crown|rightful|bow|salute|proclaim|true heir|reclaim",
    "cruelty / humiliation": r"slap|mud|mock|humiliat|kneel|scrub|beg|chains|crop|whip|scullery|filth",
    "protector romance": r"protect|carries|wound|bandage|hold|swear|vow|hearth|husband|kiss",
    "danger / action": r"fire|flames|ablaze|explo|fight|thug|blade|sword|attack|guard|seize",
    "injustice / trial": r"trial|witch|gallows|hang|execution|dock|testimony|judge|framed|arrest|dungeon",
    "scheming villain": r"plot|scheme|conspir|poison|arsenic|secret|frame|forge|bribe",
}


def _count(pattern: str, text: str) -> int:
    return len(re.findall(pattern, text, flags=re.I))


_MEMO: dict[int, tuple[Beat, float]] = {}


def beat_intensity(b: Beat) -> float:
    """How much a single beat grabs attention (memoised: scored once per beat)."""
    hit = _MEMO.get(id(b))
    if hit is not None and hit[0] is b:
        return hit[1]
    v = _beat_intensity(b)
    _MEMO[id(b)] = (b, v)
    return v


def _beat_intensity(b: Beat) -> float:
    text = b.text
    score = 0.0
    for w, pat in HOOK_WORDS.items():
        score += w * min(_count(pat, text), 2)
    if b.kind == "dialogue":
        score += 1.2 * min(_count(INTENSE_CUES, b.cue), 2)
        score += 1.5 * min(_count(SHOCK_LINE, text), 2)
        if text.endswith("!"):
            score += 0.5
        if len(text.split()) <= 8:
            score += 0.5          # short, punchy line
    if b.kind == "sfx":
        score += 0.5
    if re.search(COSY, text, re.I):
        score -= 2.5          # fire in a hearth is not danger
    return max(score, 0.0)


def hook_score(beats: list[Beat], start: float) -> tuple[float, Beat | None]:
    """Strongest beat that starts in the first 3 seconds. Returns (score, beat)."""
    early = [b for b in beats if start - 0.3 <= b.start <= start + 3.0]
    if not early:
        return 0.0, None
    scored = [(beat_intensity(b), b) for b in early]
    best = max(scored, key=lambda x: x[0])
    total = sum(s for s, _ in scored)
    # a line of dialogue inside 3s matters (works with sound on), visuals matter (sound off)
    has_line = any(b.kind == "dialogue" for b in early)
    calm_open = all(re.search(r"establish|landscape|exterior|slow pan|wide shot of the (manor|forest|"
                              r"village|estate|castle)", b.text, re.I) for b in early if b.kind == "camera") \
        and not has_line
    s = best[0] + 0.35 * (total - best[0]) + (0.8 if has_line else 0)
    if calm_open:
        s -= 2.0
    return max(s, 0.0), best[1]


def cliff_score(beats: list[Beat], end: float, episode_end: float) -> tuple[float, Beat | None]:
    late = [b for b in beats if b.end >= end - 4.0 and b.start < end]
    if not late:
        return 0.0, None
    text = " ".join(b.text for b in late)
    s = 1.2 * min(_count(CLIFF_WORDS, text), 4)
    s -= 1.5 * min(_count(RESOLVED_WORDS, text), 3)
    last_line = next((b for b in reversed(late) if b.kind == "dialogue"), None)
    if last_line:
        if last_line.text.rstrip().endswith("?"):
            s += 1.5
        s += 1.0 * min(_count(SHOCK_LINE, last_line.text), 2)
        s += 0.6 * min(_count(INTENSE_CUES, last_line.cue), 2)
    resolved = _count(RESOLVED_WORDS, text)
    if abs(end - episode_end) <= 1.5:
        # writers usually place the episode cliffhanger here, unless the ending is calm
        s += 3.0 if resolved == 0 else 0.5
    anchor = max(late, key=lambda b: (b.kind != "camera", b.end))
    return s, anchor


def standalone_score(beats: list[Beat], speakers_known: set[str]) -> tuple[float, list[str]]:
    """10 = a stranger follows it. Penalties for backstory, crowding and silence."""
    notes = []
    text = " ".join(b.text for b in beats)
    dialogue = [b for b in beats if b.kind == "dialogue"]
    speakers = {b.speaker for b in dialogue}
    s = 7.0
    s += min(_count(ARCHETYPES, text), 4) * 0.5
    ctx = _count(NEEDS_CONTEXT, " ".join(b.text for b in dialogue))
    if ctx:
        s -= 1.0 * ctx
        notes.append(f"{ctx} line(s) lean on earlier events")
    if len(speakers) > 4:
        s -= (len(speakers) - 4) * 0.8
        notes.append(f"{len(speakers)} speakers is crowded")
    if len(dialogue) < 3:
        s -= 2.0
        notes.append("almost no dialogue, so stakes may be unclear")
    # names said aloud but never seen speaking in the clip need explanation
    said = set(re.findall(r"\b([A-Z][a-z]{3,})\b", " ".join(b.text for b in dialogue)))
    absent = {n for n in said if n.upper() in speakers_known and not any(n.upper() in sp for sp in speakers)}
    if absent:
        s -= 0.4 * len(absent)
        notes.append("mentions off-screen characters: " + ", ".join(sorted(absent)))
    return max(min(s, 10.0), 0.0), notes


def body_intensity(beats: list[Beat], duration: float) -> float:
    if duration <= 0:
        return 0.0
    return sum(beat_intensity(b) for b in beats) / duration * 10.0   # per 10 seconds


def tropes(beats: list[Beat]) -> list[str]:
    text = " ".join(b.text + " " + b.cue for b in beats)
    hits = sorted(((_count(p, text), t) for t, p in TROPES.items()), reverse=True)
    return [t for c, t in hits if c > 0][:2] or ["drama"]


def squash(x: float, k: float) -> float:
    """Map a raw non-negative score to 0..10."""
    x = max(x, 0.0)
    return round(10.0 * x / (x + k), 2)

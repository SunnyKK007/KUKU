"""
Parser for Kuku timestamped screenplays.

Turns each episode file into a list of Beats (camera, action, sound, dialogue),
each with start/end seconds, speaker, delivery cue and source line number.
Pure code, no model: it is deterministic, free and testable.

Tolerant of the format drift seen in the input pack (e.g. Episode 6 uses
upper-case scene headers), and of speaker modifiers like (O.S.) / (Off-screen).
"""
from __future__ import annotations

import pathlib
import re
from dataclasses import dataclass, field

LABEL_RE = re.compile(r"^\*\*(?P<label>.+?):\*\*\s*$")
TIME_RE = re.compile(r"^Start:\s*\((?P<s>[\d:.]+)\)\s*\|\s*End:\s*\((?P<e>[\d:.]+)\)", re.I)
SCENE_RE = re.compile(r"^SCENE\s+(\d+)\s*$", re.I)
HEAD_RE = re.compile(r"^scene heading:\s*(.*)$", re.I)
SSTART_RE = re.compile(r"^scene start:\s*([\d:.]+)", re.I)
SEND_RE = re.compile(r"^scene end:\s*([\d:.]+)", re.I)
MODIFIERS = {"O.S.", "OFF-SCREEN", "V.O.", "VO", "CONT'D", "O.C.", "OFF SCREEN", "VOICE-OVER"}
NON_SPEAKERS = {"CAMERA": "camera", "ACTION": "action", "SOUND FX": "sfx", "SFX": "sfx",
                "MUSIC": "sfx", "SOUND": "sfx"}


def to_sec(ts: str) -> float:
    parts = ts.strip().split(":")
    sec = 0.0
    for p in parts:
        sec = sec * 60 + float(p)
    return round(sec, 2)


def fmt(sec: float) -> str:
    m, s = divmod(max(sec, 0), 60)
    return f"{int(m):02d}:{s:05.2f}"


@dataclass
class Beat:
    kind: str
    start: float
    end: float
    text: str
    speaker: str = ""
    cue: str = ""
    offscreen: bool = False
    line: int = 0

    def as_text(self) -> str:
        if self.kind == "dialogue":
            cue = f" ({self.cue})" if self.cue else ""
            return f"[{fmt(self.start)}] {self.speaker}{cue}: {self.text}"
        return f"[{fmt(self.start)}] {self.kind.upper()}: {self.text}"


@dataclass
class Scene:
    number: int
    heading: str
    start: float
    end: float


@dataclass
class Episode:
    number: int
    path: pathlib.Path
    logline: str = ""
    continuity: str = ""
    scenes: list[Scene] = field(default_factory=list)
    beats: list[Beat] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        ends = [s.end for s in self.scenes] + [b.end for b in self.beats]
        return max(ends) if ends else 0.0

    @property
    def dialogue(self) -> list[Beat]:
        return [b for b in self.beats if b.kind == "dialogue"]

    def window(self, start: float, end: float) -> list[Beat]:
        return [b for b in self.beats if b.start < end and b.end > start]


def split_label(label: str) -> tuple[str, str, str, bool]:
    """'LADY JANE (Off-screen) (Vulnerable, Begging)' -> kind, speaker, cue, offscreen."""
    name = label.split(" (", 1)[0].strip()
    groups = re.findall(r"\(([^)]*)\)", label)
    offscreen = any(g.strip().upper() in MODIFIERS for g in groups)
    cues = [g for g in groups if g.strip().upper() not in MODIFIERS]
    kind = NON_SPEAKERS.get(name.upper(), "dialogue")
    return kind, (name if kind == "dialogue" else ""), ", ".join(cues), offscreen


def parse_episode(path: str | pathlib.Path) -> Episode:
    path = pathlib.Path(path)
    lines = path.read_text(encoding="utf-8").splitlines()
    m = re.search(r"episode-(\d+)", path.name)
    ep = Episode(number=int(m.group(1)) if m else 0, path=path)
    scene_no, pending = 1, None
    cur_scene: dict = {}
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()
        up = line.upper()
        if up.startswith("EPISODE NUMBER:"):
            n = re.search(r"(\d+)", line)
            if n:
                ep.number = int(n.group(1))
        elif up.startswith("EPISODE LOGLINE:"):
            ep.logline = line.split(":", 1)[1].strip()
        elif up.startswith("CONTINUITY NOTES:"):
            ep.continuity = line.split(":", 1)[1].strip()
        elif SCENE_RE.match(line):
            scene_no = int(SCENE_RE.match(line).group(1))
            cur_scene = {"number": scene_no}
        elif HEAD_RE.match(line):
            cur_scene["heading"] = HEAD_RE.match(line).group(1).strip()
        elif SSTART_RE.match(line):
            cur_scene["start"] = to_sec(SSTART_RE.match(line).group(1))
        elif SEND_RE.match(line):
            cur_scene["end"] = to_sec(SEND_RE.match(line).group(1))
            ep.scenes.append(Scene(cur_scene.get("number", scene_no), cur_scene.get("heading", ""),
                                   cur_scene.get("start", 0.0), cur_scene["end"]))
        elif LABEL_RE.match(line):
            pending = (*split_label(LABEL_RE.match(line).group("label")), i + 1)
        elif pending and TIME_RE.match(line):
            t = TIME_RE.match(line)
            text_lines = []
            j = i + 1
            while j < len(lines) and lines[j].strip() and not LABEL_RE.match(lines[j].strip()) \
                    and not lines[j].startswith("---"):
                text_lines.append(lines[j].strip())
                j += 1
            kind, speaker, cue, off = pending[:4]
            text = " ".join(text_lines).strip()
            if kind == "dialogue":
                text = text.strip('"“”')
            s, e = to_sec(t.group("s")), to_sec(t.group("e"))
            if e < s:
                ep.warnings.append(f"line {i+1}: end before start")
            ep.beats.append(Beat(kind, s, e, text, speaker, cue, off, pending[4]))
            pending = None
            i = j - 1
        i += 1
    if not ep.scenes:
        ep.warnings.append("no scene headers found")
    ep.beats.sort(key=lambda b: (b.start, b.end))
    return ep


def load_show(folder: str | pathlib.Path) -> list[Episode]:
    folder = pathlib.Path(folder)
    files = sorted(folder.glob("*.txt"))
    eps = [parse_episode(f) for f in files]
    eps.sort(key=lambda e: e.number)
    return eps


if __name__ == "__main__":
    import sys
    show = load_show(sys.argv[1])
    for e in show:
        kinds = {}
        for b in e.beats:
            kinds[b.kind] = kinds.get(b.kind, 0) + 1
        print(f"E{e.number:03d} {e.duration:6.1f}s scenes={len(e.scenes)} {kinds} {e.warnings or ''}")

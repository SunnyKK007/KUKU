"""
One swappable model adapter for every tool in this repo.

Every provider below speaks the OpenAI chat-completions format, so switching
models is one setting:  --model groq:llama-3.3-70b-versatile
                        --model gemini:gemini-2.5-flash
                        --model anthropic:claude-sonnet-5-5
                        --model ollama:llama3.1:8b
                        --model custom:<model>   (uses LLM_BASE_URL + LLM_API_KEY)
                        --model offline          (no model; tools fall back to rules)

Features: .env loading, on-disk response cache (re-runs are free and
reproducible), retry with backoff on rate limits, robust JSON parsing,
and token accounting so every run can report its cost.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent

PROVIDERS = {
    "groq": {"base_url": "https://api.groq.com/openai/v1", "key_env": "GROQ_API_KEY",
             "default_model": "llama-3.3-70b-versatile"},
    "gemini": {"base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
               "key_env": "GEMINI_API_KEY", "default_model": "gemini-3.5-flash"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1", "key_env": "OPENROUTER_API_KEY",
                   "default_model": "meta-llama/llama-3.3-70b-instruct:free"},
    "openai": {"base_url": "https://api.openai.com/v1", "key_env": "OPENAI_API_KEY",
               "default_model": "gpt-4o-mini"},
    "anthropic": {"base_url": "https://api.anthropic.com/v1/", "key_env": "ANTHROPIC_API_KEY",
                  "default_model": "claude-sonnet-5-5"},
    "ollama": {"base_url": "http://localhost:11434/v1", "key_env": None,
               "default_model": "llama3.1:8b"},
    "custom": {"base_url": None, "key_env": "LLM_API_KEY", "default_model": None},
}

PRICE_PER_M = {
    "llama-3.3-70b-versatile": (0.59, 0.79),
    "gemini-2.5-flash": (0.30, 2.50),
    "gpt-4o-mini": (0.15, 0.60),
}


def load_env(path: pathlib.Path | None = None) -> None:
    """Minimal .env loader so we need no extra dependency."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def first_available_spec() -> str:
    """Pick a model automatically: LLM_MODEL if set, else the first provider with a key."""
    load_env()
    if os.environ.get("LLM_MODEL"):
        return os.environ["LLM_MODEL"]
    for name in ("groq", "gemini", "openrouter", "anthropic", "openai"):
        env = PROVIDERS[name]["key_env"]
        if env and os.environ.get(env):
            return name
    return "offline"


class QuotaExhausted(RuntimeError):
    """Every model in the list is out of daily quota or unavailable; retrying will not help."""


class LLM:
    def __init__(self, spec: str | None = None, cache_dir: pathlib.Path | None = None,
                 temperature: float = 0.2, api_key: str | None = None):
        load_env()
        spec = spec or first_available_spec()
        self.spec = spec
        self.temperature = temperature
        self.usage = {"calls": 0, "cached": 0, "prompt_tokens": 0, "completion_tokens": 0}
        self.cache_dir = cache_dir or ROOT / ".llm_cache"
        if spec == "offline":
            self.provider, self.model, self.client = "offline", None, None
            self.models = []
            return
        provider, _, model = spec.partition(":")
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider '{provider}'. Choose from {list(PROVIDERS)} or 'offline'.")
        cfg = PROVIDERS[provider]
        self.provider = provider
        chain = [m.strip() for m in model.split(",") if m.strip()] if model else []
        self.models = chain or [cfg["default_model"] or os.environ.get("LLM_MODEL_NAME")]
        self.model = self.models[0]
        self.usage["models_used"] = {}
        base_url = cfg["base_url"] or os.environ.get("LLM_BASE_URL")
        key = (api_key or os.environ.get(cfg["key_env"])) if cfg["key_env"] else "ollama"
        if not key:
            raise RuntimeError(f"{cfg['key_env']} is not set. Add it to .env or use --model offline.")
        from openai import OpenAI
        self.client = OpenAI(base_url=base_url, api_key=key, timeout=60.0, max_retries=0)

    @property
    def available(self) -> bool:
        return self.client is not None

    def label(self) -> str:
        if not self.available:
            return "offline (rules only)"
        used = list(self.usage.get("models_used", {})) or [self.model]
        return f"{self.provider}:{'+'.join(used)}"

    def chat(self, messages: list[dict], json_mode: bool = False, max_tokens: int = 1500) -> str:
        if not self.available:
            raise RuntimeError("No model configured (offline mode).")
        def cache_path(model):
            key = hashlib.sha256(json.dumps([self.provider, model, self.temperature, json_mode,
                                             messages], sort_keys=True).encode()).hexdigest()
            return self.cache_dir / f"{key}.json"
        for m in self.models:
            if cache_path(m).exists():
                self.usage["cached"] += 1
                return json.loads(cache_path(m).read_text())["content"]
        kwargs = dict(model=self.model, messages=messages, temperature=self.temperature,
                      max_tokens=max_tokens)
        if json_mode and self.provider not in ("anthropic",):
            kwargs["response_format"] = {"type": "json_object"}
        if self.provider == "gemini":
            kwargs["reasoning_effort"] = "none"
        delay = 4.0
        for attempt in range(6 + len(self.models)):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                break
            except Exception as e:
                msg = str(e).lower()
                if "response_format" in msg and "response_format" in kwargs:
                    kwargs.pop("response_format")
                    continue
                unusable = "perday" in msg or "404" in msg or "no longer available" in msg or "not found" in msg
                if unusable and self.model != self.models[-1]:
                    self.model = self.models[self.models.index(self.model) + 1]
                    kwargs["model"] = self.model
                    continue
                if unusable:
                    raise QuotaExhausted(f"{self.model}: daily free quota used up or model unavailable") from e
                if attempt >= 5 + len(self.models) or not any(s in msg for s in ("429", "rate", "timeout", "503", "overloaded", "502", "resource_exhausted", "quota", "unavailable")):
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 60)
        content = resp.choices[0].message.content or ""
        self.usage["calls"] += 1
        self.usage["models_used"][self.model] = self.usage["models_used"].get(self.model, 0) + 1
        if getattr(resp, "usage", None):
            self.usage["prompt_tokens"] += resp.usage.prompt_tokens or 0
            self.usage["completion_tokens"] += resp.usage.completion_tokens or 0
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path(self.model).write_text(json.dumps({"content": content}))
        return content

    def json(self, system: str, user: str, max_tokens: int = 1500) -> dict:
        raw = self.chat([{"role": "system", "content": system}, {"role": "user", "content": user}],
                        json_mode=True, max_tokens=max_tokens)
        return parse_json(raw)

    def cost_report(self) -> dict:
        p, c = self.usage["prompt_tokens"], self.usage["completion_tokens"]
        price = PRICE_PER_M.get(self.model or "", None)
        est = round(p / 1e6 * price[0] + c / 1e6 * price[1], 4) if price else None
        return {**self.usage, "model": self.label(), "est_cost_usd_at_paid_rates": est}


def parse_json(raw: str) -> dict:
    """Parse model output that should be JSON, tolerating code fences and chatter."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?|```$", "", raw, flags=re.M).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", raw, re.S)
        if m:
            return json.loads(m.group(0))
        raise


NON_CHAT = ("embed", "tts", "image", "veo", "imagen", "aqa", "audio", "live", "transcribe", "whisper", "moderation",
            "dall-e", "davinci", "babbage", "realtime", "search", "guard", "vision-preview", "computer-use", "omni",
            "antigravity", "customtools", "lyria", "banana", "music", "speech", "robotics")


def list_models(provider: str, api_key: str | None = None, timeout: float = 15.0) -> list[str]:
    """Every chat model the provider's API reports for this key. Raises on failure."""
    load_env()
    cfg = PROVIDERS[provider]
    key = (api_key or os.environ.get(cfg["key_env"])) if cfg["key_env"] else "ollama"
    if not key:
        raise RuntimeError("no key")
    from openai import OpenAI
    client = OpenAI(base_url=cfg["base_url"] or os.environ.get("LLM_BASE_URL"), api_key=key, timeout=timeout, max_retries=0)
    names = []
    for m in client.models.list():
        mid = getattr(m, "id", "") or ""
        mid = mid.split("/", 1)[1] if provider == "gemini" and mid.startswith("models/") else mid
        if mid and not any(w in mid.lower() for w in NON_CHAT):
            names.append(mid)
    return sorted(set(names))

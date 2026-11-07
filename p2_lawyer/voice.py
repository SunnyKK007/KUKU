"""
Optional voice input: speech-to-text in Indian languages through Sarvam AI.
Only used when SARVAM_API_KEY is set. Endpoint and model names checked against
docs.sarvam.ai (speech-to-text 'transcribe' reference) on 2026-11-08.
"""
from __future__ import annotations

import os

SARVAM_URL = "https://api.sarvam.ai/speech-to-text"
SARVAM_MODEL = os.environ.get("SARVAM_STT_MODEL", "saaras:v4")


def available() -> bool:
    return bool(os.environ.get("SARVAM_API_KEY"))


def transcribe(audio_bytes: bytes, filename: str = "voice.wav", language_code: str = "unknown") -> dict:
    """Return {'text': str, 'language_code': str} or {'error': str}. Never raises."""
    key = os.environ.get("SARVAM_API_KEY")
    if not key:
        return {"error": "Voice needs SARVAM_API_KEY in .env (free credits at sarvam.ai). You can type instead."}
    try:
        import requests
        resp = requests.post(
            SARVAM_URL,
            headers={"api-subscription-key": key},
            files={"file": (filename, audio_bytes, "audio/wav")},
            data={"model": SARVAM_MODEL, "language_code": language_code},
            timeout=60,
        )
        if resp.status_code != 200:
            return {"error": f"Sarvam returned {resp.status_code}: {resp.text[:200]}"}
        data = resp.json()
        return {"text": data.get("transcript", ""), "language_code": data.get("language_code", language_code)}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

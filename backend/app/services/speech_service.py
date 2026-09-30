"""
speech_service.py

Server-side speech helper. The primary TTS path for the MVP is the
browser's Web Speech API (see frontend/src/services/speechService.ts),
so this module is currently a thin optional layer: if SARVAM_API_KEY
is configured, requests can be routed through sarvam_service instead
of the browser. If no key is set, callers should keep using the
browser API - this module never runs unless explicitly wired up by
a future /api/speech route.
"""
from ..config import settings
from . import sarvam_service


def is_server_tts_available() -> bool:
    return bool(settings.SARVAM_API_KEY)


def synthesize_speech(text: str, lang: str = "hi-IN") -> bytes | None:
    """Returns audio bytes if server-side TTS is configured, else None
    (meaning the caller should fall back to the browser's Web Speech API)."""
    if not is_server_tts_available():
        return None
    return sarvam_service.text_to_speech(text, lang)

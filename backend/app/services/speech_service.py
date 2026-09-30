"""
speech_service.py

Server-side speech helper used by the optional /api/speech/tts route.
When Sarvam is not configured or the request fails, the frontend keeps
using its existing Web Speech API fallback.
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

"""
speech_service.py

Server-side speech helper used by the /api/tts proxy route.
Returns decoded WAV bytes or None when Sarvam is unavailable.
"""
from ..config import settings
from . import sarvam_service


def is_server_tts_available() -> bool:
    return bool(settings.SARVAM_API_KEY)


async def synthesize_speech(text: str, lang: str = "hi-IN") -> bytes | None:
    """Return decoded WAV bytes when server-side TTS is configured."""
    if not is_server_tts_available():
        return None
    return await sarvam_service.text_to_speech(text, lang)

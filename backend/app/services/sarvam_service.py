"""
sarvam_service.py

Optional integration with Sarvam AI for Indian-language text-to-speech.
Disabled unless SARVAM_API_KEY is set in the backend environment.
The key is NEVER sent to or used by the frontend - all requests are
made from this backend module only.
"""
from ..config import settings

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"


def text_to_speech(text: str, lang: str = "hi-IN") -> bytes | None:
    if not settings.SARVAM_API_KEY:
        return None

    import requests  # imported lazily; not a hard dependency for demo/base installs

    try:
        response = requests.post(
            SARVAM_TTS_URL,
            headers={"API-Subscription-Key": settings.SARVAM_API_KEY},
            json={"inputs": [text], "target_language_code": lang, "speaker": "meera"},
            timeout=15,
        )
        response.raise_for_status()
        # Sarvam returns base64 audio; decoding is left to the caller/route
        # that wires this up, since response shape may evolve.
        return response.content
    except Exception as exc:  # noqa: BLE001
        print(f"[KhetSetu] Sarvam TTS request failed: {exc}")
        return None

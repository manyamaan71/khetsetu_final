"""
sarvam_service.py

Optional integration with Sarvam AI for Indian-language text-to-speech.
Disabled unless SARVAM_API_KEY is set in the backend environment.
The key is NEVER sent to or used by the frontend - all requests are
made from this backend module only.
"""
import base64
import binascii

import httpx

from ..config import settings

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
SCRIPT_RANGES = {
    "hi-IN": (0x0900, 0x097F),
    "mr-IN": (0x0900, 0x097F),
    "bn-IN": (0x0980, 0x09FF),
    "ta-IN": (0x0B80, 0x0BFF),
    "te-IN": (0x0C00, 0x0C7F),
    "kn-IN": (0x0C80, 0x0CFF),
    "ml-IN": (0x0D00, 0x0D7F),
}


def is_in_target_script(text: str, lang: str) -> bool:
    script_range = SCRIPT_RANGES.get(lang)
    return bool(script_range and any(script_range[0] <= ord(char) <= script_range[1] for char in text))


async def translate_text(client: httpx.AsyncClient, text: str, lang: str) -> str:
    response = await client.post(
        SARVAM_TRANSLATE_URL,
        headers={"api-subscription-key": settings.SARVAM_API_KEY},
        json={
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": lang,
            "model": "sarvam-translate:v1",
            "output_script": "fully-native",
        },
    )
    response.raise_for_status()
    translated = response.json().get("translated_text", "").strip()
    if not translated:
        raise ValueError("Sarvam returned empty translated text")
    return translated


async def text_to_speech(text: str, lang: str = "hi-IN") -> bytes | None:
    if not settings.SARVAM_API_KEY:
        return None

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            spoken_text = text
            if lang != "en-IN" and not is_in_target_script(text, lang):
                spoken_text = await translate_text(client, text, lang)
            response = await client.post(
                SARVAM_TTS_URL,
                headers={"api-subscription-key": settings.SARVAM_API_KEY},
                json={"text": spoken_text, "language_code": lang, "model": "bulbul:v3"},
            )
            response.raise_for_status()
            audios = response.json().get("audios")
            if not isinstance(audios, list) or not audios or not isinstance(audios[0], str):
                raise ValueError("Sarvam returned no audio")

            encoded_audio = audios[0].split(",base64,", 1)[-1]
            return base64.b64decode(encoded_audio, validate=True)
    except (httpx.HTTPError, ValueError, binascii.Error) as exc:
        print(f"[KhetSetu] Sarvam TTS request failed: {exc}")
        return None

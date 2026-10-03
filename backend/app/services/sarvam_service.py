"""
sarvam_service.py

Optional integration with Sarvam AI for Indian-language text-to-speech.
Disabled unless SARVAM_API_KEY is set in the backend environment.
The key is NEVER sent to or used by the frontend - all requests are
made from this backend module only.
"""
import base64
import binascii
import asyncio
import hashlib
import logging
import time
from collections import OrderedDict

import httpx

from ..config import settings

logger = logging.getLogger(__name__)
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

_translation_cache: dict[tuple[str, str], tuple[float, str]] = {}
_TRANSLATION_CACHE_TTL = 12 * 60 * 60
_tts_cache: OrderedDict[str, bytes] = OrderedDict()
_TTS_CACHE_SIZE = 64


class TtsTextTooLongError(Exception):
    """Sarvam rejected a TTS request because its text exceeded a service limit."""


def _tts_cache_key(text: str, lang: str) -> str:
    return hashlib.sha256(f"{lang}\0{text}".encode("utf-8")).hexdigest()


def _log_request_failure(
    operation: str,
    exc: Exception,
    response: httpx.Response | None = None,
) -> None:
    if response is None:
        response = getattr(exc, "response", None)
    status = response.status_code if response else "unavailable"
    body = response.text[:200] if response else ""
    logger.warning("Sarvam %s failed status=%s body=%r error=%s", operation, status, body, exc)

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
        },
    )
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        _log_request_failure("translation", exc)
        raise
    translated = response.json().get("translated_text", "").strip()
    if not translated:
        raise ValueError("Sarvam returned empty translated text")
    return translated


async def translate_texts(texts: list[str], lang: str) -> list[str] | None:
    if not settings.SARVAM_API_KEY:
        return None
    if lang == "en-IN":
        return texts

    now = time.monotonic()
    results: list[str | None] = [None] * len(texts)
    pending: dict[str, list[int]] = {}
    for index, text in enumerate(texts):
        key = (lang, text)
        cached = _translation_cache.get(key)
        if cached and now - cached[0] < _TRANSLATION_CACHE_TTL:
            results[index] = cached[1]
        else:
            pending.setdefault(text, []).append(index)

    if pending:
        semaphore = asyncio.Semaphore(4)
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                async def translate_one(text: str) -> tuple[str, str]:
                    async with semaphore:
                        return text, await translate_text(client, text, lang)

                translations = await asyncio.gather(*(translate_one(text) for text in pending))
        except (httpx.HTTPError, ValueError) as exc:
            _log_request_failure("translation batch", exc)
            return None

        translated_at = time.monotonic()
        for original, translated in translations:
            _translation_cache[(lang, original)] = (translated_at, translated)
            for index in pending[original]:
                results[index] = translated

    if any(text is None for text in results):
        return None
    return [text for text in results if text is not None]


async def text_to_speech(text: str, lang: str = "hi-IN") -> bytes | None:
    cache_key = _tts_cache_key(text, lang)
    cached = _tts_cache.get(cache_key)
    if cached is not None:
        _tts_cache.move_to_end(cache_key)
        return cached
    if not settings.SARVAM_API_KEY:
        return None

    response: httpx.Response | None = None
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            spoken_text = text
            if lang != "en-IN" and not is_in_target_script(text, lang):
                logger.warning("Sarvam TTS translating text on the fly for language=%s", lang)
                spoken_text = await translate_text(client, text, lang)
            tts_response = await client.post(
                SARVAM_TTS_URL,
                headers={"api-subscription-key": settings.SARVAM_API_KEY},
                json={"text": spoken_text, "language_code": lang, "model": "bulbul:v3"},
            )
            response = tts_response
            tts_response.raise_for_status()
            audios = tts_response.json().get("audios")
            if not isinstance(audios, list) or not audios or not isinstance(audios[0], str):
                raise ValueError("Sarvam returned no audio")

            encoded_audio = audios[0].split(",base64,", 1)[-1]
            audio = base64.b64decode(encoded_audio, validate=True)
            _tts_cache[cache_key] = audio
            _tts_cache.move_to_end(cache_key)
            if len(_tts_cache) > _TTS_CACHE_SIZE:
                _tts_cache.popitem(last=False)
            return audio
    except httpx.HTTPStatusError as exc:
        _log_request_failure("TTS request", exc, response)
        body = response.text.lower() if response is not None else ""
        if exc.response.status_code == 413 or (
            exc.response.status_code == 400
            and any(term in body for term in ("length", "too long", "maximum", "characters", "payload"))
        ):
            raise TtsTextTooLongError("Sarvam rejected TTS text length.") from exc
        return None
    except (httpx.HTTPError, ValueError, binascii.Error) as exc:
        _log_request_failure("TTS request", exc, response)
        return None

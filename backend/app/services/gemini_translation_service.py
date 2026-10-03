"""Gemini-backed translation for user-facing API response fields."""
from __future__ import annotations

import asyncio
import copy
from functools import lru_cache
import logging
from typing import Any

from pydantic import BaseModel

from ..config import settings

log = logging.getLogger("khetsetu.gemini_translation")

LANGUAGE_NAMES = {
    "en": "English",
    "hi": "Hindi",
    "kn": "Kannada",
    "te": "Telugu",
    "ta": "Tamil",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
    "or": "Odia",
}

_SKIP_KEYS = {
    "status", "class_name", "mode", "format", "source", "explanation_source",
    "client_scan_id", "language", "target_language", "fetched_at", "date",
}
_PLAIN_TRANSLATABLE_KEYS = {"crop", "disease", "unit", "variety", "summary", "text", "title", "body"}


class TranslationUnavailableError(RuntimeError):
    """Raised when a requested non-English response cannot be translated."""


class TranslationResult(BaseModel):
    translated_text: str


_SYSTEM_INSTRUCTION = (
    "You translate user-facing text for KhetSetu, a smart farming application. "
    "Return only the requested native script. Use natural regional agricultural "
    "terms, not word-for-word transliteration. Preserve KhetSetu, crop and disease "
    "meaning, numbers, units, currency symbols such as ₹, and safety instructions. "
    "Do not add facts, diagnosis, pesticide dosage, or commentary."
)


def is_available() -> bool:
    return bool(settings.GEMINI_API_KEY)


@lru_cache(maxsize=1)
def _client():
    from google import genai

    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _generate(text: str, target_lang: str) -> str:
    from google.genai import types

    language_name = LANGUAGE_NAMES.get(target_lang, target_lang)
    response = _client().models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=(
            f"Translate this English agricultural/UI text into {language_name} "
            f"({target_lang}) using its official native script.\n\n{text}"
        ),
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            temperature=0.15,
            response_mime_type="application/json",
            response_schema=TranslationResult,
        ),
    )
    parsed = response.parsed
    if isinstance(parsed, TranslationResult):
        translated = parsed.translated_text.strip()
    else:
        translated = TranslationResult.model_validate_json(response.text).translated_text.strip()
    if not translated:
        raise ValueError("Gemini returned an empty translation")
    return translated


async def translate_text(text: str, target_lang: str) -> str:
    """Translate one English string into the requested native language."""
    if not text.strip() or target_lang == "en":
        return text
    if target_lang not in LANGUAGE_NAMES:
        raise ValueError(f"Unsupported target language: {target_lang}")
    if not is_available():
        raise RuntimeError("GEMINI_API_KEY is not configured")
    return await asyncio.to_thread(_generate, text, target_lang)


async def _translate_unique(texts: list[str], target_lang: str) -> dict[str, str]:
    unique = list(dict.fromkeys(text for text in texts if text.strip()))
    if not unique:
        return {}
    semaphore = asyncio.Semaphore(4)

    async def one(text: str) -> tuple[str, str]:
        async with semaphore:
            return text, await translate_text(text, target_lang)

    pairs = await asyncio.gather(*(one(text) for text in unique))
    return dict(pairs)


def _collect_localized_strings(value: Any, target_lang: str, output: list[str]) -> None:
    if isinstance(value, list):
        for item in value:
            _collect_localized_strings(item, target_lang, output)
        return
    if not isinstance(value, dict):
        return
    if isinstance(value.get("en"), str) and target_lang not in value:
        output.append(value["en"])
    elif isinstance(value.get("en"), list) and target_lang not in value:
        output.extend(item for item in value["en"] if isinstance(item, str))
    for key, item in value.items():
        if key not in {"en", target_lang}:
            _collect_localized_strings(item, target_lang, output)


def _fill_localized_strings(value: Any, target_lang: str, translations: dict[str, str]) -> None:
    if isinstance(value, list):
        for item in value:
            _fill_localized_strings(item, target_lang, translations)
        return
    if not isinstance(value, dict):
        return
    if isinstance(value.get("en"), str) and target_lang not in value:
        value[target_lang] = translations[value["en"]]
    elif isinstance(value.get("en"), list) and target_lang not in value:
        value[target_lang] = [translations[item] if isinstance(item, str) else item for item in value["en"]]
    for key, item in value.items():
        if key not in {"en", target_lang}:
            _fill_localized_strings(item, target_lang, translations)


def _collect_plain_strings(value: Any, output: list[str], key: str = "") -> None:
    if isinstance(value, list):
        for item in value:
            _collect_plain_strings(item, output, key)
    elif isinstance(value, dict):
        for child_key, item in value.items():
            if child_key not in _SKIP_KEYS:
                _collect_plain_strings(item, output, child_key)
    elif isinstance(value, str) and key in _PLAIN_TRANSLATABLE_KEYS:
        output.append(value)


def _fill_plain_strings(value: Any, translations: dict[str, str], key: str = "") -> None:
    if isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, str) and key in _PLAIN_TRANSLATABLE_KEYS:
                value[index] = translations.get(item, item)
            else:
                _fill_plain_strings(item, translations, key)
    elif isinstance(value, dict):
        for child_key, item in value.items():
            if child_key not in _SKIP_KEYS:
                if isinstance(item, str) and child_key in _PLAIN_TRANSLATABLE_KEYS:
                    value[child_key] = translations.get(item, item)
                else:
                    _fill_plain_strings(item, translations, child_key)


async def translate_payload(payload: dict[str, Any], target_lang: str) -> dict[str, Any]:
    """Add target-language values to a JSON response without changing metadata."""
    if target_lang == "en":
        return payload
    translated = copy.deepcopy(payload)
    localized_texts: list[str] = []
    _collect_localized_strings(translated, target_lang, localized_texts)
    plain_texts: list[str] = []
    _collect_plain_strings(translated, plain_texts)
    try:
        dictionary = await _translate_unique(localized_texts + plain_texts, target_lang)
    except Exception as exc:  # noqa: BLE001
        log.warning("Gemini translation failed for %s: %s", target_lang, exc)
        return payload
    _fill_localized_strings(translated, target_lang, dictionary)
    _fill_plain_strings(translated, dictionary)
    return translated

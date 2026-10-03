"""Sarvam-backed English-to-Indic translation with persistent SQLite caching."""
from __future__ import annotations

import asyncio
import copy
import hashlib
import logging
import re
from typing import Any

import httpx
from sqlalchemy.exc import SQLAlchemyError

from ..config import settings
from ..database import SessionLocal, TranslationCache

log = logging.getLogger("khetsetu.translate")
SARVAM_TRANSLATE_URL = "https://api.sarvam.ai/translate"
LANGUAGE_CODES = {
    "en": "en-IN", "hi": "hi-IN", "kn": "kn-IN", "ta": "ta-IN",
    "te": "te-IN", "mr": "mr-IN", "bn": "bn-IN",
}
_LANGUAGE_ALIASES = {code: short for short, code in LANGUAGE_CODES.items()}
_LANGUAGE_KEYS = set(LANGUAGE_CODES) | set(LANGUAGE_CODES.values())
_MAX_CHUNK_CHARS = 900


def _chunk_text(text: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """Split on sentence boundaries, then words if a sentence is oversized."""
    sentences = re.split(r"(?<=[.!?।])\s+", text.strip())
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        words = sentence.split()
        fragments: list[str] = []
        fragment = ""
        for word in words:
            if len(word) > max_chars:
                if fragment:
                    fragments.append(fragment)
                    fragment = ""
                fragments.extend(word[index:index + max_chars] for index in range(0, len(word), max_chars))
            elif len(fragment) + len(word) + bool(fragment) <= max_chars:
                fragment = f"{fragment} {word}".strip()
            else:
                fragments.append(fragment)
                fragment = word
        if fragment:
            fragments.append(fragment)

        for part in fragments:
            if current and len(current) + len(part) + 1 > max_chars:
                chunks.append(current)
                current = part
            else:
                current = f"{current} {part}".strip()
    if current:
        chunks.append(current)
    return chunks


def _cache_key(text: str, language: str) -> tuple[str, str]:
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), language


def _read_cache(text: str, language: str) -> str | None:
    text_hash, language = _cache_key(text, language)
    session = SessionLocal()
    try:
        row = session.get(TranslationCache, (text_hash, language))
        return row.translated_text if row else None
    except SQLAlchemyError:
        log.exception("Could not read translation cache for %s", text_hash)
        return None
    finally:
        session.close()


def _write_cache(text: str, language: str, translated: str) -> None:
    text_hash, language = _cache_key(text, language)
    session = SessionLocal()
    try:
        row = session.get(TranslationCache, (text_hash, language))
        if row:
            row.translated_text = translated
        else:
            session.add(TranslationCache(text_hash=text_hash, language=language, translated_text=translated))
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        log.exception("Could not write translation cache for %s", text_hash)
    finally:
        session.close()


async def _request_chunk(client: httpx.AsyncClient, text: str, target_code: str) -> str:
    response = await client.post(
        SARVAM_TRANSLATE_URL,
        headers={"api-subscription-key": settings.SARVAM_API_KEY},
        json={
            "input": text,
            "source_language_code": "en-IN",
            "target_language_code": target_code,
            "model": "sarvam-translate:v1",
            "output_script": "fully-native",
        },
    )
    response.raise_for_status()
    translated = response.json().get("translated_text", "").strip()
    if not translated:
        raise ValueError("Sarvam returned empty translated text")
    return translated


async def translate_text(text: str, target_lang: str) -> str:
    """Translate English text, returning the original English on provider failure."""
    if not text or not text.strip() or target_lang in ("en", "en-IN"):
        return text
    language = _LANGUAGE_ALIASES.get(target_lang, target_lang)
    target_code = LANGUAGE_CODES.get(language)
    if not target_code:
        raise ValueError(f"Unsupported target language: {target_lang}")
    if not settings.SARVAM_API_KEY:
        log.warning("Sarvam translation unavailable: SARVAM_API_KEY is not configured")
        return text

    cached = _read_cache(text, language)
    if cached is not None:
        return cached

    chunks = _chunk_text(text)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            translated_chunks = []
            for chunk in chunks:
                for attempt in range(2):
                    try:
                        translated_chunks.append(await _request_chunk(client, chunk, target_code))
                        break
                    except Exception:
                        if attempt == 1:
                            raise
            translated = " ".join(translated_chunks).strip()
        if not translated:
            raise ValueError("Sarvam returned empty translated text")
    except Exception:
        log.exception("Sarvam translation failed for language %s; returning English source", language)
        return text

    _write_cache(text, language, translated)
    return translated


async def translate_list(items: list[str], lang: str) -> list[str]:
    """Translate string items concurrently while preserving order."""
    semaphore = asyncio.Semaphore(4)

    async def translate_one(item: str) -> str:
        if not isinstance(item, str):
            return item
        async with semaphore:
            return await translate_text(item, lang)

    return list(await asyncio.gather(*(translate_one(item) for item in items)))


async def translate_dict(value: dict[str, Any], lang: str) -> dict[str, Any]:
    """Fill missing locale values in nested bilingual leaves; mapping keys stay intact."""
    target = _LANGUAGE_ALIASES.get(lang, lang)
    output = copy.deepcopy(value)
    pending: list[str] = []
    locations: list[tuple[dict[str, Any], str, list[int] | None]] = []

    def collect(node: Any) -> None:
        if isinstance(node, dict):
            english = node.get("en")
            if target not in node and isinstance(english, str):
                pending.append(english)
                locations.append((node, target, None))
            elif target not in node and isinstance(english, list):
                indices = [index for index, item in enumerate(english) if isinstance(item, str)]
                pending.extend(english[index] for index in indices)
                locations.append((node, target, indices))
            for key, child in node.items():
                if key not in _LANGUAGE_KEYS:
                    collect(child)
        elif isinstance(node, list):
            for child in node:
                collect(child)

    collect(output)
    translations = await translate_list(pending, target)
    offset = 0
    for node, locale, indices in locations:
        if indices is None:
            node[locale] = translations[offset]
            offset += 1
            continue
        source = node["en"]
        localized = list(source)
        for index in indices:
            localized[index] = translations[offset]
            offset += 1
        node[locale] = localized
    return output
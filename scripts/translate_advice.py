#!/usr/bin/env python3
"""Create resumable Sarvam translations for canonical disease advice."""

import argparse
import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DATA = ROOT / "data" / "advice_i18n"
sys.path.insert(0, str(BACKEND))

from app.config import settings
from app.disease_info import get_guidance
from app.services.sarvam_service import translate_text

LANGUAGES = {
    "kn": "kn-IN",
    "ta": "ta-IN",
    "te": "te-IN",
    "mr": "mr-IN",
    "bn": "bn-IN",
}
FIELDS = (
    "what_we_found",
    "what_is_it",
    "why_it_happened",
    "possible_cause",
    "symptoms",
    "immediate_actions",
    "basic_care",
    "management",
    "prevention",
    "avoid",
    "when_to_seek_help",
    "consult_expert_when",
    "severity",
    "spread_risk",
    "source_note",
)
CACHE_FILE = DATA / ".cache.json"
GLOSSARY_FILE = DATA / "glossary.json"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
LANGUAGE_NAMES = {
    "kn": "Kannada",
    "ta": "Tamil",
    "te": "Telugu",
    "mr": "Marathi",
    "bn": "Bengali",
}


def _read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _english(value: Any) -> Any:
    return value.get("en", "") if isinstance(value, dict) else value


def _glossary_override(glossary: dict, text: str, lang: str) -> str | None:
    entry = glossary.get(text)
    if isinstance(entry, str):
        return entry
    if isinstance(entry, dict):
        override = entry.get(lang) or entry.get(LANGUAGES[lang])
        if isinstance(override, str):
            return override
    return None


def _cache_key(text: str, lang: str) -> str:
    return json.dumps([text, lang], ensure_ascii=False, separators=(",", ":"))


def _glossary_prompt_terms(glossary: dict, lang: str) -> dict[str, str]:
    terms = {}
    for english, entry in glossary.items():
        if isinstance(entry, dict):
            translated = entry.get(lang) or entry.get(LANGUAGES[lang])
            if isinstance(translated, str) and translated:
                terms[english] = translated
    return terms


def _validate_translation(original: dict, translated: Any) -> dict:
    if not isinstance(translated, dict) or translated.keys() != original.keys():
        raise ValueError("Gemini returned different JSON keys.")
    for key, source in original.items():
        value = translated[key]
        expected_length = len(source) if isinstance(source, list) else None
        if expected_length is not None:
            if not isinstance(value, list) or len(value) != expected_length:
                raise ValueError(f"Gemini returned a different list length for {key}.")
            if any(not isinstance(item, str) or not item.strip() for item in value):
                raise ValueError(f"Gemini returned an empty or invalid string in {key}.")
        elif not isinstance(value, str) or not value.strip():
            raise ValueError(f"Gemini returned an empty or invalid string for {key}.")
    return translated


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


class GeminiTranslator:
    def __init__(self, client, model: str, api_key: str):
        self.client = client
        self.model = model
        self.api_key = api_key
        self.last_request_at: float | None = None

    async def _request(self, lang: str, source: dict, glossary_terms: dict[str, str]) -> Any:
        prompt = (
            f"Translate the JSON values into {LANGUAGE_NAMES[lang]} for farmers with limited literacy, "
            "using simple everyday words. Keep numbers, units, and percentages unchanged. Keep "
            "scientific and pathogen names in Latin script. Do not add or remove information. "
            "For crop and disease names, use the supplied glossary translations exactly. "
            "Preserve all keys, value types, and list lengths. Output only valid JSON.\n"
            f"Glossary terms: {json.dumps(glossary_terms, ensure_ascii=False)}\n"
            f"JSON to translate: {json.dumps(source, ensure_ascii=False)}"
        )
        url = GEMINI_API_URL.format(model=quote(self.model, safe="-_."))
        for attempt in range(5):
            if self.last_request_at is not None:
                elapsed = time.monotonic() - self.last_request_at
                if elapsed < 5:
                    await asyncio.sleep(5 - elapsed)
            response = await self.client.post(
                url,
                headers={"x-goog-api-key": self.api_key},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"responseMimeType": "application/json"},
                },
            )
            self.last_request_at = time.monotonic()
            if response.status_code == 429:
                if attempt == 4:
                    raise RuntimeError("Gemini rate limit persisted after 5 attempts; stopping.")
                retry_after = _retry_after_seconds(response.headers.get("Retry-After"))
                await asyncio.sleep(retry_after if retry_after is not None else 2**attempt)
                continue
            response.raise_for_status()
            payload = response.json()
            try:
                return payload["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError) as exc:
                raise ValueError("Gemini response did not contain translated JSON text.") from exc
        raise RuntimeError("Gemini request attempts exhausted.")

    async def translate_object(
        self,
        source: dict,
        lang: str,
        glossary_terms: dict[str, str],
    ) -> dict:
        last_error = None
        for attempt in range(2):
            try:
                response_text = await self._request(
                    lang,
                    source,
                    glossary_terms,
                )
                translated = json.loads(response_text)
                return _validate_translation(source, translated)
            except (ValueError, KeyError, TypeError, httpx.HTTPError) as exc:
                last_error = exc
                if attempt == 0:
                    continue
        raise ValueError(f"Gemini returned invalid translations twice: {last_error}")


async def _translate(
    client,
    text: str,
    lang: str,
    cache: dict[str, str],
    glossary: dict,
    *,
    is_name: bool = False,
) -> str:
    if not text:
        return ""
    if is_name:
        override = _glossary_override(glossary, text, lang)
        if override is not None:
            return override

    key = _cache_key(text, lang)
    if key in cache:
        return cache[key]

    translated = await translate_text(client, text, LANGUAGES[lang])
    if not isinstance(translated, str) or not translated:
        raise ValueError(f"Sarvam returned an empty translation for {lang}.")
    cache[key] = translated
    _write_json(CACHE_FILE, cache)
    await asyncio.sleep(0.3)
    return translated


async def _translate_value(
    value: Any,
    lang: str,
    cache: dict,
    glossary: dict,
    client,
) -> str | list[str]:
    english = _english(value)
    if isinstance(english, list):
        translated = []
        for item in english:
            if not isinstance(item, str):
                raise ValueError(f"Expected English list item to be text, got {type(item).__name__}.")
            translated.append(await _translate(client, item, lang, cache, glossary))
        return translated
    if isinstance(english, str):
        return await _translate(client, english, lang, cache, glossary)
    raise ValueError(f"Expected English advice to be text or a list, got {type(english).__name__}.")


def _class_source(profile: dict) -> dict[str, str | list[str]]:
    source = {
        "crop": _english(profile["crop"]),
        "disease": _english(profile["disease"]),
    }
    source.update({field: _english(profile[field]) for field in FIELDS})
    for key, value in source.items():
        if isinstance(value, str):
            continue
        if isinstance(value, list) and all(isinstance(item, str) for item in value):
            continue
        raise ValueError(f"Expected English value for {key} to be text or a list of text.")
    return source


def _source_name(source: dict[str, str | list[str]], key: str) -> str:
    value = source[key]
    if not isinstance(value, str):
        raise ValueError(f"Expected {key} to be text.")
    return value


def _cached_class(source: dict, lang: str, cache: dict[str, str]) -> dict:
    translated = {}
    for key, value in source.items():
        if isinstance(value, list):
            translated[key] = [cache.get(_cache_key(item, lang)) for item in value]
        else:
            translated[key] = cache.get(_cache_key(value, lang))
    return translated


def _update_cache(source: dict, translated: dict, lang: str, cache: dict[str, str]) -> None:
    for key, value in source.items():
        translated_value = translated[key]
        if isinstance(value, list):
            for original, result in zip(value, translated_value):
                cache.setdefault(_cache_key(original, lang), result)
        else:
            cache.setdefault(_cache_key(value, lang), translated_value)


def _prefer_cache(source: dict, translated: dict, lang: str, cache: dict[str, str]) -> dict:
    result = {}
    for key, value in source.items():
        if isinstance(value, list):
            result[key] = [
                cache.get(_cache_key(original, lang), generated)
                for original, generated in zip(value, translated[key])
            ]
        else:
            result[key] = cache.get(_cache_key(value, lang), translated[key])
    return result


async def _translate_gemini_class(
    translator: GeminiTranslator,
    source: dict,
    lang: str,
    cache: dict[str, str],
    glossary: dict,
) -> dict:
    glossary_terms = _glossary_prompt_terms(glossary, lang)
    cached = _cached_class(source, lang, cache)
    if all(
        all(value is not None for value in cached[key]) if isinstance(cached[key], list)
        else cached[key] is not None
        for key in source
    ):
        translated = cached
    else:
        try:
            generated = await translator.translate_object(source, lang, glossary_terms)
        except (ValueError, json.JSONDecodeError, httpx.HTTPError):
            generated = {}
            for key, value in source.items():
                cached_value = cached[key]
                if (
                    all(item is not None for item in cached_value)
                    if isinstance(cached_value, list)
                    else cached_value is not None
                ):
                    generated[key] = cached_value
                    continue
                single = {key: value}
                generated.update(await translator.translate_object(single, lang, glossary_terms))
        translated = _prefer_cache(source, generated, lang, cache)

    for name in ("crop", "disease"):
        override = _glossary_override(glossary, source[name], lang)
        if override is not None:
            translated[name] = override
            cache[_cache_key(source[name], lang)] = override
    _update_cache(source, translated, lang, cache)
    return translated


async def _run(
    languages: list[str],
    engine: str,
    api_key: str | None,
    gemini_model: str | None,
) -> None:
    if engine == "gemini":
        if not api_key or not gemini_model:
            raise ValueError("Gemini translation requires an API key and model name.")
    elif not api_key:
        raise ValueError("SARVAM_API_KEY is empty.")
    else:
        settings.SARVAM_API_KEY = api_key
    class_config = _read_json(ROOT / "model" / "class_config.json", {})
    canonical_classes = [
        item["class_name"] for item in class_config.get("classes", [])
    ]
    if len(canonical_classes) != 8:
        raise ValueError("Expected exactly 8 canonical classes in model/class_config.json.")

    glossary = _read_json(GLOSSARY_FILE, {})
    cache = _read_json(CACHE_FILE, {})
    if not isinstance(glossary, dict) or not isinstance(cache, dict):
        raise ValueError("glossary.json and .cache.json must contain JSON objects.")

    for lang in languages:
        draft_path = DATA / "drafts" / f"{lang}.json"
        existing = _read_json(draft_path, {"status": "draft", "classes": {}})
        if existing.get("status") == "reviewed":
            raise ValueError(f"Refusing to overwrite reviewed draft: {draft_path}")
        translations = existing.get("classes", {})
        if not isinstance(translations, dict):
            raise ValueError(f"Draft classes must be an object: {draft_path}")

        async with httpx.AsyncClient(timeout=60) as client:
            if engine == "gemini":
                if api_key is None or gemini_model is None:
                    raise RuntimeError("Gemini translation credentials were not configured.")
                gemini = GeminiTranslator(client, gemini_model, api_key)
            else:
                gemini = None
            for index, class_name in enumerate(canonical_classes, start=1):
                profile = get_guidance(class_name)
                source = _class_source(profile)
                if engine == "gemini":
                    if gemini is None:
                        raise RuntimeError("Gemini translator was not configured.")
                    translated_class = await _translate_gemini_class(
                        gemini, source, lang, cache, glossary
                    )
                else:
                    translated_class = {
                        "crop": await _translate(
                            client, _source_name(source, "crop"), lang, cache, glossary, is_name=True
                        ),
                        "disease": await _translate(
                            client, _source_name(source, "disease"), lang, cache, glossary, is_name=True
                        ),
                        **{
                            field: await _translate_value(
                                profile[field], lang, cache, glossary, client
                            )
                            for field in FIELDS
                        },
                    }
                translations[class_name] = {
                    "crop": translated_class["crop"],
                    "disease": translated_class["disease"],
                    "fields": {field: translated_class[field] for field in FIELDS},
                }
                _write_json(CACHE_FILE, cache)
                _write_json(draft_path, {"status": "draft", "classes": translations})
                print(f"[{lang}] {index}/{len(canonical_classes)} {class_name}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--lang",
        action="append",
        choices=tuple(LANGUAGES),
        dest="languages",
        help="language to generate; repeat to select multiple (default: all five)",
    )
    parser.add_argument(
        "--engine",
        choices=("sarvam", "gemini"),
        default="sarvam",
        help="translation provider (default: sarvam)",
    )
    args = parser.parse_args()

    backend_env = dotenv_values(BACKEND / ".env")
    if args.engine == "gemini":
        api_key = backend_env.get("TRANSLATE_GEMINI_API_KEY")
        model = backend_env.get("GEMINI_TRANSLATE_MODEL")
        if not isinstance(api_key, str) or not api_key.strip() or not isinstance(model, str) or not model.strip():
            raise SystemExit(
                "Gemini translation requires TRANSLATE_GEMINI_API_KEY and "
                "GEMINI_TRANSLATE_MODEL in backend/.env."
            )
    else:
        api_key = os.environ.get("SARVAM_API_KEY") or backend_env.get("SARVAM_API_KEY")
        if not api_key:
            raise SystemExit(
                "SARVAM_API_KEY is empty. Configure it in backend/.env or the environment."
            )
        model = None
    try:
        asyncio.run(_run(args.languages or list(LANGUAGES), args.engine, api_key, model))
    except Exception as exc:
        raise SystemExit(f"Translation stopped: {exc}") from exc


if __name__ == "__main__":
    main()

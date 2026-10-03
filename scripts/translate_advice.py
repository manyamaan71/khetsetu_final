#!/usr/bin/env python3
"""Create unreviewed Sarvam translations of canonical disease advice."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings
from app.disease_info import get_guidance
from app.services.sarvam_service import translate_text

LANGUAGES = {"kn": "kn-IN", "ta": "ta-IN", "te": "te-IN", "mr": "mr-IN", "bn": "bn-IN"}
FIELDS = (
    "what_we_found", "what_is_it", "why_it_happened", "possible_cause",
    "symptoms", "immediate_actions", "basic_care", "management", "prevention",
    "avoid", "when_to_seek_help", "consult_expert_when", "severity", "spread_risk",
    "source_note",
)
CACHE_FILE = ROOT / "data" / "advice_i18n" / ".cache.json"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def english_value(value):
    if isinstance(value, dict):
        return value.get("en", "")
    return value


async def run(languages: list[str]) -> None:
    if not settings.SARVAM_API_KEY:
        raise SystemExit("SARVAM_API_KEY is empty. Set it before running this command.")

    classes = read_json(ROOT / "model" / "class_config.json")["classes"]
    canonical_classes = [entry["class_name"] for entry in classes]
    glossary = read_json(ROOT / "data" / "advice_i18n" / "glossary.json")
    cache = read_json(CACHE_FILE) if CACHE_FILE.exists() else {}
    async with httpx.AsyncClient(timeout=30) as client:
        for lang in languages:
            translations: dict[str, dict] = {}
            for class_name in canonical_classes:
                profile = get_guidance(class_name)
                crop, disease = profile["crop"], profile["disease"]
                fields = {field: english_value(profile[field]) for field in FIELDS}

                async def translated(text: str, is_name: bool = False) -> str:
                    if is_name:
                        override = glossary.get(text, {}).get(lang)
                        if isinstance(override, str) and override:
                            return override
                    cache_key = f"{lang}\t{text}"
                    if cache_key in cache:
                        return cache[cache_key]
                    value = await translate_text(client, text, LANGUAGES[lang])
                    cache[cache_key] = value
                    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
                    await asyncio.sleep(0.2)
                    return value

                translated_fields = {}
                for field, value in fields.items():
                    if isinstance(value, list):
                        translated_fields[field] = [await translated(item) for item in value]
                    elif isinstance(value, str):
                        translated_fields[field] = await translated(value) if value else ""
                translations[class_name] = {
                    "crop": await translated(crop, is_name=True),
                    "disease": await translated(disease, is_name=True),
                    "fields": translated_fields,
                }
            output = {"status": "draft", "classes": translations}
            path = ROOT / "data" / "advice_i18n" / "drafts" / f"{lang}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lang", action="append", choices=LANGUAGES, dest="languages")
    args = parser.parse_args()
    asyncio.run(run(args.languages or list(LANGUAGES)))


if __name__ == "__main__":
    main()

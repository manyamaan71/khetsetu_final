"""Fill missing KhetSetu guidance and class-name translations via Sarvam."""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import init_db
from app.services.translate_service import LANGUAGE_CODES, translate_text

TARGET_LANGUAGES = ("kn", "ta", "te", "mr", "bn")
GLOSSARY: dict[str, dict[str, str]] = {
    "Corn": {"kn": "ಮೆಕ್ಕೆಜೋಳ", "ta": "மக்காச்சோளம்", "te": "మొక్కజొన్న", "mr": "मका", "bn": "ভুট্টা"},
    "Maize": {"kn": "ಮೆಕ್ಕೆಜೋಳ", "ta": "மக்காச்சோளம்", "te": "మొక్కజొన్న", "mr": "मका", "bn": "ভুট্টা"},
    "Tomato": {"kn": "ಟೊಮೆಟೊ", "ta": "தக்காளி", "te": "టమాటా", "mr": "टोमॅटो", "bn": "টমেটো"},
    "Potato": {"kn": "ಆಲೂಗಡ್ಡೆ", "ta": "உருளைக்கிழங்கு", "te": "బంగాళాదుంప", "mr": "बटाटा", "bn": "আলু"},
    "Common Rust": {"kn": "ಸಾಮಾನ್ಯ ತುಕ್ಕು ರೋಗ", "ta": "பொதுத் துரு நோய்", "te": "సాధారణ తుప్పు తెగులు", "mr": "सामान्य तांबेरा", "bn": "সাধারণ মরিচা রোগ"},
    "Early Blight": {"kn": "ಆರಂಭಿಕ ಅಂಗಮಾರಿ", "ta": "ஆரம்பகால கருகல் நோய்", "te": "ఎర్లీ బ్లైట్ తెగులు", "mr": "अर्ली ब्लाइट", "bn": "আর্লি ব্লাইট"},
    "Late Blight": {"kn": "ತಡ ಅಂಗಮಾರಿ", "ta": "தாமதக் கருகல் நோய்", "te": "లేట్ బ్లైట్ తెగులు", "mr": "लेट ब्लाइट", "bn": "লেট ব্লাইট"},
    "Leaf Mold": {"kn": "ಎಲೆ ಅಚ್ಚು ರೋಗ", "ta": "இலை அச்சு நோய்", "te": "ఆకు బూజు తెగులు", "mr": "पानावरील बुरशी", "bn": "পাতার ছাঁচ রোগ"},
    "Healthy": {"kn": "ಆರೋಗ್ಯಕರ", "ta": "ஆரோக்கியமான", "te": "ఆరోగ్యకరమైన", "mr": "निरोगी", "bn": "স্বাস্থ্যকর"},
}
_GLOSSARY_PATTERN = re.compile("|".join(re.escape(term) for term in sorted(GLOSSARY, key=len, reverse=True)), re.IGNORECASE)
Translator = Callable[[str, str], Awaitable[str]]


async def _translate_glossary_aware(text: str, lang: str, translator: Translator) -> str:
    substitutions: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        token = f"KSGLOSSARY{len(substitutions):03d}TOKEN"
        term = next(term for term in GLOSSARY if term.lower() == match.group(0).lower())
        substitutions[token] = GLOSSARY[term][lang]
        return token

    protected = _GLOSSARY_PATTERN.sub(replace, text)
    translated = await translator(protected, lang)
    for token, localized in substitutions.items():
        translated = translated.replace(token, localized)
    return translated


async def fill_guidance_translations(
    guidance_path: Path,
    class_config_path: Path,
    translator: Translator = translate_text,
) -> dict[str, int]:
    guidance = json.loads(guidance_path.read_text(encoding="utf-8"))
    additions = 0

    async def fill_node(node: Any) -> None:
        nonlocal additions
        if isinstance(node, dict):
            english = node.get("en")
            if isinstance(english, str):
                for lang in TARGET_LANGUAGES:
                    if lang not in node:
                        node[lang] = await _translate_glossary_aware(english, lang, translator)
                        additions += 1
            elif isinstance(english, list):
                for lang in TARGET_LANGUAGES:
                    if lang not in node:
                        node[lang] = [await _translate_glossary_aware(item, lang, translator) if isinstance(item, str) else item
                                      for item in english]
                        additions += sum(isinstance(item, str) for item in english)
            for key, child in node.items():
                if key not in LANGUAGE_CODES:
                    await fill_node(child)
        elif isinstance(node, list):
            for child in node:
                await fill_node(child)

    for entry in guidance.values():
        if not isinstance(entry, dict):
            continue
        crop = entry.get("crop")
        if isinstance(crop, str) and "crop_name" not in entry:
            entry["crop_name"] = {
                "en": crop,
                "hi": {"corn": "मक्का", "maize": "मक्का", "potato": "आलू", "tomato": "टमाटर"}.get(crop.lower(), crop),
            }
        await fill_node(entry)

    class_config = json.loads(class_config_path.read_text(encoding="utf-8"))
    guidance_by_class = {item.get("class_name"): item for item in guidance.values() if isinstance(item, dict)}
    for item in class_config.get("classes", []):
        source = guidance_by_class.get(item.get("class_name"), {})
        crop_map = source.get("crop_name", {})
        disease_map = source.get("condition", {})
        for lang in TARGET_LANGUAGES:
            crop_value = crop_map.get(lang) or await _translate_glossary_aware(item.get("crop", ""), lang, translator)
            disease_value = disease_map.get(lang) or await _translate_glossary_aware(item.get("disease", ""), lang, translator)
            if f"crop_{lang}" not in item:
                item[f"crop_{lang}"] = crop_value
                additions += 1
            if f"disease_{lang}" not in item:
                item[f"disease_{lang}"] = disease_value
                additions += 1

    for path, payload in ((guidance_path, guidance), (class_config_path, class_config)):
        backup = path.with_suffix(path.suffix + ".bak")
        if not backup.exists():
            shutil.copy2(path, backup)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {"guidance_entries": len(guidance), "class_names": len(class_config.get("classes", [])), "translations_added": additions}


async def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--guidance", type=Path, default=ROOT / "data" / "guidance.json")
    parser.add_argument("--class-config", type=Path, default=ROOT / "model" / "class_config.json")
    args = parser.parse_args()
    init_db()
    summary = await fill_guidance_translations(args.guidance, args.class_config)
    print("Translation fill complete:")
    for key, value in summary.items():
        print(f"  {key.replace('_', ' ')}: {value}")


if __name__ == "__main__":
    asyncio.run(_main())
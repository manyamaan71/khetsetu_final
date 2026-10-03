import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from app.services import translate_service
from scripts.fill_guidance_translations import TARGET_LANGUAGES, fill_guidance_translations


def test_chunking_respects_limit_and_sentence_boundaries():
    text = "First sentence. " + ("long phrase " * 100) + ". Final sentence!"
    chunks = translate_service._chunk_text(text)

    assert len(chunks) > 1
    assert all(len(chunk) <= 900 for chunk in chunks)
    assert chunks[0] == "First sentence."
    assert chunks[-1].endswith("Final sentence!")


@pytest.mark.parametrize("language", ["en", "en-IN"])
def test_english_and_empty_text_skip_provider(monkeypatch, language):
    request = AsyncMock(side_effect=AssertionError("provider must not be called"))
    monkeypatch.setattr(translate_service, "_request_chunk", request)

    assert asyncio.run(translate_service.translate_text("Keep this text.", language)) == "Keep this text."
    assert asyncio.run(translate_service.translate_text("  ", "kn")) == "  "
    request.assert_not_called()


def test_translate_dict_localizes_values_and_preserves_keys(monkeypatch):
    payload = {"what_is_it": {"en": "English value", "hi": "Hindi value"},
               "symptoms": {"en": ["One", "Two"]}}
    translated_values = AsyncMock(return_value=["ಸ್ಥಳೀಯ ಮೌಲ್ಯ", "ಒಂದು", "ಎರಡು"])
    monkeypatch.setattr(translate_service, "translate_list", translated_values)

    localized = asyncio.run(translate_service.translate_dict(payload, "kn"))

    assert localized["what_is_it"]["kn"] == "ಸ್ಥಳೀಯ ಮೌಲ್ಯ"
    assert localized["symptoms"]["kn"] == ["ಒಂದು", "ಎರಡು"]
    assert set(localized) == set(payload)
    assert "kn" not in payload["what_is_it"]
    assert translated_values.await_args.args == (["English value", "One", "Two"], "kn")


def test_provider_failure_retries_once_then_returns_english(monkeypatch):
    monkeypatch.setattr(translate_service.settings, "SARVAM_API_KEY", "test-key")
    monkeypatch.setattr(translate_service, "_read_cache", lambda *_: None)
    monkeypatch.setattr(translate_service, "_write_cache", lambda *args: None)
    request = AsyncMock(side_effect=RuntimeError("mock provider error"))
    monkeypatch.setattr(translate_service, "_request_chunk", request)

    result = asyncio.run(translate_service.translate_text("English source.", "ta"))

    assert result == "English source."
    assert request.await_count == 2


def _assert_guidance_leaves_complete(value):
    if isinstance(value, list):
        for item in value:
            _assert_guidance_leaves_complete(item)
    elif isinstance(value, dict):
        if isinstance(value.get("en"), str):
            assert all(language in value for language in ("en", "hi", *TARGET_LANGUAGES))
        elif isinstance(value.get("en"), list):
            assert all(language in value for language in ("en", "hi", *TARGET_LANGUAGES))
        for key, child in value.items():
            if key not in {"en", "hi", *TARGET_LANGUAGES}:
                _assert_guidance_leaves_complete(child)


def test_fill_script_translates_every_guidance_leaf_and_class_names(tmp_path):
    guidance_path = tmp_path / "guidance.json"
    class_config_path = tmp_path / "class_config.json"
    guidance_path.write_text(json.dumps({
        "Tomato___Leaf_Mold": {
            "class_name": "Tomato___Leaf_Mold", "crop": "Tomato",
            "condition": {"en": "Leaf Mold", "hi": "लीफ मोल्ड"},
            "symptoms": {"en": ["Visible leaves."], "hi": ["दिखने वाले पत्ते।"]},
        },
    }), encoding="utf-8")
    class_config_path.write_text(json.dumps({"classes": [{
        "class_name": "Tomato___Leaf_Mold", "crop": "Tomato", "crop_hi": "टमाटर",
        "disease": "Leaf Mold", "disease_hi": "लीफ मोल्ड",
    }]}), encoding="utf-8")

    async def fake_translate(text, language):
        return f"{language}:{text}"

    summary = asyncio.run(fill_guidance_translations(guidance_path, class_config_path, fake_translate))
    guidance = json.loads(guidance_path.read_text(encoding="utf-8"))
    class_config = json.loads(class_config_path.read_text(encoding="utf-8"))

    _assert_guidance_leaves_complete(guidance)
    assert all(f"crop_{language}" in class_config["classes"][0] for language in TARGET_LANGUAGES)
    assert all(f"disease_{language}" in class_config["classes"][0] for language in TARGET_LANGUAGES)
    assert summary["translations_added"] > 0
    assert guidance_path.with_suffix(".json.bak").exists()
    assert class_config_path.with_suffix(".json.bak").exists()


def test_speech_language_codes_cover_all_requested_languages():
    from app.api.speech import LANGUAGE_CODES

    assert all(LANGUAGE_CODES[language] == f"{language}-IN" for language in ("en", "hi", *TARGET_LANGUAGES))
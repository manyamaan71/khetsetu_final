import json
from pathlib import Path

import pytest

from app.disease_info import _ADVICE_FIELDS, _advice_translations, get_guidance


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("language", ("ta", "te"))
def test_advice_overlay_matches_english_fields_and_list_lengths(monkeypatch, language):
    monkeypatch.setenv("ALLOW_DRAFT_TRANSLATIONS", "true")
    _advice_translations.cache_clear()
    class_config = json.loads(
        (ROOT / "model" / "class_config.json").read_text(encoding="utf-8")
    )
    draft = json.loads(
        (ROOT / "data" / "advice_i18n" / "drafts" / f"{language}.json").read_text(
            encoding="utf-8"
        )
    )
    assert draft["status"] == "draft"

    try:
        for item in class_config["classes"]:
            class_name = item["class_name"]
            translated_fields = draft["classes"][class_name]["fields"]
            assert set(translated_fields) == set(_ADVICE_FIELDS)
            profile = get_guidance(class_name)
            for field in _ADVICE_FIELDS:
                english = profile[field]["en"]
                translated = translated_fields[field]
                assert language in profile[field]
                assert isinstance(translated, type(english)), (class_name, field)
                if isinstance(english, list):
                    assert len(translated) == len(english), (class_name, field)
                if isinstance(translated, list):
                    assert all(isinstance(value, str) and value.strip() for value in translated)
                else:
                    assert translated.strip(), (class_name, field)
    finally:
        _advice_translations.cache_clear()

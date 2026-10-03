import asyncio

from app.services import gemini_translation_service as translator


def test_translate_payload_fills_target_language_without_translating_metadata(monkeypatch):
    async def fake_translate(text, target_lang):
        return f"{target_lang}:{text}"

    monkeypatch.setattr(translator, "translate_text", fake_translate)
    payload = {
        "status": "ok",
        "prediction": {"crop": "Corn", "disease": "Common Rust", "confidence": 0.91},
        "guidance": {
            "what_we_found": {"en": "The leaf looks healthy."},
            "immediate_actions": {"en": ["Monitor the field.", "Keep soil moist."]},
        },
    }

    result = asyncio.run(translator.translate_payload(payload, "kn"))

    assert result["status"] == "ok"
    assert result["prediction"]["confidence"] == 0.91
    assert result["prediction"]["crop"] == "kn:Corn"
    assert result["guidance"]["what_we_found"]["kn"] == "kn:The leaf looks healthy."
    assert result["guidance"]["immediate_actions"]["kn"] == [
        "kn:Monitor the field.",
        "kn:Keep soil moist.",
    ]


def test_translate_payload_keeps_english_payload_unchanged():
    payload = {"status": "ok", "message": {"en": "Ready"}}
    assert asyncio.run(translator.translate_payload(payload, "en")) is payload


def test_translate_payload_returns_raw_result_when_provider_fails(monkeypatch):
    async def failed_translate(text, target_lang):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(translator, "translate_text", failed_translate)
    payload = {
        "status": "ok",
        "guidance": {"what_we_found": {"en": "The leaf looks healthy."}},
    }

    assert asyncio.run(translator.translate_payload(payload, "kn")) == payload

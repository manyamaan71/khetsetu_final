from fastapi import FastAPI
from fastapi.testclient import TestClient
import base64
import json

import httpx

from app.api import speech
from app.services import sarvam_service


APP = FastAPI()
APP.include_router(speech.router, prefix="/api")


def test_sarvam_speech_route_returns_wav_binary_and_maps_locale(monkeypatch):
    calls = []
    audio_bytes = b"RIFF-test-wav"

    async def fake_synthesize(text, language):
        calls.append((text, language))
        return audio_bytes

    monkeypatch.setattr(speech, "synthesize_speech", fake_synthesize)

    with TestClient(APP) as client:
        response = client.post("/api/tts", json={"text": "Tomato leaf advice", "language": "kn"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.content == audio_bytes
    assert calls == [("Tomato leaf advice", "kn-IN")]


def test_sarvam_speech_route_falls_back_for_unsupported_locale(monkeypatch):
    with TestClient(APP) as client:
        response = client.post("/api/tts", json={"text": "hello", "language": "unsupported"})

    assert response.status_code == 422


def test_translation_route_returns_translated_texts_and_maps_locale(monkeypatch):
    calls = []

    async def fake_translate(texts, language):
        calls.append((texts, language))
        return ["ಟೊಮೇಟೊ", "ಆರಂಭಿಕ ರೋಗ"]

    monkeypatch.setattr(speech, "translate_texts", fake_translate)

    with TestClient(APP) as client:
        response = client.post("/api/translate", json={"texts": ["Tomato", "Early Blight"], "language": "kn"})

    assert response.status_code == 200
    assert response.json() == {"texts": ["ಟೊಮೇಟೊ", "ಆರಂಭಿಕ ರೋಗ"]}
    assert calls == [(["Tomato", "Early Blight"], "kn-IN")]


def test_translation_route_rejects_unsupported_language():
    with TestClient(APP) as client:
        response = client.post("/api/translate", json={"texts": ["Tomato"], "language": "xx"})

    assert response.status_code == 422


def test_translation_route_maps_all_supported_languages(monkeypatch):
    calls = []

    async def fake_translate(texts, language):
        calls.append(language)
        return texts

    monkeypatch.setattr(speech, "translate_texts", fake_translate)

    expected = {
        "en": "en-IN",
        "hi": "hi-IN",
        "kn": "kn-IN",
        "ta": "ta-IN",
        "te": "te-IN",
        "mr": "mr-IN",
        "bn": "bn-IN",
    }
    with TestClient(APP) as client:
        for language, locale in expected.items():
            response = client.post("/api/translate", json={"texts": ["Tomato"], "language": language})
            assert response.status_code == 200
            assert calls[-1] == locale


def test_sarvam_service_translates_then_returns_decoded_wav(monkeypatch):
    calls = []
    audio_bytes = b"RIFF-kannada-wav"

    def fake_sarvam(request):
        calls.append(request)
        if request.url == httpx.URL(sarvam_service.SARVAM_TRANSLATE_URL):
            return httpx.Response(200, json={"translated_text": "ಟೊಮೇಟೊ ಎಲೆ ಪರಿಶೀಲಿಸಿ"})
        return httpx.Response(200, json={"audios": [base64.b64encode(audio_bytes).decode()]})

    monkeypatch.setattr(sarvam_service.settings, "SARVAM_API_KEY", "test-key")
    original_async_client = httpx.AsyncClient
    monkeypatch.setattr(
        sarvam_service.httpx,
        "AsyncClient",
        lambda **kwargs: original_async_client(
            transport=httpx.MockTransport(fake_sarvam),
            **kwargs,
        ),
    )

    import asyncio
    result = asyncio.run(sarvam_service.text_to_speech("Tomato Early Blight. Inspect the leaves.", "kn-IN"))

    assert result == audio_bytes
    assert len(calls) == 2
    assert json.loads(calls[0].content) == {
        "input": "Tomato Early Blight. Inspect the leaves.",
        "source_language_code": "en-IN",
        "target_language_code": "kn-IN",
        "model": "sarvam-translate:v1",
    }
    assert json.loads(calls[1].content) == {
        "text": "ಟೊಮೇಟೊ ಎಲೆ ಪರಿಶೀಲಿಸಿ",
        "language_code": "kn-IN",
        "model": "bulbul:v3",
    }

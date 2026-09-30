from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import speech


APP = FastAPI()
APP.include_router(speech.router, prefix="/api")


def test_sarvam_speech_route_forwards_selected_locale(monkeypatch):
    calls = []
    response_payload = b'{"audios":["sample-base64"]}'
    monkeypatch.setattr(speech, "synthesize_speech", lambda text, language: calls.append((text, language)) or response_payload)

    with TestClient(APP) as client:
        response = client.post("/api/speech/tts", data={"text": "ಬೆಳೆ ಸಲಹೆ", "language": "kn-IN"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.content == response_payload
    assert calls == [("ಬೆಳೆ ಸಲಹೆ", "kn-IN")]


def test_sarvam_speech_route_falls_back_for_unsupported_locale(monkeypatch):
    calls = []
    monkeypatch.setattr(speech, "synthesize_speech", lambda text, language: calls.append(language) or b"{}")

    with TestClient(APP) as client:
        response = client.post("/api/speech/tts", data={"text": "hello", "language": "unsupported"})

    assert response.status_code == 200
    assert calls == ["en-IN"]

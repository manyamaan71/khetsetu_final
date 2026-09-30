import hashlib
import hmac
import io
import json

import pytest

from conftest import make_image_bytes


@pytest.fixture
def wa(monkeypatch):
    """Capture outgoing WhatsApp messages instead of calling Meta."""
    from app.config import settings
    from app.services import whatsapp_service as svc
    sent = []
    monkeypatch.setattr(settings, "WHATSAPP_VERIFY_TOKEN", "verify-me")
    monkeypatch.setattr(svc, "send_text", lambda to, body: sent.append((to, body)) or True)
    svc._seen_ids.clear()
    return sent


def payload(message):
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {"messages": [message]}}]}]}


def text_msg(body, mid="m1"):
    return {"from": "919999999999", "id": mid, "type": "text", "text": {"body": body}}


def test_verify_handshake_ok(client, wa):
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "verify-me", "hub.challenge": "12345"})
    assert r.status_code == 200 and r.text == "12345"


def test_verify_handshake_rejects_wrong_token(client, wa):
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": "nope", "hub.challenge": "1"})
    assert r.status_code == 403


@pytest.mark.parametrize("text,crop", [("BHAV TOMATO", "Tomato"), ("PRICE POTATO", "Potato"), ("भाव आलू", "Potato"), ("bhav corn", "Maize")])
def test_price_requests(client, wa, text, crop):
    assert client.post("/webhook", json=payload(text_msg(text, mid=text))).status_code == 200
    assert len(wa) == 1
    body = wa[0][1]
    assert "mandi prices" in body and "Demo market data" in body     # never presented as live without a key


def test_price_without_crop_asks_which(client, wa):
    client.post("/webhook", json=payload(text_msg("bhav")))
    assert "Which crop" in wa[0][1]


def test_unsupported_text(client, wa):
    client.post("/webhook", json=payload(text_msg("what is the weather tomorrow")))
    assert "only read leaf photos" in wa[0][1]


def test_help_message(client, wa):
    client.post("/webhook", json=payload(text_msg("hi")))
    assert "KhetSetu" in wa[0][1]


def test_unsupported_message_type(client, wa):
    client.post("/webhook", json=payload({"from": "91999", "id": "aud1", "type": "audio", "audio": {"id": "x"}}))
    assert "only read leaf photos" in wa[0][1]


def test_duplicate_delivery_is_ignored(client, wa):
    p = payload(text_msg("BHAV TOMATO", mid="dup-1"))
    client.post("/webhook", json=p); client.post("/webhook", json=p)
    assert len(wa) == 1


def test_photo_confident_reply_english_and_hindi(client, wa, monkeypatch, fake_model):
    from app.services import whatsapp_service as svc
    fake_model("Tomato___Late_blight", 0.93)
    monkeypatch.setattr(svc, "download_media", lambda media_id: make_image_bytes())
    client.post("/webhook", json=payload({"from": "91999", "id": "img1", "type": "image", "image": {"id": "MEDIA"}}))
    assert len(wa) == 2
    en, hi = wa[0][1], wa[1][1]
    assert "Tomato - Late Blight" in en and "93%" in en and "What to do" in en
    assert "पछेती" in hi and "क्या करें" in hi
    assert "agriculture officer" in en                                   # safety footer


def test_photo_low_confidence_reply(client, wa, monkeypatch, fake_model):
    from app.services import whatsapp_service as svc
    fake_model("Tomato___Late_blight", 0.40)
    monkeypatch.setattr(svc, "download_media", lambda media_id: make_image_bytes())
    client.post("/webhook", json=payload({"from": "91999", "id": "img2", "type": "image", "image": {"id": "M"}}))
    assert "Photo unclear" in wa[0][1] and "Late Blight" not in wa[0][1]


def test_photo_healthy_reply(client, wa, monkeypatch, fake_model):
    from app.services import whatsapp_service as svc
    fake_model("Potato___healthy", 0.95)
    monkeypatch.setattr(svc, "download_media", lambda media_id: make_image_bytes())
    client.post("/webhook", json=payload({"from": "91999", "id": "img3", "type": "image", "image": {"id": "M"}}))
    assert "Healthy Leaf" in wa[0][1] and "स्वस्थ पत्ता" in wa[1][1]


def test_photo_download_failure_and_bad_image(client, wa, monkeypatch):
    from app.services import whatsapp_service as svc
    def fail(_): raise RuntimeError("boom")
    monkeypatch.setattr(svc, "download_media", fail)
    client.post("/webhook", json=payload({"from": "91999", "id": "img4", "type": "image", "image": {"id": "M"}}))
    assert "could not download" in wa[0][1]
    monkeypatch.setattr(svc, "download_media", lambda _: b"not an image")
    client.post("/webhook", json=payload({"from": "91999", "id": "img5", "type": "image", "image": {"id": "M"}}))
    assert "could not read" in wa[1][1]


def test_signature_enforced_when_secret_set(client, wa, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "WHATSAPP_APP_SECRET", "s3cret")
    raw = json.dumps(payload(text_msg("BHAV TOMATO", mid="sig1"))).encode()
    assert client.post("/webhook", content=raw, headers={"Content-Type": "application/json"}).status_code == 403
    good = "sha256=" + hmac.new(b"s3cret", raw, hashlib.sha256).hexdigest()
    r = client.post("/webhook", content=raw, headers={"Content-Type": "application/json", "X-Hub-Signature-256": good})
    assert r.status_code == 200 and len(wa) == 1


def test_status_updates_are_acknowledged(client, wa):
    r = client.post("/webhook", json={"entry": [{"changes": [{"value": {"statuses": [{"id": "x"}]}}]}]})
    assert r.status_code == 200 and wa == []


def test_no_secrets_in_source_tree():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for f in list((root / "backend" / "app").rglob("*.py")) + list((root / "frontend" / "src").rglob("*.ts*")):
        t = f.read_text(encoding="utf-8")
        assert "EAAG" not in t and "sk-" not in t, f

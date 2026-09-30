"""
WhatsApp Cloud API webhook (root path /webhook, as configured in the Meta developer console).

GET  /webhook  - Meta's verification handshake (hub.mode / hub.verify_token / hub.challenge)
POST /webhook  - incoming messages. We answer 200 immediately and do the slow work
                 (download image -> classify -> reply) in a background task.
"""
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from ..config import settings
from ..database import SessionLocal
from ..services import whatsapp_service as wa

router = APIRouter()
log = logging.getLogger("khetsetu.whatsapp")


@router.get("/webhook")
async def verify(mode: str = Query(None, alias="hub.mode"), token: str = Query(None, alias="hub.verify_token"),
                 challenge: str = Query(None, alias="hub.challenge")):
    if mode == "subscribe" and settings.WHATSAPP_VERIFY_TOKEN and token == settings.WHATSAPP_VERIFY_TOKEN:
        return PlainTextResponse(challenge or "")
    raise HTTPException(status_code=403, detail="Verification failed")


def _process(messages: list[dict]) -> None:
    db = SessionLocal()
    try:
        for m in messages:
            wa.handle_message(m, db=db)
    finally:
        db.close()


@router.post("/webhook")
async def receive(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if not wa.verify_signature(raw, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Bad signature")
    try:
        payload = await request.json()
    except Exception:                                                        # noqa: BLE001
        return {"status": "ignored"}
    messages = [m for e in payload.get("entry", []) for ch in e.get("changes", [])
                for m in ch.get("value", {}).get("messages", [])]
    if messages:
        background.add_task(_process, messages)
    return {"status": "received", "messages": len(messages)}      # status updates etc. are simply acknowledged

"""Sarvam speech proxy."""
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from ..auth import require_user
from ..rate_limit import limiter

from ..services.speech_service import synthesize_speech
from ..services.sarvam_service import TtsTextTooLongError, translate_texts

router = APIRouter()
LANGUAGE_CODES = {
    "en": "en-IN", "en-IN": "en-IN",
    "hi": "hi-IN", "hi-IN": "hi-IN",
    "kn": "kn-IN", "kn-IN": "kn-IN",
    "ta": "ta-IN", "ta-IN": "ta-IN",
    "te": "te-IN", "te-IN": "te-IN",
    "ml": "ml-IN", "ml-IN": "ml-IN",
    "mr": "mr-IN", "mr-IN": "mr-IN",
    "bn": "bn-IN", "bn-IN": "bn-IN",
}


class TTSRequest(BaseModel):
    text: str = Field(min_length=1, max_length=2500)
    language: str = "en"


class TranslationRequest(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=40)
    language: str = "en"


@router.post("/translate")
async def translate_ui_text(payload: TranslationRequest):
    target_language = LANGUAGE_CODES.get(payload.language)
    if not target_language:
        raise HTTPException(status_code=422, detail={"code": "unsupported_language"})
    if any(not text.strip() or len(text) > 2000 for text in payload.texts):
        raise HTTPException(status_code=422, detail={"code": "invalid_text"})

    translated = await translate_texts(payload.texts, target_language)
    if translated is None:
        raise HTTPException(status_code=502, detail={"code": "translation_unavailable"})
    return {"texts": translated}


@router.post("/tts")
@router.post("/speech/tts", include_in_schema=False)
@limiter.limit("20/minute")
async def text_to_speech(request: Request, payload: TTSRequest, _user: dict | None = Depends(require_user)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail={"code": "empty_text"})

    target_language = LANGUAGE_CODES.get(payload.language)
    if not target_language:
        raise HTTPException(status_code=422, detail={"code": "unsupported_language"})

    try:
        audio_bytes = await synthesize_speech(text, target_language)
    except TtsTextTooLongError as exc:
        raise HTTPException(status_code=413, detail={"code": "speech_text_too_long"}) from exc
    if audio_bytes is None:
        raise HTTPException(status_code=502, detail={"code": "speech_unavailable"})

    return Response(content=audio_bytes, media_type="audio/wav")

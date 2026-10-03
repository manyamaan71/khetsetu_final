"""Sarvam speech proxy."""
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ..services.speech_service import synthesize_speech

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


@router.post("/tts")
@router.post("/speech/tts", include_in_schema=False)
async def text_to_speech(payload: TTSRequest):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail={"code": "empty_text"})

    target_language = LANGUAGE_CODES.get(payload.language)
    if not target_language:
        raise HTTPException(status_code=422, detail={"code": "unsupported_language"})

    audio_bytes = await synthesize_speech(text, target_language)
    if audio_bytes is None:
        raise HTTPException(status_code=502, detail={"code": "speech_unavailable"})

    return Response(content=audio_bytes, media_type="audio/wav")
    if audio_response is None:
        raise HTTPException(status_code=503, detail={"code": "sarvam_unavailable"})

    # Sarvam returns JSON containing its base64 audio payload; the existing
    # frontend speech service decodes it and falls back to browser speech on error.
    return Response(content=audio_response, media_type="application/json")

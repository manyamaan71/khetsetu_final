"""Optional Sarvam speech proxy. The frontend falls back to Web Speech when unavailable."""
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import Response

from ..services.speech_service import synthesize_speech

router = APIRouter()
SUPPORTED_SARVAM_LANGUAGES = {"en-IN", "hi-IN", "kn-IN", "ta-IN", "te-IN", "mr-IN", "bn-IN"}


@router.post("/speech/tts")
def text_to_speech(text: str = Form(...), language: str = Form("en-IN")):
    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail={"code": "empty_text"})

    target_language = language if language in SUPPORTED_SARVAM_LANGUAGES else "en-IN"
    audio_response = synthesize_speech(text, target_language)
    if audio_response is None:
        raise HTTPException(status_code=503, detail={"code": "sarvam_unavailable"})

    # Sarvam returns JSON containing its base64 audio payload; the existing
    # frontend speech service decodes it and falls back to browser speech on error.
    return Response(content=audio_response, media_type="application/json")

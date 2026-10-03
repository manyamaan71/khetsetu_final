"""
POST /api/predict  (multipart/form-data: image, language)

The confidence gate lives in services/analysis_service.py (server side): below
CONFIDENCE_THRESHOLD the response contains no disease name at all.
"""
import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from ..auth import require_user
from ..config import settings
from ..database import get_session
from ..model import classifier
from ..preprocessing import InvalidImageError
from ..rate_limit import limiter
from ..services.analysis_service import analyze_image

router = APIRouter()


def _err(code: int, key: str, en: str, hi: str):
    return HTTPException(status_code=code, detail={"code": key, "message": {"en": en, "hi": hi}})


@limiter.limit("20/minute")
@router.post("/predict")
async def predict_endpoint(request: Request, image: UploadFile = File(...), language: str = Form("en"),
                           db: Session = Depends(get_session),
                           _user: dict | None = Depends(require_user)):
    if not classifier.available:
        raise _err(503, "model_unavailable", "The crop scanner is not ready. Please try again later.",
                   "फसल स्कैनर अभी तैयार नहीं है। कृपया बाद में कोशिश करें।")
    data = await image.read(settings.MAX_UPLOAD_BYTES + 1)
    if len(data) == 0:
        raise _err(422, "empty_file", "The file is empty.", "फाइल खाली है।")
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise _err(413, "image_too_large", "Photo is too big (maximum 5 MB). Please use a smaller photo.",
                   "फोटो बहुत बड़ी है (अधिकतम 5 MB)। कृपया छोटी फोटो लें।")
    try:
        return await run_in_threadpool(
            asyncio.run, analyze_image(data, db=db, source="web", language=language)
        )
    except InvalidImageError:
        raise _err(422, "invalid_image", "We could not read this photo. Please use a JPG, PNG or WEBP photo.",
                   "यह फोटो पढ़ी नहीं जा सकी। कृपया JPG, PNG या WEBP फोटो लें।")

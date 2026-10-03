"""Generate a PDF from a freshly verified image, never from client result fields."""
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from ..config import settings
from ..model import classifier
from ..preprocessing import InvalidImageError
from ..services.analysis_service import analyze_image
from ..services.report_service import make_report_pdf

router = APIRouter()


@router.post("/report/pdf")
async def create_pdf_report(
    image: UploadFile = File(...),
    language: str = Form("en"),
    farmer_name: str | None = Form(None),
):
    supported_languages = ("en", "hi", "kn", "ta", "te", "mr", "bn")
    if language not in supported_languages:
        language = "en"
    if not classifier.available:
        raise HTTPException(status_code=503, detail={"code": "model_unavailable"})

    data = await image.read(settings.MAX_UPLOAD_BYTES + 1)
    if not data:
        raise HTTPException(status_code=422, detail={"code": "empty_file"})
    if len(data) > settings.MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail={"code": "image_too_large"})

    try:
        current_result = analyze_image(data, source="report", language=language)
        pdf_bytes, report_id, date_stamp = make_report_pdf(data, current_result, language, farmer_name)
    except InvalidImageError as exc:
        raise HTTPException(status_code=422, detail={"code": "invalid_image"}) from exc

    filename = f"KhetSetu_Report_{date_stamp}_{report_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

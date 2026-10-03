"""
analysis_service.py - the ONE place where a photo becomes a result.

    image bytes -> validate -> non-leaf check -> preprocess -> model inference
                -> confidence gate (backend enforced) -> prediction
                -> guidance lookup (separate object, never alters the prediction)

Used by POST /api/predict and by the WhatsApp webhook so both channels behave identically.
"""
import time

from ..config import settings
from ..database import ScanRecord
from ..disease_info import get_guidance, prediction_block
from ..model import classifier
from ..preprocessing import load_image_from_bytes, plant_pixel_ratio, preprocess_image
from . import ai_explanation_service

LOW_CONF_MESSAGE = {
    "title": {"en": "Photo unclear", "hi": "फोटो साफ नहीं है"},
    "body": {"en": "AI confidence is low. Please take another clear photo.",
             "hi": "AI का भरोसा कम है। कृपया एक और साफ फोटो लीजिए।"},
    "tips": {"en": ["Keep one leaf clearly visible", "Use good daylight", "Avoid blur", "Hold the camera steady"],
             "hi": ["एक पत्ता साफ दिखाएं", "अच्छी रोशनी में फोटो लें", "धुंधली फोटो न लें", "कैमरा स्थिर रखें"]},
}
NOT_LEAF_MESSAGE = {
    "title": {"en": "This does not look like a crop leaf", "hi": "यह फसल के पत्ते जैसा नहीं दिखता"},
    "body": {"en": "Please take a close, clear photo of a single leaf.",
             "hi": "कृपया एक पत्ते की पास से, साफ फोटो लीजिए।"},
    "tips": LOW_CONF_MESSAGE["tips"],
}


def analyze_image(data: bytes, db=None, source: str = "web", language: str = "en") -> dict:
    """Raises preprocessing.InvalidImageError for unreadable/unsupported images."""
    t0 = time.perf_counter()
    img = load_image_from_bytes(data)
    leaf_ratio = plant_pixel_ratio(img)
    batch = preprocess_image(img)
    t_pre = (time.perf_counter() - t0) * 1000

    base = {
        "demo_mode": classifier.is_demo,
        "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
        "model": {"mode": classifier.mode, "format": classifier.format},
    }

    if leaf_ratio < settings.MIN_LEAF_RATIO:
        result = {**base, "status": "not_a_leaf", "is_confident": False, "confidence": None,
                  "prediction": None, "guidance": None, "message": NOT_LEAF_MESSAGE}
        _log(db, source, "not_a_leaf", None, 0.0)
        return _finish(result, t0, t_pre, 0.0)

    class_name, confidence, t_inf = classifier.predict(batch, data)

    if confidence < settings.CONFIDENCE_THRESHOLD:
        # Backend-enforced safety: NO disease/crop name leaves the server below the threshold.
        result = {**base, "status": "low_confidence", "is_confident": False,
                  "confidence": round(confidence, 4), "prediction": None, "guidance": None,
                  "message": LOW_CONF_MESSAGE}
        _log(db, source, "low_confidence", None, confidence)
        return _finish(result, t0, t_pre, t_inf)

    prediction = prediction_block(class_name, confidence)
    guidance = get_guidance(class_name)
    advisory = guidance
    result = {**base, "status": "ok", "is_confident": True, "confidence": prediction["confidence"],
              "prediction": prediction, "guidance": guidance, "advisory": advisory, "message": None,
              "source": "ml_model", "explanation_source": "guidance"}
    extra = ai_explanation_service.generate_extra_explanation(
        prediction["crop"], prediction["disease"], language,
        confidence=prediction["confidence"], guidance=guidance)
    if extra:
        result["extra_explanation"] = {"text": extra, "language": language, "ai_generated": True}
        result["explanation_source"] = "guidance+llm"
    _log(db, source, "ok", prediction, confidence)
    return _finish(result, t0, t_pre, t_inf)


def _finish(result: dict, t0: float, t_pre: float, t_inf: float) -> dict:
    result["timing_ms"] = {"preprocess": round(t_pre, 1), "inference": round(t_inf, 1),
                           "total": round((time.perf_counter() - t0) * 1000, 1)}
    return result


def _log(db, source: str, status: str, pred: dict | None, confidence: float) -> None:
    """Aggregate-only log (no image, no farmer identity)."""
    if db is None:
        return
    try:
        db.add(ScanRecord(
            class_name=pred["class_name"] if pred else status, crop=pred["crop"] if pred else "unknown",
            disease=pred["disease"] if pred else "unknown", confidence=float(confidence or 0.0),
            is_healthy=bool(pred["is_healthy"]) if pred else False, is_confident=pred is not None,
            demo_mode=classifier.is_demo, status=status, source=source))
        db.commit()
    except Exception:                                                         # noqa: BLE001
        db.rollback()

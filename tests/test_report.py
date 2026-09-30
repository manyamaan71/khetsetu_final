import io

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fpdf import FPDF
import pytest
from pypdf import PdfReader

from app.api.report import router
from app.model import classifier
from app.services.report_service import FONT_FILES, FONT_DIR, SCRIPT
from conftest import ROOT, SAMPLES


APP = FastAPI()
APP.include_router(router, prefix="/api")


def _post_report(client, image: bytes, language: str = "en"):
    return client.post(
        "/api/report/pdf",
        files={"image": ("leaf.jpg", io.BytesIO(image), "image/jpeg")},
        data={"language": language, "disease": "Tomato___Late_blight", "confidence": "0.99"},
    )


def _text(pdf: bytes) -> str:
    return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(pdf)).pages)


def _sample() -> bytes:
    return (SAMPLES / "Tomato___healthy" / "sample_1.jpg").read_bytes()


def test_pdf_uses_fresh_prediction_not_client_result(monkeypatch):
    monkeypatch.setattr(classifier, "mode", "real")
    monkeypatch.setattr(classifier, "predict", lambda batch, image_bytes=b"": ("Tomato___healthy", 0.91, 1.0))
    with TestClient(APP) as client:
        response = _post_report(client, _sample())

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("attachment; filename=\"KhetSetu_Report_")
    text = _text(response.content)
    assert "Tomato" in text and "Healthy" in text and "91%" in text
    assert "Late Blight" not in text
    assert response.content.startswith(b"%PDF-")


def test_pdf_endpoint_with_shipped_model():
    classifier.load()
    if not classifier.available or classifier.is_demo:
        pytest.skip("real model could not be loaded")
    with TestClient(APP) as client:
        response = _post_report(client, _sample())
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    assert "KhetSetu_Report_" in response.headers["content-disposition"]


def test_low_confidence_report_contains_no_disease_name(monkeypatch):
    monkeypatch.setattr(classifier, "mode", "real")
    monkeypatch.setattr(classifier, "predict", lambda batch, image_bytes=b"": ("Tomato___Late_blight", 0.69, 1.0))
    with TestClient(APP) as client:
        response = _post_report(client, _sample(), "hi")

    assert response.status_code == 200
    text = _text(response.content)
    assert "KHETSETU" in text
    assert "Late Blight" not in text and "Tomato" not in text


def test_report_font_files_cover_all_indic_scripts():
    assert all((FONT_DIR / name).is_file() for name in FONT_FILES.values())


def test_harfbuzz_shapes_all_six_supported_scripts():
    samples = {
        "en": "Crop health report", "hi": "फसल स्वास्थ्य रिपोर्ट",
        "kn": "ಬೆಳೆ ಆರೋಗ್ಯ ವರದಿ", "te": "పంట ఆరోగ్య నివేదిక",
        "ta": "பயிர் ஆரோக்கிய அறிக்கை", "ml": "വിള ആരോഗ്യ റിപ്പോർട്ട്",
    }
    pdf = FPDF()
    pdf.add_page()
    for language, filename in FONT_FILES.items():
        family = f"KhetSetuTest-{language}"
        pdf.add_font(family, fname=str(FONT_DIR / filename))
        pdf.set_font(family, size=12)
        script, language_tag = SCRIPT[language]
        pdf.set_text_shaping(True, direction="ltr", script=script, language=language_tag)
        pdf.multi_cell(pdf.epw, 8, samples[language])
    assert bytes(pdf.output()).startswith(b"%PDF-")

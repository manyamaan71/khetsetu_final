import io

from fastapi import FastAPI
from fastapi.testclient import TestClient
from fpdf import FPDF
import pytest
from pypdf import PdfReader

# pyrefly: ignore [missing-import]
from app.api.report import router
# pyrefly: ignore [missing-import]
from app.model import classifier
# pyrefly: ignore [missing-import]
from app.services.report_service import FONT_FILES, FONT_DIR, SCRIPT
from conftest import ROOT, SAMPLES


APP = FastAPI()
APP.include_router(router, prefix="/api")


def _post_report(client, image: bytes, language: str = "en", farmer_name: str | None = None):
    form = {"language": language, "disease": "Tomato___Late_blight", "confidence": "0.99"}
    if farmer_name is not None:
        form["farmer_name"] = farmer_name
    return client.post(
        "/api/report/pdf",
        files={"image": ("leaf.jpg", io.BytesIO(image), "image/jpeg")},
        data=form,
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
    assert "Farmer Name" in text and "Not provided" in text
    assert "Late Blight" not in text
    assert response.content.startswith(b"%PDF-")


def test_disease_report_preserves_profile_metadata_and_every_advisory_item(monkeypatch):
    monkeypatch.setattr(classifier, "mode", "real")
    monkeypatch.setattr(classifier, "predict", lambda batch, image_bytes=b"": ("Tomato___Late_blight", 0.99, 1.0))
    advisory = {
        "what_we_found": {"en": "Finding preserved verbatim.", "hi": "परिणाम सुरक्षित है।"},
        "why_it_happened": {"en": ["Cause item one.", "Cause item two."], "hi": ["कारण एक।"]},
        "risk_factors": {"en": ["Risk factor one."], "hi": ["जोखिम कारक।"]},
        "symptoms": {"en": ["Symptom one.", "Symptom two."], "hi": ["लक्षण एक।"]},
        "immediate_actions": {"en": ["Action one now.", "Action two now."], "hi": ["अभी कदम एक।"]},
        "management": {"en": ["Management item one."], "hi": ["प्रबंधन एक।"]},
        "prevention": {"en": ["Prevention item one."], "hi": ["बचाव एक।"]},
        "avoid": {"en": ["Avoid item one."], "hi": ["इससे बचें।"]},
        "when_to_seek_help": {"en": ["Expert condition one."], "hi": ["विशेषज्ञ से पूछें।"]},
        "severity": {"en": "High", "hi": "अधिक"},
        "spread_risk": {"en": "High", "hi": "अधिक"},
        "source_note": {"en": "Complete source advisory preserved.", "hi": "पूरी सलाह सुरक्षित है।"},
    }
    monkeypatch.setattr("app.services.analysis_service.get_guidance", lambda _class_name: advisory)

    with TestClient(APP) as client:
        response = _post_report(client, _sample(), farmer_name="Sita")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF-")
    text = " ".join(_text(response.content).split())
    for expected in (
        "Sita", "Report ID", "Date", "Time", "Timezone", "Language", "English", "Tomato",
        "Disease detected", "Late Blight", "99%", "High", "Finding preserved verbatim.",
        "What we found", "Why did this happen?", "Risk factors", "Symptoms", "What should I do now?",
        "Treatment & management", "How to prevent it", "Avoid", "When to seek expert help",
        "Disease severity", "Spread risk", "Additional advisory",
        "Cause item one.", "Cause item two.", "Risk factor one.", "Symptom one.", "Symptom two.",
        "Action one now.", "Action two now.", "Management item one.", "Prevention item one.",
        "Avoid item one.", "Expert condition one.", "Complete source advisory preserved.",
        "KHETSETU", "Crop health guidance", "Page 1 of",
    ):
        assert expected in text

    reader = PdfReader(io.BytesIO(response.content))
    assert len(reader.pages) > 1
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = " ".join((page.extract_text() or "").split())
        assert "KHETSETU" in page_text
        assert "Crop health guidance" in page_text
        assert f"Page {page_number} of {len(reader.pages)}" in page_text


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


def test_harfbuzz_shapes_all_supported_scripts():
    samples = {
        "en": "Crop health report", "hi": "फसल स्वास्थ्य रिपोर्ट",
        "kn": "ಬೆಳೆ ಆರೋಗ್ಯ ವರದಿ", "te": "పంట ఆరోగ్య నివేదిక",
        "ta": "பயிர் ஆரோக்கிய அறிக்கை", "ml": "വിള ആരോഗ്യ റിപ്പോർട്ട്",
        "mr": "पीक आरोग्य अहवाल", "bn": "ফসল স্বাস্থ্য প্রতিবেদন",
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


def test_multilingual_pdf_reports_for_all_supported_languages(monkeypatch):
    monkeypatch.setattr(classifier, "mode", "real")
    monkeypatch.setattr(classifier, "predict", lambda batch, image_bytes=b"": ("Tomato___Late_blight", 0.95, 1.0))
    languages = ("en", "hi", "kn", "ta", "te", "mr", "bn")
    with TestClient(APP) as client:
        for lang in languages:
            res = _post_report(client, _sample(), language=lang, farmer_name="Farmer")
            assert res.status_code == 200, f"Failed for language {lang}"
            assert res.headers["content-type"] == "application/pdf"
            assert res.content.startswith(b"%PDF-")


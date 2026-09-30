"""Build a scan report from a fresh backend prediction using embedded Unicode fonts."""
from __future__ import annotations

import io
import uuid
from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[3]
FONT_DIR = ROOT / "backend" / "assets" / "fonts"
FONT_FILES = {
    "en": "NotoSans.ttf",
    "hi": "NotoSansDevanagari.ttf",
    "kn": "NotoSansKannada.ttf",
    "te": "NotoSansTelugu.ttf",
    "ta": "NotoSansTamil.ttf",
    "ml": "NotoSansMalayalam.ttf",
}
SCRIPT = {"en": ("latn", "eng"), "hi": ("deva", "hin"), "kn": ("knda", "kan"),
          "te": ("telu", "tel"), "ta": ("taml", "tam"), "ml": ("mlym", "mal")}
LANGUAGE_NAME = {"en": "English", "hi": "हिन्दी", "kn": "ಕನ್ನಡ", "te": "తెలుగు",
                 "ta": "தமிழ்", "ml": "മലയാളം"}
COPY = {
    "en": {
        "title": "Crop health report", "unclear": "Photo unclear report", "report_id": "Report ID",
        "date": "Date", "time": "Time", "language": "Language", "crop": "Crop",
        "condition": "Disease / condition", "confidence": "ML confidence", "status": "Status",
        "healthy": "Healthy", "disease": "Disease detected", "unclear_status": "Photo unclear",
        "what": "What this means", "symptoms": "Symptoms", "cause": "Possible causes",
        "actions": "Recommended actions", "prevention": "Prevention", "watering": "Watering care",
        "nutrients": "Nutrient guidance", "expert": "When to ask an expert", "avoid": "Precautions",
        "advisory": "Additional advisory", "ai_note": "Optional AI explanation", "demo": "Demo result",
        "low_reason": "The photo did not meet the safe confidence threshold. No disease diagnosis is provided.",
        "not_leaf_reason": "The image does not look like a supported crop leaf. No disease diagnosis is provided.",
        "tips_title": "Photo-taking tips", "tips": ["Keep one leaf clearly visible", "Use good daylight",
            "Avoid blur", "Hold the camera steady"],
        "disclaimer": "This image-model result is not a laboratory diagnosis. Follow locally approved guidance and product labels. Do not use chemicals without advice from an agricultural expert.",
        "watermark": "KHETSETU",
    },
    "hi": {
        "title": "फसल स्वास्थ्य रिपोर्ट", "unclear": "फोटो स्पष्ट नहीं रिपोर्ट", "report_id": "रिपोर्ट आईडी",
        "date": "तारीख", "time": "समय", "language": "भाषा", "crop": "फसल",
        "condition": "रोग / स्थिति", "confidence": "मॉडल का विश्वास", "status": "स्थिति",
        "healthy": "स्वस्थ", "disease": "रोग के संकेत मिले", "unclear_status": "फोटो स्पष्ट नहीं",
        "what": "इसका क्या अर्थ है", "symptoms": "लक्षण", "cause": "संभावित कारण",
        "actions": "सुझाए गए कदम", "prevention": "बचाव", "watering": "सिंचाई", "nutrients": "पोषक तत्व",
        "expert": "विशेषज्ञ से कब पूछें", "avoid": "सावधानियां", "advisory": "अतिरिक्त सलाह",
        "ai_note": "वैकल्पिक AI जानकारी", "demo": "डेमो परिणाम",
        "low_reason": "फोटो सुरक्षित विश्वास सीमा तक नहीं पहुंची। कोई रोग निदान नहीं दिया गया है।",
        "not_leaf_reason": "यह तस्वीर समर्थित फसल के पत्ते जैसी नहीं दिखती। कोई रोग निदान नहीं दिया गया है।",
        "tips_title": "फोटो लेने के सुझाव", "tips": ["एक पत्ता साफ दिखाएं", "अच्छी रोशनी में फोटो लें",
            "धुंधली फोटो से बचें", "कैमरा स्थिर रखें"],
        "disclaimer": "यह तस्वीर पर आधारित मॉडल का अनुमान है, प्रयोगशाला जांच नहीं। स्थानीय रूप से मान्य सलाह और उत्पाद के लेबल मानें। कृषि विशेषज्ञ की सलाह के बिना रसायन का उपयोग न करें।",
        "watermark": "KHETSETU",
    },
}


class KhetSetuPDF(FPDF):
    def __init__(self, language: str, font_family: str, report_id: str):
        super().__init__(format="A4", unit="mm")
        self.language = language
        self.font_family = font_family
        self.report_id = report_id
        self.set_margins(16, 24, 16)
        self.set_auto_page_break(auto=True, margin=19)

    def header(self):
        self.set_fill_color(30, 91, 56)
        self.rect(0, 0, self.w, 18, style="F")
        self.set_text_color(255, 255, 255)
        self.set_font(self.font_family, "B", 12)
        self.set_xy(16, 5)
        self.cell(50, 8, "KHETSETU")
        self.set_font(self.font_family, size=8)
        self.set_xy(self.w - 70, 6)
        self.cell(54, 7, self.report_id, align="R")
        self.set_text_color(34, 48, 39)
        self.set_xy(self.l_margin, self.t_margin)

    def footer(self):
        self.set_draw_color(220, 229, 222)
        self.line(16, self.h - 14, self.w - 16, self.h - 14)
        self.set_text_color(150, 170, 155)
        self.set_font(self.font_family, size=8)
        self.set_xy(16, self.h - 11)
        self.cell(80, 6, "KHETSETU  |  Crop health guidance")
        self.set_xy(self.w - 40, self.h - 11)
        self.cell(24, 6, str(self.page_no()), align="R")
        self.set_text_color(34, 48, 39)


def _write_section(pdf: KhetSetuPDF, title: str, value: str | list[str]) -> None:
    if not value:
        return
    if pdf.get_y() > pdf.h - 36:
        pdf.add_page()
    pdf.set_x(pdf.l_margin)
    pdf.ln(3)
    pdf.set_font(pdf.font_family, "B", 11)
    pdf.set_text_color(30, 91, 56)
    pdf.multi_cell(pdf.epw, 7, title)
    pdf.set_text_color(44, 54, 47)
    pdf.set_font(pdf.font_family, size=10)
    values = value if isinstance(value, list) else [value]
    for item in values:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 5.5, f"- {item}" if isinstance(value, list) else item)


def make_report_pdf(image_bytes: bytes, result: dict, language: str) -> tuple[bytes, str, str]:
    """Return PDF bytes, unique report ID and local date for the download filename."""
    if language not in FONT_FILES or language not in COPY:
        raise ValueError("Unsupported report language")

    copy = COPY[language]
    report_id = f"KS-{uuid.uuid4().hex[:10].upper()}"
    now = datetime.now().astimezone()
    date_stamp = now.strftime("%Y%m%d")
    family = f"KhetSetu-{language}"
    font_path = FONT_DIR / FONT_FILES[language]
    if not font_path.is_file():
        raise RuntimeError(f"Required PDF font is missing: {font_path.name}")

    pdf = KhetSetuPDF(language, family, report_id)
    pdf.add_font(family, fname=str(font_path))
    pdf.add_font(family, style="B", fname=str(font_path))
    script, language_tag = SCRIPT[language]
    pdf.set_text_shaping(True, direction="ltr", script=script, language=language_tag)
    pdf.set_title(copy["title"])
    pdf.set_author("KhetSetu")
    pdf.set_subject(report_id)
    pdf.add_page()

    pdf.set_font(family, "B", 18)
    pdf.set_text_color(30, 91, 56)
    title = copy["title"] if result["is_confident"] else copy["unclear"]
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 10, title)
    pdf.ln(2)
    pdf.set_text_color(65, 75, 68)
    pdf.set_font(family, size=9)
    date_label = f"{copy['date']}: {now.strftime('%d %b %Y')}    {copy['time']}: {now.strftime('%H:%M %Z')}"
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(pdf.epw, 5, f"{copy['report_id']}: {report_id}\n{date_label}\n{copy['language']}: {LANGUAGE_NAME[language]}")

    image = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="JPEG", quality=88)
    image_buffer.seek(0)
    pdf.ln(4)
    pdf.image(image_buffer, x=16, w=88, h=61, keep_aspect_ratio=True)
    pdf.ln(3)

    if not result["is_confident"]:
        message = result.get("message") or {}
        status = message.get("title", {}).get(language, copy["unclear_status"])
        pdf.set_fill_color(255, 246, 222)
        pdf.set_draw_color(235, 197, 116)
        pdf.set_font(family, "B", 12)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 8, f"{copy['status']}: {status}", border=1, fill=True)
        reason = copy["not_leaf_reason"] if result.get("status") == "not_a_leaf" else copy["low_reason"]
        _write_section(pdf, copy["what"], reason)
        tips = message.get("tips", {}).get(language) or copy["tips"]
        _write_section(pdf, copy["tips_title"], tips)
    else:
        prediction = result["prediction"]
        guidance = result["guidance"]
        crop = prediction["crop"] if language == "en" else prediction["crop_hi"]
        condition = prediction["disease"] if language == "en" else prediction["disease_hi"]
        status = copy["healthy"] if prediction["is_healthy"] else copy["disease"]
        pdf.set_fill_color(232, 243, 234)
        pdf.set_draw_color(188, 215, 191)
        pdf.set_font(family, "B", 12)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 8, f"{copy['crop']}: {crop}    |    {copy['status']}: {status}", border=1, fill=True)
        if not prediction["is_healthy"]:
            _write_section(pdf, copy["condition"], condition)
        confidence = round(float(prediction["confidence"]) * 100)
        pdf.set_font(family, size=10)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(pdf.epw, 7, f"{copy['confidence']}: {confidence}%")
        bar_y = pdf.get_y() + 1
        pdf.set_fill_color(226, 235, 228)
        pdf.rect(pdf.l_margin, bar_y, 120, 3, style="F")
        pdf.set_fill_color(52, 125, 76)
        pdf.rect(pdf.l_margin, bar_y, 120 * confidence / 100, 3, style="F")
        pdf.set_y(bar_y + 5)
        if result.get("demo_mode"):
            _write_section(pdf, copy["demo"], copy["disclaimer"])
        fields = [
            ("what_is_it", "what"), ("symptoms", "symptoms"), ("possible_cause", "cause"),
            ("basic_care", "actions"), ("prevention", "prevention"),
            ("watering_care", "watering"), ("nutrient_guidance", "nutrients"),
            ("consult_expert_when", "expert"), ("avoid", "avoid"),
        ]
        for field, label in fields:
            value = guidance[field][language]
            if field != "symptoms" or not prediction["is_healthy"]:
                _write_section(pdf, copy[label], value)
        extra = result.get("extra_explanation")
        if extra and extra.get("text"):
            _write_section(pdf, copy["ai_note"], extra["text"])
        source_note = guidance["source_note"][language]
        _write_section(pdf, copy["advisory"], source_note + " " + copy["disclaimer"])

    output = pdf.output()
    return bytes(output), report_id, date_stamp

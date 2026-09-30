"""Build a scan report from a fresh backend prediction using embedded Unicode fonts."""
from __future__ import annotations

import io
import uuid
from datetime import datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace
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
    "mr": "NotoSansDevanagari.ttf",
    "bn": "NotoSansBengali.ttf",
}
SCRIPT = {
    "en": ("latn", "eng"),
    "hi": ("deva", "hin"),
    "kn": ("knda", "kan"),
    "te": ("telu", "tel"),
    "ta": ("taml", "tam"),
    "ml": ("mlym", "mal"),
    "mr": ("deva", "mar"),
    "bn": ("beng", "ben"),
}
LANGUAGE_NAME = {
    "en": "English",
    "hi": "हिन्दी",
    "kn": "ಕನ್ನಡ",
    "te": "తెలుగు",
    "ta": "தமிழ்",
    "ml": "മലയാളം",
    "mr": "मराठी",
    "bn": "বাংলা",
}
COPY = {
    "en": {
        "title": "Crop health report", "unclear": "Photo unclear report", "report_id": "Report ID",
        "farmer_info": "Farmer information", "field": "Field", "value": "Details",
        "farmer": "Farmer Name", "not_provided": "Not provided", "date": "Date", "time": "Time",
        "timezone": "Timezone", "language": "Language", "crop": "Crop",
        "condition": "Disease / condition", "confidence": "ML confidence", "status": "Status",
        "healthy": "Healthy", "disease": "Disease detected", "unclear_status": "Photo unclear",
        "assessment": "Crop assessment", "details": "Disease details", "severity": "Disease severity",
        "spread_risk": "Spread risk", "risk_factors": "Risk factors", "reason": "Possible reason",
        "recommendation": "Recommendation", "guidance": "Guidance", "priority": "Priority",
        "what": "What this means", "what_found": "What we found", "why_question": "Why did this happen?",
        "what_do": "What should I do now?", "management_title": "Treatment & management", "prevention_title": "How to prevent it",
        "avoid_title": "Avoid", "expert_title": "When to seek expert help",
        "symptoms": "Symptoms", "cause": "Possible causes",
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
        "farmer_info": "किसान की जानकारी", "field": "जानकारी", "value": "विवरण",
        "farmer": "किसान का नाम", "not_provided": "जानकारी नहीं दी गई", "date": "तारीख", "time": "समय",
        "timezone": "समय क्षेत्र", "language": "भाषा", "crop": "फसल",
        "condition": "रोग / स्थिति", "confidence": "मॉडल का विश्वास", "status": "स्थिति",
        "healthy": "स्वस्थ", "disease": "रोग के संकेत मिले", "unclear_status": "फोटो स्पष्ट नहीं",
        "assessment": "फसल का आकलन", "details": "रोग की जानकारी", "severity": "रोग की गंभीरता",
        "spread_risk": "फैलने का जोखिम", "risk_factors": "जोखिम के कारक", "reason": "संभावित कारण",
        "recommendation": "सुझाव", "guidance": "सलाह", "priority": "प्राथमिकता",
        "what": "इसका क्या अर्थ है", "what_found": "हमें क्या मिला", "why_question": "यह क्यों हुआ?",
        "what_do": "अब मुझे क्या करना चाहिए?", "management_title": "इलाज और प्रबंधन", "prevention_title": "इसे कैसे रोका जाए",
        "avoid_title": "क्या न करें", "expert_title": "विशेषज्ञ की मदद कब लें",
        "symptoms": "लक्षण", "cause": "संभावित कारण",
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
    "kn": {
        "title": "ಬೆಳೆ ಆರೋಗ್ಯ ವರದಿ", "unclear": "ಅಸ್ಪಷ್ಟ ಫೋಟೋ ವರದಿ", "report_id": "ವರದಿ ID",
        "farmer_info": "ರೈತರ ಮಾಹಿತಿ", "field": "ಮಾಹಿತಿ", "value": "ವಿವರಗಳು",
        "farmer": "ರೈತರ ಹೆಸರು", "not_provided": "ನೀಡಲಾಗಿಲ್ಲ", "date": "ದಿನಾಂಕ", "time": "ಸಮಯ",
        "timezone": "ಸಮಯ ವಲಯ", "language": "ಭಾಷೆ", "crop": "ಬೆಳೆ",
        "condition": "ರೋಗ / ಸ್ಥಿತಿ", "confidence": "ಮಾದರಿಯ ವಿಶ್ವಾಸ", "status": "ಸ್ಥಿತಿ",
        "healthy": "ಆರೋಗ್ಯಕರ", "disease": "ರೋಗ ಪತ್ತೆಯಾಗಿದೆ", "unclear_status": "ಫೋಟೋ ಸ್ಪಷ್ಟವಿಲ್ಲ",
        "assessment": "ಬೆಳೆ ಮೌಲ್ಯಮಾಪನ", "details": "ರೋಗದ ವಿವರಗಳು", "severity": "ರೋಗದ ತೀವ್ರತೆ",
        "spread_risk": "ಹರಡುವ ಅಪಾಯ", "risk_factors": "ಅಪಾಯಕಾರಿ ಅಂಶಗಳು", "reason": "ಸಾಧ್ಯವಾದ ಕಾರಣ",
        "recommendation": "ಸಲಹೆ", "guidance": "ಮಾರ್ಗದರ್ಶನ", "priority": "ಆದ್ಯತೆ",
        "what": "ಇದರ ಅರ್ಥವೇನು", "what_found": "ನಮಗೆ ಕಂಡದ್ದು", "why_question": "ಇದು ಏಕೆ ಸಂಭವಿಸಿತು?",
        "what_do": "ಈಗ ನಾನು ಏನು ಮಾಡಬೇಕು?", "management_title": "ಚಿಕಿತ್ಸೆ ಮತ್ತು ನಿರ್ವಹಣೆ", "prevention_title": "ಇದನ್ನು ತಡೆಯುವುದು ಹೇಗೆ",
        "avoid_title": "ಏನು ಮಾಡಬಾರದು", "expert_title": "ತಜ್ಞರ ಸಹಾಯ ಯಾವಾಗ ಪಡೆಯಬೇಕು",
        "symptoms": "ಲಕ್ಷಣಗಳು", "cause": "ಸಾಧ್ಯವಿರುವ ಕಾರಣಗಳು",
        "actions": "ಶಿಫಾರಸು ಮಾಡಿದ ಕ್ರಮಗಳು", "prevention": "ತಡೆಗಟ್ಟುವಿಕೆ", "watering": "ನೀರು ಉಣಿಸುವಿಕೆ", "nutrients": "ಪೋಷಕಾಂಶಗಳು",
        "expert": "ತಜ್ಞರನ್ನು ಯಾವಾಗ ಸಂಪರ್ಕಿಸಬೇಕು", "avoid": "ಮುನ್ನೆಚ್ಚರಿಕೆಗಳು", "advisory": "ಹೆಚ್ಚುವರಿ ಸಲಹೆ",
        "ai_note": "ಐಚ್ಛಿಕ AI ವಿವರಣೆ", "demo": "ಡೆಮೊ ಫಲಿತಾಂಶ",
        "low_reason": "ಫೋಟೋ ಸುರಕ್ಷಿತ ವಿಶ್ವಾಸಮಟ್ಟವನ್ನು ತಲುಪಿಲ್ಲ. ಯಾವುದೇ ರೋಗ ನಿರ್ಣಯ ನೀಡಲಾಗಿಲ್ಲ.",
        "not_leaf_reason": "ಚಿತ್ರವು ಬೆಂಬಲಿತ ಬೆಳೆಯ ಎಲೆಯಂತೆ ಕಾಣುತ್ತಿಲ್ಲ.",
        "tips_title": "ಫೋಟೋ ತೆಗೆಯುವ ಸಲಹೆಗಳು", "tips": ["ಒಂದು ಎಲೆಯನ್ನು ಸ್ಪಷ್ಟವಾಗಿ ತೋರಿಸಿ", "ಉತ್ತಮ ಬೆಳಕಿನಲ್ಲಿ ಫೋಟೋ ತೆಗೆಯಿರಿ",
            "ಮಸಕು ಚಿತ್ರಗಳನ್ನು ತಡೆಯಿರಿ", "ಕ್ಯಾಮೆರಾವನ್ನು ಸ್ಥಿರವಾಗಿರಿಸಿ"],
        "disclaimer": "ಇದು ಚಿತ್ರ-ಮಾದರಿಯ ಅಂದಾಜು ಫಲಿತಾಂಶವಾಗಿದೆ. ಸ್ಥಳೀಯ ಕೃಷಿ ತಜ್ಞರ ಸಲಹೆಯಿಲ್ಲದೆ ರಾಸಾಯನಿಕಗಳನ್ನು ಬಳಸಬೇಡಿ.",
        "watermark": "KHETSETU",
    },
}

COPY.update({
    "ta": {
        "title": "பயிர் ஆரோக்கிய அறிக்கை", "unclear": "தெளிவற்ற புகைப்பட அறிக்கை", "report_id": "அறிக்கை எண்",
        "farmer_info": "விவசாயி தகவல்", "field": "விவரம்", "value": "தகவல்", "farmer": "விவசாயி பெயர்",
        "not_provided": "வழங்கப்படவில்லை", "date": "தேதி", "time": "நேரம்", "timezone": "நேர மண்டலம்",
        "language": "மொழி", "crop": "பயிர்", "condition": "நோய் / நிலை", "confidence": "AI நம்பிக்கை",
        "status": "நிலை", "healthy": "ஆரோக்கியமானது", "disease": "நோய் கண்டறியப்பட்டது",
        "unclear_status": "புகைப்படம் தெளிவாக இல்லை", "assessment": "பயிர் மதிப்பீடு", "details": "நோய் விவரங்கள்",
        "severity": "நோய் தீவிரம்", "spread_risk": "பரவல் அபாயம்", "risk_factors": "ஆபத்து காரணிகள்",
        "cause": "சாத்தியமான காரணங்கள்", "why_question": "இது ஏன் நடந்தது?", "what_do": "இப்போது என்ன செய்ய வேண்டும்?",
        "what_found": "நாங்கள் கண்டறிந்தது", "management_title": "சிகிச்சை மற்றும் மேலாண்மை", "prevention_title": "இதை எவ்வாறு தடுப்பது",
        "avoid_title": "தவிர்க்கவும்", "expert_title": "நிபுணரின் உதவியை எப்போது நாட வேண்டும்",
        "management": "சிகிச்சை மற்றும் மேலாண்மை", "prevention": "தடுப்பு", "symptoms": "அறிகுறிகள்",
        "actions": "பரிந்துரைக்கப்பட்ட நடவடிக்கைகள்", "expert": "நிபுணரின் உதவியை எப்போது நாட வேண்டும்",
        "avoid": "தவிர்க்கவும்", "advisory": "கூடுதல் ஆலோசனை", "ai_note": "விருப்ப AI விளக்கம்",
        "demo": "மாதிரி முடிவு", "tips_title": "புகைப்படம் எடுக்கும் குறிப்புகள்",
        "low_reason": "புகைப்படம் பாதுகாப்பான நம்பிக்கை வரம்பை எட்டவில்லை. நோய் கண்டறிதல் வழங்கப்படவில்லை.",
        "not_leaf_reason": "இந்த படம் ஆதரிக்கப்படும் பயிர் இலையாகத் தெரியவில்லை.",
        "disclaimer": "இது பட மாதிரியின் முடிவு; ஆய்வக நோயறிதல் அல்ல. உள்ளூர் வேளாண் நிபுணரின் ஆலோசனையைப் பின்பற்றவும்.",
        "tips": ["ஒரு இலையைத் தெளிவாகக் காட்டவும்", "நல்ல வெளிச்சத்தைப் பயன்படுத்தவும்", "மங்கலான படங்களைத் தவிர்க்கவும்", "கேமராவை நிலையாகப் பிடிக்கவும்"],
    },
    "te": {
        "title": "పంట ఆరోగ్య నివేదిక", "unclear": "స్పష్టత లేని ఫోటో నివేదిక", "report_id": "నివేదిక ID",
        "farmer_info": "రైతు సమాచారం", "field": "వివరం", "value": "వివరాలు", "farmer": "రైతు పేరు",
        "not_provided": "పేర్కొనలేదు", "date": "తేదీ", "time": "సమయం", "timezone": "సమయ మండలం",
        "language": "భాష", "crop": "పంట", "condition": "వ్యాధి / పరిస్థితి", "confidence": "ML నమ్మకం",
        "status": "స్థితి", "healthy": "ఆరోగ్యకరమైనది", "disease": "వ్యాధి గుర్తించబడింది",
        "unclear_status": "ఫోటో స్పష్టంగా లేదు", "assessment": "పంట అంచనా", "details": "వ్యాధి వివరాలు",
        "severity": "వ్యాధి తీవ్రత", "spread_risk": "వ్యాప్తి ప్రమాదం", "risk_factors": "ప్రమాద కారకాలు",
        "cause": "సాధ్యమైన కారణాలు", "why_question": "ఇది ఎందుకు జరిగింది?", "what_do": "ఇప్పుడు ఏమి చేయాలి?",
        "what_found": "మేము గుర్తించినది", "management_title": "చికిత్స మరియు నిర్వహణ", "prevention_title": "దీనిని ఎలా నివారించాలి",
        "avoid_title": "నివారించండి", "expert_title": "నిపుణుడిని ఎప్పుడు సంప్రదించాలి",
        "management": "చికిత్స మరియు నిర్వహణ", "prevention": "నివారణ", "symptoms": "లక్షణాలు",
        "actions": "సిఫార్సు చేసిన చర్యలు", "expert": "నిపుణుడిని ఎప్పుడు సంప్రదించాలి",
        "avoid": "నివారించండి", "advisory": "అదనపు సలహా", "ai_note": "ఐచ్ఛిక AI వివరణ",
        "demo": "డెమో ఫలితం", "tips_title": "ఫోటో తీసే సూచనలు",
        "low_reason": "ఫోటో సురక్షిత నమ్మక పరిమితిని చేరలేదు. వ్యాధి నిర్ధారణ ఇవ్వలేదు.",
        "not_leaf_reason": "ఈ చిత్రం మద్దతు ఉన్న పంట ఆకులా కనిపించడం లేదు.",
        "disclaimer": "ఇది చిత్ర నమూనా అంచనా మాత్రమే; ప్రయోగశాల నిర్ధారణ కాదు. స్థానిక వ్యవసాయ నిపుణుడిని సంప్రదించండి.",
        "tips": ["ఒక ఆకును స్పష్టంగా చూపండి", "మంచి వెలుతురును ఉపయోగించండి", "మసక చిత్రాలను నివారించండి", "కెమెరాను స్థిరంగా పట్టుకోండి"],
    },
    "mr": {
        "title": "पीक आरोग्य अहवाल", "unclear": "अस्पष्ट फोटो अहवाल", "report_id": "अहवाल क्रमांक",
        "farmer_info": "शेतकरी माहिती", "field": "घटक", "value": "तपशील", "farmer": "शेतकऱ्याचे नाव",
        "not_provided": "दिलेली नाही", "date": "दिनांक", "time": "वेळ", "timezone": "वेळ क्षेत्र",
        "language": "भाषा", "crop": "पीक", "condition": "रोग / स्थिती", "confidence": "ML विश्वास",
        "status": "स्थिती", "healthy": "निरोगी", "disease": "रोग आढळला", "unclear_status": "फोटो स्पष्ट नाही",
        "assessment": "पीक मूल्यांकन", "details": "रोग तपशील", "severity": "रोगाची तीव्रता",
        "spread_risk": "प्रसाराचा धोका", "risk_factors": "धोका घटक", "cause": "संभाव्य कारणे",
        "why_question": "हे का घडले?", "what_do": "आता काय करावे?", "management": "उपचार आणि व्यवस्थापन",
        "what_found": "आम्हाला काय आढळले", "management_title": "उपचार आणि व्यवस्थापन", "prevention_title": "हे कसे टाळावे",
        "avoid_title": "टाळा", "expert_title": "तज्ञांची मदत कधी घ्यावी",
        "prevention": "प्रतिबंध", "symptoms": "लक्षणे", "actions": "शिफारस केलेली पावले",
        "expert": "तज्ञांची मदत कधी घ्यावी", "avoid": "टाळा", "advisory": "अतिरिक्त सल्ला",
        "ai_note": "पर्यायी AI स्पष्टीकरण", "demo": "डेमो निकाल", "tips_title": "फोटो घेण्याच्या टिप्स",
        "low_reason": "फोटो सुरक्षित विश्वास मर्यादेपर्यंत पोहोचला नाही. रोगनिदान दिलेले नाही.",
        "not_leaf_reason": "ही प्रतिमा समर्थित पिकाच्या पानासारखी दिसत नाही.",
        "disclaimer": "हा प्रतिमा-मॉडेलचा अंदाज आहे, प्रयोगशाळेतील निदान नाही. स्थानिक कृषी तज्ञांचा सल्ला घ्या.",
        "tips": ["एक पान स्पष्ट दिसू द्या", "चांगला प्रकाश वापरा", "अस्पष्ट फोटो टाळा", "कॅमेरा स्थिर ठेवा"],
    },
    "bn": {
        "title": "ফসলের স্বাস্থ্য প্রতিবেদন", "unclear": "অস্পষ্ট ছবির প্রতিবেদন", "report_id": "রিপোর্ট ID",
        "farmer_info": "কৃষকের তথ্য", "field": "বিষয়", "value": "বিবরণ", "farmer": "কৃষকের নাম",
        "not_provided": "দেওয়া হয়নি", "date": "তারিখ", "time": "সময়", "timezone": "সময় অঞ্চল",
        "language": "ভাষা", "crop": "ফসল", "condition": "রোগ / অবস্থা", "confidence": "ML নির্ভরতা",
        "status": "অবস্থা", "healthy": "স্বাস্থ্যকর", "disease": "রোগ শনাক্ত হয়েছে", "unclear_status": "ছবি পরিষ্কার নয়",
        "assessment": "ফসল মূল্যায়ন", "details": "রোগের বিবরণ", "severity": "রোগের তীব্রতা",
        "spread_risk": "ছড়ানোর ঝুঁকি", "risk_factors": "ঝুঁকির কারণ", "cause": "সম্ভাব্য কারণ",
        "why_question": "এটি কেন ঘটেছে?", "what_do": "এখন কী করা উচিত?", "management": "চিকিৎসা ও ব্যবস্থাপনা",
        "what_found": "আমরা যা পেয়েছি", "management_title": "চিকিৎসা ও ব্যবস্থাপনা", "prevention_title": "কীভাবে প্রতিরোধ করবেন",
        "avoid_title": "এড়িয়ে চলুন", "expert_title": "কখন বিশেষজ্ঞের সাহায্য নেবেন",
        "prevention": "প্রতিরোধ", "symptoms": "লক্ষণ", "actions": "প্রস্তাবিত পদক্ষেপ",
        "expert": "কখন বিশেষজ্ঞের সাহায্য নেবেন", "avoid": "এড়িয়ে চলুন", "advisory": "অতিরিক্ত পরামর্শ",
        "ai_note": "ঐচ্ছিক AI ব্যাখ্যা", "demo": "ডেমো ফলাফল", "tips_title": "ছবি তোলার পরামর্শ",
        "low_reason": "ছবিটি নিরাপদ নির্ভরতার সীমায় পৌঁছায়নি। কোনো রোগ নির্ণয় দেওয়া হয়নি।",
        "not_leaf_reason": "ছবিটি সমর্থিত ফসলের পাতা বলে মনে হচ্ছে না।",
        "disclaimer": "এটি ছবির মডেলের ফল, পরীক্ষাগারের রোগ নির্ণয় নয়। স্থানীয় কৃষি বিশেষজ্ঞের পরামর্শ নিন।",
        "tips": ["একটি পাতা স্পষ্ট রাখুন", "ভালো আলো ব্যবহার করুন", "ঝাপসা ছবি এড়িয়ে চলুন", "ক্যামেরা স্থির রাখুন"],
    },
})

for _language, _labels in COPY.items():
    if _language not in ("en", "hi"):
        COPY[_language] = {**COPY["en"], **_labels}


class KhetSetuPDF(FPDF):
    def __init__(self, language: str, font_family: str, report_id: str):
        super().__init__(format="A4", unit="mm")
        self.language = language
        self.font_family = font_family
        self.report_id = report_id
        self.set_margins(16, 24, 16)
        self.set_auto_page_break(auto=True, margin=19)
        self.alias_nb_pages()

    def header(self):
        self.set_text_color(30, 91, 56)
        self.set_font(self.font_family, "B", 38)
        with self.local_context(fill_opacity=0.07):
            with self.rotation(34, x=self.w / 2, y=self.h / 2):
                self.text(x=self.w / 2 - 44, y=self.h / 2, text="KHETSETU")

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
        self.set_xy(self.w - 68, self.h - 11)
        self.cell(52, 6, f"{self.report_id}  |  Page {self.page_no()} of {{nb}}", align="R")
        self.set_text_color(34, 48, 39)


def _localized(value, language: str):
    if isinstance(value, dict):
        value = value.get(language) or value.get("en")
    if isinstance(value, list):
        return [str(item) for item in value if item]
    return str(value) if value else ""


def _write_table(
    pdf: KhetSetuPDF,
    rows: list[tuple[str, ...]],
    widths: tuple[float, ...],
    headings: tuple[str, ...] | None = None,
    emphasize_first: bool = False,
) -> None:
    if not rows and not headings:
        return

    heading_style = FontFace(emphasis="B", size_pt=9, color=(255, 255, 255), fill_color=(30, 91, 56))
    cell_style = FontFace(size_pt=9, color=(44, 54, 47))
    label_style = FontFace(emphasis="B", size_pt=9, color=(30, 91, 56), fill_color=(239, 246, 240))
    with pdf.table(
        col_widths=widths,
        line_height=6,
        padding=2,
        borders_layout="ALL",
        first_row_as_headings=bool(headings),
        headings_style=heading_style,
        text_align="LEFT",
        v_align="TOP",
    ) as table:
        if headings:
            table.row(headings)
        for values in rows:
            row = table.row()
            for index, value in enumerate(values):
                style = label_style if emphasize_first and index == 0 else cell_style
                row.cell(str(value), style=style)


def _write_section(pdf: KhetSetuPDF, title: str, value: str | list[str]) -> None:
    if not value:
        return
    if pdf.get_y() > pdf.h - 37:
        pdf.add_page()
    pdf.ln(3)
    pdf.set_fill_color(232, 243, 234)
    pdf.set_text_color(30, 91, 56)
    pdf.set_font(pdf.font_family, "B", 10)
    pdf.multi_cell(pdf.epw, 8, title, fill=True)
    pdf.set_text_color(44, 54, 47)

    values = value if isinstance(value, list) else [value]
    values = [str(item) for item in values if item]
    if not values:
        return
    if isinstance(value, list):
        _write_table(
            pdf,
            [(str(index), item) for index, item in enumerate(values, start=1)],
            (12, pdf.epw - 12),
            headings=("#", get_copy(pdf.language)["value"]),
        )
    else:
        _write_table(pdf, [(values[0],)], (pdf.epw,))


def get_copy(language: str) -> dict:
    base = dict(COPY["en"])
    if language in COPY:
        base.update(COPY[language])
    return base

def make_report_pdf(
    image_bytes: bytes,
    result: dict,
    language: str,
    farmer_name: str | None = None,
) -> tuple[bytes, str, str]:
    """Return PDF bytes, unique report ID and local date for the download filename."""
    copy = get_copy(language)
    report_id = f"KS-{uuid.uuid4().hex[:10].upper()}"
    now = datetime.now().astimezone()
    date_stamp = now.strftime("%Y%m%d")
    
    font_lang = language if language in FONT_FILES else "en"
    font_file = FONT_FILES.get(font_lang, "NotoSans.ttf")
    font_path = FONT_DIR / font_file
    if not font_path.is_file():
        font_path = FONT_DIR / "NotoSans.ttf"
        font_lang = "en"

    family = f"KhetSetu-{font_lang}"
    pdf = KhetSetuPDF(language, family, report_id)
    pdf.add_font(family, fname=str(font_path))
    pdf.add_font(family, style="B", fname=str(font_path))
    script, language_tag = SCRIPT.get(font_lang, ("latn", "eng"))
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
    pdf.set_fill_color(232, 243, 234)
    pdf.set_text_color(30, 91, 56)
    pdf.set_font(family, "B", 10)
    pdf.multi_cell(pdf.epw, 8, copy["farmer_info"], fill=True)
    farmer = farmer_name.strip() if farmer_name and farmer_name.strip() else copy["not_provided"]
    timezone_name = now.tzname() or now.strftime("%Z") or "Local"
    metadata_rows = [
        (copy["farmer"], farmer),
        (copy["report_id"], report_id),
        (copy["date"], now.strftime("%d %b %Y")),
        (copy["time"], now.strftime("%H:%M %Z")),
        (copy["timezone"], timezone_name),
        (copy["language"], LANGUAGE_NAME.get(language, language)),
    ]
    _write_table(
        pdf,
        metadata_rows,
        (pdf.epw * 0.34, pdf.epw * 0.66),
        headings=(copy["field"], copy["value"]),
        emphasize_first=True,
    )

    image = ImageOps.exif_transpose(Image.open(io.BytesIO(image_bytes))).convert("RGB")
    image_buffer = io.BytesIO()
    image.save(image_buffer, format="JPEG", quality=88)
    image_buffer.seek(0)
    pdf.ln(4)
    pdf.image(image_buffer, x=16, w=88, h=61, keep_aspect_ratio=True)
    pdf.ln(3)

    if not result["is_confident"]:
        message = result.get("message") or {}
        status = _localized(message.get("title"), language) or copy["unclear_status"]
        assessment_rows = [(copy["crop"], "-"), (copy["status"], status)]
        confidence = result.get("confidence")
        if confidence is not None:
            assessment_rows.append((copy["confidence"], f"{round(float(confidence) * 100)}%"))
        pdf.set_fill_color(232, 243, 234)
        pdf.set_text_color(30, 91, 56)
        pdf.set_font(family, "B", 10)
        pdf.multi_cell(pdf.epw, 8, copy["assessment"], fill=True)
        _write_table(pdf, assessment_rows, (pdf.epw * 0.34, pdf.epw * 0.66), emphasize_first=True)

        reason = copy["not_leaf_reason"] if result.get("status") == "not_a_leaf" else copy["low_reason"]
        _write_section(pdf, copy["what"], reason)
        tips = _localized(message.get("tips"), language) or copy["tips"]
        _write_section(pdf, copy["tips_title"], tips)
        _write_section(pdf, copy["advisory"], copy["disclaimer"])
    else:
        prediction = result["prediction"]
        advisory = result.get("advisory") or result.get("guidance") or {}
        crop = prediction["crop"] if language == "en" else prediction["crop_hi"]
        condition = prediction["disease"] if language == "en" else prediction["disease_hi"]
        status = copy["healthy"] if prediction["is_healthy"] else copy["disease"]
        confidence = round(float(prediction["confidence"]) * 100)
        severity = _localized(advisory.get("severity"), language) or "-"
        spread_risk = _localized(advisory.get("spread_risk"), language) or "-"
        pdf.set_fill_color(232, 243, 234)
        pdf.set_text_color(30, 91, 56)
        pdf.set_font(family, "B", 10)
        pdf.multi_cell(pdf.epw, 8, copy["assessment"], fill=True)
        assessment_rows = [
            (copy["crop"], crop),
            (copy["status"], status),
            (copy["condition"], condition),
            (copy["confidence"], f"{confidence}%"),
            (copy["severity"], severity),
            (copy["spread_risk"], spread_risk),
        ]
        _write_table(pdf, assessment_rows, (pdf.epw * 0.34, pdf.epw * 0.66), emphasize_first=True)
        pdf.ln(2)
        pdf.set_draw_color(188, 215, 191)
        pdf.set_fill_color(226, 235, 228)
        pdf.rect(pdf.l_margin, pdf.get_y(), pdf.epw, 3, style="F")
        pdf.set_fill_color(52, 125, 76)
        pdf.rect(pdf.l_margin, pdf.get_y(), pdf.epw * confidence / 100, 3, style="F")
        pdf.ln(5)

        _write_section(pdf, copy["what_found"],
                       _localized(advisory.get("what_we_found") or advisory.get("what_is_it"), language))
        if result.get("demo_mode"):
            _write_section(pdf, copy["demo"], copy["disclaimer"])

        detail_rows = [(copy["condition"], condition)]
        for field, label in (("why_it_happened", copy["cause"]), ("severity", copy["severity"]),
                             ("spread_risk", copy["spread_risk"])):
            detail = _localized(advisory.get(field), language)
            if isinstance(detail, list):
                detail = "; ".join(detail)
            if detail:
                detail_rows.append((label, detail))
        pdf.ln(3)
        pdf.set_fill_color(232, 243, 234)
        pdf.set_text_color(30, 91, 56)
        pdf.set_font(family, "B", 10)
        pdf.multi_cell(pdf.epw, 8, copy["details"], fill=True)
        _write_table(
            pdf,
            detail_rows,
            (pdf.epw * 0.34, pdf.epw * 0.66),
            headings=(copy["field"], copy["value"]),
            emphasize_first=True,
        )

        section_specs = [
            ("why_it_happened", copy["why_question"], "possible_cause"),
            ("risk_factors", copy["risk_factors"], None),
            ("symptoms", copy["symptoms"], None),
            ("immediate_actions", copy["what_do"], "basic_care"),
            ("management", copy["management_title"], None),
            ("prevention", copy["prevention_title"], None),
            ("avoid", copy["avoid_title"], None),
            ("when_to_seek_help", copy["expert_title"], "consult_expert_when"),
            ("severity", copy["severity"], None),
            ("spread_risk", copy["spread_risk"], None),
        ]
        for field, title, fallback in section_specs:
            value = advisory.get(field)
            if value is None and fallback:
                value = advisory.get(fallback)
            text = _localized(value, language)
            if isinstance(text, list):
                _write_section(pdf, title, text)
            elif text:
                _write_section(pdf, title, text)

        extra = result.get("extra_explanation")
        if extra and extra.get("text"):
            _write_section(pdf, copy["ai_note"], extra["text"])
        source_note = _localized(advisory.get("source_note"), language) or copy["disclaimer"]
        if isinstance(source_note, list):
            source_note = " ".join(source_note)
        _write_section(pdf, copy["advisory"], source_note + " " + copy["disclaimer"])

    output = pdf.output()
    return bytes(output), report_id, date_stamp

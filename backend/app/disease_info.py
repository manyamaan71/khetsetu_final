"""Disease-specific advisory lookup for KhetSetu.

This module is the single source of truth for disease knowledge. The model still
provides the class label; the advisory lookup happens afterwards and never alters
or reinterprets the prediction itself.
"""
from __future__ import annotations

import copy
import json
import os
from functools import lru_cache
from pathlib import Path

from .config import settings


REQUIRED_FIELDS = (
    "class_name",
    "crop",
    "disease",
    "is_healthy",
    "what_we_found",
    "why_it_happened",
    "symptoms",
    "risk_factors",
    "immediate_actions",
    "management",
    "prevention",
    "avoid",
    "when_to_seek_help",
    "severity",
    "spread_risk",
)


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def class_config() -> dict:
    return _read(Path(settings.MODEL_DIR) / "class_config.json")


@lru_cache(maxsize=1)
def _classes() -> list[dict]:
    return sorted(class_config()["classes"], key=lambda c: c["index"])


@lru_cache(maxsize=1)
def _class_names() -> list[str]:
    names = _read(Path(settings.MODEL_DIR) / "class_names.json")
    expected = [item["class_name"] for item in _classes()]
    if names != expected:
        raise ValueError("class_names.json does not match class_config.json order")
    return names


def class_names() -> list[str]:
    return _class_names()


@lru_cache(maxsize=1)
def _by_name() -> dict[str, dict]:
    return {c["class_name"]: c for c in _classes()}


def get_class(class_name: str) -> dict:
    return _by_name()[class_name]


@lru_cache(maxsize=1)
def _crops() -> dict:
    return _read(Path(settings.DATA_DIR) / "crops.json")


def get_crop(crop: str) -> dict | None:
    return _crops().get(crop)


def all_crops() -> dict:
    return _crops()


def _bi(en: str | list[str], hi: str | list[str]) -> dict:
    return {"en": en, "hi": hi}


def _narrative_section(text_en: str, text_hi: str) -> dict:
    return {"en": text_en, "hi": text_hi}


def _list_section(en_items: list[str], hi_items: list[str]) -> dict:
    return {"en": en_items, "hi": hi_items}


def _norm_class_name(raw: str) -> str:
    name = (raw or "").strip()
    if not name:
        return ""
    name = name.replace("___", "_").replace("__", "_")
    name = name.replace(" ", "_")
    return name


def _alias_key(raw: str) -> str:
    key = _norm_class_name(raw)
    aliases = {
        "Corn_Common_rust": "Corn_Common_rust",
        "Corn_healthy": "Corn_healthy",
        "Potato_Early_blight": "Potato_early_blight",
        "Potato_Late_blight": "Potato_late_blight",
        "Potato_healthy": "Potato_healthy",
        "Tomato_Early_blight": "Tomato_early_blight",
        "Tomato_Late_blight": "Tomato_late_blight",
        "Tomato_healthy": "Tomato_healthy",
        "Apple_scab": "Apple_scab",
        "Apple_black_rot": "Apple_black_rot",
        "Apple_cedar_apple_rust": "Apple_cedar_apple_rust",
        "Apple_healthy": "Apple_healthy",
        "Pepper_bacterial_spot": "Pepper_bacterial_spot",
        "Pepper_healthy": "Pepper_healthy",
    }
    return aliases.get(key, key)


def _make_compat_profile(profile: dict, class_name: str) -> dict:
    """Add published generic fields so older code and tests still work."""
    output = copy.deepcopy(profile)
    output["class_name"] = class_name
    output["condition"] = _narrative_section(output["disease"], output["hindi"]["disease"])
    output["what_is_it"] = output["what_we_found"]
    output["possible_cause"] = _narrative_section(
        " ".join(output["why_it_happened"]["en"]),
        " ".join(output["why_it_happened"]["hi"]),
    )
    output["basic_care"] = output["immediate_actions"]
    output["consult_expert_when"] = output["when_to_seek_help"]
    output["watering_care"] = _list_section(
        ["Keep soil moisture steady and avoid unnecessary leaf wetness.",
         "Water early in the day when possible so foliage dries quickly."],
        ["मिट्टी की नमी स्थिर रखें और अनावश्यक पत्ती की नमी से बचें।",
         "संभव हो तो सुबह जल्दी पानी दें ताकि पत्ते जल्दी सूख जाएं।"],
    )
    output["nutrient_guidance"] = _list_section(
        ["Follow local crop nutrition guidance and avoid plant stress.",
         "Healthy, well-balanced plants recover more quickly."],
        ["स्थानीय फसल पोषण सलाह का पालन करें और पौधे पर तनाव से बचें।",
         "स्वस्थ, संतुलित पौधे जल्दी उबरते हैं।"],
    )
    output["source_note"] = _narrative_section(
        "This disease-specific advice is generated from the crop disease database for the detected class. Follow locally approved agricultural guidance and product labels.",
        "यह रोग-विशिष्ट सलाह पता चली हुई फसल की बीमारी की जानकारी से तैयार की गई है। स्थानीय रूप से स्वीकृत कृषि सलाह और उत्पाद लेबल का पालन करें।",
    )
    output["urgency"] = "act_fast" if output["spread_risk"]["en"].lower() in {"high", "very high"} else "act_soon" if output["severity"]["en"].lower() in {"moderate", "high"} else "none"
    return output


_ADVICE_FIELDS = (
    "what_we_found", "what_is_it", "why_it_happened", "possible_cause",
    "symptoms", "immediate_actions", "basic_care", "management", "prevention",
    "avoid", "when_to_seek_help", "consult_expert_when", "severity", "spread_risk",
    "source_note",
)
_ADVICE_LANGUAGES = ("kn", "ta", "te", "mr", "bn")


def _canonical_class_name(name: str) -> str:
    key = _alias_key(name)
    return next(
        (item["class_name"] for item in _classes() if _alias_key(item["class_name"]) == key),
        name,
    )


@lru_cache(maxsize=5)
def _advice_translations(lang: str) -> dict:
    root = Path(__file__).resolve().parents[2] / "data" / "advice_i18n"
    translations: dict = {}
    reviewed_path = root / f"{lang}.json"
    if reviewed_path.is_file():
        reviewed = _read(reviewed_path)
        if reviewed.get("status") == "reviewed":
            translations = reviewed.get("classes", {})
    if os.getenv("ALLOW_DRAFT_TRANSLATIONS", "").lower() == "true":
        draft_path = root / "drafts" / f"{lang}.json"
        if draft_path.is_file():
            draft = _read(draft_path)
            if draft.get("status") in {"draft", "reviewed"}:
                translations = {**translations, **draft.get("classes", {})}
    return translations


def _overlay_advice_translations(profile: dict, class_name: str) -> dict:
    canonical = _canonical_class_name(class_name)
    for lang in _ADVICE_LANGUAGES:
        translated = _advice_translations(lang).get(canonical, {})
        fields = translated.get("fields", {})
        for field in _ADVICE_FIELDS:
            value = fields.get(field)
            if value is not None and isinstance(profile.get(field), dict):
                profile[field][lang] = value
    return profile


def _profile_for_key(name: str) -> dict:
    key = _alias_key(name)
    if key not in DISEASE_INFO:
        raise KeyError(f"No disease advisory exists for {name!r}")
    profile = copy.deepcopy(DISEASE_INFO[key])
    profile["class_name"] = name
    return _overlay_advice_translations(_make_compat_profile(profile, name), name)


DISEASE_INFO: dict[str, dict] = {
    "Apple_scab": {
        "crop": "Apple",
        "disease": "Scab",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The apple leaf and fruit show patterns consistent with apple scab, including olive-brown lesions and roughened tissue.",
            "सेब के पत्ते और फल में सेब स्कैब के अनुरूप जैतून-भूरे धब्बे और खुरदरी ऊतकों के लक्षण दिख रहे हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "Apple scab is caused by the fungus Venturia inaequalis.",
                "Cool, wet spring conditions and long leaf wetness favour infection.",
                "Rain-splash and humid air can carry spores from infected leaves or fruit.",
                "Trees with dense canopies and poor airflow stay wet longer.",
            ],
            [
                "सेब स्कैब फफूंद Venturia inaequalis से होता है।",
                "ठंडे, नम वसंत मौसम और लंबे समय तक पत्तों की नमी संक्रमण को बढ़ाती है।",
                "बारिश की छींटें और नम हवा संक्रमित पत्तों या फलों से बीजाणु फैलाती है।",
                "घने डालियों और खराब हवा के कारण पेड़ लंबे समय तक गीले रहते हैं।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Olive-brown, irregular spots on leaves and fruit",
                "Leaf lesions may become rough or cracked",
                "Severely affected fruit may be distorted and unsaleable",
            ],
            [
                "पत्तों और फलों पर जैतून-भूरे, अनियमित धब्बे",
                "पत्तों के घाव खुरदरे या फटे दिखाई दे सकते हैं",
                "बहुत प्रभावित फल विकृत हो सकते हैं और बेचने योग्य नहीं रह सकते",
            ],
        ),
        "risk_factors": _list_section(
            [
                "Cool, rainy spring weather",
                "Dense canopies with poor airflow",
                "Infected leaves or fruit left on the tree",
            ],
            [
                "ठंडा, बरसाती वसंत मौसम",
                "अच्छी हवा न होने वाली घनी डालियाँ",
                "पेड़ पर संक्रमित पत्ते या फल रह जाना",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Remove heavily infected leaves or fruit where practical.",
                "Avoid overhead irrigation or prolonged leaf wetness.",
                "Check nearby trees for similar symptoms.",
            ],
            [
                "संभव हो तो अधिक प्रभावित पत्ते या फल हटा दें।",
                "ओवरहेड सिंचाई या लंबे समय तक पत्तों की नमी से बचें।",
                "आस-पास के पेड़ों में समान लक्षण देखें।",
            ],
        ),
        "management": _list_section(
            [
                "Use orchard sanitation to reduce infected material in the canopy.",
                "Improve airflow through pruning and canopy management.",
                "Use only a locally approved treatment recommended for apple scab and follow the label.",
            ],
            [
                "पेड़ की छत में संक्रमित सामग्री कम करने के लिए बगीचे की सफाई करें।",
                "काट-छाँट और छत्रिय प्रबंधन से हवा का प्रवाह बेहतर करें।",
                "केवल स्थानीय रूप से स्वीकृत, सेब स्कैब के लिए अनुशंसित उपचार का उपयोग करें और लेबल का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Collect and remove infected fallen leaves and mummified fruit.",
                "Use resistant varieties where available.",
                "Maintain good spacing and pruning to reduce leaf wetness.",
            ],
            [
                "संक्रमित गिरे पत्ते और ममी फलों को हटाकर नष्ट करें।",
                "संभव हो तो प्रतिरोधी किस्में चुनें।",
                "अच्छी दूरी और छाँट से पत्ती की नमी कम करें।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid leaving diseased leaves or fruit in the orchard.",
                "Avoid dense canopy blocks that keep leaves wet for hours.",
            ],
            [
                "बगीचे में संक्रमित पत्ते या फल छोड़ने से बचें।",
                "ऐसी घनी डालियाँ न रखें जो पत्तों को कई घंटे तक गीला रखती हैं।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "If fruit loss is increasing rapidly or the disease moves into new branches.",
                "If the orchard is highly affected and sanitation alone is not enough.",
            ],
            [
                "यदि फल का नुकसान तेजी से बढ़ रहा हो या रोग नई डालियों में फैल रहा हो।",
                "यदि बगीचा अत्यधिक प्रभावित है और सफाई से काम नहीं बन रहा हो।",
            ],
        ),
        "severity": _narrative_section("Moderate", "मध्यम"),
        "spread_risk": _narrative_section("High", "उच्च"),
        "hindi": {"disease": "सेब स्कैब", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Apple_black_rot": {
        "crop": "Apple",
        "disease": "Black Rot",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The fruit or leaf symptoms are consistent with black rot, a fungal disease that can cause dark, sunken lesions and fruit decay.",
            "फल या पत्तों के लक्षण ब्लैक रोट के अनुरूप हैं, एक फफूंद रोग जो गहरे, धंसते धब्बे और फल सड़न पैदा करता है।",
        ),
        "why_it_happened": _list_section(
            [
                "Black rot is caused by fungi that infect wounded fruit, pruning cuts or weak tissue.",
                "Warm, wet weather and splashing rain spread spores between leaves, fruit and branches.",
                "Poor sanitation and unmanaged infected fruit can keep the disease active in the orchard.",
            ],
            [
                "ब्लैक रोट फफूंद के कारण होता है जो घायल फलों, कटिंग स्थानों या कमजोर ऊतक को संक्रमित करता है।",
                "गर्म, नम मौसम और बारिश की छींटें पत्तों, फलों और डालियों के बीच बीजाणु फैलाती हैं।",
                "अच्छी सफाई न होने और संक्रमित फलों को न हटाने से रोग बगीचे में सक्रिय रहता है।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Dark sunken spots on fruit or twigs",
                "Fruit often develops concentric ring patterns and soft decay",
                "Leaves may also show irregular lesions and dieback",
            ],
            [
                "फल या टहनियों पर गहरे धंसते धब्बे",
                "फल में अक्सर वृत्ताकार छल्ले और नरम सड़न आती है",
                "पत्तों पर भी अनियमित धब्बे और सूखापन दिखाई दे सकता है",
            ],
        ),
        "risk_factors": _list_section(
            [
                "Warm, humid weather",
                "Fruit wounds from pruning, hail or insect damage",
                "Infected fruit or wood left in the orchard",
            ],
            [
                "गर्म, नम मौसम",
                "काट-छाँट, ओला या कीट से हुए फल के घाव",
                "बगीचे में संक्रमित फल या लकड़ी रह जाना",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Remove visible infected fruit and badly affected shoots.",
                "Prune or clean affected wood where safe and practical.",
                "Reduce excess canopy moisture and improve airflow.",
            ],
            [
                "दिखने वाले संक्रमित फल और heavily प्रभावित टहनियाँ हटाएँ।",
                "जहाँ सुरक्षित और संभव हो, प्रभावित लकड़ी की छँटाई करें।",
                "अतिरिक्त छत्रीय नमी कम करें और हवा का प्रवाह बेहतर करें।",
            ],
        ),
        "management": _list_section(
            [
                "Remove mummified fruits and infected limbs from the orchard.",
                "Keep wounds to a minimum and avoid unnecessary physical damage.",
                "Use only a locally approved treatment recommended for black rot and follow product guidance.",
            ],
            [
                "ममी फलों और संक्रमित शाखाओं को बगीचे से हटाएं।",
                "घाव कम रखें और अनावश्यक भौतिक नुकसान से बचें।",
                "केवल स्थानीय रूप से स्वीकृत, ब्लैक रोट के लिए अनुशंसित उपचार का उपयोग करें और लेबल का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Practice orchard sanitation after harvest.",
                "Remove dead fruit and weak wood from trees.",
                "Maintain vigorous but not excessively dense canopies.",
            ],
            [
                "कटाई के बाद बगीचे की सफाई करें।",
                "पेड़ से मृत फल और कमजोर लकड़ी हटाएं।",
                "तेज लेकिन अत्यधिक घनी डालियाँ न रखें।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid leaving infected fruit on the tree or ground.",
                "Avoid excessive wounding during pruning or fruit handling.",
            ],
            [
                "पेड़ या जमीन पर संक्रमित फल छोड़ने से बचें।",
                "काट-छाँट या फल संभालते समय अधिक घाव से बचें।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "When new fruit infections continue despite sanitation and pruning.",
                "If the disease is spreading into many branches or fruit clusters.",
            ],
            [
                "जब सफाई और छँटाई के बाद भी नए फलों में संक्रमण जारी रहे।",
                "यदि रोग कई शाखाओं या फल समूहों में फैल रहा हो।",
            ],
        ),
        "severity": _narrative_section("Moderate", "मध्यम"),
        "spread_risk": _narrative_section("Moderate", "मध्यम"),
        "hindi": {"disease": "ब्लैक रोट", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Apple_cedar_apple_rust": {
        "crop": "Apple",
        "disease": "Cedar Apple Rust",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The apple tissue shows rust symptoms typical of cedar-apple rust, with orange or yellow pustules on leaves and fruit.",
            "सेब के ऊतकों में सिडर-एपल रस्ट जैसे नारंगी या पीले दाने दिख रहे हैं, जो इससे रोग की पुष्टि करते हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "This disease is caused by a rust fungus that can move between apple and cedar hosts.",
                "Moisture and cool periods favour infection and spore release.",
                "Nearby cedar trees can act as a source of spores for apple orchards.",
            ],
            [
                "यह रोग एक रस्ट फफूंद के कारण होता है जो सेब और सिडर (देवदार/सिडार) पादप के बीच घूम सकता है।",
                "नमी और ठंडे समय में संक्रमण और बीजाणु निकलना आसान होता है।",
                "आस-पास के सिडर पेड़ सेब के बगीचे में बीजाणु दे सकते हैं।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Yellow to orange spots or pustules on leaves",
                "Raised, rough lesions on fruit or leaves",
                "Affected tissue may later turn brown and drop out",
            ],
            [
                "पत्तों पर पीले से नारंगी धब्बे या दाने",
                "फल या पत्तों पर उठे हुए, खुरदुरे घाव",
                "प्रभावित ऊतक बाद में भूरे पड़ सकते हैं और गिर सकते हैं",
            ],
        ),
        "risk_factors": _list_section(
            [
                "Nearby cedar or juniper hosts",
                "Cool, wet weather during early growth",
                "Long periods of leaf wetness",
            ],
            [
                "आस-पास के सिडर या जुनिपर पेड़",
                "विकास के शुरुआती समय में ठंडी, नम हवा",
                "पत्तों की लंबी नमी",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Monitor the orchard closely after rainy periods.",
                "Remove heavily infected leaves where reasonable.",
                "Check nearby alternative hosts and act if they are close to the orchard.",
            ],
            [
                "बरसात के बाद बाग की निगरानी बढ़ाएं।",
                "संभव हो तो अधिक प्रभावित पत्ते हटा दें।",
                "आस-पास के वैकल्पिक Hosts की जांच करें अगर वे बगीचे के पास हैं।",
            ],
        ),
        "management": _list_section(
            [
                "Improve canopy airflow and reduce prolonged leaf wetness.",
                "Manage alternate hosts near the orchard if practical.",
                "Use only a locally approved treatment recommended for cedar apple rust and follow the label.",
            ],
            [
                "वनस्पति छत्र में हवा का प्रवाह बेहतर करें और लंबे समय तक पत्ती की नमी कम रखें।",
                "संभव हो तो बगीचे के पास वैकल्पिक Hosts का प्रबंधन करें।",
                "केवल स्थानीय रूप से स्वीकृत, सिडर-एपल रस्ट के लिए अनुशंसित उपचार का उपयोग करें और लेबल का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Remove nearby cedar or juniper sources if feasible.",
                "Keep foliage dry during high-risk periods.",
                "Use resistant cultivars where available.",
            ],
            [
                "संभव हो तो पास के सिडर या जुनिपर स्रोत हटाएँ।",
                "उच्च जोखिम के समय पत्तों को सूखा रखें।",
                "संभव हो तो प्रतिरोधी किस्में चुनें।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid leaving infected tissue in the orchard.",
                "Avoid dense, shaded canopies that stay wet for long periods.",
            ],
            [
                "बगीचे में संक्रमित ऊतक छोड़ने से बचें।",
                "ऐसी घनी, छायादार डालियाँ न रखें जो लंबे समय तक गीली रहें।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "If orange rust symptoms spread quickly after rain.",
                "If the orchard has many affected leaves or fruit clusters.",
            ],
            [
                "यदि बारिश के बाद नारंगी रस्ट के लक्षण तेजी से फैलें।",
                "यदि बगीचे में कई पत्ते या फल समूह प्रभावित हों।",
            ],
        ),
        "severity": _narrative_section("Moderate", "मध्यम"),
        "spread_risk": _narrative_section("Moderate", "मध्यम"),
        "hindi": {"disease": "सिडर-एपल रस्ट", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Apple_healthy": {
        "crop": "Apple",
        "disease": "Healthy",
        "is_healthy": True,
        "what_we_found": _narrative_section(
            "The apple leaf appears healthy and does not show strong disease patterns.",
            "सेब का पत्ता स्वस्थ दिख रहा है और इसमें मजबूत रोग के संकेत नहीं दिखाई दे रहे हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "No strong disease pattern was detected in this sample.",
                "Good orchard condition and normal leaf appearance are reassuring.",
            ],
            [
                "इस नमूने में कोई मजबूत रोग पैटर्न नहीं मिला।",
                "अच्छा बगीचा स्थिति और सामान्य पत्ती दिखना राहत देने वाला है।",
            ],
        ),
        "symptoms": _list_section(["No disease lesions or unusual spots detected."], ["कोई रोग-जनित धब्बे या असामान्य लक्षण नहीं मिले।"]),
        "risk_factors": _list_section(["No clear disease pressure seen at this moment."], ["अभी इस समय कोई स्पष्ट रोग दबाव नहीं दिख रहा है।"]),
        "immediate_actions": _list_section(
            ["Continue regular scouting and note any new spots or sudden leaf changes.", "Keep good orchard hygiene and moisture management."],
            ["नियमित निगरानी जारी रखें और नए धब्बे या पत्ती में बदलाव नोट करें।", "अच्छी बगीचे की सफाई और नमी प्रबंधन बनाए रखें।"],
        ),
        "management": _list_section(["No treatment is needed for this sample."], ["इस नमूने के लिए कोई उपचार आवश्यक नहीं है।"]),
        "prevention": _list_section(["Continue good orchard hygiene and monitoring."], ["अच्छी बगीचे की सफाई और निगरानी जारी रखें।"]),
        "avoid": _list_section(["No active disease issue is present in this sample."], ["इस नमूने में कोई सक्रिय रोग समस्या नहीं है।"]),
        "when_to_seek_help": _list_section(["Only if new symptoms appear or the tree declines rapidly."], ["सिर्फ तभी विशेषज्ञ से सलाह लें जब नए लक्षण दिखाई दें या पेड़ जल्दी गिर जाए।"]),
        "severity": _narrative_section("Low", "कम"),
        "spread_risk": _narrative_section("Low", "कम"),
        "hindi": {"disease": "स्वस्थ", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Corn_Common_rust": {
        "crop": "Corn",
        "disease": "Common Rust",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The leaf shows signs consistent with common rust, including small rust-coloured pustules on the leaf surface.",
            "पत्ते में सामान्य रस्ट के अनुरूप छोटे जंग-रंग के दाने दिखाई दे रहे हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "Common rust is caused by a fungal pathogen that spreads by wind and dew.",
                "Cool nights and humid conditions favour disease development.",
                "Dense canopies and heavy dew can keep leaves wet and increase infection.",
            ],
            [
                "सामान्य रस्ट एक फफूंद रोगजनक के कारण होता है जो हवा और ओस से फैलता है।",
                "ठंडी रातें और नम मौसम रोग को बढ़ाते हैं।",
                "घने छत्र और भारी ओस पत्तों को गीला रखती है और संक्रमण बढ़ाता है।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Small raised rust-brown pustules on both sides of the leaf",
                "Leaves may yellow and dry early under heavy infection",
                "Lower leaves are often affected first",
            ],
            [
                "पत्ती के दोनों तरफ छोटे उठे हुए जंग-भूरे दाने",
                "भारी संक्रमण में पत्ते पीले होकर जल्दी सूख सकते हैं",
                "अक्सर निचले पत्ते पहले प्रभावित होते हैं",
            ],
        ),
        "risk_factors": _list_section(
            [
                "High humidity and dew",
                "Late planting or susceptible hybrids",
                "Dense crop stands",
            ],
            [
                "उच्च नमी और ओस",
                "देर से बोआई या संवेदनशील संकर",
                "घना फसल ढाँचा",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Check whether rust is moving up into newer leaves.",
                "Remove or isolate heavily affected lower leaf material when practical.",
                "Monitor the field closely during humid periods.",
            ],
            [
                "देखें कि रस्ट नए पत्तों तक ऊपर जा रहा है या नहीं।",
                "संभव हो तो अधिक प्रभावित निचले पत्तों को हटाएं या अलग रखें।",
                "नम मौसम में खेत की करीबी निगरानी करें।",
            ],
        ),
        "management": _list_section(
            [
                "Choose rust-tolerant hybrids where available.",
                "Keep crop spacing suitable to improve airflow.",
                "Use only a locally approved treatment recommended for corn rust and follow the label.",
            ],
            [
                "संभव हो तो रस्ट सहनशील संकर चुनें।",
                "उचित दूरी देकर हवा का प्रवाह बेहतर रखें।",
                "केवल स्थानीय रूप से स्वीकृत, मक्का रस्ट के लिए अनुशंसित उपचार का उपयोग करें और लेबल का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Avoid dense planting and improve air movement.",
                "Rotate crops and remove old residue where practical.",
                "Select resistant varieties when possible.",
            ],
            [
                "घनी बुवाई से बचें और हवा के प्रवाह को बेहतर रखें।",
                "फसल चक्र अपनाएं और पुराने अवशेष हटाएं।",
                "संभव हो तो प्रतिरोधी किस्में चुनें।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid leaving heavily infected lower leaves in the field.",
                "Avoid very dense stands that trap moisture.",
            ],
            [
                "खेत में अधिक प्रभावित निचले पत्ते छोड़ने से बचें।",
                "ऐसे घने पट्टे न बनाएं जो नमी को रोकें।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "If rust is progressing rapidly toward the upper canopy.",
                "If large parts of the field are affected before grain filling.",
            ],
            [
                "यदि रस्ट तेजी से ऊपरी पत्तियों तक बढ़ रहा हो।",
                "यदि दाने भरने से पहले खेत का बड़ा भाग प्रभावित हो।",
            ],
        ),
        "severity": _narrative_section("Moderate", "मध्यम"),
        "spread_risk": _narrative_section("Moderate", "मध्यम"),
        "hindi": {"disease": "सामान्य रस्ट", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Corn_healthy": {
        "crop": "Corn",
        "disease": "Healthy",
        "is_healthy": True,
        "what_we_found": _narrative_section(
            "The corn leaf appears healthy and no strong disease pattern is detected.",
            "मक्के का पत्ता स्वस्थ दिखाई दे रहा है और कोई मजबूत रोग पैटर्न नहीं दिख रहा है।",
        ),
        "why_it_happened": _list_section(["No strong disease pattern was detected."], ["कोई मजबूत रोग पैटर्न नहीं मिला।"]),
        "symptoms": _list_section(["No observed lesions or rust pustules."], ["कोई धब्बे या रस्ट दाने नहीं दिखे।"]),
        "risk_factors": _list_section(["No active disease pressure is visible."], ["अभी सक्रिय रोग दबाव नहीं दिख रहा है।"]),
        "immediate_actions": _list_section(["Continue normal field monitoring.", "Maintain steady moisture and healthy plant nutrition."], ["नियमित खेत निगरानी जारी रखें।", "स्थिर नमी और स्वस्थ पोषण बनाए रखें।"]),
        "management": _list_section(["No treatment is required for this sample."], ["इस नमूने के लिए कोई उपचार जरूरी नहीं है।"]),
        "prevention": _list_section(["Keep monitoring and maintain healthy crop hygiene."], ["निगरानी जारी रखें और स्वस्थ फसल सफाई बनाए रखें।"]),
        "avoid": _list_section(["No active disease issue is present in this sample."], ["इस नमूने में कोई सक्रिय रोग समस्या नहीं है।"]),
        "when_to_seek_help": _list_section(["Only if symptoms appear suddenly or spread rapidly."], ["सिर्फ तभी विशेषज्ञ से सलाह लें जब लक्षण अचानक दिखाई दें या तेजी से फैलें।"]),
        "severity": _narrative_section("Low", "कम"),
        "spread_risk": _narrative_section("Low", "कम"),
        "hindi": {"disease": "स्वस्थ", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Pepper_bacterial_spot": {
        "crop": "Pepper",
        "disease": "Bacterial Spot",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The pepper leaf shows symptoms consistent with bacterial spot, including water-soaked lesions with yellow halos.",
            "मिर्च के पत्ते में बैक्टीरियल स्पॉट के अनुरूप पानी जैसा धब्बे और पीले चकत्ते दिखाई दे रहे हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "Bacterial spot is caused by bacteria that spread with splashing water, machinery and contaminated leaves.",
                "High humidity and leaf wetness favour disease spread.",
                "Warm, wet weather and stress can make the disease worse.",
            ],
            [
                "बैटेरियल स्पॉट बैक्टीरिया के कारण होता है जो पानी की छींटों, मशीनरी और संक्रमित पत्तों से फैलता है।",
                "उच्च नमी और पत्तों की नमी संक्रमण बढ़ाती है।",
                "गर्म, नम मौसम और तनाव रोग को और खराब कर सकते हैं।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Water-soaked spots with yellow halos on leaves",
                "Lesions may turn dark and dry out over time",
                "Severe outbreaks can reduce the plant’s vigour and fruit quality",
            ],
            [
                "पत्तों पर पानी जैसा धब्बे और पीले चकत्ते",
                "धब्बे बाद में गहरे और सूखे दिखाई दे सकते हैं",
                "भारी संक्रमण से पौधे की ताकत और फलों की गुणवत्ता कम हो सकती है",
            ],
        ),
        "risk_factors": _list_section(
            [
                "Leaf wetness from rain or overhead irrigation",
                "Crowded planting and poor air movement",
                "Movement of diseased crop debris",
            ],
            [
                "बारिश या ओवरहेड सिंचाई से पत्तों की नमी",
                "घनी बुवाई और खराब हवा का प्रवाह",
                "संक्रमित फसल के अवशेषों का ले जाना",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Remove badly affected leaves where practical.",
                "Avoid overhead irrigation and reduce leaf wetness.",
                "Inspect nearby plants for the same symptoms.",
            ],
            [
                "संभव हो तो ज्यादा प्रभावित पत्ते निकाल दें।",
                "ओवरहेड सिंचाई से बचें और पत्तों की नमी कम करें।",
                "आस-पास के पौधों में समान लक्षण देखें।",
            ],
        ),
        "management": _list_section(
            [
                "Improve spacing, airflow and sanitation in the field.",
                "Remove and discard severely diseased plant material.",
                "Use only a locally approved treatment recommended for pepper bacterial spot and follow the label.",
            ],
            [
                "खेत में दूरी, हवा और सफाई बेहतर करें।",
                "अत्यधिक प्रभावित पौधों के मलबे को हटाकर फेंक दें।",
                "केवल स्थानीय रूप से स्वीकृत, मिर्च बैक्टीरियल स्पॉट के लिए अनुशंसित उपचार का उपयोग करें और लेबल का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Use clean planting material and avoid moving infected debris.",
                "Keep foliage dry and reduce humidity around plants.",
                "Practice regular field sanitation.",
            ],
            [
                "स्वच्छ रोपण सामग्री का उपयोग करें और संक्रमित अवशेष ले जाने से बचें।",
                "पत्तों को सूखा रखें और पौधों के आसपास नमी कम करें।",
                "नियमित खेत सफाई का पालन करें।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid overhead watering when leaves remain wet for long periods.",
                "Avoid moving infected leaves or debris between beds.",
            ],
            [
                "ओवरहेड सिंचाई से बचें जब पत्ते लंबे समय तक गीले रहें।",
                "संक्रमित पत्तों या अवशेषों को बेड के बीच ले जाने से बचें।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "If the disease is affecting many plants or fruit quality is dropping quickly.",
                "If disease pressure remains high after sanitation and field adjustments.",
            ],
            [
                "यदि रोग कई पौधों को प्रभावित कर रहा हो या फलों की गुणवत्ता जल्दी गिर रही हो।",
                "यदि सफाई और खेत में बदलाव के बाद भी रोग का दबाव बना रहे।",
            ],
        ),
        "severity": _narrative_section("Moderate", "मध्यम"),
        "spread_risk": _narrative_section("High", "उच्च"),
        "hindi": {"disease": "बैक्टीरियल स्पॉट", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Pepper_healthy": {
        "crop": "Pepper",
        "disease": "Healthy",
        "is_healthy": True,
        "what_we_found": _narrative_section("The pepper leaf appears healthy and no strong disease pattern is detected.", "मिर्च का पत्ता स्वस्थ दिखाई दे रहा है और कोई मजबूत रोग पैटर्न नहीं दिख रहा है।"),
        "why_it_happened": _list_section(["No strong disease pattern was detected."], ["कोई मजबूत रोग पैटर्न नहीं मिला।"]),
        "symptoms": _list_section(["No lesions, spotting or yellow halo symptoms are evident."], ["कोई धब्बे, स्पॉटिंग या पीले चकत्ते के लक्षण नहीं हैं।"]),
        "risk_factors": _list_section(["No clear bacterial pressure is visible at this moment."], ["अभी कोई स्पष्ट बैक्टीरियल दबाव नहीं दिख रहा है।"]),
        "immediate_actions": _list_section(["Keep regular field checks going.", "Maintain steady watering and airflow."], ["नियमित खेत जांच जारी रखें।", "स्थिर पानी और हवा का प्रवाह बनाए रखें।"]),
        "management": _list_section(["No treatment is needed for this sample."], ["इस नमूने के लिए कोई उपचार आवश्यक नहीं है।"]),
        "prevention": _list_section(["Continue good field hygiene and routine scouting."], ["अच्छी फसल सफाई और नियमित निगरानी जारी रखें।"]),
        "avoid": _list_section(["No active disease issue is present in this sample."], ["इस नमूने में कोई सक्रिय रोग समस्या नहीं है।"]),
        "when_to_seek_help": _list_section(["Only if new symptoms appear or plants suddenly decline."], ["सिर्फ तभी विशेषज्ञ से सलाह लें जब नए लक्षण दिखाई दें या पौधे अचानक कमजोर पड़ें।"]),
        "severity": _narrative_section("Low", "कम"),
        "spread_risk": _narrative_section("Low", "कम"),
        "hindi": {"disease": "स्वस्थ", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Potato_early_blight": {
        "crop": "Potato",
        "disease": "Early Blight",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The potato leaf shows patterns consistent with early blight, including brown lesions with concentric ring-like markings.",
            "आलू के पत्ते में अगेती झुलसा के अनुरूप भूरे धब्बे दिखाई दे रहे हैं, जिनमें वृत्ताकार छल्ले जैसे निशान हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "Early blight is associated with the fungus Alternaria solani.",
                "The disease can survive on infected crop debris and in soil.",
                "Warm, humid weather and repeated leaf wetness encourage infection.",
                "Older leaves and stressed plants are often affected first.",
            ],
            [
                "अगेती झुलसा फफूंद Alternaria solani से जुड़ा है।",
                "यह रोग संक्रमित फसल अवशेषों और मिट्टी में जीवित रह सकता है।",
                "गर्म, नम मौसम और बार-बार पत्ती की नमी संक्रमण को बढ़ाती है।",
                "पुराने पत्ते और तनावग्रस्त पौधे अक्सर पहले प्रभावित होते हैं।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Brown circular or irregular lesions on lower leaves",
                "Target-like concentric rings within spots",
                "Yellowing around lesions and early leaf drop under severe infection",
            ],
            [
                "निचले पत्तों पर भूरे गोल या अनियमित धब्बे",
                "धब्बों के भीतर लक्ष्य जैसा वृत्ताकार छल्ला",
                "धब्बों के आसपास पीला पड़ना और भारी संक्रमण में पत्तियों का जल्दी गिरना",
            ],
        ),
        "risk_factors": _list_section(
            [
                "Warm, humid weather and leaf wetness",
                "Infected crop residue left in the field",
                "Dense stands with poor airflow",
            ],
            [
                "गर्म, नम मौसम और पत्ती की नमी",
                "खेत में संक्रमित फसल के अवशेष रह जाना",
                "अच्छी हवा न होने वाले घने पौधे",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Remove severely affected lower leaves where practical.",
                "Keep infected debris away from healthy plants.",
                "Avoid unnecessary overhead watering and maintain spacing.",
            ],
            [
                "संभव हो तो अत्यधिक प्रभावित निचली पत्तियाँ हटा दें।",
                "संक्रमित अवशेष स्वस्थ पौधों से दूर रखें।",
                "अनावश्यक ओवरहेड सिंचाई से बचें और दूरी बनाए रखें।",
            ],
        ),
        "management": _list_section(
            [
                "Use sanitation, proper spacing and moisture management.",
                "Rotate crops where practical and remove infected residues after harvest.",
                "Use only a locally approved treatment recommended for potato early blight and follow the label.",
            ],
            [
                "सफाई, सही दूरी और नमी प्रबंधन का उपयोग करें।",
                "संभव हो तो फसल चक्र अपनाएं और कटाई के बाद संक्रमित अवशेष हटाएं।",
                "केवल स्थानीय रूप से स्वीकृत, आलू अगेती झुलसा के लिए अनुशंसित उपचार का उपयोग करें और लेबल का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Remove crop debris after harvest.",
                "Use healthy seed tubers and avoid crowding.",
                "Maintain suitable plant spacing and monitor regularly.",
            ],
            [
                "कटाई के बाद फसल अवशेष हटाएं।",
                "स्वस्थ बीज कंद का उपयोग करें और घनत्व से बचें।",
                "उचित दूरी बनाकर नियमित निगरानी करें।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid leaving heavily infected leaves and debris in the field.",
                "Avoid repeated overhead watering that keeps leaves wet.",
            ],
            [
                "अत्यधिक संक्रमित पत्ते और अवशेष खेत में छोड़ने से बचें।",
                "बार-बार ओवरहेड सिंचाई से बचें जो पत्तों को गीला रखे।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "If the disease is spreading upward across many plants.",
                "If the field shows rapid leaf loss or uncertain diagnosis.",
            ],
            [
                "यदि रोग कई पौधों में ऊपर की ओर तेजी से फैल रहा हो।",
                "यदि खेत में पत्तियों का तेजी से गिरना या अनिश्चित निदान हो।",
            ],
        ),
        "severity": _narrative_section("Moderate", "मध्यम"),
        "spread_risk": _narrative_section("Moderate", "मध्यम"),
        "hindi": {"disease": "अगेती झुलसा", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Potato_late_blight": {
        "crop": "Potato",
        "disease": "Late Blight",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The leaf shows symptoms consistent with late blight, including water-soaked lesions that can spread rapidly in cool, wet weather.",
            "पत्ते में पछेती झुलसा के अनुरूप पानी जैसा धब्बे दिख रहे हैं, जो ठंडे, नम मौसम में बहुत तेजी से फैल सकते हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "Late blight is caused by Phytophthora infestans, a rapidly spreading pathogen.",
                "Cool nights, fog, dew and rain create ideal conditions for spread.",
                "Infected seed, volunteers and discarded tubers can carry the disease into a field.",
            ],
            [
                "पछेती झुलसा Phytophthora infestans नामक जीव द्वारा होता है, जो बहुत तेजी से फैलता है।",
                "ठंडी रातें, कोहरा, ओस और बारिश फैलने के लिए आदर्श परिस्थिति बनाती हैं।",
                "संक्रमित बीज, स्वयं उगे पौधे और फेंके गए कंद रोग को खेत में ले जा सकते हैं।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Water-soaked patches on leaves that expand quickly",
                "White fuzzy growth on the underside in humid conditions",
                "Dark stem lesions and soft rotting can occur in severe outbreaks",
            ],
            [
                "पत्तों पर पानी जैसा धब्बे जो जल्दी फैलते हैं",
                "नम मौसम में पत्तियों की निचली सतह पर सफेद रूसी फफूंद",
                "भारी संक्रमण में तने पर काले धब्बे और नरम सड़न दिखाई दे सकती है",
            ],
        ),
        "risk_factors": _list_section(
            [
                "Cool, foggy, wet weather",
                "Infected seed or discarded tubers",
                "Poor field sanitation and nearby volunteer plants",
            ],
            [
                "ठंडा, कोहरे वाला, नम मौसम",
                "संक्रमित बीज या फेंके गए कंद",
                "खेत की खराब सफाई और आसपास उगे हुए स्वैच्छिक पौधे",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Act quickly and inspect the whole field for new lesions.",
                "Remove infected foliage from small areas where practical.",
                "Contact local agricultural support and follow their guidance urgently.",
            ],
            [
                "जल्दी कदम उठाएं और पूरे खेत में नए धब्बे देखें।",
                "संभव हो तो छोटे क्षेत्रों से संक्रमित पत्ते हटा दें।",
                "स्थानीय कृषि सहायता से तुरंत संपर्क करें और उनकी सलाह का पालन करें।",
            ],
        ),
        "management": _list_section(
            [
                "Rapidly monitor the field and remove infected tissues when practical.",
                "Improve drainage and avoid extended leaf wetness.",
                "Use only a locally approved treatment recommended for late blight and follow the label or local advice.",
            ],
            [
                "तेजी से खेत की निगरानी करें और संभव हो तो संक्रमित ऊतक हटाएं।",
                "जल निकासी बेहतर करें और लंबे समय तक पत्ती की नमी से बचें।",
                "केवल स्थानीय रूप से स्वीकृत, पछेती झुलसा के लिए अनुशंसित उपचार का उपयोग करें और लेबल या स्थानीय सलाह का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Use healthy certified seed only.",
                "Remove volunteer potato plants and cull piles.",
                "Watch weather conditions and act quickly during cool wet spells.",
            ],
            [
                "केवल स्वस्थ प्रमाणित बीज का उपयोग करें।",
                "आत्म उगे आलू के पौधों और बेकार ढेरों को हटाएं।",
                "मौसम की स्थिति पर नजर रखें और ठंडे, नम समय में जल्दी कदम उठाएं।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid moving infected tubers or foliage between fields.",
                "Avoid leaving volunteer plants or infected piles near healthy crops.",
            ],
            [
                "संक्रमित कंद या पत्तियों को खेतों के बीच ले जाने से बचें।",
                "स्वस्थ फसलों के पास स्वयं उगे पौधे या संक्रमित ढेर छोड़ने से बचें।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "If symptoms are spreading quickly after rain or fog.",
                "If the field has many plants affected or large sections turning dark.",
            ],
            [
                "यदि बारिश या कोहरे के बाद लक्षण तेजी से फैल रहे हों।",
                "यदि खेत के कई पौधे प्रभावित हों या बड़े हिस्से काले पड़ रहे हों।",
            ],
        ),
        "severity": _narrative_section("High", "उच्च"),
        "spread_risk": _narrative_section("High", "उच्च"),
        "hindi": {"disease": "पछेती झुलसा", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Potato_healthy": {
        "crop": "Potato",
        "disease": "Healthy",
        "is_healthy": True,
        "what_we_found": _narrative_section("The potato leaf appears healthy and no clear disease pattern is detected.", "आलू का पत्ता स्वस्थ दिख रहा है और कोई साफ रोग पैटर्न नहीं दिखाई दे रहा है।"),
        "why_it_happened": _list_section(["No strong disease pattern was detected."], ["कोई मजबूत रोग पैटर्न नहीं मिला।"]),
        "symptoms": _list_section(["No early blight or late blight lesions are visible."], ["कोई अगेती या पछेती झुलसा के धब्बे नहीं दिख रहे हैं।"]),
        "risk_factors": _list_section(["No active blight pressure is visible right now."], ["अभी कोई सक्रिय झुलसा दबाव नहीं दिख रहा है।"]),
        "immediate_actions": _list_section(["Continue field monitoring and maintain good plant spacing.", "Keep watering steady and avoid unnecessary leaf wetness."], ["खेत की निगरानी जारी रखें और उचित दूरी बनाएं।", "सिंचाई स्थिर रखें और अनावश्यक पत्ती की नमी से बचें।"]),
        "management": _list_section(["No treatment is needed for this sample."], ["इस नमूने के लिए कोई उपचार आवश्यक नहीं है।"]),
        "prevention": _list_section(["Keep crop hygiene and regular scouting in place."], ["फसल की सफाई और नियमित निगरानी बनाए रखें।"]),
        "avoid": _list_section(["No active disease issue is present in this sample."], ["इस नमूने में कोई सक्रिय रोग समस्या नहीं है।"]),
        "when_to_seek_help": _list_section(["Only if new spots or wilting appear suddenly."], ["सिर्फ तभी विशेषज्ञ से सलाह लें जब नए धब्बे या झुकाव अचानक दिखाई दें।"]),
        "severity": _narrative_section("Low", "कम"),
        "spread_risk": _narrative_section("Low", "कम"),
        "hindi": {"disease": "स्वस्थ", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Tomato_early_blight": {
        "crop": "Tomato",
        "disease": "Early Blight",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The tomato leaf shows patterns consistent with early blight, including brown lesions with concentric ring-like markings.",
            "टमाटर के पत्ते में अगेती झुलसा के अनुरूप भूरे धब्बे दिखाई दे रहे हैं, जिनमें वृत्ताकार छल्ले जैसे निशान हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "Early blight is commonly associated with the fungus Alternaria solani.",
                "The pathogen can survive on infected crop debris and soil.",
                "Warm, humid weather and prolonged leaf wetness encourage infection.",
                "Older leaves and stressed plants are often more vulnerable.",
            ],
            [
                "अगेती झुलसा अक्सर फफूंद Alternaria solani से जुड़ा होता है।",
                "रोगजनक संक्रमित फसल के अवशेषों और मिट्टी में जीवित रह सकता है।",
                "गर्म, नम मौसम और लंबे समय तक पत्ती की नमी संक्रमण को बढ़ाती है।",
                "पुराने पत्ते और तनावग्रस्त पौधे अक्सर अधिक संवेदनशील रहते हैं।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Brown circular or irregular lesions on lower leaves",
                "Concentric ring patterns similar to a target",
                "Yellowing around lesions and early leaf drop in severe cases",
            ],
            [
                "निचले पत्तों पर भूरे गोल या अनियमित धब्बे",
                "लक्ष्य जैसा वृत्ताकार छल्ला",
                "धब्बों के आसपास पीला पड़ना और गंभीर मामलों में पत्तियों का जल्दी गिरना",
            ],
        ),
        "risk_factors": _list_section(
            [
                "Warm, humid weather and rain splash",
                "Long periods of leaf wetness from irrigation or dew",
                "Dense plantings and older stressed foliage",
            ],
            [
                "गर्म, नम मौसम और बारिश की छींटें",
                "सिंचाई या ओस के कारण लंबे समय तक पत्ती की नमी",
                "घने रोपण और पुराने, तनावग्रस्त पत्ते",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Remove severely affected lower leaves where practical.",
                "Keep infected leaf material away from healthy plants.",
                "Avoid overhead watering and improve airflow between plants.",
            ],
            [
                "संभव हो तो अत्यधिक प्रभावित निचली पत्तियाँ हटा दें।",
                "संक्रमित पत्तियों को स्वस्थ पौधों से दूर रखें।",
                "ओवरहेड सिंचाई से बचें और पौधों के बीच हवा का प्रवाह बेहतर करें।",
            ],
        ),
        "management": _list_section(
            [
                "Use sanitation, foliage hygiene and crop rotation where practical.",
                "Reduce leaf wetness and keep plant spacing suitable for airflow.",
                "Use only a locally approved treatment recommended for tomato early blight and follow the label.",
            ],
            [
                "सफाई, पत्ते की स्वच्छता और फसल चक्र का उपयोग करें।",
                "पत्ती की नमी कम करें और पौधों के बीच उचित दूरी बनाएं।",
                "केवल स्थानीय रूप से स्वीकृत, टमाटर अगेती झुलसा के लिए अनुशंसित उपचार का उपयोग करें और लेबल का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Remove infected crop debris after harvest.",
                "Maintain good spacing and airflow.",
                "Monitor plants frequently during warm, humid weather.",
            ],
            [
                "कटाई के बाद संक्रमित फसल अवशेष हटाएं।",
                "अच्छी दूरी और हवा का प्रवाह बनाए रखें।",
                "गर्म, नम मौसम में पौधों की नियमित निगरानी करें।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid leaving heavily infected debris around plants.",
                "Avoid overhead watering that keeps the canopy wet for long periods.",
            ],
            [
                "पौधों के आसपास अत्यधिक संक्रमित अवशेष छोड़ने से बचें।",
                "ओवरहेड सिंचाई से बचें जो छत्र को लंबे समय तक गीला रखे।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "If the disease is rapidly spreading across multiple plants or rows.",
                "If the plant is quickly losing leaves and you are unsure of the diagnosis.",
            ],
            [
                "यदि रोग कई पौधों या कतारों में तेजी से फैल रहा हो।",
                "यदि पौधा जल्दी पत्ते खो रहा हो और निदान असमंजस में हो।",
            ],
        ),
        "severity": _narrative_section("Moderate", "मध्यम"),
        "spread_risk": _narrative_section("High", "उच्च"),
        "hindi": {"disease": "अगेती झुलसा", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Tomato_late_blight": {
        "crop": "Tomato",
        "disease": "Late Blight",
        "is_healthy": False,
        "what_we_found": _narrative_section(
            "The tomato leaf shows signs consistent with late blight, including water-soaked lesions that can expand quickly under cool, wet conditions.",
            "टमाटर के पत्ते में पछेती झुलसा के अनुरूप पानी जैसा धब्बे दिखाई दे रहे हैं, जो ठंडे, नम परिस्थितियों में जल्दी फैल सकते हैं।",
        ),
        "why_it_happened": _list_section(
            [
                "Late blight is caused by the pathogen Phytophthora infestans.",
                "Cool nights, fog and persistent moisture create ideal conditions for rapid spread.",
                "Infected seed, volunteer plants and infected debris can carry the disease into the field.",
            ],
            [
                "पछेती झुलसा रोगजनक Phytophthora infestans के कारण होता है।",
                "ठंडी रातें, कोहरा और लगातार नमी तेजी से फैलने के लिए आदर्श स्थिति बनाते हैं।",
                "संक्रमित बीज, स्वयं उगे पौधे और संक्रमित अवशेष खेत में रोग ले जा सकते हैं।",
            ],
        ),
        "symptoms": _list_section(
            [
                "Water-soaked leaf lesions that expand rapidly",
                "Pale green to dark patches with irregular edges",
                "White fuzzy growth may appear under humid conditions",
            ],
            [
                "पत्तों पर पानी जैसा धब्बे जो जल्दी फैलते हैं",
                "हल्के हरे से गहरे धब्बे अनियमित किनारों के साथ",
                "नम मौसम में नीचे सफेद रूसी फफूंद दिखाई दे सकती है",
            ],
        ),
        "risk_factors": _list_section(
            [
                "Cool, foggy and rainy weather",
                "Nearby volunteer potato or tomato plants",
                "Poor sanitation and infected debris left near crops",
            ],
            [
                "ठंडा, कोहरे वाला और बरसाती मौसम",
                "आस-पास के स्वयं उगे आलू या टमाटर के पौधे",
                "खेत की खराब सफाई और आस-पास छोड़ा गया संक्रमित अवशेष",
            ],
        ),
        "immediate_actions": _list_section(
            [
                "Act quickly: inspect the whole field and check for new lesions.",
                "Remove infected foliage from small affected areas when practical.",
                "Contact local agriculture support without delay.",
            ],
            [
                "जल्दी काम करें: पूरे खेत की जांच करें और नए धब्बे देखें।",
                "संभव हो तो छोटे प्रभावित क्षेत्रों से संक्रमित पत्ते हटा दें।",
                "विलंब किए बिना स्थानीय कृषि सहायता से संपर्क करें।",
            ],
        ),
        "management": _list_section(
            [
                "Prioritize rapid monitoring and sanitation.",
                "Manage leaf wetness and avoid overcrowding.",
                "Use only a locally approved treatment recommended for tomato late blight and follow the label or local guidance.",
            ],
            [
                "तेजी से निगरानी और सफाई को प्राथमिकता दें।",
                "पत्ती की नमी और भीड़भाड़ को कम रखें।",
                "केवल स्थानीय रूप से स्वीकृत, टमाटर पछेती झुलसा के लिए अनुशंसित उपचार का उपयोग करें और लेबल या स्थानीय सलाह का पालन करें।",
            ],
        ),
        "prevention": _list_section(
            [
                "Use healthy planting material and remove volunteers.",
                "Avoid wet, crowded canopies and improve airflow.",
                "Monitor the crop carefully during cool, wet weather.",
            ],
            [
                "स्वस्थ रोपण सामग्री का उपयोग करें और स्वयं उगे पौधों को हटाएं।",
                "गीले और घने छत्र से बचें और हवा का प्रवाह बेहतर करें।",
                "ठंडे, नम मौसम में फसल की सावधानी से निगरानी करें।",
            ],
        ),
        "avoid": _list_section(
            [
                "Avoid moving infected leaves or tubers between areas.",
                "Avoid leaving volunteer plants or cull piles around healthy crops.",
            ],
            [
                "संक्रमित पत्ते या कंदों को क्षेत्रों के बीच ले जाने से बचें।",
                "स्वस्थ फसलों के आसपास स्वयं उगे पौधे या बेकार ढेर छोड़ने से बचें।",
            ],
        ),
        "when_to_seek_help": _list_section(
            [
                "If disease symptoms expand quickly after rain or dew.",
                "If multiple plants or rows are affected in a short time.",
            ],
            [
                "यदि बारिश या ओस के बाद लक्षण तेजी से फैल रहे हों।",
                "यदि कम समय में कई पौधे या कतारें प्रभावित हों।",
            ],
        ),
        "severity": _narrative_section("High", "उच्च"),
        "spread_risk": _narrative_section("High", "उच्च"),
        "hindi": {"disease": "पछेती झुलसा", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
    "Tomato_healthy": {
        "crop": "Tomato",
        "disease": "Healthy",
        "is_healthy": True,
        "what_we_found": _narrative_section("The tomato leaf appears healthy and no strong disease pattern is detected.", "टमाटर का पत्ता स्वस्थ दिख रहा है और कोई मजबूत रोग पैटर्न नहीं दिखाई दे रहा है।"),
        "why_it_happened": _list_section(["No strong disease pattern was detected in this sample."], ["इस नमूने में कोई मजबूत रोग पैटर्न नहीं मिला।"]),
        "symptoms": _list_section(["No lesions or abnormal yellowing were detected."], ["कोई धब्बे या असामान्य पीला पड़ना नहीं मिला।"]),
        "risk_factors": _list_section(["No active disease pressure is visible right now."], ["अभी कोई सक्रिय रोग दबाव नहीं दिख रहा है।"]),
        "immediate_actions": _list_section(["Continue regular monitoring.", "Maintain appropriate watering and airflow."], ["नियमित निगरानी जारी रखें।", "उचित सिंचाई और हवा का प्रवाह बनाए रखें।"]),
        "management": _list_section(["No treatment is needed for this sample."], ["इस नमूने के लिए कोई उपचार आवश्यक नहीं है।"]),
        "prevention": _list_section(["Continue crop hygiene and regular checks."], ["फसल सफाई और नियमित जांच जारी रखें।"]),
        "avoid": _list_section(["No active disease issue is present in this sample."], ["इस नमूने में कोई सक्रिय रोग समस्या नहीं है।"]),
        "when_to_seek_help": _list_section(["Only if new symptoms appear or the crop suddenly declines."], ["सिर्फ तभी विशेषज्ञ से सलाह लें जब नए लक्षण दिखाई दें या फसल अचानक कमजोर पड़ जाए।"]),
        "severity": _narrative_section("Low", "कम"),
        "spread_risk": _narrative_section("Low", "कम"),
        "hindi": {"disease": "स्वस्थ", "what_we_found": "", "why_it_happened": [], "symptoms": [], "risk_factors": [], "immediate_actions": [], "management": [], "prevention": [], "avoid": [], "when_to_seek_help": []},
    },
}


@lru_cache(maxsize=1)
def supported_disease_names() -> list[str]:
    names = set(DISEASE_INFO)
    for item in _classes():
        names.add(item["class_name"])
    return sorted(names)


def list_supported_classes() -> list[str]:
    return supported_disease_names()


def validate_supporting_data() -> list[str]:
    missing = []
    for class_name in supported_disease_names():
        try:
            profile = _profile_for_key(class_name)
        except KeyError:
            missing.append(f"{class_name}: no advisory profile")
            continue
        for field in REQUIRED_FIELDS:
            value = profile.get(field)
            if value is None:
                missing.append(f"{class_name}: missing {field}")
                continue
            if isinstance(value, dict) and "en" in value and "hi" in value:
                if value["en"] in (None, "") or value["hi"] in (None, ""):
                    missing.append(f"{class_name}: empty bilingual value for {field}")
            elif isinstance(value, dict):
                if not value:
                    missing.append(f"{class_name}: empty {field}")
            elif isinstance(value, list):
                if not value:
                    missing.append(f"{class_name}: empty {field}")
    return missing


def prediction_block(class_name: str, confidence: float) -> dict:
    """The ML prediction, in the exact shape requested for the API."""
    class_key = _alias_key(class_name)
    # Prefer the configured class metadata when it exists; otherwise fall back to the disease database.
    c = _by_name().get(class_name, _by_name().get(class_key, {"crop": DISEASE_INFO.get(class_key, {}).get("crop", "Unknown"), "disease": DISEASE_INFO.get(class_key, {}).get("disease", "Unknown"), "is_healthy": False, "crop_hi": "अज्ञात", "disease_hi": "अज्ञात"}))
    prediction = {
        "class_name": class_name,
        "crop": c["crop"],
        "disease": c["disease"],
        "confidence": round(float(confidence), 4),
        "is_healthy": c.get("is_healthy", False),
        "crop_hi": c.get("crop_hi", c["crop"]),
        "disease_hi": c.get("disease_hi", c["disease"]),
    }
    canonical = _canonical_class_name(class_name)
    crop_i18n = {"en": c["crop"], "hi": c.get("crop_hi", c["crop"])}
    disease_i18n = {"en": c["disease"], "hi": c.get("disease_hi", c["disease"])}
    for language in _ADVICE_LANGUAGES:
        translated = _advice_translations(language).get(canonical, {})
        crop_name = translated.get("crop") or c.get(f"crop_{language}")
        disease_name = translated.get("disease") or c.get(f"disease_{language}")
        if crop_name:
            crop_i18n[language] = crop_name
            prediction[f"crop_{language}"] = crop_name
        if disease_name:
            disease_i18n[language] = disease_name
            prediction[f"disease_{language}"] = disease_name
    prediction["crop_i18n"] = crop_i18n
    prediction["disease_i18n"] = disease_i18n
    return prediction


@lru_cache(maxsize=1)
def _guidance() -> dict:
    # Backwards-compatibility for older code paths. This is built from the structured disease profiles.
    out = {}
    for class_name in list_supported_classes():
        try:
            profile = _profile_for_key(class_name)
        except KeyError:
            continue
        out[class_name] = profile
        out[_norm_class_name(class_name)] = profile
    return out


def get_guidance(class_name: str) -> dict:
    key = _alias_key(class_name)
    if key in DISEASE_INFO:
        return _profile_for_key(key)
    if class_name in _guidance():
        return _guidance()[class_name]
    raise KeyError(f"No disease advisory exists for {class_name!r}")


def get_disease_profile(class_name: str) -> dict:
    return get_guidance(class_name)

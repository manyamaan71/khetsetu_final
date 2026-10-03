import json
from pathlib import Path

from app.disease_info import get_guidance


ROOT = Path(__file__).resolve().parents[1]
LANGUAGES = ("kn", "ta", "te", "mr", "bn")
FIELDS = (
    "what_we_found", "what_is_it", "why_it_happened", "possible_cause",
    "symptoms", "immediate_actions", "basic_care", "management", "prevention",
    "avoid", "when_to_seek_help", "consult_expert_when", "severity", "spread_risk",
    "source_note",
)


def test_reviewed_advice_list_lengths_match_english():
    directory = ROOT / "data" / "advice_i18n"
    canonical_classes = [
        item["class_name"]
        for item in json.loads((ROOT / "model" / "class_config.json").read_text(encoding="utf-8"))["classes"]
    ]
    for language in LANGUAGES:
        path = directory / f"{language}.json"
        reviewed = json.loads(path.read_text(encoding="utf-8"))
        assert reviewed["status"] == "reviewed"
        classes = reviewed["classes"]
        if not classes:
            continue
        assert set(classes) == set(canonical_classes)
        for class_name in canonical_classes:
            translated_class = classes[class_name]
            english = get_guidance(class_name)
            assert isinstance(translated_class["crop"], str)
            assert isinstance(translated_class["disease"], str)
            assert set(translated_class["fields"]) == set(FIELDS)
            for field in FIELDS:
                translated = translated_class["fields"][field]
                if isinstance(english[field], list):
                    assert isinstance(translated, list)
                    assert len(translated) == len(english[field]), (language, class_name, field)
                else:
                    assert isinstance(translated, str), (language, class_name, field)

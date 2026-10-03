"""
ai_explanation_service.py

Optional integration point for Google Gemini to turn the ALREADY-DECIDED
ML result + trusted guidance.json data into a short, simple, farmer-friendly
explanation.

Architecture (never violated):
    image -> ML classifier (model.py) -> crop + disease + confidence
          -> disease_info.get_guidance()  (trusted, human-written)
          -> [OPTIONAL] Gemini rewrites/summarises that trusted content
          -> existing UI

Gemini is GROUNDED: every fact it is allowed to mention comes from
guidance.json, passed to it in the prompt. It is explicitly told not to
name a disease of its own choosing, not to add facts that are not in the
supplied guidance, and not to give pesticide dosages. Its output is always
additive (`extra_explanation`) and never replaces disease_info.py's
symptoms / possible_cause / prevention, which the UI already renders
regardless of whether Gemini is configured.

Disabled unless GEMINI_API_KEY is set. Any failure (missing key, network,
quota, malformed response) falls back to returning None so the caller uses
guidance.json text directly - Gemini is never a required dependency.
"""
from ..config import settings

_MAX_LIST_ITEMS = 4


def is_available() -> bool:
    return bool(settings.GEMINI_API_KEY)


def _guidance_context(guidance: dict, language: str) -> str:
    """Flatten the trusted guidance fields Gemini is allowed to draw on."""
    lang = language if language in ("hi", "kn", "ta", "te", "mr", "bn") else "en"

    def txt(key: str) -> str:
        val = guidance.get(key)
        if isinstance(val, dict):
            return val.get(lang) or val.get("en") or ""
        return ""

    def items(key: str) -> list[str]:
        val = guidance.get(key)
        if isinstance(val, dict):
            lst = val.get(lang) or val.get("en") or []
            return list(lst)[:_MAX_LIST_ITEMS]
        return []

    lines = [
        f"What it is: {txt('what_is_it')}",
        f"Symptoms: {'; '.join(items('symptoms'))}",
        f"Possible cause: {txt('possible_cause')}",
        f"What to do: {'; '.join(items('basic_care'))}",
        f"Prevention: {'; '.join(items('prevention'))}",
    ]
    return "\n".join(line for line in lines if line.split(": ", 1)[1])


def generate_extra_explanation(crop: str, disease: str, language: str = "en",
                               confidence: float | None = None,
                               guidance: dict | None = None) -> str | None:
    """Returns an additive plain-language explanation string grounded in
    `guidance`, or None if the integration is disabled, unconfigured, or
    the request fails for any reason. NEVER used to pick crop/disease -
    those are passed in already decided by the ML classifier."""
    if not is_available():
        return None

    try:
        from google import genai

        client = genai.Client(api_key=settings.GEMINI_API_KEY)

        lang_map = {"en": "English", "hi": "Hindi", "kn": "Kannada", "ta": "Tamil", "te": "Telugu", "mr": "Marathi", "bn": "Bengali"}
        lang_name = lang_map.get(language, "English")
        context = _guidance_context(guidance, language) if guidance else ""
        conf_pct = f"{confidence * 100:.0f}%" if confidence is not None else "unknown"

        prompt = (
            "You are writing a short farmer-facing note for an agricultural app. "
            "A trained image-classification model has ALREADY determined the crop and "
            "condition below - do not question, change, or re-diagnose it.\n\n"
            f"Crop: {crop}\nCondition: {disease}\nModel confidence: {conf_pct}\n\n"
            f"Trusted reference information (use ONLY facts from here, in your own simple words):\n"
            f"{context}\n\n"
            f"Write 2-3 short, simple sentences in {lang_name} for a farmer with limited literacy, "
            "summarising what this means and the single most important next step. "
            "Do not invent facts not in the reference information above. "
            "Do not name any pesticide product or give a dosage. "
            "Do not mention percentages, models, or AI."
        )
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={"temperature": 0.4, "max_output_tokens": 200},
        )
        text = (getattr(response, "text", "") or "").strip()
        return text or None
    except Exception as exc:  # noqa: BLE001 - Gemini must never be a hard dependency
        import logging
        logging.getLogger("khetsetu.gemini").warning("Gemini explanation request failed: %s", exc)
        return None

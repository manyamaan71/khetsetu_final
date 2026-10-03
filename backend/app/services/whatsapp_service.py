"""
whatsapp_service.py - WhatsApp Cloud API glue + reply composer.

Photo  -> download media -> analysis_service.analyze_image (same pipeline as the web app)
       -> reply composer (English message + Hindi message)
Text   -> BHAV TOMATO / PRICE POTATO / भाव आलू -> market_service -> price reply
Anything else -> short help message.

All credentials come from environment variables (config.py). They are never sent to the browser.
When credentials are missing, replies are logged instead of sent, so the flow is testable locally.
"""
import asyncio
import hashlib
import hmac
import logging
import re

import httpx

from ..config import settings
from . import market_service
from .analysis_service import analyze_image
from ..preprocessing import InvalidImageError

log = logging.getLogger("khetsetu.whatsapp")

GRAPH = "https://graph.facebook.com"
FOOTER_EN = "General farming advice, not a lab test. Follow locally approved product labels and ask your agriculture officer / KVK."
FOOTER_HI = "यह सामान्य कृषि सलाह है, प्रयोगशाला जांच नहीं। स्थानीय रूप से मान्य दवा-लेबल का पालन करें और अपने कृषि अधिकारी / KVK से पूछें।"

PRICE_WORDS = {"bhav", "bhaav", "bhaw", "price", "rate", "mandi", "prices", "भाव", "कीमत", "दाम", "रेट", "मंडी"}
COMMODITIES = {  # alias -> data.gov.in commodity name
    "tomato": "Tomato", "tamatar": "Tomato", "टमाटर": "Tomato",
    "potato": "Potato", "aloo": "Potato", "alu": "Potato", "आलू": "Potato",
    "maize": "Maize", "corn": "Maize", "makka": "Maize", "मक्का": "Maize", "मकई": "Maize",
}
EMOJI = {"Tomato": "🍅", "Potato": "🥔", "Maize": "🌽"}
HI_NAME = {"Tomato": "टमाटर", "Potato": "आलू", "Maize": "मक्का"}

_seen_ids: list[str] = []          # WhatsApp retries deliveries; ignore ids we already handled


# ------------------------------------------------------------------ security
def verify_signature(raw_body: bytes, header: str | None) -> bool:
    """X-Hub-Signature-256 check. Skipped (True) only when no app secret is configured."""
    if not settings.WHATSAPP_APP_SECRET:
        return True
    if not header or not header.startswith("sha256="):
        return False
    digest = hmac.new(settings.WHATSAPP_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, header.split("=", 1)[1])


def is_configured() -> bool:
    return bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)


def already_handled(message_id: str) -> bool:
    if message_id in _seen_ids:
        return True
    _seen_ids.append(message_id)
    del _seen_ids[:-500]
    return False


# ------------------------------------------------------------------ Graph API
def send_text(to: str, body: str) -> bool:
    if not is_configured():
        log.warning("[WhatsApp not configured] would send to %s:\n%s", to, body)
        return False
    try:
        r = httpx.post(
            f"{GRAPH}/{settings.WHATSAPP_GRAPH_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages",
            headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"},
            json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": body[:4000]}},
            timeout=15)
        r.raise_for_status()
        return True
    except Exception as exc:                                                 # noqa: BLE001
        log.error("WhatsApp send failed: %s", exc)
        return False


def download_media(media_id: str) -> bytes:
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"}
    with httpx.Client(timeout=20) as c:
        meta = c.get(f"{GRAPH}/{settings.WHATSAPP_GRAPH_VERSION}/{media_id}", headers=headers)
        meta.raise_for_status()
        info = meta.json()
        if int(info.get("file_size", 0) or 0) > settings.MAX_UPLOAD_BYTES:
            raise ValueError("image too large")
        f = c.get(info["url"], headers=headers)
        f.raise_for_status()
        if len(f.content) > settings.MAX_UPLOAD_BYTES:
            raise ValueError("image too large")
        return f.content


# ------------------------------------------------------------------ text intent
def parse_text(text: str) -> dict:
    t = (text or "").strip().lower()
    words = re.findall(r"[\w\u0900-\u097F]+", t)
    commodity = next((COMMODITIES[w] for w in words if w in COMMODITIES), None)
    is_price = any(w in PRICE_WORDS for w in words)
    if is_price and commodity:
        return {"intent": "price", "commodity": commodity}
    if is_price:
        return {"intent": "price_missing_crop"}
    if commodity:                                     # bare "tomato" is treated as a price question
        return {"intent": "price", "commodity": commodity}
    if not words or words[0] in {"hi", "hello", "help", "start", "namaste", "नमस्ते", "मदद"}:
        return {"intent": "help"}
    return {"intent": "unsupported"}


# ------------------------------------------------------------------ reply composer
def _bullets(items: list[str], n: int) -> str:
    return "\n".join(f"• {x}" for x in items[:n])


def compose_photo_reply(result: dict) -> tuple[str, str]:
    """-> (english_message, hindi_message)"""
    demo_en = "⚠️ *Demo Mode* - simulated result, not real AI.\n\n" if result.get("demo_mode") else ""
    demo_hi = "⚠️ *डेमो मोड* - यह नकली परिणाम है, असली AI नहीं।\n\n" if result.get("demo_mode") else ""

    if result["status"] != "ok":
        m = result["message"]
        tips_en, tips_hi = m["tips"]["en"], m["tips"]["hi"]
        return (f"{demo_en}📷 *{m['title']['en']}*\n{m['body']['en']}\n\n{_bullets(tips_en, 4)}",
                f"{demo_hi}📷 *{m['title']['hi']}*\n{m['body']['hi']}\n\n{_bullets(tips_hi, 4)}")

    p, g = result["prediction"], result["guidance"]
    pct = round(p["confidence"] * 100)
    if p["is_healthy"]:
        en = (f"{demo_en}🌱 *Healthy Leaf*\nYour {p['crop'].lower()} leaf appears healthy (AI confidence {pct}%).\n\n"
              f"*Keep doing:*\n{_bullets(g['prevention']['en'], 3)}\n\n⚠️ {FOOTER_EN}")
        hi = (f"{demo_hi}🌱 *स्वस्थ पत्ता*\nआपका {p['crop_hi']} का पत्ता स्वस्थ दिख रहा है (AI भरोसा {pct}%)।\n\n"
              f"*यह करते रहें:*\n{_bullets(g['prevention']['hi'], 3)}\n\n⚠️ {FOOTER_HI}")
        return en, hi
    urgent_en = "\n🚨 This disease can spread fast - act today." if g.get("urgency") == "act_fast" else ""
    urgent_hi = "\n🚨 यह रोग तेजी से फैल सकता है - आज ही कदम उठाएं।" if g.get("urgency") == "act_fast" else ""
    en = (f"{demo_en}🔍 *{p['crop']} - {p['disease']}* (AI confidence {pct}%){urgent_en}\n\n"
          f"{g['what_is_it']['en']}\n\n*What to do:*\n{_bullets(g['basic_care']['en'], 3)}\n\n"
          f"*Prevention:*\n{_bullets(g['prevention']['en'], 2)}\n\n*Avoid:*\n{_bullets(g['avoid']['en'], 2)}\n\n"
          f"*Ask an expert if:* {g['consult_expert_when']['en'][0]}\n\n⚠️ {FOOTER_EN}")
    hi = (f"{demo_hi}🔍 *{p['crop_hi']} - {p['disease_hi']}* (AI भरोसा {pct}%){urgent_hi}\n\n"
          f"{g['what_is_it']['hi']}\n\n*क्या करें:*\n{_bullets(g['basic_care']['hi'], 3)}\n\n"
          f"*रोकथाम:*\n{_bullets(g['prevention']['hi'], 2)}\n\n*न करें:*\n{_bullets(g['avoid']['hi'], 2)}\n\n"
          f"*विशेषज्ञ से पूछें यदि:* {g['consult_expert_when']['hi'][0]}\n\n⚠️ {FOOTER_HI}")
    return en, hi


def compose_price_reply(commodity: str) -> str:
    data = market_service.get_market_prices(commodity)
    em = EMOJI.get(commodity, "🌾")
    head = f"{em} *{commodity} / {HI_NAME.get(commodity, commodity)}* - mandi prices (₹ per quintal)"
    if not data["rows"]:
        return f"{head}\n\n{data['message']['en']}\n{data['message']['hi']}"
    rows = sorted(data["rows"], key=lambda r: r["modal_price"], reverse=True)[:5]
    lines = [f"• {r['market']}, {r['state']}: *₹{r['modal_price']}* (₹{r['min_price']}-{r['max_price']}) {r.get('date', '')}"
             for r in rows]
    note = ""
    if data["source"] == "demo":
        note = "\n\n⚠️ *Demo market data - not live prices.*\n*डेमो डेटा - असली भाव नहीं।*"
    elif data["source"] == "cached":
        note = f"\n\n⚠️ Live data unavailable. Last saved prices ({data.get('fetched_at', '')}).\nलाइव भाव उपलब्ध नहीं; पिछले सहेजे भाव।"
    else:
        note = "\n\nSource: Agmarknet / data.gov.in"
    return head + "\n\n" + "\n".join(lines) + note


HELP = ("🌾 *KhetSetu*\n📷 Send a clear photo of ONE crop leaf (tomato, potato or maize) for a health check.\n"
        "💰 Send *BHAV TOMATO*, *PRICE POTATO* or *भाव आलू* for mandi prices.\n\n"
        "📷 फसल के एक पत्ते की साफ फोटो भेजें (टमाटर, आलू या मक्का)।\n💰 भाव जानने के लिए लिखें: *भाव आलू*")
UNSUPPORTED = ("Sorry, I can only read leaf photos and price requests like *BHAV TOMATO*.\n"
               "क्षमा करें, मैं केवल पत्ते की फोटो और भाव के संदेश (जैसे *भाव आलू*) समझ पाता हूं।")
PRICE_MISSING = ("Which crop? Send for example *BHAV TOMATO*, *PRICE POTATO* or *BHAV MAIZE*.\n"
                 "कौन सी फसल? जैसे लिखें: *भाव टमाटर*, *भाव आलू*, *भाव मक्का*।")
PHOTO_ERR = ("We could not read that photo. Please send a clear JPG/PNG photo of one leaf.\n"
             "फोटो पढ़ी नहीं जा सकी। कृपया एक पत्ते की साफ JPG/PNG फोटो भेजें।")
DOWNLOAD_ERR = ("We could not download your photo. Please send it again.\nफोटो डाउनलोड नहीं हो सकी। कृपया फिर से भेजें।")
UNAVAILABLE = ("The crop scanner is not ready right now. Please try again later.\nफसल स्कैनर अभी तैयार नहीं है। कृपया बाद में कोशिश करें।")


# ------------------------------------------------------------------ dispatcher
def handle_message(msg: dict, db=None) -> None:
    """Process ONE WhatsApp message object (called from a background task)."""
    sender, mtype = msg.get("from"), msg.get("type")
    if not sender or already_handled(msg.get("id", "")):
        return
    try:
        if mtype == "image":
            from ..model import classifier
            if not classifier.available:
                send_text(sender, UNAVAILABLE)
                return
            try:
                data = download_media(msg["image"]["id"])
            except Exception as exc:                                         # noqa: BLE001
                log.error("media download failed: %s", exc)
                send_text(sender, DOWNLOAD_ERR)
                return
            try:
                result = asyncio.run(analyze_image(data, db=db, source="whatsapp"))
            except InvalidImageError:
                send_text(sender, PHOTO_ERR)
                return
            en, hi = compose_photo_reply(result)
            send_text(sender, en)
            send_text(sender, hi)
        elif mtype == "text":
            intent = parse_text(msg.get("text", {}).get("body", ""))
            if intent["intent"] == "price":
                send_text(sender, compose_price_reply(intent["commodity"]))
            elif intent["intent"] == "price_missing_crop":
                send_text(sender, PRICE_MISSING)
            elif intent["intent"] == "help":
                send_text(sender, HELP)
            else:
                send_text(sender, UNSUPPORTED)
        else:
            send_text(sender, UNSUPPORTED)
    except Exception:                                                        # noqa: BLE001
        log.exception("WhatsApp handler failed")
        send_text(sender, "Something went wrong. Please try again.\nकुछ गड़बड़ हुई। कृपया फिर से कोशिश करें।")

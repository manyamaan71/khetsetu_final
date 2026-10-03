"""
market_service.py - mandi prices.

Priority:
  1. LIVE   - data.gov.in "Current daily price of commodities" (Agmarknet), needs MARKET_API_KEY.
              Every successful response is written to data/cache/market_cache.json.
  2. CACHED - if the live call fails, the last successful response for the same query is
              returned and flagged source="cached" with its fetch time.
  3. DEMO   - ONLY when no MARKET_API_KEY is configured. Always flagged is_demo=true /
              source="demo"; the UI and WhatsApp replies say "Demo market data".
If a key IS configured but live + cache both fail we return source="unavailable" with no rows.
We never show demo numbers as if they were live.

NOTE: the live parser follows the documented data.gov.in record format (state, district,
market, commodity, arrival_date, min_price, max_price, modal_price; Rs per quintal). It has
been unit-tested against sample records but not against the live service (no API key was
available while building).
"""
import hashlib
import json
import logging
import random
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from ..config import settings

log = logging.getLogger("khetsetu.market")

COMMODITY_ALIASES = {"corn": "Maize", "maize": "Maize", "tomato": "Tomato", "potato": "Potato"}
SUPPORTED = ["Tomato", "Potato", "Maize"]

_DEMO_MARKETS = {
    "Karnataka": ["Bengaluru", "Mysuru", "Hubballi"],
    "Maharashtra": ["Pune", "Nashik", "Nagpur"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra"],
    "Punjab": ["Ludhiana", "Amritsar", "Jalandhar"],
    "Himachal Pradesh": ["Shimla", "Solan", "Kullu"],
}
_DEMO_BASE = {"Tomato": 1800, "Potato": 1400, "Maize": 2100}     # illustrative only

_TTL_SECONDS = 15 * 60
_mem: dict[str, tuple[float, dict]] = {}


def normalize_commodity(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    return COMMODITY_ALIASES.get(name.strip().lower(), name.strip().title())


def _cache_file() -> Path:
    p = Path(settings.DATA_DIR) / "cache"
    p.mkdir(parents=True, exist_ok=True)
    return p / "market_cache.json"


def _cache_read() -> dict:
    try:
        return json.loads(_cache_file().read_text(encoding="utf-8"))
    except Exception:                                                        # noqa: BLE001
        return {}


def _cache_write(key: str, payload: dict) -> None:
    try:
        data = _cache_read()
        data[key] = payload
        _cache_file().write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception as exc:                                                 # noqa: BLE001
        log.warning("could not write market cache: %s", exc)


def _num(v) -> Optional[int]:
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def parse_live_records(records: list[dict]) -> list[dict]:
    rows = []
    for r in records:
        modal = _num(r.get("modal_price"))
        if modal is None:
            continue
        rows.append({
            "market": f"{r.get('market', '')} Mandi".strip(), "crop": r.get("commodity", ""),
            "state": r.get("state", ""), "district": r.get("district", ""),
            "min_price": _num(r.get("min_price")) or modal, "max_price": _num(r.get("max_price")) or modal,
            "modal_price": modal, "date": r.get("arrival_date", ""), "unit": "quintal",
            "variety": r.get("variety", "")})
    return rows


def _fetch_live(crop, state, district) -> list[dict]:
    params = {"api-key": settings.MARKET_API_KEY, "format": "json", "limit": "50"}
    if crop:
        params["filters[commodity]"] = crop
    if state:
        params["filters[state]"] = state
    if district:
        params["filters[district]"] = district
    with httpx.Client(timeout=settings.MARKET_TIMEOUT_SECONDS) as c:
        r = c.get(settings.MARKET_API_URL, params=params)
        r.raise_for_status()
        return parse_live_records(r.json().get("records", []))


def _demo_rows(crop, state, district) -> list[dict]:
    crops = [crop] if crop in _DEMO_BASE else ([] if crop else SUPPORTED)
    states = [state] if state in _DEMO_MARKETS else ([] if state else list(_DEMO_MARKETS))
    rows = []
    for s in states:
        for d in ([district] if district else _DEMO_MARKETS[s]):
            for c in crops:
                seed = int(hashlib.sha256(f"{c}-{d}-{date.today()}".encode()).hexdigest(), 16) % 10_000
                rng = random.Random(seed)
                modal = _DEMO_BASE[c] + rng.randint(-150, 150)
                rows.append({"market": f"{d} Mandi", "crop": c, "state": s, "district": d,
                             "min_price": modal - rng.randint(50, 200), "max_price": modal + rng.randint(50, 200),
                             "modal_price": modal, "date": date.today().strftime("%d %b %Y"), "unit": "quintal"})
    return rows


def get_market_prices(crop: Optional[str] = None, state: Optional[str] = None,
                      district: Optional[str] = None) -> dict:
    crop = normalize_commodity(crop)
    key = f"{crop}|{state}|{district}"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if not settings.MARKET_API_KEY:
        return {"rows": _demo_rows(crop, state, district)[:12], "is_demo": True, "source": "demo",
                "stale": False, "fetched_at": now,
                "message": {"en": "Demo market data - not live prices.", "hi": "डेमो बाज़ार डेटा - यह असली भाव नहीं हैं।"}}

    hit = _mem.get(key)
    if hit and time.time() - hit[0] < _TTL_SECONDS:
        return hit[1]
    try:
        rows = _fetch_live(crop, state, district)
        payload = {"rows": rows[:20], "is_demo": False, "source": "live", "stale": False, "fetched_at": now,
                   "message": None if rows else {"en": "No prices reported for this search today.",
                                                 "hi": "इस खोज के लिए आज कोई भाव दर्ज नहीं है।"}}
        _mem[key] = (time.time(), payload)
        if rows:
            _cache_write(key, payload)
        return payload
    except Exception as exc:                                                 # noqa: BLE001
        log.warning("live market API failed: %s", exc)
        cached = _cache_read().get(key)
        if cached and cached.get("rows"):
            return {**cached, "source": "cached", "stale": True,
                    "message": {"en": f"Live prices are unavailable. Showing the last saved prices from {cached.get('fetched_at', 'earlier')}.",
                                "hi": "लाइव भाव अभी उपलब्ध नहीं हैं। पिछली बार सहेजे गए भाव दिखाए जा रहे हैं।"}}
        return {"rows": [], "is_demo": False, "source": "unavailable", "stale": False, "fetched_at": now,
                "message": {"en": "Market prices are not available right now. Please try again later.",
                            "hi": "बाज़ार भाव अभी उपलब्ध नहीं हैं। कृपया बाद में कोशिश करें।"}}

import json
from pathlib import Path

from app.config import settings
from app.services import market_service


FIXTURE = Path(__file__).parent / "fixtures" / "market_sample.json"


def test_parse_documented_market_sample():
    records = json.loads(FIXTURE.read_text(encoding="utf-8"))["records"]

    rows = market_service.parse_live_records(records)

    assert rows == [
        {
            "market": "Bengaluru Mandi",
            "crop": "Tomato",
            "state": "Karnataka",
            "district": "Bengaluru",
            "min_price": 1500,
            "max_price": 2100,
            "modal_price": 1800,
            "date": "02/10/2026",
            "unit": "quintal",
            "variety": "Local",
        },
        {
            "market": "Pune Mandi",
            "crop": "Potato",
            "state": "Maharashtra",
            "district": "Pune",
            "min_price": 1200,
            "max_price": 1700,
            "modal_price": 1450,
            "date": "01/10/2026",
            "unit": "quintal",
            "variety": "",
        },
        {
            "market": "Mysuru Mandi",
            "crop": "Maize",
            "state": "Karnataka",
            "district": "Mysuru",
            "min_price": 2200,
            "max_price": 2400,
            "modal_price": 2200,
            "date": "29/09/2026",
            "unit": "quintal",
            "variety": "Hybrid",
        },
    ]


def test_demo_disabled_without_key_returns_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "MARKET_API_KEY", "")
    monkeypatch.setattr(settings, "ALLOW_DEMO_MARKET", False)

    result = market_service.get_market_prices("Tomato")

    assert result["source"] == "unavailable"
    assert result["rows"] == []
    assert result["is_demo"] is False


def test_demo_disabled_on_live_failure_without_cache_returns_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "MARKET_API_KEY", "test-key")
    monkeypatch.setattr(settings, "ALLOW_DEMO_MARKET", False)
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))

    def fail_live_request(*args, **kwargs):
        raise RuntimeError("offline")

    monkeypatch.setattr(market_service, "_fetch_live", fail_live_request)
    market_service._mem.clear()

    result = market_service.get_market_prices("Tomato")

    assert result["source"] == "unavailable"
    assert result["rows"] == []
    assert result["is_demo"] is False

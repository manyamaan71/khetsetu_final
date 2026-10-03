from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..services.market_service import get_market_prices
from ..services.gemini_translation_service import TranslationUnavailableError, translate_payload
from ..rate_limit import limiter

router = APIRouter()


@router.get("/market-prices")
@limiter.limit("60/minute")
async def market_prices_endpoint(request: Request, crop: Optional[str] = Query(None, max_length=40),
                           state: Optional[str] = Query(None, max_length=40),
                           district: Optional[str] = Query(None, max_length=40),
                           language: str = Query("en", min_length=2, max_length=5)):
    # plain `def` -> FastAPI runs it in a worker thread, so a slow market API never blocks other requests
    payload = get_market_prices(crop, state, district)
    try:
        return await translate_payload(payload, language)
    except TranslationUnavailableError:
        raise HTTPException(status_code=502, detail={
            "code": "translation_unavailable",
            "message": {"en": "The selected-language translation is temporarily unavailable."},
        }) from None

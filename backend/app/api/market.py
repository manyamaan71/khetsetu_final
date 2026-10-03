from typing import Optional

from fastapi import APIRouter, Query, Request

from ..services.market_service import get_market_prices
from ..rate_limit import limiter

router = APIRouter()


@router.get("/market-prices")
@limiter.limit("60/minute")
def market_prices_endpoint(request: Request, crop: Optional[str] = Query(None, max_length=40),
                           state: Optional[str] = Query(None, max_length=40),
                           district: Optional[str] = Query(None, max_length=40)):
    # plain `def` -> FastAPI runs it in a worker thread, so a slow market API never blocks other requests
    return get_market_prices(crop, state, district)

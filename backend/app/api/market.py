from typing import Optional

from fastapi import APIRouter, Query

from ..services.market_service import get_market_prices

router = APIRouter()


@router.get("/market-prices")
def market_prices_endpoint(crop: Optional[str] = Query(None, max_length=40),
                           state: Optional[str] = Query(None, max_length=40),
                           district: Optional[str] = Query(None, max_length=40)):
    # plain `def` -> FastAPI runs it in a worker thread, so a slow market API never blocks other requests
    return get_market_prices(crop, state, district)

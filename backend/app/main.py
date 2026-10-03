"""
KhetSetu API.   Run from backend/:   uvicorn app.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from .api import admin, crops, history, market, predict, report, speech, whatsapp
from .config import settings
from .database import init_db
from .model import classifier
from .rate_limit import limiter
from .services import whatsapp_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("khetsetu")


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_production_settings()
    init_db()
    classifier.load()          # the model is loaded ONCE here, never per request
    log.info("Model status: %s", classifier.info())
    yield


def validate_production_settings() -> None:
    if settings.APP_ENV != "production":
        return
    missing = [
        name for name, value in (
            ("WHATSAPP_APP_SECRET", settings.WHATSAPP_APP_SECRET),
            ("SUPABASE_JWT_SECRET", settings.SUPABASE_JWT_SECRET),
        ) if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required production settings: {', '.join(missing)}")
    settings.REQUIRE_AUTH = True


app = FastAPI(title="KhetSetu API", description="Smart Crop Health & Market Assistant for Farmers",
              version="2.0.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins_list, allow_credentials=True,
                   allow_methods=["GET", "POST"], allow_headers=["*"])


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": {"code": "bad_request", "message": {
        "en": "Please send a photo and try again.", "hi": "कृपया एक फोटो भेजकर फिर कोशिश करें।"}}})


@app.exception_handler(Exception)
async def safe_error_handler(request: Request, exc: Exception):
    log.exception("Unhandled error on %s", request.url.path)          # full trace goes to the server log only
    return JSONResponse(status_code=500, content={"detail": {"code": "server_error", "message": {
        "en": "Something went wrong. Please try again.", "hi": "कुछ गड़बड़ हो गई। कृपया फिर से कोशिश करें।"}}})


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"detail": {"code": "rate_limited", "message": {
        "en": "Too many requests. Please try again later.",
        "hi": "बहुत अधिक अनुरोध। कृपया बाद में फिर कोशिश करें।"}}})


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": app.version, "demo_mode": classifier.is_demo,
            "model": classifier.info(), "confidence_threshold": settings.CONFIDENCE_THRESHOLD,
            "market_data": "live-configured" if settings.MARKET_API_KEY else "demo",
            "whatsapp_configured": whatsapp_service.is_configured(),
            "gemini_enabled": bool(settings.GEMINI_API_KEY)}


app.include_router(predict.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(speech.router, prefix="/api")
app.include_router(crops.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(whatsapp.router)                # /webhook (no /api prefix)

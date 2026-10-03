"""
api/admin.py

GET /api/admin/stats - aggregate-only statistics for extension workers.
Deliberately exposes counts and distributions only, never individual
farmer records or images (see database.ScanRecord for what is/isn't stored).
"""
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_session, ScanRecord

router = APIRouter()


@router.get("/admin/stats")
async def admin_stats(db: Session = Depends(get_session)):
    records = db.query(ScanRecord).all()

    total = len(records)
    healthy = sum(1 for r in records if r.is_confident and r.is_healthy)
    diseased = sum(1 for r in records if r.is_confident and not r.is_healthy)
    low_confidence = sum(1 for r in records if not r.is_confident)

    disease_counter = Counter(r.disease for r in records if r.is_confident and not r.is_healthy)
    crop_counter = Counter(r.crop for r in records if r.is_confident)

    return {
        "total_scans": total,
        "healthy_count": healthy,
        "disease_count": diseased,
        "low_confidence_count": low_confidence,
        "disease_distribution": dict(disease_counter),
        "crop_distribution": dict(crop_counter),
    }

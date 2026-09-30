"""GET /api/crops, /api/crops/{crop}, /api/guidance/{class_name}: read-only knowledge base."""
from fastapi import APIRouter, HTTPException

from ..disease_info import all_crops, class_config, get_crop, get_guidance

router = APIRouter()


@router.get("/crops")
async def crops():
    return {"crops": list(all_crops().values()),
            "classes": [{k: c[k] for k in ("class_name", "crop", "disease", "disease_hi", "is_healthy", "scope")}
                        for c in class_config()["classes"]]}


@router.get("/crops/{crop}")
async def crop_detail(crop: str):
    c = get_crop(crop.capitalize())
    if not c:
        raise HTTPException(404, detail={"code": "unknown_crop", "message": {"en": "Crop not supported.", "hi": "यह फसल समर्थित नहीं है।"}})
    return c


@router.get("/guidance/{class_name}")
async def guidance(class_name: str):
    try:
        return get_guidance(class_name)
    except KeyError:
        raise HTTPException(404, detail={"code": "unknown_class", "message": {"en": "Not supported.", "hi": "समर्थित नहीं है।"}})

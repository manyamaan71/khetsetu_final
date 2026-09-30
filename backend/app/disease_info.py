"""
disease_info.py - class labels + agricultural guidance lookup.

Two DIFFERENT things live here and are kept strictly apart:
  * model/class_config.json  -> what the ML model can predict (labels, order)
  * data/guidance.json       -> general agricultural advice for each label
Guidance is looked up AFTER the model has predicted; it can never change a prediction.
"""
import json
from functools import lru_cache
from pathlib import Path

from .config import settings


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def class_config() -> dict:
    return _read(Path(settings.MODEL_DIR) / "class_config.json")


@lru_cache(maxsize=1)
def _classes() -> list[dict]:
    return sorted(class_config()["classes"], key=lambda c: c["index"])


@lru_cache(maxsize=1)
def _class_names() -> list[str]:
    names = _read(Path(settings.MODEL_DIR) / "class_names.json")
    expected = [item["class_name"] for item in _classes()]
    if names != expected:
        raise ValueError("class_names.json does not match class_config.json order")
    return names


def class_names() -> list[str]:
    return _class_names()


@lru_cache(maxsize=1)
def _by_name() -> dict[str, dict]:
    return {c["class_name"]: c for c in _classes()}


def get_class(class_name: str) -> dict:
    return _by_name()[class_name]          # KeyError if the model returns an unknown label


@lru_cache(maxsize=1)
def _guidance() -> dict:
    return _read(Path(settings.DATA_DIR) / "guidance.json")


@lru_cache(maxsize=1)
def _crops() -> dict:
    return _read(Path(settings.DATA_DIR) / "crops.json")


def get_guidance(class_name: str) -> dict:
    return _guidance()[class_name]


def get_crop(crop: str) -> dict | None:
    return _crops().get(crop)


def all_crops() -> dict:
    return _crops()


def prediction_block(class_name: str, confidence: float) -> dict:
    """The ML prediction, in the exact shape requested for the API."""
    c = get_class(class_name)
    return {
        "class_name": class_name, "crop": c["crop"], "disease": c["disease"],
        "confidence": round(float(confidence), 4), "is_healthy": c["is_healthy"],
        "crop_hi": c["crop_hi"], "disease_hi": c["disease_hi"],
    }

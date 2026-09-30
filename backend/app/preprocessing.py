"""
preprocessing.py - image validation + preprocessing.

MUST stay identical to ml/training/common.py::load_and_resize (EXIF-rotate ->
RGB -> 224x224 bilinear).  The model itself rescales 0-255 pixels to [-1, 1],
so we hand it RAW float pixel values.
"""
import io

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

IMAGE_SIZE = (224, 224)
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class InvalidImageError(Exception):
    pass


def load_image_from_bytes(data: bytes) -> Image.Image:
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in ALLOWED_FORMATS:          # sniff real format, ignore the filename
            raise InvalidImageError("Only JPG, PNG or WEBP photos are supported")
        img.load()
    except InvalidImageError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, ValueError) as exc:
        raise InvalidImageError("File is not a readable image") from exc
    img = ImageOps.exif_transpose(img)
    return img.convert("RGB")


def preprocess_image(img: Image.Image) -> np.ndarray:
    """-> float32 (1, 224, 224, 3) with raw 0-255 values."""
    arr = np.asarray(img.resize(IMAGE_SIZE, Image.BILINEAR), dtype=np.float32)
    return arr[None, ...]


def plant_pixel_ratio(img: Image.Image) -> float:
    """Share of pixels with leaf-like colour (green / yellow / brown, not grey/white/blue).
    A cheap guard so obvious non-leaf photos (sky, floor, faces, screenshots) are not
    sent to a classifier that can only ever answer with one of its own classes."""
    small = img.resize((96, 96), Image.BILINEAR).convert("HSV")
    hsv = np.asarray(small, dtype=np.float32)
    h, s, v = hsv[..., 0] * 360 / 255, hsv[..., 1] / 255, hsv[..., 2] / 255
    plant = (h >= 20) & (h <= 170) & (s >= 0.12) & (v >= 0.12)
    return float(plant.mean())

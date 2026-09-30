"""
common.py - helpers shared by train.py, evaluate.py and export_model.py.

IMPORTANT (train/serve parity): `load_and_resize()` performs exactly the same
steps as backend/app/preprocessing.py (EXIF-rotate -> RGB -> 224x224 bilinear).
The model itself contains the "scale to [-1, 1]" step, so both training and the
backend feed RAW 0-255 pixel values.  Do not change one without the other.
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ML_DIR = Path(__file__).resolve().parents[1]
IMG_SIZE = 224
IMG_EXT = {".jpg", ".jpeg", ".png"}

CONFIG_PATH = ML_DIR.parent / "model" / "class_config.json"   # the ONE class-mapping file
CONFIG = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
CLASS_NAMES_PATH = ML_DIR.parent / "model" / "class_names.json"
CLASS_NAMES = json.loads(CLASS_NAMES_PATH.read_text(encoding="utf-8"))
if CLASS_NAMES != [c["class_name"] for c in sorted(CONFIG["classes"], key=lambda c: c["index"])]:
    raise ValueError("class_names.json does not match class_config.json order")
FOLDER_TO_CLASS = {c["source_folder"]: c["class_name"] for c in CONFIG["classes"]}


def load_and_resize(path) -> np.ndarray:
    """Returns uint8 array (224, 224, 3). Same logic as the backend."""
    with Image.open(path) as im:
        im.load()
        im = ImageOps.exif_transpose(im).convert("RGB")
    im = im.resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR)
    return np.asarray(im, dtype=np.uint8)


def list_split(split_dir: Path):
    """(paths, labels) for split_dir/<class_name>/*.jpg using CLASS_NAMES order."""
    paths, labels = [], []
    for idx, cls in enumerate(CLASS_NAMES):
        d = split_dir / cls
        if not d.is_dir():
            continue
        for p in sorted(d.iterdir()):
            if p.suffix.lower() in IMG_EXT:
                paths.append(p)
                labels.append(idx)
    return paths, np.array(labels, dtype=np.int32)


def build_cache(split_dir: Path, cache_dir: Path, name: str):
    """Decode + resize a split ONCE into a uint8 .npy memmap (fast re-runs).
    Returns (X memmap [n,224,224,3], y [n], paths)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    x_path, y_path, list_path = (cache_dir / f"{name}_x.npy", cache_dir / f"{name}_y.npy",
                                 cache_dir / f"{name}_paths.json")
    paths, labels = list_split(split_dir)
    if not paths:
        raise SystemExit(f"No images in {split_dir}. Run training/prepare_dataset.py first.")
    if x_path.exists() and y_path.exists() and list_path.exists():
        if json.loads(list_path.read_text()) == [str(p) for p in paths]:
            return np.load(x_path, mmap_mode="r"), np.load(y_path), paths
    print(f"[cache] building {name}: {len(paths)} images ...", flush=True)
    X = np.lib.format.open_memmap(x_path, mode="w+", dtype=np.uint8,
                                  shape=(len(paths), IMG_SIZE, IMG_SIZE, 3))
    for i, p in enumerate(paths):
        X[i] = load_and_resize(p)
        if (i + 1) % 2000 == 0:
            print(f"   {i + 1}/{len(paths)}", flush=True)
    X.flush()
    np.save(y_path, labels)
    list_path.write_text(json.dumps([str(p) for p in paths]))
    return np.load(x_path, mmap_mode="r"), labels, paths


def fit_temperature(probs: np.ndarray, labels: np.ndarray) -> float:
    """Temperature scaling on validation data: finds T>0 minimising NLL of
    softmax(log(p)/T).  T>1 softens over-confident models."""
    from scipy.optimize import minimize_scalar

    logp = np.log(np.clip(probs, 1e-12, 1.0))

    def nll(t):
        z = logp / t
        z = z - z.max(1, keepdims=True)
        lp = z - np.log(np.exp(z).sum(1, keepdims=True))
        return -lp[np.arange(len(labels)), labels].mean()

    return float(minimize_scalar(nll, bounds=(0.3, 5.0), method="bounded").x)


def apply_temperature(probs: np.ndarray, t: float) -> np.ndarray:
    z = np.log(np.clip(probs, 1e-12, 1.0)) / t
    z = z - z.max(-1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(-1, keepdims=True)

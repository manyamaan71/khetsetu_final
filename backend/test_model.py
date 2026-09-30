#!/usr/bin/env python3
"""
test_model.py - run the REAL production model on one image from the command line.

This intentionally reuses the exact backend code path (app.preprocessing +
app.model.classifier) rather than a separate re-implementation, so what you
see here is guaranteed to match what /api/predict returns.

Usage (from backend/, with the venv active):
    python test_model.py path/to/image.jpg
    python test_model.py path/to/image.jpg --topk 5
    python test_model.py path/to/image.jpg --demo        # force DEMO_MODE=true

Example output:
    Model mode : real (tflite)
    Image      : leaf.jpg

    1. Tomato Healthy         91.4%
    2. Tomato Early Blight     4.7%
    3. Tomato Late Blight      2.3%

    Confidence threshold: 0.70  -> ACCEPTED (diagnosis would be shown)
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("image", help="Path to a JPG/PNG/WEBP image")
    ap.add_argument("--topk", type=int, default=3, help="How many ranked predictions to print (default 3)")
    ap.add_argument("--demo", action="store_true", help="Force DEMO_MODE=true for this run")
    args = ap.parse_args()

    if args.demo:
        os.environ["DEMO_MODE"] = "true"

    img_path = Path(args.image)
    if not img_path.exists():
        print(f"ERROR: file not found: {img_path}", file=sys.stderr)
        return 1

    # Import AFTER the env var is set so config.py picks it up.
    from app.config import settings
    from app.disease_info import class_names, get_class
    from app.model import classifier
    from app.preprocessing import InvalidImageError, load_image_from_bytes, plant_pixel_ratio, preprocess_image

    classifier.load()
    print(f"Model mode : {classifier.mode} ({classifier.format})")
    if classifier.load_error:
        print(f"Load note  : {classifier.load_error}")
    print(f"Image      : {img_path.name}\n")

    if not classifier.available:
        print("ERROR: no model available (DEMO_MODE=false and no model file found). "
              "This is the correct, safe behaviour - the API would return 503, not a fake prediction.")
        return 1

    data = img_path.read_bytes()
    try:
        img = load_image_from_bytes(data)
    except InvalidImageError as exc:
        print(f"ERROR: {exc}")
        return 1

    leaf_ratio = plant_pixel_ratio(img)
    if leaf_ratio < settings.MIN_LEAF_RATIO:
        print(f"leaf-pixel ratio = {leaf_ratio:.3f} (< {settings.MIN_LEAF_RATIO}) -> "
              "'Photo unclear' (this does not look like a crop leaf)")
        return 0

    batch = preprocess_image(img)

    if classifier.mode == "demo":
        class_name, confidence, _ = classifier.predict(batch, data)
        ranked = [(class_name, confidence)]
    else:
        import numpy as np
        from app.model import _softmax_temperature

        raw = classifier.predict_probs(batch)
        probs = _softmax_temperature(raw, classifier.temperature)
        order = np.argsort(probs)[::-1]
        names = class_names()
        ranked = [(names[i], float(probs[i])) for i in order[: args.topk]]

    for rank, (class_name, conf) in enumerate(ranked, start=1):
        c = get_class(class_name)
        label = f"{c['crop']} {c['disease']}"
        print(f"{rank}. {label:<28s} {conf * 100:5.1f}%")

    top_class, top_conf = ranked[0]
    print(f"\nConfidence threshold: {settings.CONFIDENCE_THRESHOLD:.2f}", end="  -> ")
    if top_conf >= settings.CONFIDENCE_THRESHOLD:
        c = get_class(top_class)
        print(f"ACCEPTED: {c['crop']} / {c['disease']} (this is what the API would show)")
    else:
        print("REJECTED: 'Photo unclear. Please take another clear photo of one leaf.' "
              "(no diagnosis shown, per the 70% safety threshold)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

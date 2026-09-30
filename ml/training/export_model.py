"""
export_model.py - convert model/khetsetu.keras -> model/khetsetu.tflite (mobile / backend friendly).

    python training/export_model.py                      # float32 (same accuracy as Keras)
    python training/export_model.py --quantize dynamic   # ~4x smaller, weights int8 (re-run evaluate.py to check accuracy)

The TFLite model keeps the same interface: float32 input (1,224,224,3) with RAW 0-255
pixels (rescaling is inside the model) and 8 softmax outputs in model/class_config.json order.
"""
import argparse
from pathlib import Path

import tensorflow as tf

ROOT = Path(__file__).resolve().parents[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default=str(ROOT / "model" / "khetsetu.keras"))
    ap.add_argument("--out", default=str(ROOT / "model" / "khetsetu.tflite"))
    ap.add_argument("--quantize", choices=["none", "dynamic", "float16"], default="none")
    ap.add_argument("--slim-keras", action=argparse.BooleanOptionalAction, default=True)
    a = ap.parse_args()

    model = tf.keras.models.load_model(a.model, compile=False)
    if a.slim_keras:                       # drop optimizer state -> much smaller .keras file, same predictions
        model.save(a.model)
        print(f"re-saved slim {a.model} ({Path(a.model).stat().st_size / 1e6:.1f} MB)")
    import tempfile
    saved = tempfile.mkdtemp()
    model.export(saved)                    # Keras 3 + TF 2.16: from_keras_model() is broken, SavedModel route works
    conv = tf.lite.TFLiteConverter.from_saved_model(saved)
    if a.quantize == "dynamic":
        conv.optimizations = [tf.lite.Optimize.DEFAULT]
    elif a.quantize == "float16":
        conv.optimizations = [tf.lite.Optimize.DEFAULT]
        conv.target_spec.supported_types = [tf.float16]
    data = conv.convert()
    Path(a.out).write_bytes(data)
    print(f"wrote {a.out}  ({len(data) / 1e6:.2f} MB, quantize={a.quantize})")


if __name__ == "__main__":
    main()

"""
model.py - loads the trained classifier ONCE (called from main.py lifespan) and
serves predictions.

Supported formats (auto-detected):
  model/khetsetu.tflite  - preferred (small, fast). Runs on tflite_runtime,
                           ai_edge_litert or TensorFlow's built-in interpreter.
  model/khetsetu.keras   - fallback (needs TensorFlow).
Modes:
  real        - trained model loaded
  demo        - simulated predictions, ALWAYS labelled demo by the API
  unavailable - DEMO_MODE=false but no model could be loaded (API answers 503)
"""
import hashlib
import json
import logging
import threading
import time
from pathlib import Path

import numpy as np

from .config import settings
from .disease_info import class_names

log = logging.getLogger("khetsetu.model")


def _softmax_temperature(probs: np.ndarray, t: float) -> np.ndarray:
    z = np.log(np.clip(probs, 1e-12, 1.0)) / max(t, 1e-3)
    z -= z.max()
    e = np.exp(z)
    return e / e.sum()


class Classifier:
    def __init__(self):
        self.mode = "unloaded"
        self.format = "none"
        self.model_file: str | None = None
        self.meta: dict = {}
        self.temperature = 1.0
        self.load_error: str | None = None
        self._interp = None
        self._keras = None
        self._lock = threading.Lock()      # tflite interpreters are not thread-safe

    # ---------------------------------------------------------------- loading
    def _find_model_file(self) -> Path | None:
        if settings.MODEL_PATH:
            p = Path(settings.MODEL_PATH)
            return p if p.exists() else None
        for name in ("khetsetu.tflite", "khetsetu.keras"):
            p = Path(settings.MODEL_DIR) / name
            if p.exists():
                return p
        return None

    def load(self) -> None:
        """Called exactly once at application start-up."""
        if settings.DEMO_MODE == "true":
            self.mode, self.format = "demo", "demo"
            log.warning("DEMO_MODE=true -> simulated predictions (labelled Demo Mode).")
            return
        path = self._find_model_file()
        if path is None:
            self._fallback(f"no model file found in {settings.MODEL_DIR}")
            return
        try:
            meta_path = Path(settings.MODEL_DIR) / "model_meta.json"
            if meta_path.exists():
                self.meta = json.loads(meta_path.read_text(encoding="utf-8"))
                self.temperature = float(self.meta.get("temperature", 1.0))
            if path.suffix == ".tflite":
                self._load_tflite(path)
            else:
                import tensorflow as tf
                self._keras = tf.keras.models.load_model(path)
                self.format = "keras"
            n_out = self._n_outputs()
            if n_out != len(class_names()):
                raise RuntimeError(f"model has {n_out} outputs but class_config.json lists {len(class_names())}")
            self.mode, self.model_file = "real", str(path)
            log.info("Loaded real model %s (%s), temperature=%.3f", path.name, self.format, self.temperature)
            self.predict_probs(np.zeros((1, 224, 224, 3), np.float32))     # warm-up
        except Exception as exc:                                              # noqa: BLE001
            self._fallback(f"could not load {path.name}: {exc}")

    def _fallback(self, reason: str) -> None:
        self.load_error = reason
        if settings.DEMO_MODE == "auto":
            self.mode, self.format = "demo", "demo"
            log.warning("%s -> falling back to labelled DEMO predictions.", reason)
        else:
            self.mode, self.format = "unavailable", "none"
            log.error("DEMO_MODE=false but %s. /api/predict will return 503.", reason)

    def _load_tflite(self, path: Path) -> None:
        interp = None
        for mod in ("tflite_runtime.interpreter", "ai_edge_litert.interpreter"):
            try:
                interp = __import__(mod, fromlist=["Interpreter"]).Interpreter(model_path=str(path))
                break
            except Exception:                                                # noqa: BLE001
                continue
        if interp is None:
            import tensorflow as tf
            interp = tf.lite.Interpreter(model_path=str(path))
        interp.allocate_tensors()
        self._interp = interp
        self._in = interp.get_input_details()[0]
        self._out = interp.get_output_details()[0]
        self.format = "tflite"

    def _n_outputs(self) -> int:
        if self._interp is not None:
            return int(self._out["shape"][-1])
        return int(self._keras.output_shape[-1])

    # -------------------------------------------------------------- inference
    def predict_probs(self, batch: np.ndarray) -> np.ndarray:
        """batch (1,224,224,3) raw 0-255 float32 -> probs (n_classes,) from the model (uncalibrated)."""
        if self._interp is not None:
            with self._lock:
                self._interp.set_tensor(self._in["index"], batch.astype(self._in["dtype"]))
                self._interp.invoke()
                return self._interp.get_tensor(self._out["index"])[0].copy()
        return np.asarray(self._keras(batch, training=False))[0]

    def predict(self, batch: np.ndarray, image_bytes: bytes = b"") -> tuple[str, float, float]:
        """-> (class_name, calibrated_confidence, inference_ms)."""
        names = class_names()
        t0 = time.perf_counter()
        if self.mode == "demo":
            return (*self._demo(names, image_bytes), (time.perf_counter() - t0) * 1000)
        probs = _softmax_temperature(self.predict_probs(batch), self.temperature)
        idx = int(np.argmax(probs))
        return names[idx], float(probs[idx]), (time.perf_counter() - t0) * 1000

    @staticmethod
    def _demo(names: list[str], image_bytes: bytes) -> tuple[str, float]:
        """Simulated result, stable per image. NOT AI - the API always flags it as demo."""
        seed = int(hashlib.sha256(image_bytes or b"x").hexdigest(), 16)
        rng = np.random.default_rng(seed % (2**32))
        conf = float(rng.uniform(0.35, 0.69)) if rng.random() < 0.2 else float(rng.uniform(0.75, 0.97))
        return names[int(rng.integers(len(names)))], conf

    # ------------------------------------------------------------------ info
    @property
    def is_demo(self) -> bool:
        return self.mode == "demo"

    @property
    def available(self) -> bool:
        return self.mode in ("real", "demo")

    def info(self) -> dict:
        return {"mode": self.mode, "format": self.format,
                "model_file": Path(self.model_file).name if self.model_file else None,
                "architecture": self.meta.get("model"), "temperature": self.temperature,
                "classes": len(class_names()), "load_error": self.load_error}


classifier = Classifier()

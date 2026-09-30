"""
evaluate.py - honest evaluation on the held-out TEST split (never used for training,
early stopping or temperature fitting).

Writes to ml/evaluation/results/:
  metrics.json, class_report.csv, confusion_matrix.csv/.png, threshold_analysis.csv, EVALUATION_REPORT.md

Reports: accuracy, macro/weighted precision-recall-F1, per-class metrics, confusion matrix,
calibration (ECE) before/after temperature scaling, confidence-threshold trade-off,
model size, average inference time (batch 1, this machine), robustness to degraded photos,
and how synthetic NON-leaf images are handled.

Usage (from ml/):  python evaluation/evaluate.py [--tflite ../model/khetsetu.tflite]
"""
import argparse
import csv
import io
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

HERE = Path(__file__).resolve().parent
ML = HERE.parent
ROOT = ML.parent
sys.path.insert(0, str(ML / "training"))
sys.path.insert(0, str(ROOT / "backend"))

from common import CLASS_NAMES, IMG_SIZE, apply_temperature, build_cache, load_and_resize, list_split  # noqa: E402
from app.preprocessing import plant_pixel_ratio  # noqa: E402

import tensorflow as tf  # noqa: E402
from sklearn.metrics import (accuracy_score, classification_report, confusion_matrix,  # noqa: E402
                             precision_recall_fscore_support)


def ece(conf, correct, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    total, out = len(conf), 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (conf > lo) & (conf <= hi)
        if m.any():
            out += m.sum() / total * abs(correct[m].mean() - conf[m].mean())
    return float(out)


class TFLiteRunner:
    def __init__(self, path):
        self.i = tf.lite.Interpreter(model_path=str(path))
        self.i.allocate_tensors()
        self.inp, self.out = self.i.get_input_details()[0], self.i.get_output_details()[0]

    def __call__(self, x):                     # x: (n,224,224,3) float32
        res = []
        for k in range(len(x)):
            self.i.set_tensor(self.inp["index"], np.asarray(x[k:k + 1], dtype=np.float32))
            self.i.invoke()
            res.append(self.i.get_tensor(self.out["index"])[0].copy())
        return np.array(res)


def predict_keras(model, X, bs=16):
    out = []
    for s in range(0, len(X), bs):
        out.append(model(np.asarray(X[s:s + bs], dtype=np.float32), training=False).numpy())
    return np.concatenate(out)


def degrade(img: Image.Image, kind: str) -> Image.Image:
    if kind == "blur":
        return img.filter(ImageFilter.GaussianBlur(2.5))
    if kind == "dark":
        return ImageEnhance.Brightness(img).enhance(0.45)
    if kind == "bright":
        return ImageEnhance.Brightness(img).enhance(1.6)
    if kind == "low_jpeg":
        b = io.BytesIO(); img.save(b, "JPEG", quality=12); b.seek(0); return Image.open(b).convert("RGB")
    if kind == "small_crop":                  # leaf photographed from further away
        w, h = img.size; c = img.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4)); return c
    raise ValueError(kind)


def synthetic_non_leaf(n=200, seed=0):
    rng = np.random.default_rng(seed)
    imgs = []
    for k in range(n):
        t = k % 5
        if t == 0:   a = rng.integers(0, 256, (256, 256, 3), dtype=np.uint8)                      # noise
        elif t == 1: a = np.full((256, 256, 3), rng.integers(0, 256, 3), dtype=np.uint8)          # solid colour
        elif t == 2:                                                                               # gradient
            g = np.linspace(0, 255, 256, dtype=np.uint8); a = np.stack([np.tile(g, (256, 1))] * 3, -1)
        elif t == 3:                                                                               # checkerboard
            c = ((np.indices((256, 256)).sum(0) // 32) % 2 * 255).astype(np.uint8); a = np.stack([c] * 3, -1)
        else:                                                                                      # sky-ish / skin-ish blocks
            a = np.zeros((256, 256, 3), np.uint8); a[:] = [135, 180, 235] if k % 2 else [224, 172, 150]
            a[128:] = rng.integers(60, 200, 3)
        imgs.append(Image.fromarray(a))
    return imgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ML / "dataset_split"))
    ap.add_argument("--keras", default=str(ROOT / "model" / "khetsetu.keras"))
    ap.add_argument("--tflite", default=str(ROOT / "model" / "khetsetu.tflite"))
    ap.add_argument("--threshold", type=float, default=0.70)
    ap.add_argument("--robust-n", type=int, default=300, help="images per degradation test")
    a = ap.parse_args()

    res_dir = HERE / "results"; res_dir.mkdir(exist_ok=True)
    meta = json.loads((ROOT / "model" / "model_meta.json").read_text())
    T = float(meta["temperature"])
    names = CLASS_NAMES

    Xte, yte, paths = build_cache(Path(a.data) / "test", ML / "cache", "test")
    print(f"test images: {len(yte)}")
    keras_model = tf.keras.models.load_model(a.keras)
    print('keras loaded; predicting', flush=True)
    raw = predict_keras(keras_model, Xte)
    cal = apply_temperature(raw, T)
    pred = cal.argmax(1)
    conf = cal.max(1)
    correct = (pred == yte).astype(float)

    acc = accuracy_score(yte, pred)
    p, r, f, sup = precision_recall_fscore_support(yte, pred, labels=range(len(names)), zero_division=0)
    macro = precision_recall_fscore_support(yte, pred, average="macro", zero_division=0)[:3]
    weighted = precision_recall_fscore_support(yte, pred, average="weighted", zero_division=0)[:3]
    cm = confusion_matrix(yte, pred, labels=range(len(names)))

    with open(res_dir / "class_report.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["class", "precision", "recall", "f1", "support"])
        for i, n in enumerate(names):
            w.writerow([n, round(p[i], 4), round(r[i], 4), round(f[i], 4), int(sup[i])])
    with open(res_dir / "confusion_matrix.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["true\\pred"] + names)
        for i, n in enumerate(names):
            w.writerow([n] + cm[i].tolist())

    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 8))
    cmn = cm / cm.sum(1, keepdims=True)
    ax.imshow(cmn, cmap="Greens", vmin=0, vmax=1)
    short = [n.replace("___", "\n") for n in names]
    ax.set_xticks(range(len(names)), short, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(names)), short, fontsize=8)
    for i in range(len(names)):
        for j in range(len(names)):
            ax.text(j, i, f"{cm[i, j]}", ha="center", va="center", fontsize=8,
                    color="white" if cmn[i, j] > 0.6 else "black")
    ax.set_xlabel("Predicted"); ax.set_ylabel("True"); ax.set_title(f"Confusion matrix (test, n={len(yte)}, acc={acc:.3f})")
    fig.tight_layout(); fig.savefig(res_dir / "confusion_matrix.png", dpi=140); plt.close(fig)

    # ---------- confidence threshold trade-off (calibrated confidence)
    thr_rows = []
    for t in (0.5, 0.6, 0.7, 0.8, 0.9, 0.95):
        m = conf >= t
        thr_rows.append({"threshold": t, "answered_share": round(float(m.mean()), 4),
                         "accuracy_when_answered": round(float(correct[m].mean()), 4) if m.any() else None,
                         "wrong_answers_shown": int(((correct == 0) & m).sum()),
                         "correct_answers_withheld": int(((correct == 1) & ~m).sum())})
    with open(res_dir / "threshold_analysis.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(thr_rows[0])); w.writeheader(); w.writerows(thr_rows)

    # ---------- top confusions
    conf_pairs = sorted(((int(cm[i, j]), names[i], names[j]) for i in range(len(names))
                         for j in range(len(names)) if i != j and cm[i, j] > 0), reverse=True)[:8]

    print('metrics done; timing', flush=True)
    # ---------- sizes + timing
    sizes = {}
    for label, path in (("keras_mb", a.keras), ("tflite_mb", a.tflite)):
        if Path(path).exists():
            sizes[label] = round(Path(path).stat().st_size / 1e6, 2)

    rng = np.random.default_rng(1)
    idx = rng.choice(len(yte), 100, replace=False)
    one = np.asarray(Xte[int(idx[0])], dtype=np.float32)[None]
    keras_model(one, training=False)                                   # warm-up
    t0 = time.perf_counter()
    for k in idx:
        keras_model(np.asarray(Xte[int(k)], dtype=np.float32)[None], training=False)
    keras_ms = (time.perf_counter() - t0) / len(idx) * 1000

    tflite = None
    if Path(a.tflite).exists():
        tflite = TFLiteRunner(a.tflite)
        tflite(one)
        t0 = time.perf_counter()
        for k in idx:
            tflite(np.asarray(Xte[int(k)], dtype=np.float32)[None])
        tfl_ms = (time.perf_counter() - t0) / len(idx) * 1000
        traw = tflite(Xte)
        tpred = apply_temperature(traw, T).argmax(1)
        tflite_res = {"accuracy": round(float(accuracy_score(yte, tpred)), 4),
                      "macro_f1": round(float(precision_recall_fscore_support(yte, tpred, average="macro", zero_division=0)[2]), 4),
                      "agreement_with_keras": round(float((tpred == pred).mean()), 4),
                      "avg_inference_ms_batch1": round(tfl_ms, 1)}
    else:
        tflite_res = None

    print('tflite done; robustness', flush=True)
    # ---------- robustness (degraded photos) on a random subset of test images
    sub = rng.choice(len(yte), min(a.robust_n, len(yte)), replace=False)
    robust = {}
    for kind in ("blur", "dark", "bright", "low_jpeg", "small_crop"):
        xs = []
        for k in sub:
            im = degrade(Image.open(paths[int(k)]).convert("RGB"), kind)
            xs.append(np.asarray(im.resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR), dtype=np.float32))
        pr = apply_temperature(predict_keras(keras_model, np.array(xs)), T)
        cf, pd = pr.max(1), pr.argmax(1)
        ok = pd == yte[sub]
        robust[kind] = {"accuracy": round(float(ok.mean()), 4),
                        "answered_share_at_threshold": round(float((cf >= a.threshold).mean()), 4),
                        "accuracy_when_answered": round(float(ok[cf >= a.threshold].mean()), 4) if (cf >= a.threshold).any() else None}

    print('robustness done; leaf guard', flush=True)
    # ---------- leaf-colour guard + synthetic non-leaf
    ratios = np.array([plant_pixel_ratio(Image.open(p_).convert("RGB")) for p_ in paths])
    MIN_RATIO = 0.08
    fake = synthetic_non_leaf()
    fake_ratio = np.array([plant_pixel_ratio(i) for i in fake])
    fx = np.array([np.asarray(i.resize((IMG_SIZE, IMG_SIZE), Image.BILINEAR), dtype=np.float32) for i in fake])
    fcf = apply_temperature(predict_keras(keras_model, fx), T).max(1)
    non_leaf = {
        "leaf_guard_min_ratio": MIN_RATIO,
        "real_test_leaves_wrongly_rejected_by_guard": int((ratios < MIN_RATIO).sum()),
        "real_test_leaves_total": int(len(ratios)),
        "synthetic_non_leaf_images": len(fake),
        "synthetic_rejected_by_leaf_guard": int((fake_ratio < MIN_RATIO).sum()),
        "synthetic_passing_guard_and_threshold_(false_diagnosis)": int(((fake_ratio >= MIN_RATIO) & (fcf >= a.threshold)).sum()),
        "synthetic_passing_threshold_without_guard": int((fcf >= a.threshold).sum()),
    }

    metrics = {
        "test_images": int(len(yte)), "accuracy": round(float(acc), 4),
        "macro": {"precision": round(macro[0], 4), "recall": round(macro[1], 4), "f1": round(macro[2], 4)},
        "weighted": {"precision": round(weighted[0], 4), "recall": round(weighted[1], 4), "f1": round(weighted[2], 4)},
        "calibration": {"temperature": T,
                        "ece_before": round(ece(raw.max(1), (raw.argmax(1) == yte).astype(float)), 4),
                        "ece_after": round(ece(conf, correct), 4),
                        "mean_confidence_wrong": round(float(conf[correct == 0].mean()), 4) if (correct == 0).any() else None,
                        "mean_confidence_right": round(float(conf[correct == 1].mean()), 4)},
        "per_class": {n: {"precision": round(p[i], 4), "recall": round(r[i], 4), "f1": round(f[i], 4), "support": int(sup[i])}
                      for i, n in enumerate(names)},
        "top_confusions": [{"count": c, "true": t, "predicted": q} for c, t, q in conf_pairs],
        "threshold_analysis": thr_rows,
        "model_size_mb": sizes,
        "inference": {"keras_avg_ms_batch1": round(keras_ms, 1), "tflite": tflite_res,
                      "measured_on": f"{platform.processor() or platform.machine()}, {platform.system()}, TF {tf.__version__}, CPU only, 1 thread-pool"},
        "robustness_degraded_test_images": robust,
        "non_leaf_handling": non_leaf,
        "caveat": "Test images come from the same lab-style dataset as training (split by duplicate cluster). "
                  "Accuracy on real field photos (cluttered background, sunlight, different cameras) is expected to be LOWER.",
    }
    (res_dir / "metrics.json").write_text(json.dumps(metrics, indent=2))

    # ---------- markdown report
    L = [f"# KhetSetu model evaluation (held-out test split, n={len(yte)})\n",
         f"- **Accuracy:** {acc:.4f}", f"- **Macro** precision / recall / F1: {macro[0]:.4f} / {macro[1]:.4f} / {macro[2]:.4f}",
         f"- **Weighted** precision / recall / F1: {weighted[0]:.4f} / {weighted[1]:.4f} / {weighted[2]:.4f}",
         f"- Model size: {sizes}", f"- Avg inference (batch 1): Keras {keras_ms:.1f} ms; TFLite {tflite_res['avg_inference_ms_batch1'] if tflite_res else 'n/a'} ms",
         f"- Calibration (ECE): {metrics['calibration']['ece_before']} -> {metrics['calibration']['ece_after']} after temperature scaling (T={T})\n",
         "## Per-class\n", "| class | precision | recall | F1 | support |", "|---|---|---|---|---|"]
    L += [f"| {n} | {p[i]:.3f} | {r[i]:.3f} | {f[i]:.3f} | {int(sup[i])} |" for i, n in enumerate(names)]
    L += ["\n## Confidence threshold trade-off\n", "| threshold | answered | accuracy when answered | wrong answers shown | correct answers withheld |", "|---|---|---|---|---|"]
    L += [f"| {t['threshold']} | {t['answered_share']} | {t['accuracy_when_answered']} | {t['wrong_answers_shown']} | {t['correct_answers_withheld']} |" for t in thr_rows]
    L += ["\n## Robustness to degraded photos\n", "| degradation | accuracy | answered @thr | accuracy when answered |", "|---|---|---|---|"]
    L += [f"| {k} | {v['accuracy']} | {v['answered_share_at_threshold']} | {v['accuracy_when_answered']} |" for k, v in robust.items()]
    L += ["\n## Non-leaf images\n", "```json", json.dumps(non_leaf, indent=2), "```", f"\n**Caveat:** {metrics['caveat']}\n",
          "## Top confusions\n"] + [f"- {c}x  {t}  ->  {q}" for c, t, q in conf_pairs]
    if tflite_res:
        L += ["\n## TFLite model", "```json", json.dumps(tflite_res, indent=2), "```"]
    (res_dir / "EVALUATION_REPORT.md").write_text("\n".join(L), encoding="utf-8")
    print(json.dumps({k: metrics[k] for k in ("accuracy", "macro", "model_size_mb", "inference")}, indent=2))
    print("Full report:", res_dir / "EVALUATION_REPORT.md")


if __name__ == "__main__":
    main()

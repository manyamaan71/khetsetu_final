"""
train.py - MobileNetV2 transfer learning for the KhetSetu 8-class dataset (see model/class_config.json).

Pipeline
  dataset_split/{train,val}  ->  uint8 cache (ml/cache)  ->  tf.data (augment train only)
  Phase 1: frozen ImageNet MobileNetV2 base, train the classification head.
  Phase 2: unfreeze the last blocks of the base, fine-tune at a low learning rate
           (BatchNorm layers stay in inference mode).
  After training: temperature-scale the softmax on the VALIDATION set so that the
  reported confidence is better calibrated (test set is never touched here).

Class imbalance: balanced class weights computed from the TRAIN split.

Outputs (model/): khetsetu.keras, model_meta.json, training_history.json

Usage (from ml/):
    python training/train.py --data ./dataset_split
Offline / firewall: pass --weights path/to/mobilenet_v2_..._no_top.h5
"""
import argparse
import json
import shutil
import time
from pathlib import Path

import numpy as np
import tensorflow as tf
from tensorflow.keras import layers, callbacks

from common import (CLASS_NAMES, IMG_SIZE, ML_DIR, apply_temperature, build_cache, fit_temperature)

SEED = 42


def add_camera_artifacts(images):
    """Apply mild blur, sensor noise, and JPEG variation to training batches only."""
    channels = images.shape[-1]
    gaussian = tf.constant([[1, 2, 1], [2, 4, 2], [1, 2, 1]], dtype=tf.float32) / 16.0
    horizontal = tf.constant([[0, 0, 0], [1, 1, 1], [0, 0, 0]], dtype=tf.float32) / 3.0
    vertical = tf.transpose(horizontal)
    gaussian_filter = tf.tile(gaussian[:, :, None, None], [1, 1, channels, 1])
    horizontal_filter = tf.tile(horizontal[:, :, None, None], [1, 1, channels, 1])
    vertical_filter = tf.tile(vertical[:, :, None, None], [1, 1, channels, 1])

    gaussian_blur = tf.nn.depthwise_conv2d(images, gaussian_filter, [1, 1, 1, 1], "SAME")
    motion_h = tf.nn.depthwise_conv2d(images, horizontal_filter, [1, 1, 1, 1], "SAME")
    motion_v = tf.nn.depthwise_conv2d(images, vertical_filter, [1, 1, 1, 1], "SAME")
    motion_blur = tf.where(tf.random.uniform([tf.shape(images)[0], 1, 1, 1]) < 0.5, motion_h, motion_v)
    blur = tf.where(tf.random.uniform([tf.shape(images)[0], 1, 1, 1]) < 0.2,
                    motion_blur, gaussian_blur)
    blur_strength = tf.random.uniform([tf.shape(images)[0], 1, 1, 1], 0.05, 0.25)
    blur_mask = tf.random.uniform([tf.shape(images)[0], 1, 1, 1]) < 0.25
    images = tf.where(blur_mask, images * (1 - blur_strength) + blur * blur_strength, images)

    noise_std = tf.random.uniform([tf.shape(images)[0], 1, 1, 1], 1.0, 7.0)
    noise_mask = tf.random.uniform([tf.shape(images)[0], 1, 1, 1]) < 0.25
    noisy = images + tf.random.normal(tf.shape(images)) * noise_std
    images = tf.where(noise_mask, noisy, images)

    def jpeg_variation(image):
        image = tf.cast(tf.clip_by_value(image, 0, 255), tf.uint8)
        return tf.cond(
            tf.random.uniform(()) < 0.2,
            lambda: tf.image.adjust_jpeg_quality(image, tf.random.uniform((), 72, 96, dtype=tf.int32)),
            lambda: image,
        )

    images = tf.map_fn(jpeg_variation, images, fn_output_signature=tf.uint8)
    return tf.cast(images, tf.float32)


def make_dataset(X, y, batch_size, training, augment=None, weights=None):
    n = len(y)

    def gen():
        idx = np.random.permutation(n) if training else np.arange(n)
        for s in range(0, n, batch_size):
            b = np.sort(idx[s:s + batch_size])          # sorted -> sequential memmap reads
            yield np.asarray(X[b]), y[b]

    ds = tf.data.Dataset.from_generator(
        gen, output_signature=(tf.TensorSpec((None, IMG_SIZE, IMG_SIZE, 3), tf.uint8),
                               tf.TensorSpec((None,), tf.int32)))
    if training:
        ds = ds.repeat()          # generator re-runs -> new random order every epoch
    ds = ds.map(lambda a, b: (tf.cast(a, tf.float32), b), num_parallel_calls=tf.data.AUTOTUNE)
    if training and augment is not None:
        ds = ds.map(lambda a, b: (add_camera_artifacts(
            tf.clip_by_value(augment(a, training=True), 0.0, 255.0)), b),
                    num_parallel_calls=tf.data.AUTOTUNE)
    if weights is not None:      # class-balancing as per-sample weights
        wt = tf.constant(weights, tf.float32)
        ds = ds.map(lambda a, b: (a, b, tf.gather(wt, b)))
    return ds.prefetch(2)


def build_model(weights):
    base = tf.keras.applications.MobileNetV2(
        input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights=weights)
    base.trainable = False
    inp = tf.keras.Input((IMG_SIZE, IMG_SIZE, 3), name="raw_pixels_0_255")
    x = layers.Rescaling(1 / 127.5, offset=-1.0, name="scale_to_minus1_1")(inp)   # == mobilenet_v2.preprocess_input
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    out = layers.Dense(len(CLASS_NAMES), activation="softmax", name="disease_probs")(x)
    return tf.keras.Model(inp, out, name="khetsetu_mobilenetv2"), base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ML_DIR / "dataset_split"))
    ap.add_argument("--weights", default="imagenet", help="'imagenet' or path to a *_no_top.h5 file")
    ap.add_argument("--epochs-head", type=int, default=3)
    ap.add_argument("--epochs-finetune", type=int, default=6)
    ap.add_argument("--fine-tune-from", type=int, default=120, help="unfreeze base layers from this index")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--skip-training", action="store_true", help="only calibrate + save the best saved checkpoint (ml/cache/checkpoint_best.keras)")
    ap.add_argument("--out", default=str(ML_DIR.parent / "model"))
    args = ap.parse_args()

    tf.keras.utils.set_random_seed(SEED)
    data, out = Path(args.data), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = ML_DIR / "cache"

    Xtr, ytr, _ = build_cache(data / "train", cache, "train")
    Xva, yva, _ = build_cache(data / "val", cache, "val")
    print(f"train={len(ytr)} val={len(yva)}")

    # --- imbalance handling: balanced class weights from TRAIN only
    counts = np.bincount(ytr, minlength=len(CLASS_NAMES))
    cw = {i: float(len(ytr) / (len(CLASS_NAMES) * c)) for i, c in enumerate(counts)}
    print("class weights:", {CLASS_NAMES[i]: round(w, 2) for i, w in cw.items()})

    augment = tf.keras.Sequential([
        layers.RandomFlip("horizontal"),
        layers.RandomRotation(0.08, fill_mode="reflect"),
        layers.RandomZoom((-0.12, 0.08), fill_mode="reflect"),
        layers.RandomBrightness(0.15, value_range=(0, 255)),
        layers.RandomContrast(0.15),
    ], name="train_only_augmentation")

    train_ds = make_dataset(Xtr, ytr, args.batch_size, True, augment,
                            weights=[cw[i] for i in range(len(CLASS_NAMES))])
    val_ds = make_dataset(Xva, yva, args.batch_size, False)

    model, base = build_model(args.weights)
    ckpt = cache / "checkpoint_best.keras"
    cb = [callbacks.ModelCheckpoint(str(ckpt), monitor="val_accuracy", save_best_only=True, verbose=1),
          callbacks.EarlyStopping(monitor="val_loss", patience=3, restore_best_weights=True),
          callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=1, min_lr=1e-6)]
    hist = {}
    steps = int(np.ceil(len(ytr) / args.batch_size))

    t0 = time.time()
    if args.skip_training:
        print("--skip-training: using saved best checkpoint")
    else:
        print("\n=== Phase 1: head only (base frozen) ===", flush=True)
        model.compile(tf.keras.optimizers.Adam(1e-3), "sparse_categorical_crossentropy", metrics=["accuracy"])
        h1 = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs_head, steps_per_epoch=steps,
                       callbacks=cb, verbose=2)
        hist["phase1"] = {k: [float(v) for v in vs] for k, vs in h1.history.items()}

        print("\n=== Phase 2: fine-tuning last layers of MobileNetV2 ===", flush=True)
        base.trainable = True
        for l in base.layers[:args.fine_tune_from]:
            l.trainable = False
        model.compile(tf.keras.optimizers.Adam(1e-4), "sparse_categorical_crossentropy", metrics=["accuracy"])
        h2 = model.fit(train_ds, validation_data=val_ds, epochs=args.epochs_finetune, steps_per_epoch=steps,
                       callbacks=cb, verbose=2)
        hist["phase2"] = {k: [float(v) for v in vs] for k, vs in h2.history.items()}
    train_minutes = (time.time() - t0) / 60

    # --- restore best (EarlyStopping restores weights only if it triggered) and calibrate on VAL
    if ckpt.exists():
        model = tf.keras.models.load_model(ckpt)
    val_probs = model.predict(make_dataset(Xva, yva, 64, False), verbose=0)
    val_acc = float((val_probs.argmax(1) == yva).mean())
    T = fit_temperature(val_probs, yva)
    print(f"val accuracy={val_acc:.4f}  temperature={T:.3f}")

    model.save(out / "khetsetu.keras")
    meta = {
        "model": "MobileNetV2 (alpha=1.0) transfer learning, ImageNet init",
        "input_size": IMG_SIZE,
        "input_note": "raw RGB pixels 0-255 (scaling to [-1,1] is inside the model)",
        "class_names": CLASS_NAMES,
        "temperature": round(T, 4),
        "recommended_confidence_threshold": 0.70,
        "val_accuracy": round(val_acc, 4),
        "train_images": int(len(ytr)), "val_images": int(len(yva)),
        "class_weights": {CLASS_NAMES[i]: round(w, 3) for i, w in cw.items()},
        "fine_tune_from_layer": args.fine_tune_from,
        "epochs": {"head": args.epochs_head, "finetune": args.epochs_finetune},
        "training_minutes": round(train_minutes, 1),
        "trained_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (out / "model_meta.json").write_text(json.dumps(meta, indent=2))
    (out / "training_history.json").write_text(json.dumps(hist, indent=2))

    print(f"\nSaved model + metadata to {out}")
    print("Next: python evaluation/evaluate.py  then  python training/export_model.py")


if __name__ == "__main__":
    main()
